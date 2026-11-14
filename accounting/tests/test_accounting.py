"""تست‌های یکپارچگی ماژول حسابداری (MySQL — از تراکنش‌های واقعی استفاده می‌کنیم)."""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounting.models import (
    Account,
    AccountingOrg,
    AccountingSession,
    AccountingUser,
    AuditLog,
    Cheque,
    FiscalYear,
    JournalEntry,
)
from accounting import services

D = Decimal


class BaseAccountingTest(TestCase):
    """راه‌اندازی مشترک: کاربر اصلی + دفتر + سال مالی ۱۴۰۵ با پلان پیش‌فرض."""

    @classmethod
    def setUpTestData(cls):
        cls.main_user = User.objects.create_user(mobile_number="09121110000")
        cls.org = services.get_or_create_org(cls.main_user)
        cls.fy = services.create_fiscal_year(cls.org, 1405, is_default=True)
        cls.acc_user = AccountingUser.objects.create(org=cls.org, username="boss",
                                                     full_name="مدیر دفتر", role="manager")
        cls.acc_user.set_password("secret1")
        cls.acc_user.save()

    def login_acc(self):
        """ورود از مسیر واقعی HTTP تا کوکی نشست ست شود."""
        url = reverse("accounting:login", args=[self.fy.id])
        return self.client.post(url, {"username": "boss", "password": "secret1"}, follow=True)


class OrgAndFiscalYearTests(BaseAccountingTest):
    def test_org_auto_created_once(self):
        org2 = services.get_or_create_org(self.main_user)
        self.assertEqual(org2.pk, self.org.pk)
        self.assertTrue(AccountingOrg.objects.filter(owner=self.main_user).count() == 1)

    def test_default_plan_seeded(self):
        # ۹ گروه + حساب‌های کل/معین + صندوق/بانک
        for code in ["1", "2", "9", "31", "3101", "81", "8101", "110101", "110102"]:
            self.assertTrue(self.fy.accounts.filter(code=code).exists(), code)
        group1 = self.fy.accounts.get(code="1")
        self.assertEqual(group1.level, Account.LEVEL_GROUP)
        bank = self.fy.accounts.get(code="110102")
        self.assertTrue(bank.is_leaf)

    def test_fiscal_year_bounds_and_name(self):
        self.assertEqual(self.fy.start_date, date(2026, 3, 21))
        self.assertEqual(self.fy.end_date, date(2027, 3, 20))
        self.assertIn("۱۴۰۵", self.fy.name)

    def test_duplicate_fiscal_year_rejected(self):
        with self.assertRaises(ValueError):
            services.create_fiscal_year(self.org, 1405)

    def test_max_eight_years(self):
        for y in range(1406, 1413):  # 7 more → total 8
            services.create_fiscal_year(self.org, y)
        with self.assertRaises(ValueError):
            services.create_fiscal_year(self.org, 1413)


