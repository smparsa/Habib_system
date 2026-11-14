"""جریان جدید چک در فرم سند: چک به‌صورت ردیف به جدول سند اضافه می‌شود.

تا زمان ثبت/ذخیرهٔ سند هیچ چیز ذخیره نمی‌شود؛ در لحظهٔ ثبت سند، چک(ها) + ردیف‌های
دستی کاربر در «یک» سند (با auto_code=cheq) ذخیره/ثبت می‌شوند.
"""

import json
from decimal import Decimal as D

from django.urls import reverse

from accounting.models import Cheque, JournalEntry, TransactionLine

from .test_persons_and_guide import PersonsBaseTestCase


class ChequeInEntryFormTests(PersonsBaseTestCase):
    def _payload(self, direction="received", **overrides):
        ch = {
            "direction": direction,
            "number": "123456",
            "amount": "50000000",
            "due": "1405/08/15",
            "sayad": "1234567890123456",
            "bank": "ملت/شعبه مرکزی",
            "person_id": str(self.person_user.pk),
            "person_name": "علی محمدی",
            "deposit": "",
            "desc": "چک بابت خرید کالا",
        }
        # overrides اول روی مشخصات چک اعمال می‌شوند؛ کلیدهای بیرونی (date/action/...)
        # روی خود payload می‌مانند.
        for k, v in overrides.items():
            if k in ch:
                ch[k] = v
        payload = {
            "date": "1405/07/02",
            "description": "سند با چک",
            "pending_cheques": json.dumps([ch]),
            "action": "post",
        }
        for k, v in overrides.items():
            if k not in ch:
                payload[k] = v
        return payload

    def test_cheque_saved_with_entry_submit(self):
        """مسیر کامل: submit سند → چک + ردیف‌های چک در همان سند."""
        fy = self._login_accounting()
        resp = self.client.post(reverse("accounting:entry_create"), self._payload())
        self.assertEqual(resp.status_code, 302)  # ریدایرکت به لیست اسناد
        # هیچ چک و هیچ سندی ساخته نشده (در مسیر غیر-POST ما عملاً POST کامل بود؛
        # این تست اطمینان می‌دهد که جریان قدیمی «سند فوری» باقی نمانده)
        ch = Cheque.objects.filter(fiscal_year=fy).first()
        self.assertIsNotNone(ch)  # سند submit شد و چک با آن ذخیره شد
        self.assertIsNotNone(ch.entry)

    def test_nothing_saved_without_submit(self):
        """مشخصات چک در فرم (بدون submit) نباید هیچ رکوردی بسازد."""
        fy = self._login_accounting()
        # فقط GET می‌زنیم — هیچ چکی وجود ندارد
        self.client.get(reverse("accounting:entry_create"))
        self.assertFalse(Cheque.objects.filter(fiscal_year=fy).exists())

    def test_cheque_saved_only_on_entry_submit(self):
        """مسیر کامل: submit سند → چک + ردیف‌های چک در همان سند."""
        fy = self._login_accounting()
        resp = self.client.post(
            reverse("accounting:entry_create"), self._payload(), follow=True)
        self.assertContains(resp, "به سند شماره")
        ch = Cheque.objects.get(fiscal_year=fy, number="123456")
        self.assertIsNotNone(ch.entry)
        self.assertEqual(ch.entry.status, JournalEntry.STATUS_POSTED)
        self.assertEqual(ch.entry.auto_code, "cheq")
        self.assertEqual(ch.party_name, "علی محمدی")
        self.assertEqual(ch.bank_name, "ملت")
        self.assertEqual(ch.branch, "شعبه مرکزی")
        codes = {ln.account.code for ln in ch.entry.lines.all()}
        self.assertIn("140101", codes)
        party_line = ch.entry.lines.filter(account__group=6).first()
        self.assertIsNotNone(party_line)
        self.assertEqual(party_line.person_id, self.person_user.pk)
        self.assertEqual(party_line.credit, D("50000000"))

    def test_cheque_plus_manual_rows_single_entry(self):
        """چک + ردیف‌های دستی همزمان در یک سند؛ ردیف‌های فلگ‌دار دوباره شمرده نمی‌شوند."""
        fy = self._login_accounting()
        cash = fy.accounts.get(code="110101")
        capital = fy.accounts.get(code="3101")
        payload = self._payload()
        payload.update({
            # ردیف‌های دستی (بدون فلگ چک): بدهکار صندوق ۵۰M / بستانکار سرمایه ۵۰M
            # (چک خودش بدهکار ۵۰M اسناد دریافتنی / بستانکار ۵۰M حساب شخص می‌سازد)
            "account_0": str(cash.pk), "person_0": "",
            "debit_0": "50000000", "credit_0": "", "desc_0": "واریز نقدی",
            "cheque_row_0": "",
            "account_1": str(capital.pk), "person_1": "",
            "debit_1": "", "credit_1": "50000000", "desc_1": "سرمایه",
            "cheque_row_1": "",
        })
        resp = self.client.post(reverse("accounting:entry_create"), payload, follow=True)
        self.assertContains(resp, "به سند شماره")
        ch = Cheque.objects.get(fiscal_year=fy, number="123456")
        entry = ch.entry
        # ردیف‌ها: ۲ ردیف چک + بدهکار صندوق + بستانکار سرمایه = ۴
        self.assertEqual(entry.lines.count(), 4)
        self.assertEqual(entry.total_debit, D("100000000"))
        self.assertEqual(entry.total_credit, D("100000000"))
        cash_line = entry.lines.filter(account=cash).first()
        self.assertIsNotNone(cash_line)
        self.assertEqual(cash_line.debit, D("50000000"))

    def test_paid_cheque_flow(self):
        fy = self._login_accounting()
        self.client.post(
            reverse("accounting:entry_create"),
            self._payload(direction="paid", description="سند چک پرداختی"), follow=True)
        ch = Cheque.objects.get(fiscal_year=fy, number="123456")
        codes = {ln.account.code for ln in ch.entry.lines.all()}
        self.assertIn("230101", codes)  # اسناد پرداختنی بستانکار
        party_line = ch.entry.lines.filter(account__group=6).first()
        self.assertEqual(party_line.person_id, self.person_user.pk)
        self.assertEqual(party_line.debit, D("50000000"))

    def test_cheque_without_person_is_rejected(self):
        fy = self._login_accounting()
        resp = self.client.post(
            reverse("accounting:entry_create"),
            self._payload(person_id="", person_name=""), follow=True)
        self.assertContains(resp, "صاحب چک را از فهرست اشخاص انتخاب کنید")
        self.assertFalse(Cheque.objects.filter(fiscal_year=fy).exists())

    def test_pending_cheques_repainted_after_error(self):
        """پس از خطا، چک‌های در انتظار در بازپرکردن فرم برمی‌گردند."""
        fy = self._login_accounting()
        resp = self.client.post(
            reverse("accounting:entry_create"),
            self._payload(person_id="", person_name=""))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("formData", content)
        self.assertIn("123456", content)  # مشخصات چک در فرم بازگشته
        self.assertFalse(Cheque.objects.filter(fiscal_year=fy).exists())

    def test_cheques_page_no_longer_has_entry_form(self):
        self._login_accounting()
        resp = self.client.get(reverse("accounting:cheques"))
        content = resp.content.decode()
        # فرم ثبت چک دیگر در صفحهٔ گزارش نیست؛ راهنمای ارجاع به فرم سند هست
        self.assertNotIn("action=\"/accounting/cheques/new/\"", content)
        self.assertIn("فرم سند جدید ← پنل «ثبت چک»", content)
        self.assertIn("#chequePanel", content)


