"""قابلیت‌های چک: هشدار نزدیک سررسید داشبورد، ستون صاحب چک، حساب وصول."""

from datetime import date, timedelta

from decimal import Decimal as D

from django.urls import reverse

from accounting import services
from accounting.models import Account, Cheque, JournalEntry

from .test_persons_and_guide import PersonsBaseTestCase


class ChequeFeaturesTests(PersonsBaseTestCase):
    def _fy(self):
        return self._login_accounting()

    def test_upcoming_cheques_in_dashboard(self):
        fy = self._fy()
        today = date.today()
        # چک نزدیک سررسید (۳ روز دیگر)
        services.create_cheque(fy, Cheque.DIR_RECEIVED, "N1", D("1000"), today + timedelta(days=3),
                               party_name="شرکت الف")
        # چک معوقه (۲ روز گذشته)
        services.create_cheque(fy, Cheque.DIR_PAID, "N2", D("2000"), today - timedelta(days=2),
                               party_name="شرکت ب")
        # چک دور (۳۰ روز دیگر) — نباید بیاید
        services.create_cheque(fy, Cheque.DIR_RECEIVED, "N3", D("4000"), today + timedelta(days=30),
                               party_name="شرکت ج")

        items = services.upcoming_cheques(fy, days=10)
        nums = {it["cheque"].number for it in items}
        self.assertIn("N1", nums)
        self.assertIn("N2", nums)
        self.assertNotIn("N3", nums)
        by_num = {it["cheque"].number: it for it in items}
        self.assertEqual(by_num["N2"]["urgency"], "overdue")
        self.assertEqual(by_num["N1"]["urgency"], "soon")

        resp = self.client.get(reverse("accounting:dashboard"))
        content = resp.content.decode()
        self.assertIn("هشدار چک‌های نزدیک سررسید", content)
        self.assertIn("معوقه", content)

    def test_cheques_list_owner_column_links_person_ledger(self):
        fy = self._fy()
        services.create_cheque(fy, Cheque.DIR_RECEIVED, "OWN1", D("5000"),
                               date(2026, 10, 1), party_name="علی محمدی",
                               person=self.person_user)
        resp = self.client.get(reverse("accounting:cheques"))
        content = resp.content.decode()
        self.assertIn("صاحب چک", content)
        self.assertIn(f'href="{reverse("accounting:person_ledger", args=[self.person_user.pk])}"', content)
        self.assertIn("علی محمدی", content)

    def test_received_cheque_with_deposit_account_collected_there(self):
        fy = self._fy()
        # حساب وصول سفارشی: تنخواه (110103)
        deposit = fy.accounts.get(code="110103")
        ch = services.create_cheque(
            fy, Cheque.DIR_RECEIVED, "DEP1", D("7000"), date(2026, 9, 20),
            party_name="شرکت الف", person=self.person_user,
            deposit_account=deposit,
        )
        self.assertEqual(ch.deposit_account_id, deposit.pk)
        # وصول چک → سند وصول باید بدهکارِ «تنخواه» داشته باشد نه بانک
        services.transition_cheque(ch, Cheque.STATUS_REGISTERED)
        services.transition_cheque(ch, Cheque.STATUS_DEPOSITED)
        services.transition_cheque(ch, Cheque.STATUS_COLLECTED)
        codes = {ln.account.code for ln in ch.entry.lines.all()}
        self.assertIn("110103", codes)
        self.assertNotIn("110102", codes)

    def test_received_cheque_without_deposit_defaults_to_bank(self):
        fy = self._fy()
        ch = services.create_cheque(fy, Cheque.DIR_RECEIVED, "DEP2", D("3000"),
                                    date(2026, 9, 20), party_name="شرکت ب")
        services.transition_cheque(ch, Cheque.STATUS_REGISTERED)
        services.transition_cheque(ch, Cheque.STATUS_DEPOSITED)
        services.transition_cheque(ch, Cheque.STATUS_COLLECTED)
        codes = {ln.account.code for ln in ch.entry.lines.all()}
        self.assertIn("110102", codes)  # بانک پیش‌فرض

    def test_deposit_selector_rendered_in_entry_form(self):
        self._fy()
        resp = self.client.get(reverse("accounting:entry_create"))
        content = resp.content.decode()
        self.assertIn("حساب وصول (بانک شرکت)", content)
        self.assertIn('name="ch_deposit"', content)