class JournalEntryTests(BaseAccountingTest):
    def _accounts(self):
        cash = self.fy.accounts.get(code="110101")
        capital = self.fy.accounts.get(code="3101")
        return cash, capital

    def test_balanced_entry_posts(self):
        cash, capital = self._accounts()
        entry = services.create_journal_entry(self.fy, [
            {"account": cash, "debit": D("1000000"), "credit": D("0"), "description": "آورده نقدی"},
            {"account": capital, "debit": D("0"), "credit": D("1000000"), "description": "سرمایه"},
        ], date=self.fy.start_date, description="افتتاحیه")
        self.assertEqual(entry.status, JournalEntry.STATUS_POSTED)
        self.assertEqual(entry.number, 1)
        self.assertTrue(AuditLog.objects.filter(action="entry_post").exists())

    def test_unbalanced_entry_rejected(self):
        cash, capital = self._accounts()
        with self.assertRaises(ValueError):
            services.create_journal_entry(self.fy, [
                {"account": cash, "debit": D("1000000"), "credit": D("0")},
                {"account": capital, "debit": D("0"), "credit": D("900000")},
            ], date=self.fy.start_date)

    def test_group_account_not_allowed_in_entry(self):
        group = self.fy.accounts.get(code="1")
        cash, capital = self._accounts()
        with self.assertRaises(ValueError):
            services.create_journal_entry(self.fy, [
                {"account": group, "debit": D("500"), "credit": D("0")},
                {"account": capital, "debit": D("0"), "credit": D("500")},
            ], date=self.fy.start_date)

    def test_out_of_range_date_rejected(self):
        cash, capital = self._accounts()
        with self.assertRaises(ValueError):
            services.create_journal_entry(self.fy, [
                {"account": cash, "debit": D("100"), "credit": D("0")},
                {"account": capital, "debit": D("0"), "credit": D("100")},
            ], date=self.fy.start_date - timedelta(days=1))

    def test_posted_entry_immutable_and_cancellable(self):
        cash, capital = self._accounts()
        entry = services.create_journal_entry(self.fy, [
            {"account": cash, "debit": D("700"), "credit": D("0")},
            {"account": capital, "debit": D("0"), "credit": D("700")},
        ], date=self.fy.start_date)
        self.assertFalse(entry.can_edit())
        with self.assertRaises(ValueError):
            services.post_journal_entry(entry)
        services.cancel_journal_entry(entry)
        entry.refresh_from_db()
        self.assertEqual(entry.status, JournalEntry.STATUS_CANCELLED)

    def test_draft_deletable(self):
        cash, capital = self._accounts()
        entry = services.create_journal_entry(self.fy, [
            {"account": cash, "debit": D("300"), "credit": D("0")},
            {"account": capital, "debit": D("0"), "credit": D("300")},
        ], date=self.fy.start_date, post=False)
        self.assertTrue(entry.can_edit())
        services.delete_journal_entry(entry)
        self.assertFalse(JournalEntry.objects.filter(pk=entry.pk).exists())

    def test_numbering_sequential(self):
        cash, capital = self._accounts()
        lines = [
            {"account": cash, "debit": D("100"), "credit": D("0")},
            {"account": capital, "debit": D("0"), "credit": D("100")},
        ]
        e1 = services.create_journal_entry(self.fy, lines, date=self.fy.start_date)
        e2 = services.create_journal_entry(self.fy, lines, date=self.fy.start_date)
        self.assertEqual((e1.number, e2.number), (1, 2))