class EntryNavigationTests(PersonsBaseTestCase):
    def _make_entry(self, fy, desc, post=True):
        from accounting import services
        cash = fy.accounts.get(code="110101")
        capital = fy.accounts.get(code="3101")
        return services.create_journal_entry(
            fy,
            [
                {"account": cash, "debit": D("1000"), "credit": D("0"), "description": ""},
                {"account": capital, "debit": D("0"), "credit": D("1000"), "description": ""},
            ],
            description=desc, post=post,
        )

    def test_nav_links_render(self):
        fy = self._login_accounting()
        self._make_entry(fy, "سند اول")
        resp = self.client.get(reverse("accounting:entry_create"))
        content = resp.content.decode()
        self.assertIn("سند قبلی", content)
        self.assertIn("سند بعدی", content)
        self.assertIn("آخرین سند", content)
        self.assertIn("انتخاب سریع سند", content)
        # سند جدید: «قبلی» غیرفعال است (سندی قبل از شمارهٔ بعدی نیست... در واقع هست)
        self.assertIn("entries/", content)

    def test_edit_draft_via_nav(self):
        fy = self._login_accounting()
        e1 = self._make_entry(fy, "سند اول", post=False)
        e2 = self._make_entry(fy, "سند دوم", post=False)
        # از سند دوم به سند اول برو (ویرایش پیش‌نویس)
        resp = self.client.get(reverse("accounting:entry_create") + f"?edit={e1.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ویرایش سند")
        content = resp.content.decode()
        # دکمهٔ «سند بعدی» باید به سند دوم برود
        self.assertIn(f"edit={e2.pk}", content)
        # دکمهٔ «سند قبلی» باید غیرفعال باشد (سند اول اولین سند است)
        self.assertIn("aria-disabled", content)

    def test_posted_entry_not_editable_via_get(self):
        fy = self._login_accounting()
        e1 = self._make_entry(fy, "سند ثبت‌شده", post=True)
        resp = self.client.get(reverse("accounting:entry_create") + f"?edit={e1.pk}", follow=True)
        # ریدایرکت به سند جدید با پیام خطا
        self.assertContains(resp, "فقط سند پیش‌نویس قابل ویرایش است")
