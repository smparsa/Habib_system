"""تست‌های گزارش «صورتحساب» — گردش و ماندهٔ یک حساب یا شخص از تاریخ تا تاریخ."""

from decimal import Decimal

from django.urls import reverse

from accounting import services
from accounting.jalali import JalaliDate

from .test_persons_and_guide import PersonsBaseTestCase


class StatementReportTests(PersonsBaseTestCase):
    def _entry(self, fy, lines, jy, jm, jd, post=True, description=""):
        return services.create_journal_entry(
            fy, lines, date=JalaliDate(jy, jm, jd).togregorian(),
            description=description, post=post,
        )

    def _setup(self):
        fy = self._login_accounting()
        cash = fy.accounts.get(code="110101")
        capital = fy.accounts.get(code="3101")
        income = services._leaf_account(fy, "410101", "درآمد فروش", parent_code="4101", group=4)
        return fy, cash, capital, income

    def test_statement_page_renders_with_subject_and_defaults(self):
        fy, cash, capital, income = self._setup()
        self._entry(fy, [
            {"account": cash, "debit": Decimal("1000"), "credit": Decimal("0")},
            {"account": capital, "debit": Decimal("0"), "credit": Decimal("1000")},
        ], 1405, 1, 15, description="سرمایه اولیه")
        self._entry(fy, [
            {"account": cash, "debit": Decimal("500"), "credit": Decimal("0")},
            {"account": income, "debit": Decimal("0"), "credit": Decimal("500")},
        ], 1405, 3, 10, description="فروش نقدی")

        resp = self.client.get(
            reverse("accounting:report_statement") + f"?account={cash.pk}")
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("صورتحساب", content)
        self.assertIn("ماندهٔ ابتدای دوره", content)
        self.assertIn("جمع دوره", content)
        self.assertIn("ماندهٔ پایان دوره", content)
        # سندهای ثبت‌شده دیده می‌شوند
        self.assertIn("سرمایه اولیه", content)
        self.assertIn("فروش نقدی", content)

    def test_statement_date_range_filters_and_opening_balance(self):
        fy, cash, capital, income = self._setup()
        # اسناد فروردین، مرداد و آذر
        self._entry(fy, [
            {"account": cash, "debit": Decimal("1000"), "credit": Decimal("0")},
            {"account": capital, "debit": Decimal("0"), "credit": Decimal("1000")},
        ], 1405, 1, 10)
        self._entry(fy, [
            {"account": cash, "debit": Decimal("400"), "credit": Decimal("0")},
            {"account": income, "debit": Decimal("0"), "credit": Decimal("400")},
        ], 1405, 5, 20)
        self._entry(fy, [
            {"account": cash, "debit": Decimal("0"), "credit": Decimal("250")},
            {"account": income, "debit": Decimal("250"), "credit": Decimal("0")},
        ], 1405, 9, 5)

        # بازهٔ تیر تا پایان سال: مانده ابتدا = 1000، فقط دو سندِ ۵ و ۹ در ردیف‌ها
        resp = self.client.get(
            reverse("accounting:report_statement")
            + f"?account={cash.pk}&date_from=1405/04/01&date_to=1405/12/29")
        data = resp.context
        self.assertEqual(data["opening"], Decimal("1000"))
        self.assertEqual(len(data["rows"]), 2)
        self.assertEqual(data["total_debit"], Decimal("400"))
        self.assertEqual(data["total_credit"], Decimal("250"))
        # مانده پایانی = 1000 + 400 - 250 = 1150 (مانده کل حساب)
        self.assertEqual(data["closing"], Decimal("1150"))

        # بازهٔ فروردین تا اردیبهشت: فقط سند اول
        resp2 = self.client.get(
            reverse("accounting:report_statement")
            + f"?account={cash.pk}&date_from=1405/01/01&date_to=1405/03/31")
        data2 = resp2.context
        self.assertEqual(data2["opening"], Decimal("0"))
        self.assertEqual(len(data2["rows"]), 1)
        self.assertEqual(data2["closing"], Decimal("1000"))

    def test_statement_for_person(self):
        fy, cash, capital, income = self._setup()
        self._entry(fy, [
            {"account": cash, "debit": Decimal("700"), "credit": Decimal("0"),
             "person": self.person_user},
            {"account": income, "debit": Decimal("0"), "credit": Decimal("700")},
        ], 1405, 2, 5, description="دریافت از شخص")
        self._entry(fy, [
            {"account": cash, "debit": Decimal("0"), "credit": Decimal("300"),
             "person": self.person_user},
            {"account": income, "debit": Decimal("300"), "credit": Decimal("0")},
        ], 1405, 6, 25, description="عودت به شخص")

        resp = self.client.get(
            reverse("accounting:report_statement") + f"?person={self.person_user.pk}")
        self.assertEqual(resp.status_code, 200)
        data = resp.context
        self.assertEqual(data["subject_kind"], "person")
        self.assertEqual(len(data["rows"]), 2)
        # مانده شخص = 700 - 300 = 400 (طلب از شخص)
        self.assertEqual(data["closing"], Decimal("400"))
        content = resp.content.decode()
        # ستون «حساب» در صورتحساب شخص دیده می‌شود
        self.assertIn("حساب", content)
        self.assertIn("دریافت از شخص", content)

    def test_statement_excludes_drafts(self):
        fy, cash, capital, income = self._setup()
        self._entry(fy, [
            {"account": cash, "debit": Decimal("1000"), "credit": Decimal("0")},
            {"account": capital, "debit": Decimal("0"), "credit": Decimal("1000")},
        ], 1405, 1, 15, post=True)
        self._entry(fy, [
            {"account": cash, "debit": Decimal("999"), "credit": Decimal("0")},
            {"account": income, "debit": Decimal("0"), "credit": Decimal("999")},
        ], 1405, 2, 2, post=False)  # پیش‌نویس

        resp = self.client.get(
            reverse("accounting:report_statement") + f"?account={cash.pk}")
        self.assertEqual(len(resp.context["rows"]), 1)
        self.assertEqual(resp.context["closing"], Decimal("1000"))

    def test_statement_menu_link_and_empty_state(self):
        fy, cash, capital, income = self._setup()
        # شخص فقط وقتی در فهرست می‌آید که مانده داشته باشد
        self._entry(fy, [
            {"account": cash, "debit": Decimal("1000"), "credit": Decimal("0"),
             "person": self.person_user},
            {"account": capital, "debit": Decimal("0"), "credit": Decimal("1000")},
        ], 1405, 1, 15)
        resp = self.client.get(reverse("accounting:report_statement"))
        content = resp.content.decode()
        self.assertIn("صورتحساب", content)
        # دو بخش مجزای انتخاب: نام حساب (آبشاری) و اشخاص (لیست)
        self.assertIn("stmtPickers", content)
        self.assertIn("نام حساب", content)
        self.assertIn("اشخاص", content)
        self.assertIn("personFilter", content)
        self.assertIn("stmt-branch", content)  # دکمه‌های آبشاری درخت
        self.assertIn(f"person={self.person_user.pk}", content)  # ردیف لیست اشخاص (بامانده)
        # بدون موضوع، جدول گزارش رندر نمی‌شود (عبارت مخصوص tfoot جدول)
        self.assertNotIn("ماندهٔ پایان دوره", content)

    def test_statement_tree_is_cascading_and_clickable(self):
        fy, cash, capital, income = self._setup()
        # حساب‌ها فقط با ماندهٔ غیرصفر می‌آیند؛ سند بزن تا صندوق/سرمایه/درآمد پدیدار شوند
        self._entry(fy, [
            {"account": cash, "debit": Decimal("1000"), "credit": Decimal("0")},
            {"account": capital, "debit": Decimal("0"), "credit": Decimal("1000")},
        ], 1405, 1, 15)
        # درخت باید گروه‌ها، والد‌ها و حساب تفصیلی با لینک انتخاب را داشته باشد
        resp = self.client.get(reverse("accounting:report_statement"))
        content = resp.content.decode()
        self.assertIn('data-node=', content)          # گره‌های بازشونده (گروه/کل/معین)
        self.assertIn('data-ancestors=', content)     # زنجیرهٔ پدران برای باز/بستن آبشاری
        self.assertIn(f"account={cash.pk}", content)  # لینک انتخاب حساب تفصیلی
        self.assertIn("ارسال به چاپگر", content)      # دکمهٔ چاپ در مرحلهٔ انتخاب
        # حساب بدون گردش (درآمد فروش) در لیست نیست
        self.assertNotIn(f"account={income.pk}", content)

    def test_statement_only_shows_nonzero_balances(self):
        fy, cash, capital, income = self._setup()
        # بدون هیچ سندی: نه حسابی در درخت است نه شخصی در فهرست
        resp = self.client.get(reverse("accounting:report_statement"))
        content = resp.content.decode()
        self.assertNotIn(f"account={cash.pk}", content)
        self.assertNotIn(f"person={self.person_user.pk}", content)
        self.assertIn("شخصی با ماندهٔ باز وجود ندارد", content)

        # سند شخصی: صندوق، سرمایه و شخص ظاهر می‌شوند؛ درآمد همچنان نه
        self._entry(fy, [
            {"account": cash, "debit": Decimal("700"), "credit": Decimal("0"),
             "person": self.person_user},
            {"account": capital, "debit": Decimal("0"), "credit": Decimal("700")},
        ], 1405, 2, 5)
        resp2 = self.client.get(reverse("accounting:report_statement"))
        content2 = resp2.content.decode()
        self.assertIn(f"account={cash.pk}", content2)
        self.assertIn(f"person={self.person_user.pk}", content2)
        self.assertNotIn(f"account={income.pk}", content2)

        # ماندهٔ صفرشده (تسویه کامل) → از لیست محو می‌شود
        self._entry(fy, [
            {"account": cash, "debit": Decimal("0"), "credit": Decimal("700"),
             "person": self.person_user},
            {"account": income, "debit": Decimal("700"), "credit": Decimal("0")},
        ], 1405, 3, 5)
        resp3 = self.client.get(reverse("accounting:report_statement"))
        self.assertNotIn(f"person={self.person_user.pk}", resp3.content.decode())

    def test_statement_result_has_print_button(self):
        fy, cash, capital, income = self._setup()
        self._entry(fy, [
            {"account": cash, "debit": Decimal("1000"), "credit": Decimal("0")},
            {"account": capital, "debit": Decimal("0"), "credit": Decimal("1000")},
        ], 1405, 1, 15)
        resp = self.client.get(
            reverse("accounting:report_statement") + f"?account={cash.pk}")
        content = resp.content.decode()
        self.assertIn("printStatement", content)
        self.assertIn('id="stmtResult"', content)
        # درخت کنار نتیجه هم هست و لینک‌ها به لنگرگاه نتیجه می‌روند
        self.assertIn("#stmtResult", content)