class AuthAndSessionTests(BaseAccountingTest):
    def test_two_step_login_flow(self):
        self.client.force_login(self.main_user)
        index_url = reverse("accounting:index")
        # گام ۱: انتخاب سال مالی
        resp = self.client.get(index_url)
        self.assertContains(resp, self.fy.name)
        # گام ۲: ورود
        login_url = reverse("accounting:login", args=[self.fy.id])
        resp = self.client.post(login_url, {"username": "boss", "password": "secret1"}, follow=True)
        self.assertRedirects(resp, reverse("accounting:dashboard"))
        self.assertIn("acc_session_key", self.client.cookies)
        # داشبورد با نشست باز می‌شود
        resp = self.client.get(reverse("accounting:dashboard"))
        self.assertEqual(resp.status_code, 200)

    def test_wrong_password_rejected(self):
        self.client.force_login(self.main_user)
        login_url = reverse("accounting:login", args=[self.fy.id])
        resp = self.client.post(login_url, {"username": "boss", "password": "nope"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "نادرست")

    def test_lockout_after_five_failures(self):
        self.client.force_login(self.main_user)
        login_url = reverse("accounting:login", args=[self.fy.id])
        for _ in range(5):
            self.client.post(login_url, {"username": "boss", "password": "bad"})
        resp = self.client.post(login_url, {"username": "boss", "password": "secret1"})
        self.assertContains(resp, "قفل")

    def test_session_expiry_and_logout(self):
        self.client.force_login(self.main_user)
        self.login_acc()
        from django.utils import timezone as tz
        AccountingSession.objects.update(expires_at=tz.now() - timedelta(minutes=1))
        resp = self.client.get(reverse("accounting:dashboard"), follow=True)
        # نشست منقضی → برگشت به انتخاب سال مالی
        self.assertRedirects(resp, reverse("accounting:index"))
        self.login_acc()
        self.client.get(reverse("accounting:logout"))
        resp = self.client.get(reverse("accounting:dashboard"), follow=True)
        self.assertRedirects(resp, reverse("accounting:index"))

    def test_login_requires_main_session(self):
        self.client.logout()
        resp = self.client.get(reverse("accounting:index"))
        # کاربر مهمان به صفحه اصلی سایت هدایت می‌شود
        self.assertEqual(resp.status_code, 302)


class ChequeTests(BaseAccountingTest):
    def test_received_cheque_auto_entry(self):
        ch = services.create_cheque(
            self.fy, direction=Cheque.DIR_RECEIVED, number="100200", amount=D("50000000"),
            due_date=date(2026, 10, 1), party_name="شرکت الف",
        )
        self.assertIsNotNone(ch.entry)
        self.assertEqual(ch.entry.status, JournalEntry.STATUS_POSTED)
        self.assertEqual(ch.entry.total_debit, D("50000000"))
        # بدهکار: اسناد دریافتنی (140101) / بستانکار: حساب طرف
        codes = {ln.account.code for ln in ch.entry.lines.all()}
        self.assertIn("140101", codes)
        party = [ln for ln in ch.entry.lines.all() if ln.account.code != "140101"][0]
        self.assertEqual(party.account.group, 6)

    def test_paid_cheque_entry(self):
        ch = services.create_cheque(
            self.fy, direction=Cheque.DIR_PAID, number="551001", amount=D("12000000"),
            due_date=date(2026, 11, 15), party_name="آقای رضایی",
        )
        codes = {ln.account.code for ln in ch.entry.lines.all()}
        self.assertIn("230101", codes)  # اسناد پرداختنی

    def test_cheque_state_machine_and_collection_entry(self):
        ch = services.create_cheque(
            self.fy, direction=Cheque.DIR_RECEIVED, number="700300", amount=D("8000000"),
            due_date=date(2026, 9, 1), party_name="شرکت ب",
        )
        first_entry = ch.entry
        self.assertTrue(ch.can_transition(Cheque.STATUS_REGISTERED))
        self.assertFalse(ch.can_transition(Cheque.STATUS_COLLECTED))  # پرش مجاز نیست
        with self.assertRaises(ValueError):
            services.transition_cheque(ch, Cheque.STATUS_COLLECTED)

        services.transition_cheque(ch, Cheque.STATUS_REGISTERED)
        services.transition_cheque(ch, Cheque.STATUS_DEPOSITED)
        services.transition_cheque(ch, Cheque.STATUS_COLLECTED)
        self.assertEqual(ch.status, Cheque.STATUS_COLLECTED)
        # سند وصول جدید صادر شده (بانک بدهکار / اسناد دریافتنی بستانکار)
        self.assertNotEqual(ch.entry.pk, first_entry.pk)
        codes = {ln.account.code for ln in ch.entry.lines.all()}
        self.assertIn("110102", codes)
        self.assertIn("140101", codes)

    def test_cheque_dashboard_numbers(self):
        services.create_cheque(self.fy, direction=Cheque.DIR_RECEIVED, number="X1",
                               amount=D("1000"), due_date=date.today(), party_name="پ")
        services.create_cheque(self.fy, direction=Cheque.DIR_PAID, number="X2",
                               amount=D("2000"), due_date=date.today(), party_name="ق")
        data = services.cheque_dashboard(self.fy)
        self.assertEqual(data["received_today"]["count"], 1)
        self.assertEqual(data["paid_today"]["count"], 1)
        self.assertEqual(data["received_today"]["amount"], D("1000"))
        self.assertTrue(data["today_jalali"])


class ReportsTests(BaseAccountingTest):
    def _seed(self):
        cash = self.fy.accounts.get(code="110101")
        capital = self.fy.accounts.get(code="3101")
        sales = self.fy.accounts.get(code="8101")
        cogs = self.fy.accounts.get(code="9101")
        # آورده ۱۰٬۰۰۰٬۰۰۰
        services.create_journal_entry(self.fy, [
            {"account": cash, "debit": D("10000000"), "credit": D("0")},
            {"account": capital, "debit": D("0"), "credit": D("10000000")},
        ], date=self.fy.start_date)
        # فروش نقدی ۶٬۰۰۰٬۰۰۰ با بهای تمام‌شده ۲٬۰۰۰٬۰۰۰ (بدون موجودی برای ساده‌سازی)
        services.create_journal_entry(self.fy, [
            {"account": cash, "debit": D("6000000"), "credit": D("0"), "description": "فروش نقدی"},
            {"account": sales, "debit": D("0"), "credit": D("6000000"), "description": "فروش نقدی"},
        ], date=self.fy.start_date)
        services.create_journal_entry(self.fy, [
            {"account": cogs, "debit": D("2000000"), "credit": D("0")},
            {"account": cash, "debit": D("0"), "credit": D("2000000")},
        ], date=self.fy.start_date)

    def test_trial_balance_balanced(self):
        self._seed()
        rows, totals = services.trial_balance(self.fy, level=3)
        self.assertEqual(totals["debit"], totals["credit"])
        self.assertGreater(totals["debit"], 0)

    def test_income_statement(self):
        self._seed()
        pl = services.income_statement(self.fy)
        self.assertEqual(pl["revenue"], D("6000000"))
        self.assertEqual(pl["cogs"], D("2000000"))
        self.assertEqual(pl["net_profit"], D("4000000"))

    def test_balance_sheet_balances(self):
        self._seed()
        bs = services.balance_sheet(self.fy)
        # دارایی: 10M + 6M − 2M = 14M؛ سرمایه 10M + سود 4M
        self.assertEqual(bs["assets"], D("14000000"))
        self.assertEqual(bs["equity"], D("14000000"))
        self.assertEqual(bs["difference"], 0)


class PermissionsAndSettingsTests(BaseAccountingTest):
    def test_role_permissions_matrix(self):
        manager = self.acc_user
        acc = AccountingUser.objects.create(org=self.org, username="acc1", role="accountant")
        viewer = AccountingUser.objects.create(org=self.org, username="view1", role="viewer")
        self.assertTrue(manager.can_write("settings"))
        self.assertFalse(acc.can_write("settings"))
        self.assertTrue(acc.can_write("entry"))
        self.assertFalse(viewer.can_write("entry"))
        self.assertTrue(viewer.perm("report"))

    def test_settings_page_and_fiscal_year_creation_via_ui(self):
        self.client.force_login(self.main_user)
        self.login_acc()
        resp = self.client.get(reverse("accounting:settings"))
        self.assertContains(resp, "کاربران حسابداری")
        resp = self.client.post(reverse("accounting:fiscal_year_create"),
                                {"jalali_year": "1407", "is_default": "on"}, follow=True)
        self.assertContains(resp, "۱۴۰۷")
        self.assertTrue(FiscalYear.objects.filter(org=self.org, jalali_year=1407).exists())

    def test_accountant_cannot_close_year(self):
        AccountingUser.objects.create(org=self.org, username="acc2", role="accountant")
        self.client.force_login(self.main_user)
        url = reverse("accounting:login", args=[self.fy.id])
        a = AccountingUser.objects.get(username="acc2")
        a.set_password("pass1234")
        a.save()
        self.client.post(url, {"username": "acc2", "password": "pass1234"})
        resp = self.client.post(reverse("accounting:fiscal_year_close", args=[self.fy.id]), follow=True)
        self.fy.refresh_from_db()
        self.assertFalse(self.fy.is_closed)
        self.assertContains(resp, "فقط مدیر")

    def test_account_create_via_ui(self):
        self.client.force_login(self.main_user)
        self.login_acc()
        parent = self.fy.accounts.get(code="6101")
        resp = self.client.post(reverse("accounting:account_create"),
                                {"parent": parent.id, "name": "مشتری شماره ۱"}, follow=True)
        self.assertContains(resp, "ایجاد شد")
        self.assertTrue(self.fy.accounts.filter(name="مشتری شماره ۱").exists())
        new_acc = self.fy.accounts.get(name="مشتری شماره ۱")
        self.assertEqual(new_acc.code, "61011")
