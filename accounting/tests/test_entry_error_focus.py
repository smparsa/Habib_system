"""فوکوس خودکار فیلد مقصر پس از خطای ثبت سند/چک — کاربر همان فیلد را اصلاح می‌کند."""

import json

from django.urls import reverse

from .test_persons_and_guide import PersonsBaseTestCase


class EntryErrorFocusTests(PersonsBaseTestCase):
    def test_zero_amount_error_focuses_row_field(self):
        fy = self._login_accounting()
        cash = fy.accounts.get(code="110101")
        # ردیف ۱ با حساب ولی مبلغ صفرِ صریح → خطای مبلغ + فوکوس فیلد مبلغ ردیف ۱
        resp = self.client.post(reverse("accounting:entry_create"), {
            "date": "1405/07/02",
            "description": "تست فوکوس",
            "account_0": str(cash.pk), "person_0": "", "debit_0": "0", "credit_0": "0", "desc_0": "",
            "action": "post",
        })
        # خطای مبلغ صفر ردیف ۱ + شناسهٔ فیلد مقصر برای JS
        self.assertContains(resp, "مبلغ صفر مجاز نیست")
        content = resp.content.decode()
        self.assertIn("errorFocusData", content)
        # هدف فوکوس: ردیف ۱، فیلد مبلغ
        self.assertIn('"row": 1', content)
        self.assertIn('"field": "debit"', content)

    def test_error_keeps_typed_values_for_fixing(self):
        fy = self._login_accounting()
        cash = fy.accounts.get(code="110101")
        # ردیف ۰ سالم، ردیف ۱ بدون مبلغ → خطا؛ اما مقادیر ردیف ۰ باید بماند
        resp = self.client.post(reverse("accounting:entry_create"), {
            "date": "1405/07/02",
            "description": "حفظ مقادیر",
            "account_0": str(cash.pk), "person_0": "", "debit_0": "5000", "credit_0": "", "desc_0": "دریافت",
            "account_1": "", "person_1": "", "debit_1": "", "credit_1": "", "desc_1": "",
            "action": "post",
        })
        content = resp.content.decode()
        self.assertIn("formData", content)
        # مقدار ردیف سالم در JSON بازپرکردن حفظ شده
        self.assertIn("5000", content)
        self.assertIn("دریافت", content)

    def test_cheque_error_focuses_cheque_field(self):
        self._login_accounting()
        # چکِ در انتظار بدون صاحب چک → خطا + فوکوس روی ch_person پنل چک
        resp = self.client.post(reverse("accounting:entry_create"), {
            "date": "1405/07/02", "description": "",
            "pending_cheques": json.dumps([{
                "direction": "received", "number": "999888",
                "amount": "1000", "due": "1405/08/15",
                "person_id": "", "person_name": "",
            }]),
            "action": "post",
        })
        self.assertContains(resp, "صاحب چک را از فهرست اشخاص انتخاب کنید")
        content = resp.content.decode()
        # دادهٔ فوکوس باید فیلد ch_person پنل چک را هدف بگیرد
        self.assertIn('"panel": "cheque"', content)
        self.assertIn('"field": "ch_person"', content)
        # مقادیر تایپ‌شدهٔ چک برای بازپرکردن فرم حفظ شود
        self.assertIn("999888", content)

    def test_bad_date_focuses_date_field(self):
        self._login_accounting()
        resp = self.client.post(reverse("accounting:entry_create"), {
            "date": "نامعتبر", "description": "",
            "account_0": "", "debit_0": "", "credit_0": "",
            "action": "post",
        })
        self.assertContains(resp, "تاریخ سند نامعتبر است")
        content = resp.content.decode()
        self.assertIn("id_date", content)

    def test_balance_error_still_shows_message(self):
        fy = self._login_accounting()
        cash = fy.accounts.get(code="110101")
        capital = fy.accounts.get(code="3101")
        resp = self.client.post(reverse("accounting:entry_create"), {
            "date": "1405/07/02", "description": "ناتراز",
            "account_0": str(cash.pk), "person_0": "", "debit_0": "1000", "credit_0": "", "desc_0": "",
            "account_1": str(capital.pk), "person_1": "", "debit_1": "", "credit_1": "700", "desc_1": "",
            "action": "post",
        })
        self.assertContains(resp, "سند تراز نیست")
        self.assertContains(resp, "errorFocusData")
