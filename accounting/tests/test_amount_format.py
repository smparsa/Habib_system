"""مبالغ عددی با جداکنندهٔ هزارگان + تقویم شمسی سررسید چک."""

import json
from decimal import Decimal as D

from django.urls import reverse

from accounting.models import Cheque, JournalEntry

from .test_persons_and_guide import PersonsBaseTestCase


class AmountFormatTests(PersonsBaseTestCase):
    def test_server_accepts_comma_amounts_in_entry(self):
        fy = self._login_accounting()
        cash = fy.accounts.get(code="110101")
        capital = fy.accounts.get(code="3101")
        resp = self.client.post(reverse("accounting:entry_create"), {
            "date": "1405/07/02", "description": "مبالغ کامادار",
            "account_0": str(cash.pk), "person_0": "", "debit_0": "2,500,000", "credit_0": "", "desc_0": "",
            "account_1": str(capital.pk), "person_1": "", "debit_1": "", "credit_1": "۲٬۵۰۰٬۰۰۰", "desc_1": "",
            "action": "post",
        }, follow=True)
        self.assertContains(resp, "با موفقیت ذخیره شد")
        entry = JournalEntry.objects.filter(fiscal_year=fy).order_by("-number").first()
        self.assertEqual(entry.total_debit, D("2500000"))
        self.assertEqual(entry.total_credit, D("2500000"))

    def test_server_accepts_comma_amount_in_cheque(self):
        """مبلغ چکِ کامادار در JSON چک‌های در انتظار هم پذیرفته می‌شود."""
        fy = self._login_accounting()
        resp = self.client.post(reverse("accounting:entry_create"), {
            "date": "1405/07/02", "description": "",
            "pending_cheques": json.dumps([{
                "direction": "received", "number": "555001",
                "amount": "1,200,000", "due": "1405/08/15",
                "person_id": str(self.person_user.pk),
            }]),
            "action": "post",
        }, follow=True)
        self.assertContains(resp, "به سند شماره")
        ch = Cheque.objects.get(fiscal_year=fy, number="555001")
        self.assertEqual(ch.amount, D("1200000"))
        self.assertEqual(ch.entry.total_debit, D("1200000"))

    def test_entry_form_renders_numeric_and_calendar_fields(self):
        self._login_accounting()
        resp = self.client.get(reverse("accounting:entry_create"))
        content = resp.content.decode()
        # فیلدهای عددی با فرمت‌کنندهٔ هزارگان
        self.assertIn("fmtAmount", content)
        self.assertIn('inputmode="numeric"', content)
        self.assertIn('oninput="fmtAmount(this); recalc()"', content)
        self.assertIn('id="ch_amount" name="ch_amount" dir="ltr" inputmode="numeric"', content)
        # تقویم شمسی سررسید چک
        self.assertIn("chDueCalendar", content)
        self.assertIn("chDueToggle", content)
        self.assertIn("makeCalendar", content)
        self.assertIn("inputId: 'ch_due'", content)
        # تقویم تاریخ سند سر جایش است
        self.assertIn("jalaliCalendar", content)
