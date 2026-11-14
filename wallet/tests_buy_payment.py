"""تست‌های صفحهٔ پرداخت خرید سکه (نمایش حساب + بارگذاری فیش واریز).

گردش کار: ثبت سفارش خرید → هدایت به صفحهٔ پرداخت (مبلغ/کارت/کپی) →
بارگذاری فیش واریز → تیکت درخواست خرید (با پیوست فیش) به مدیران.
"""

from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from tickets.models import Ticket, TicketAttachment
from wallet.models import CoinLedger, CoinOrder, WalletSetting
from wallet.services import create_buy_order


class BuyPaymentFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(mobile_number="09120000910")
        cls.staff = User.objects.create_user(mobile_number="09120000911", is_staff=True)
        setting = WalletSetting.get()
        setting.receiving_card_number = "6037997512345678"
        setting.receiving_iban = "IR123456789012345678901234"
        setting.save(update_fields=["receiving_card_number", "receiving_iban"])

    def _png(self, name="receipt.png"):
        # PNG یک‌بیکسلی معتبر (امضای فایل + IHDR + IEND)
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000d4944415478da63fcffff3f030005fe02fea72d3e4c0000000049454e44ae426082"
        )
        return SimpleUploadedFile(name, png, content_type="image/png")

    def _create_order(self):
        return create_buy_order(
            self.user, Decimal("5"), request=None, notify=False
        )

    def test_buy_redirects_to_payment_page(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("wallet:dashboard"), {
            "action": "buy", "coins": "5",
        })
        self.assertEqual(resp.status_code, 302)
        order = CoinOrder.objects.get(user=self.user)
        self.assertRegex(resp["Location"], rf"/wallet/buy/{order.code}/payment/")

    def test_payment_page_shows_amount_and_card(self):
        order = self._create_order()
        self.client.force_login(self.user)
        resp = self.client.get(reverse("wallet:buy_payment", args=[order.code]))
        self.assertContains(resp, "مبلغ قابل پرداخت")
        self.assertContains(resp, order.code)
        # شماره کارت به‌صورت گروه‌های ۴ رقمی
        for group in ("6037", "9975", "1234", "5678"):
            self.assertContains(resp, group)
        self.assertContains(resp, "کپی شماره کارت")

    def test_payment_page_only_for_owner(self):
        order = self._create_order()
        other = User.objects.create_user(mobile_number="09120000912")
        self.client.force_login(other)
        resp = self.client.get(reverse("wallet:buy_payment", args=[order.code]))
        self.assertEqual(resp.status_code, 404)

    def test_receipt_upload_creates_ticket_with_attachment(self):
        order = self._create_order()
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("wallet:buy_payment", args=[order.code]),
            {"receipt": self._png()},
            follow=True,
        )
        self.assertContains(resp, "برای بررسی به مدیر ارسال گردید")
        order.refresh_from_db()
        self.assertTrue(order.payment_receipt)
        self.assertIsNotNone(order.receipt_uploaded_at)
        # تیکت درخواست خرید ساخته شد و فیش به آن پیوست شده است
        ticket = Ticket.objects.get(
            subject=f"درخواست خرید سکه — {order.code}"
        )
        body = ticket.messages.order_by("-id").first()
        self.assertTrue(
            TicketAttachment.objects.filter(message=body, name__iendswith=".png").exists()
        )
        # گیرندگان شامل کارکنان (مدیر سایت) هستند
        self.assertTrue(ticket.recipients.filter(user=self.staff).exists())

    def test_receipt_upload_records_buy_request_ledger_once(self):
        """«تراکنش‌های اخیر»: لحظهٔ کامل‌شدن «کارت‌به‌کارت + ارسال رسید/تیکت» ثبت می‌شود.

        رکورد دفتر با نوع buy_request، مبلغ صفر (بدون تغییر موجودی) و فقط
        یک‌بار (بارگذاری مجدد فیش رکورد تکراری نمی‌سازد).
        """
        order = self._create_order()
        # پیش از ارسال فیش، رکورد buy_request وجود ندارد
        self.assertEqual(
            CoinLedger.objects.filter(
                user=self.user, kind=CoinLedger.KIND_BUY_REQUEST
            ).count(),
            0,
        )
        self.client.force_login(self.user)
        self.client.post(
            reverse("wallet:buy_payment", args=[order.code]),
            {"receipt": self._png()},
            follow=True,
        )
        rows = CoinLedger.objects.filter(
            user=self.user, kind=CoinLedger.KIND_BUY_REQUEST
        )
        self.assertEqual(rows.count(), 1)
        row = rows.first()
        self.assertEqual(row.amount, Decimal("0"))
        self.assertEqual(row.ref_code, order.code)
        # موجودی تغییر نکرده است (رکورد فقط رویداد است)
        self.user.wallet.refresh_from_db()
        self.assertEqual(self.user.wallet.balance, Decimal("0"))
        # بارگذاری مجدد مسدود است؛ رکورد تکراری هم ساخته نمی‌شود
        from wallet.services import submit_buy_receipt

        with self.assertRaises(Exception):
            submit_buy_receipt(order, self._png("again.png"))
        self.assertEqual(rows.count(), 1)
        # این نوع در «تراکنش‌های اخیر» داشبورد نمایش داده می‌شود
        resp = self.client.get(reverse("wallet:dashboard"))
        self.assertContains(resp, "ارسال فیش واریز")

    def test_receipt_cannot_be_uploaded_twice(self):
        order = self._create_order()
        submit_buy_receipt = __import__(
            "wallet.services", fromlist=["submit_buy_receipt"]
        ).submit_buy_receipt
        submit_buy_receipt(order, self._png("a.png"))
        with self.assertRaises(Exception):
            submit_buy_receipt(order, self._png("b.png"))

    def test_invalid_file_rejected(self):
        order = self._create_order()
        self.client.force_login(self.user)
        bad = SimpleUploadedFile("receipt.exe", b"MZ...", content_type="application/x-msdownload")
        resp = self.client.post(
            reverse("wallet:buy_payment", args=[order.code]),
            {"receipt": bad},
            follow=True,
        )
        self.assertContains(resp, "فقط تصویر فیش")
        order.refresh_from_db()
        self.assertFalse(order.payment_receipt)

    def test_dashboard_shows_pending_payment_banner(self):
        self._create_order()
        self.client.force_login(self.user)
        resp = self.client.get(reverse("wallet:dashboard"))
        self.assertContains(resp, "پرداخت و ارسال فیش")

    def test_cancel_keeps_order_pending(self):
        order = self._create_order()
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("wallet:buy_payment", args=[order.code]),
            {"cancel": "1"}, follow=True,
        )
        self.assertContains(resp, "ناتمام ماند")
        order.refresh_from_db()
        self.assertEqual(order.status, CoinOrder.STATUS_PENDING)
        self.assertFalse(order.payment_receipt)
