"""تست‌های گردش کار کیف پول: خطای درون-فریمی، ماژول‌های زیر فیلد تعداد سکه،
جست‌وجوی زندهٔ کد ملی، تأیید دوم انتقال، تیکت‌های پرداخت/دریافت و فیلتر
«تراکنش‌های اخیر» داشبورد (فقط خرید/فروش/انتقال سکه).
"""

from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from tickets.models import Ticket
from wallet.models import CoinLedger, CoinOrder, WalletSetting
from wallet.services import transfer_coins


class WalletFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(mobile_number="09120000920")
        cls.staff = User.objects.create_user(mobile_number="09120000921", is_staff=True)
        setting = WalletSetting.get()
        setting.receiving_card_number = "6037997512345678"
        setting.receiving_iban = "IR123456789012345678901234"
        setting.min_buy_coins = Decimal("10")
        setting.max_buy_coins = Decimal("100000")
        setting.save()

    @staticmethod
    def _fund(user, coins):
        """شارژ مستقیم کیف پول برای تست (دفتر کل با نوع buy)."""
        from wallet.services import _apply

        ref = CoinOrder.objects.create(
            code=f"WAL-T-{user.id}-{coins}", user=user, kind=CoinOrder.KIND_BUY,
            coins=coins, unit_price_rial=Decimal("1000"),
            total_rial=coins * Decimal("1000"), status=CoinOrder.STATUS_APPROVED,
        )
        _apply(user, coins, CoinLedger.KIND_BUY, ref_code=ref.code)

    def _make_receiver(self, nid="0079012841"):
        """گیرندهٔ تستی با کد ملی معتبر (checksum صحیح)."""
        r = User.objects.create_user(mobile_number="09120000924")
        r.profile.national_id = nid
        r.profile.save(update_fields=["national_id"])
        return r

    # ------------------------------------------------------------------ #
    # ۱) ماژول «اطلاعات سفارش و حساب مقصد» زیر فیلد تعداد سکه (فریم خرید)
    # ------------------------------------------------------------------ #
    def test_buy_frame_contains_destination_account_module(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("wallet:dashboard"))
        self.assertContains(resp, "اطلاعات سفارش و حساب مقصد")
        self.assertContains(resp, "wallet-dest-info")
        self.assertContains(resp, "6037997512345678")
        self.assertContains(resp, "IR123456789012345678901234")
        # جعبه در ابتدا پنهان است و با تکمیل تعداد سکه نمایش داده می‌شود
        self.assertContains(resp, "id='wallet-dest-info'")

    def test_buy_redirects_to_card_payment_page(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("wallet:dashboard"), {"action": "buy", "coins": "20"}
        )
        self.assertEqual(resp.status_code, 302)
        order = CoinOrder.objects.get(user=self.user, kind=CoinOrder.KIND_BUY)
        self.assertRegex(resp["Location"], rf"/wallet/buy/{order.code}/payment/")
        # سفارش با نرخِ لحظهٔ ثبت ساخته شد
        self.assertEqual(order.coins, Decimal("20"))
        self.assertEqual(order.total_rial, Decimal("20000"))

    # ------------------------------------------------------------------ #
    # ۲) خطای خرید درون فریم خرید + فوکوس فیلد
    # ------------------------------------------------------------------ #
    def test_buy_minimum_error_shown_in_buy_frame_with_focus(self):
        self.client.force_login(self.user)
        resp = self.client.get(
            reverse("wallet:dashboard"),
            {
                "wallet_action": "buy",
                "wallet_field": "coins",
                "wallet_err": "حداقل خرید 10 سکه است.",
            },
        )
        self.assertContains(resp, "حداقل خرید 10 سکه است.")
        # خطا داخل فریم خرید است (data-wallet-frame='buy' قبل از خطا می‌آید)
        html = resp.content.decode("utf-8")
        frame_pos = html.find("data-wallet-frame='buy'")
        err_pos = html.find("حداقل خرید 10 سکه است.")
        self.assertGreater(err_pos, frame_pos)
        # هندلر JS (فوکوس/اسکرول) در app.js تعریف شده است
        from django.contrib.staticfiles import finders

        with open(finders.find("core/js/app.js"), encoding="utf-8") as fh:
            self.assertIn("initWalletPage", fh.read())

    def test_buy_minimum_error_renders_field_error_via_form(self):
        """خطای سرویس روی فیلد coins در فرم رندر می‌شود (بدون پارامتر URL هم)."""
        from wallet.forms import BuyForm

        form = BuyForm(data={"coins": "5"})
        # حداقل در سطح سرویس (با پیام فارسی) سنجیده می‌شود، نه در فرم؛
        # فرم فقط min/max مرورگر را از تنظیمات تزریق می‌کند.
        self.assertTrue(form.is_valid())
        # حداقل در سطح فیلد از تنظیمات تزریق شده است (min مرورگر هم در رندر می‌آید)
        self.assertEqual(form.fields["coins"].min_value, Decimal("10"))
        # پیام خطای حداقل، فارسی و مطابق سرویس است
        self.assertEqual(
            form.fields["coins"].error_messages["min_value"],
            "حداقل خرید 10 سکه است.",
        )
        # خطای سرویس به فیلد منتقل می‌شود تا درون فریم رندر شود
        form.add_error(None, "حداقل خرید 10 سکه است.")
        self.assertIn("coins", form.errors)
        self.assertEqual(form.errors["coins"][0], "حداقل خرید 10 سکه است.")

    # ------------------------------------------------------------------ #
    # ۳) ماژول «اطلاعات سفارش بر حسب ریال» + تیکت ادمین برای فروش
    # ------------------------------------------------------------------ #
    def test_sell_frame_contains_rial_order_module(self):
        u = User.objects.create_user(mobile_number="09120000922")
        u.profile.iban = "IR123456789012345678901234"
        u.profile.save(update_fields=["iban"])
        self.client.force_login(u)
        resp = self.client.get(reverse("wallet:dashboard"))
        self.assertContains(resp, "اطلاعات سفارش بر حسب ریال")
        self.assertContains(resp, "wallet-rial-info")

    def test_sell_request_sends_admin_ticket_and_reserved_coins(self):
        u = User.objects.create_user(mobile_number="09120000923")
        u.profile.iban = "IR123456789012345678901234"
        u.profile.save(update_fields=["iban"])
        self._fund(u, Decimal("30"))

        self.client.force_login(u)
        # مرحلهٔ ۱: ثبت «قصد فروش» → به صفحهٔ تأیید دومرحله‌ای هدایت می‌شود؛
        # هنوز هیچ سفارشی ثبت و سکه‌ای رزرو نشده است.
        resp = self.client.post(
            reverse("wallet:dashboard"), {"action": "sell", "coins": "10"}, follow=True
        )
        self.assertContains(resp, "تأیید فروش سکه")
        self.assertContains(resp, "تأیید مرحلهٔ اول")
        self.assertEqual(
            CoinOrder.objects.filter(user=u, kind=CoinOrder.KIND_SELL).count(), 0
        )
        u.wallet.refresh_from_db()
        self.assertEqual(u.wallet.balance, Decimal("30"))
        self.assertFalse(
            Ticket.objects.filter(subject__startswith="درخواست فروش سکه").exists()
        )

        # مرحلهٔ ۲: تأیید اول → دکمهٔ تأیید نهایی ظاهر می‌شود (هنوز اجرا نشده)
        resp = self.client.post(
            reverse("wallet:sell_confirm"), {"confirm1": "1"}, follow=True
        )
        self.assertContains(resp, "تأیید نهایی و ثبت درخواست فروش")
        self.assertEqual(
            CoinOrder.objects.filter(user=u, kind=CoinOrder.KIND_SELL).count(), 0
        )

        # مرحلهٔ ۳: تأیید دوم → سفارش ثبت، سکه رزرو و تیکت به مدیر ارسال می‌شود
        resp = self.client.post(
            reverse("wallet:sell_confirm"), {"confirm2": "1"}, follow=True
        )
        self.assertContains(resp, "تیکت درخواست فروش برای مدیر ارسال گردید")
        self.assertTrue(
            Ticket.objects.filter(subject__startswith="درخواست فروش سکه").exists()
        )
        # سکه رزرو شد (کسر از موجودی)
        u.wallet.refresh_from_db()
        self.assertEqual(u.wallet.balance, Decimal("20"))

    def test_sell_confirm_cancel_discards_intent(self):
        """انصراف در صفحهٔ تأیید، قصد فروش را بدون رزرو سکه از بین می‌برد."""
        u = User.objects.create_user(mobile_number="09120000924")
        u.profile.iban = "IR123456789012345678901234"
        u.profile.save(update_fields=["iban"])
        self._fund(u, Decimal("30"))
        self.client.force_login(u)
        self.client.post(
            reverse("wallet:dashboard"), {"action": "sell", "coins": "10"}, follow=True
        )
        resp = self.client.post(
            reverse("wallet:sell_confirm"), {"cancel": "1"}, follow=True
        )
        self.assertContains(resp, "درخواست فروش لغو شد")
        u.wallet.refresh_from_db()
        self.assertEqual(u.wallet.balance, Decimal("30"))
        # قصد فروش حذف شده: GET بدون intent به داشبورد برمی‌گردد
        resp = self.client.get(reverse("wallet:sell_confirm"), follow=True)
        self.assertContains(resp, "هیچ درخواست فروشِ در انتظار تأییدی وجود ندارد")

    def test_sell_error_shown_in_sell_frame(self):
        u = User.objects.create_user(mobile_number="09120000925")
        u.profile.iban = "IR123456789012345678901234"
        u.profile.save(update_fields=["iban"])
        self._fund(u, Decimal("5"))
        self.client.force_login(u)
        resp = self.client.post(
            reverse("wallet:dashboard"), {"action": "sell", "coins": "50"},
            follow=True,
        )
        html = resp.content.decode("utf-8")
        frame_pos = html.find("data-wallet-frame='sell'")
        err_pos = html.find("حداکثر فروش 100000 سکه است")
        # خطای موجودی ناکافی در فریم فروش و زیر فیلد تعداد سکه رندر می‌شود
        self.assertGreater(frame_pos, -1)
        err_pos = html.find("موجودی سکه کافی نیست")
        self.assertGreater(err_pos, frame_pos)

    # ------------------------------------------------------------------ #
    # ۴) انتقال: جست‌وجوی زنده + تأیید دوم + تیکت دریافت/پرداخت دو طرف
    # ------------------------------------------------------------------ #
    def test_receiver_lookup_api_returns_name(self):
        self._make_receiver()
        self.client.force_login(self.user)
        resp = self.client.get(
            reverse("wallet:receiver_lookup"), {"national_id": "0079012841"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["found"])
        self.assertTrue(data["full_name"])
        self.assertEqual(data["national_id"], "0079012841")

    def test_receiver_lookup_api_not_found(self):
        self.client.force_login(self.user)
        resp = self.client.get(
            reverse("wallet:receiver_lookup"), {"national_id": "0079012842"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["found"])

    def test_receiver_lookup_prefix_query_lists_matching_nids(self):
        """فهرست آبشاری (Query): پیشوند کد ملی → کد ملی + نام کاربران متناظر."""
        self._make_receiver()
        r2 = User.objects.create_user(mobile_number="09120000926")
        r2.profile.national_id = "0079012842"
        r2.profile.save(update_fields=["national_id"])
        self.client.force_login(self.user)
        resp = self.client.get(reverse("wallet:receiver_lookup"), {"q": "0079"})
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        nids = {r["national_id"] for r in results}
        self.assertIn("0079012841", nids)
        self.assertIn("0079012842", nids)
        self.assertTrue(all(r["full_name"] for r in results))

    def test_receiver_lookup_prefix_query_minimum_length_and_digits(self):
        """پیشوند کمتر از ۴ رقم یا غیرعددی، فهرست خالی برمی‌گرداند."""
        self._make_receiver()
        self.client.force_login(self.user)
        resp = self.client.get(reverse("wallet:receiver_lookup"), {"q": "007"})
        self.assertEqual(resp.json()["results"], [])
        # ارقام فارسی نرمال می‌شوند (۰۰۷۹ → 0079)
        resp = self.client.get(
            reverse("wallet:receiver_lookup"), {"q": "۰۰۷۹۰۱۲۸۴۱"}
        )
        results = resp.json()["results"]
        self.assertTrue(
            any(r["national_id"] == "0079012841" for r in results)
        )

    def test_coin_image_url_endpoint(self):
        """اندپوینت تصویر سکه برای اورلی «لطفاً منتظر بمانید» بدون فایل، url خالی می‌دهد."""
        self.client.force_login(self.user)
        resp = self.client.get(reverse("wallet:coin_image_url"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["url"], "")

    def test_transfer_two_confirmations_then_executes(self):
        receiver = self._make_receiver()
        self._fund(self.user, Decimal("50"))

        self.client.force_login(self.user)
        # مرحلهٔ ۱: ثبت قصد انتقال
        resp = self.client.post(
            reverse("wallet:dashboard"),
            {"action": "transfer", "receiver_national_id": "0079012841", "coins": "15"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("transfer/confirm", resp["Location"])

        # صفحهٔ تأیید: خلاصه + نام گیرنده + دکمهٔ تأیید مرحلهٔ اول
        resp = self.client.get(reverse("wallet:transfer_confirm"))
        self.assertContains(resp, "تأیید مرحلهٔ اول")
        self.assertContains(resp, "کد ملی گیرنده")
        self.assertNotContains(resp, "تأیید نهایی و انتقال سکه")

        # POST بدون confirm1: هنوز اجرا نمی‌شود
        self.client.post(reverse("wallet:transfer_confirm"), {})
        from wallet.services import get_wallet

        self.assertEqual(get_wallet(receiver).balance, Decimal("0"))

        # تأیید اول → حالا دکمهٔ تأیید نهایی
        resp = self.client.post(
            reverse("wallet:transfer_confirm"), {"confirm1": "1"}
        )
        self.assertContains(resp, "تأیید نهایی و انتقال سکه")

        # تأیید دوم → اجرای انتقال
        resp = self.client.post(
            reverse("wallet:transfer_confirm"), {"confirm2": "1"}, follow=True
        )
        self.assertContains(resp, "منتقل شد")
        from wallet.services import get_wallet

        receiver.wallet.refresh_from_db()
        self.user.wallet.refresh_from_db()
        self.assertEqual(receiver.wallet.balance, Decimal("15"))
        self.assertEqual(self.user.wallet.balance, Decimal("35"))
        # دیتابیس انتقال ثبت شد
        transfer = self.user.sent_transfers.get()
        self.assertEqual(transfer.receiver, receiver)
        self.assertEqual(transfer.coins, Decimal("15"))

    def test_transfer_sends_pay_and_receive_tickets_to_both_sides(self):
        receiver = self._make_receiver()
        self._fund(self.user, Decimal("20"))
        transfer_coins(self.user, receiver, Decimal("7"), request=None)
        # تیکت پرداخت برای فرستنده
        pay_ticket = Ticket.objects.filter(subject__startswith="پرداخت سکه — ").first()
        self.assertIsNotNone(pay_ticket)
        self.assertTrue(pay_ticket.recipients.filter(user=self.user).exists())
        # تیکت دریافت برای گیرنده
        recv_ticket = Ticket.objects.filter(subject__startswith="دریافت سکه — ").first()
        self.assertIsNotNone(recv_ticket)
        self.assertTrue(recv_ticket.recipients.filter(user=receiver).exists())
        # گیرنده در تیکت «پرداخت» نیست و فرستنده در تیکت «دریافت» فقط به‌عنوان نویسنده است
        self.assertFalse(pay_ticket.recipients.filter(user=receiver).exists())
        self.assertTrue(
            recv_ticket.recipients.filter(user=self.user, is_author=True).exists()
        )
        # موجودی هر دو طرف آپدیت شد
        self.user.wallet.refresh_from_db()
        receiver.wallet.refresh_from_db()
        self.assertEqual(self.user.wallet.balance, Decimal("13"))
        self.assertEqual(receiver.wallet.balance, Decimal("7"))

    def test_transfer_accepts_10_digit_nid_without_checksum(self):
        # کدهای ملی ثبت‌شده در سیستم ممکن است رقم کنترل استاندارد نداشته باشند
        # (ثبت‌نام فقط ۱۰ رقم می‌خواهد)؛ فرم انتقال هم نباید سخت‌گیرتر از
        # ثبت‌نام باشد و چنین گیرنده‌ای را رد کند (مثل 0054413063).
        receiver = self._make_receiver(nid="0054413063")
        self._fund(self.user, Decimal("30"))

        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("wallet:dashboard"),
            {"action": "transfer", "receiver_national_id": "0054413063", "coins": "10"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("transfer/confirm", resp["Location"])

        resp = self.client.post(reverse("wallet:transfer_confirm"), {"confirm1": "1"})
        resp = self.client.post(
            reverse("wallet:transfer_confirm"), {"confirm2": "1"}, follow=True
        )
        self.assertContains(resp, "منتقل شد")
        receiver.wallet.refresh_from_db()
        self.user.wallet.refresh_from_db()
        self.assertEqual(receiver.wallet.balance, Decimal("10"))
        self.assertEqual(self.user.wallet.balance, Decimal("20"))

    def test_transfer_without_receiver_name_blocked_by_two_step_flow(self):
        # بدون گیرندهٔ معتبر، مرحلهٔ تأیید باز نمی‌شود
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("wallet:dashboard"),
            {"action": "transfer", "receiver_national_id": "4567891236", "coins": "5"},
            follow=True,
        )
        self.assertContains(resp, "کاربری با این کد ملی در سیستم یافت نشد")
        self.assertFalse(self.user.sent_transfers.exists())

    # ------------------------------------------------------------------ #
    # ۵) «تراکنش‌های اخیر» فقط خرید/فروش/انتقال سکه — بدون امتیاز
    # ------------------------------------------------------------------ #
    def test_recent_transactions_excludes_rewards(self):
        from wallet.services import reward_coins

        self._fund(self.user, Decimal("20"))
        reward_coins(self.user, Decimal("5"), ref_code="REF1", note="پاداش معرفی")

        self.client.force_login(self.user)
        resp = self.client.get(reverse("wallet:dashboard"))
        html = resp.content.decode("utf-8")
        section = html[html.find("تراکنش‌های اخیر"):]
        section = section[: section.find("</table>")]
        # خرید سکه در بخش اخیر هست
        self.assertIn("خرید سکه", section)
        # پاداش (امتیاز) در بخش اخیر نیست
        self.assertNotIn("پاداش (امتیاز)", section)
        self.assertNotIn("REF1", section)

    def test_dashboard_ledger_kind_list(self):
        from wallet.views import DASHBOARD_LEDGER_KINDS

        self.assertIn(CoinLedger.KIND_BUY, DASHBOARD_LEDGER_KINDS)
        self.assertIn(CoinLedger.KIND_SELL, DASHBOARD_LEDGER_KINDS)
        self.assertIn(CoinLedger.KIND_TRANSFER_OUT, DASHBOARD_LEDGER_KINDS)
        self.assertIn(CoinLedger.KIND_TRANSFER_IN, DASHBOARD_LEDGER_KINDS)
        self.assertNotIn(CoinLedger.KIND_REWARD, DASHBOARD_LEDGER_KINDS)
        self.assertNotIn(CoinLedger.KIND_CHARGE, DASHBOARD_LEDGER_KINDS)
        self.assertNotIn(CoinLedger.KIND_ADJUST, DASHBOARD_LEDGER_KINDS)
