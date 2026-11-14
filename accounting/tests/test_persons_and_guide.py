"""تست‌های منوی «اشخاص» و صفحهٔ «راهنما» در ماژول حسابداری.

سناریو: کاربرانِ سایت که کد ملی ثبت‌شده دارند در فهرست اشخاص می‌آیند، در سند
قابل انتخاب‌اند (بدهکار/بستانکار) و دفتر بدهکار/بستانکار هر شخص قابل مشاهده است.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import FamilynameTbl, FirstnameTbl, Profile, User
from accounting import services
from accounting.models import JournalEntry, TransactionLine


class PersonsBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        fn = FirstnameTbl.objects.create(first_name_fa="علی", gender="male")
        ln = FamilynameTbl.objects.create(familyname_fa="محمدی")
        cls.person_user = User.objects.create_user(mobile_number="09121110010")
        cls.person_user.profile.first_name = fn
        cls.person_user.profile.last_name = ln
        cls.person_user.profile.national_id = "1111111111"
        cls.person_user.profile.save()

        # کاربر بدون کد ملی → نباید در فهرست اشخاص بیاید
        cls.no_nid_user = User.objects.create_user(mobile_number="09121110011")

        # کاربر مالک دفتر
        cls.owner = User.objects.create_user(mobile_number="09121110012")
        cls.owner.acc_username = "accowner"
        cls.owner.set_acc_password("S3cret!pass")
        cls.owner.save()

    def _login_accounting(self):
        org = services.get_or_create_org(self.owner)
        fy = services.create_fiscal_year(org, 1405, is_default=True)
        self.client.force_login(self.owner)
        resp = self.client.post(reverse("accounting:login", args=[fy.id]),
                                {"username": "accowner", "password": "S3cret!pass"})
        return fy


class PersonsListTests(PersonsBaseTestCase):
    def test_only_users_with_national_id_listed(self):
        fy = self._login_accounting()
        resp = self.client.get(reverse("accounting:persons"))
        self.assertContains(resp, "علی")
        self.assertContains(resp, "محمدی")
        # کد ملی با ارقام فارسی نمایش داده می‌شود
        self.assertContains(resp, "۱۱۱۱۱۱۱۱۱۱")
        # کاربر بدون کد ملی نباید باشد
        content = resp.content.decode()
        self.assertNotIn("09121110011", content)

    def test_search_by_name_and_national_id(self):
        fy = self._login_accounting()
        resp = self.client.get(reverse("accounting:persons"), {"q": "محمدی"})
        self.assertContains(resp, "علی")
        resp = self.client.get(reverse("accounting:persons"), {"q": "1111111111"})
        self.assertContains(resp, "علی")
        resp = self.client.get(reverse("accounting:persons"), {"q": "ناموجود"})
        self.assertContains(resp, "شخصی یافت نشد")

    def test_person_ledger_view(self):
        fy = self._login_accounting()
        resp = self.client.get(reverse("accounting:person_ledger", args=[self.person_user.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "دفتر شخص")


class PersonsInEntriesTests(PersonsBaseTestCase):
    def test_person_selection_and_ledger_flow(self):
        """شخص در سند انتخاب می‌شود؛ گردش در دفتر شخص و جزئیات سند دیده می‌شود."""
        fy = self._login_accounting()
        cash = fy.accounts.get(code="110101")
        receivable = services._leaf_account(fy, "150101", "حساب‌های دریافتنی", parent_code="15", group=1)

        # ثبت سند: بدهکار دریافتنی از شخص / بستانکار درآمد
        income = fy.accounts.get(code="4101") if fy.accounts.filter(code="4101").exists() else None
        # درآمد باید تفصیلی باشد؛ در صورت نیاز بساز
        if income is None or not income.is_leaf:
            parent = fy.accounts.filter(code="4101").first() or \
                services._leaf_account(fy, "4101", "درآمد عملیاتی", parent_code="41", group=4)
            income = services._leaf_account(fy, "410101", "درآمد فروش", parent_code="4101", group=4)

        url = reverse("accounting:entry_create")
        resp = self.client.post(url, {
            "date": "1405/07/02",
            "description": "فروش به شخص",
            "account_0": receivable.pk, "debit_0": "500000", "credit_0": "",
            "desc_0": "طلب از علی محمدی", "person_0": self.person_user.pk,
            "account_1": income.pk, "debit_1": "", "credit_1": "500000",
            "desc_1": "درآمد فروش", "person_1": "",
            "action": "post",
        })
        self.assertEqual(resp.status_code, 302)

        entry = JournalEntry.objects.filter(fiscal_year=fy).order_by("-pk").first()
        self.assertEqual(entry.status, JournalEntry.STATUS_POSTED)
        line = entry.lines.filter(person=self.person_user).first()
        self.assertIsNotNone(line)
        self.assertEqual(line.debit, Decimal("500000"))

        # دفتر شخص: گردش + مانده
        resp = self.client.get(reverse("accounting:person_ledger", args=[self.person_user.pk]))
        content = resp.content.decode()
        self.assertIn("طلب از علی محمدی", content)
        self.assertIn("5", content)  # مبلغ در جدول

        # جزئیات سند: نام شخص و کد ملی (با ارقام فارسی) نمایش داده شود
        resp = self.client.get(reverse("accounting:entry_detail", args=[entry.pk]))
        content = resp.content.decode()
        self.assertIn("علی محمدی", content)
        self.assertIn("۱۱۱۱۱۱۱۱۱۱", content)

    def test_persons_available_in_entry_form(self):
        fy = self._login_accounting()
        resp = self.client.get(reverse("accounting:entry_create"))
        self.assertContains(resp, "PERSONS")
        self.assertContains(resp, "1111111111")


class EntryEditFromFormTests(PersonsBaseTestCase):
    """برگشت به سندهای قبلی و ویرایش از همین صفحهٔ سند جدید."""

    def test_draft_can_be_edited_from_entry_form(self):
        fy = self._login_accounting()
        cash = fy.accounts.get(code="110101")
        capital = fy.accounts.get(code="3101")

        # سند پیش‌نویس بساز
        entry = services.create_journal_entry(
            fy,
            [
                {"account": cash, "debit": Decimal("100000"), "credit": Decimal("0"), "description": "اولیه"},
                {"account": capital, "debit": Decimal("0"), "credit": Decimal("100000"), "description": ""},
            ],
            date=fy.start_date, post=False,
        )
        self.assertEqual(entry.status, JournalEntry.STATUS_DRAFT)

        # صفحهٔ سند جدید با edit= باید ردیف‌ها و شمارهٔ همان سند را نشان دهد
        resp = self.client.get(reverse("accounting:entry_create") + f"?edit={entry.pk}")
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("ویرایش سند", content)
        self.assertIn("اولیه", content)

        # ویرایش و ثبت: مبلغ تغییر کند + شخص ست شود (edit_pk مثل فیلد مخفی فرم)
        income = services._leaf_account(fy, "410101", "درآمد فروش", parent_code="4101", group=4)
        resp = self.client.post(reverse("accounting:entry_create"), {
            "edit_pk": entry.pk,
            "date": "1405/07/05",
            "description": "ویرایش‌شده",
            "account_0": cash.pk, "debit_0": "200000", "credit_0": "",
            "desc_0": "اصلاح‌شده", "person_0": self.person_user.pk,
            "account_1": income.pk, "debit_1": "", "credit_1": "200000",
            "desc_1": "", "person_1": "",
            "action": "post",
        })
        self.assertEqual(resp.status_code, 302)
        entry.refresh_from_db()
        self.assertEqual(entry.status, JournalEntry.STATUS_POSTED)
        self.assertEqual(entry.description, "ویرایش‌شده")
        self.assertEqual(entry.lines.count(), 2)
        self.assertEqual(entry.lines.first().debit, Decimal("200000"))
        self.assertTrue(entry.lines.filter(person=self.person_user).exists())
        # شمارهٔ سند تغییر نکند (ویرایش است، نه سند جدید)
        self.assertEqual(entry.number, 1)

    def test_posted_entry_cannot_be_loaded_for_edit(self):
        fy = self._login_accounting()
        cash = fy.accounts.get(code="110101")
        capital = fy.accounts.get(code="3101")
        entry = services.create_journal_entry(
            fy,
            [
                {"account": cash, "debit": Decimal("1000"), "credit": Decimal("0")},
                {"account": capital, "debit": Decimal("0"), "credit": Decimal("1000")},
            ],
            date=fy.start_date, post=True,
        )
        resp = self.client.get(reverse("accounting:entry_create") + f"?edit={entry.pk}", follow=True)
        # باید رد شود و به فرم سند جدید برگردد با پیام خطا
        self.assertContains(resp, "فقط سند پیش‌نویس قابل ویرایش است")

    def test_recent_drafts_listed_on_entry_form(self):
        fy = self._login_accounting()
        cash = fy.accounts.get(code="110101")
        capital = fy.accounts.get(code="3101")
        services.create_journal_entry(
            fy,
            [
                {"account": cash, "debit": Decimal("5000"), "credit": Decimal("0")},
                {"account": capital, "debit": Decimal("0"), "credit": Decimal("5000")},
            ],
            date=fy.start_date, post=False,
        )
        resp = self.client.get(reverse("accounting:entry_create"))
        self.assertContains(resp, "سندهای قبلی")
        self.assertContains(resp, "?edit=")


class TypeaheadComboboxTests(PersonsBaseTestCase):
    """کامبوباکس جستجوی تایپی حساب/شخص: داده‌ها و hidden inputs و فیلد حذف‌شدهٔ select."""

    def test_data_and_combo_components_rendered(self):
        fy = self._login_accounting()
        resp = self.client.get(reverse("accounting:entry_create"))
        content = resp.content.decode()
        # دادهٔ جستجو با فیلد search برای هر حساب و شخص
        self.assertIn('search: "', content)
        self.assertIn("buildEntryCombo", content)
        self.assertIn("acc-hidden", content)
        self.assertIn("person-hidden", content)
        # select قدیمی دیگر تولید نمی‌شود
        self.assertNotIn("— انتخاب حساب —", content)
        # نرمال‌سازی فارسی و امتیازدهی
        self.assertIn("normFa", content)
        self.assertIn("scoreItem", content)
        # جستجوی گروه والد حساب + نام فامیل شخص در دادهٔ ارسالی
        # (parent_name فقط کلید کانتکست است؛ در HTML مقدارِ group: رندر می‌شود)
        self.assertIn('group: "', content)
        self.assertIn('family:', content)
        # ساختار ۶ ستونی درخواستی
        self.assertIn('نام حساب / نام شخص', content)
        self.assertIn('کد حساب / کد ملی', content)
        self.assertIn('مبلغ بدهکار (ریال)', content)
        self.assertIn('مبلغ بستانکار (ریال)', content)

    def test_hidden_inputs_post_flow(self):
        """شبیه‌سازی POST فرم واقعی: hidden account_i/person_i + ردیف خالی میانی."""
        fy = self._login_accounting()
        cash = fy.accounts.get(code="110101")
        income = services._leaf_account(fy, "410101", "درآمد فروش", parent_code="4101", group=4)
        resp = self.client.post(reverse("accounting:entry_create"), {
            "date": "1405/07/02",
            "description": "تست کامبو",
            # ردیف ۰: حساب با کامبو (hidden) + شخص
            "account_0": str(cash.pk), "person_0": str(self.person_user.pk),
            "debit_0": "300000", "credit_0": "", "desc_0": "دریافت از شخص",
            # ردیف ۱: خالی (کاربر پر نکرده)
            "account_1": "", "person_1": "", "debit_1": "", "credit_1": "", "desc_1": "",
            # ردیف ۲: فقط بستانکار
            "account_2": str(income.pk), "person_2": "",
            "debit_2": "", "credit_2": "300000", "desc_2": "",
            "action": "post",
        })
        self.assertEqual(resp.status_code, 302)
        from accounting.models import JournalEntry
        entry = JournalEntry.objects.filter(fiscal_year=fy).order_by("-pk").first()
        self.assertEqual(entry.status, JournalEntry.STATUS_POSTED)
        self.assertEqual(entry.lines.count(), 2)
        self.assertTrue(entry.lines.filter(person=self.person_user).exists())


class BankScreenshotScenarioTests(PersonsBaseTestCase):
    """سناریوی خطای گزارش‌شده: سند بانک/بانک با شخص — «ردیف ۱: حساب نامعتبر است»."""

    def test_bank_debit_credit_with_person_posts(self):
        fy = self._login_accounting()
        bank = fy.accounts.get(code="110102")
        # دقیقاً مثل اسکرین‌شات: ردیف ۱ بانک بدهکار ۲، ردیف ۲ بانک بستانکار ۲ + شخص
        resp = self.client.post(reverse("accounting:entry_create"), {
            "date": "1405/07/02",
            "description": "",
            "account_0": str(bank.pk), "person_0": "",
            "debit_0": "2", "credit_0": "0", "desc_0": "",
            "account_1": str(bank.pk), "person_1": str(self.person_user.pk),
            "debit_1": "0", "credit_1": "2", "desc_1": "",
            "action": "post",
        })
        self.assertEqual(resp.status_code, 302)
        from accounting.models import JournalEntry
        entry = JournalEntry.objects.filter(fiscal_year=fy).order_by("-pk").first()
        self.assertEqual(entry.status, JournalEntry.STATUS_POSTED)
        self.assertEqual(entry.lines.count(), 2)
        self.assertTrue(entry.lines.filter(person=self.person_user).exists())

    def test_account_sent_as_code_still_resolves(self):
        """اگر مرورگر به‌جای شناسه، کد حساب را بفرستد هم سند ثبت شود (رفع «حساب نامعتبر»)."""
        fy = self._login_accounting()
        cash = fy.accounts.get(code="110101")
        capital = fy.accounts.get(code="3101")
        resp = self.client.post(reverse("accounting:entry_create"), {
            "date": "1405/07/02",
            "account_0": "110101", "person_0": "",
            "debit_0": "1000", "credit_0": "", "desc_0": "",
            "account_1": "3101", "person_1": "",
            "debit_1": "", "credit_1": "1000", "desc_1": "",
            "action": "post",
        })
        self.assertEqual(resp.status_code, 302)
        from accounting.models import JournalEntry
        entry = JournalEntry.objects.filter(fiscal_year=fy).order_by("-pk").first()
        self.assertEqual(entry.status, JournalEntry.STATUS_POSTED)

    def test_empty_hidden_does_not_break_rows(self):
        """hidden خالی حساب (پاک‌شده با ✕) نباید ردیف‌های بعدی را خراب کند."""
        fy = self._login_accounting()
        cash = fy.accounts.get(code="110101")
        capital = fy.accounts.get(code="3101")
        resp = self.client.post(reverse("accounting:entry_create"), {
            "date": "1405/07/02",
            "account_0": "", "person_0": "",  # ردیف اول خالی
            "debit_0": "", "credit_0": "", "desc_0": "",
            "account_1": str(cash.pk), "person_1": "",
            "debit_1": "5000", "credit_1": "", "desc_1": "",
            "account_2": str(capital.pk), "person_2": "",
            "debit_2": "", "credit_2": "5000", "desc_2": "",
            "action": "post",
        })
        self.assertEqual(resp.status_code, 302)
        from accounting.models import JournalEntry
        entry = JournalEntry.objects.filter(fiscal_year=fy).order_by("-pk").first()
        self.assertEqual(entry.status, JournalEntry.STATUS_POSTED)
        self.assertEqual(entry.lines.count(), 2)

    def test_person_name_or_nid_resolves(self):
        """اگر به‌جای شناسهٔ شخص، نام یا کد ملی ارسال شود هم resolve شود (کادر ناتمام)."""
        fy = self._login_accounting()
        cash = fy.accounts.get(code="110101")
        capital = fy.accounts.get(code="3101")
        for person_value in ("علی محمدی", "1111111111", "علی محمدی (1111111111)"):
            resp = self.client.post(reverse("accounting:entry_create"), {
                "date": "1405/07/02",
                "account_0": str(cash.pk), "person_0": person_value,
                "debit_0": "60", "credit_0": "", "desc_0": "",
                "account_1": str(capital.pk), "person_1": "",
                "debit_1": "", "credit_1": "60", "desc_1": "",
                "action": "post",
            })
            self.assertEqual(resp.status_code, 302)
        from accounting.models import JournalEntry, TransactionLine
        entries = JournalEntry.objects.filter(fiscal_year=fy).order_by("-pk")[:3]
        for entry in entries:
            self.assertTrue(
                entry.lines.filter(person=self.person_user).exists(),
                f"شخص در سند {entry.number} ثبت نشد (مقدار: {person_value})",
            )

    def test_person_text_field_used_when_hidden_lost(self):
        """اگر hidden شخص گم شود ولی person_text_i موجود باشد، از آن resolve شود."""
        fy = self._login_accounting()
        cash = fy.accounts.get(code="110101")
        capital = fy.accounts.get(code="3101")
        resp = self.client.post(reverse("accounting:entry_create"), {
            "date": "1405/07/02",
            "account_0": str(cash.pk), "person_0": "", "person_text_0": "1111111111",
            "debit_0": "70", "credit_0": "", "desc_0": "",
            "account_1": str(capital.pk), "person_1": "", "person_text_1": "",
            "debit_1": "", "credit_1": "70", "desc_1": "",
            "action": "post",
        })
        self.assertEqual(resp.status_code, 302)
        from accounting.models import JournalEntry
        entry = JournalEntry.objects.filter(fiscal_year=fy).order_by("-pk").first()
        self.assertTrue(entry.lines.filter(person=self.person_user).exists())

    def test_account_name_only_resolves(self):
        """اگر به‌جای شناسهٔ حساب، فقط نام حساب (مثل «بانک») ارسال شود هم resolve شود."""
        fy = self._login_accounting()
        bank = fy.accounts.get(code="110102")
        resp = self.client.post(reverse("accounting:entry_create"), {
            "date": "1405/07/02",
            "account_0": "بانک", "debit_0": "80", "credit_0": "", "desc_0": "",
            "account_1": "3101", "debit_1": "", "credit_1": "80", "desc_1": "",
            "action": "post",
        })
        self.assertEqual(resp.status_code, 302)
        from accounting.models import JournalEntry
        entry = JournalEntry.objects.filter(fiscal_year=fy).order_by("-pk").first()
        self.assertEqual(entry.status, JournalEntry.STATUS_POSTED)
        self.assertEqual(entry.lines.count(), 2)
        self.assertTrue(entry.lines.filter(account=bank).exists())


class GuideTests(PersonsBaseTestCase):
    def test_guide_page_comprehensive(self):
        fy = self._login_accounting()
        resp = self.client.get(reverse("accounting:guide"))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        for keyword in [
            "شروع به کار", "ورود، نشست و امنیت", "پلان حساب‌ها", "اسناد حسابداری",
            "اشخاص", "چک", "گزارش", "سیستم و تنظیمات", "پرسش‌های متداول",
        ]:
            self.assertIn(keyword, content)

    def test_guide_linked_in_menu(self):
        fy = self._login_accounting()
        resp = self.client.get(reverse("accounting:dashboard"))
        self.assertContains(resp, reverse("accounting:guide"))
