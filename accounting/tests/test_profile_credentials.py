"""تست‌های اعتبارنامهٔ حسابداری تعریف‌شده در «پروفایل من ← اطلاعات امنیتی»."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.acc_credentials import AccCredentialsForm, normalize_acc_username
from accounts.models import User
from accounting import services
from accounting.models import AccountingUser, AuditLog, LoginAttempt


class AccCredentialsFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(mobile_number="09121110001")

    def _data(self, **over):
        data = {
            "username": "accali",
            "current_password": "",
            "password": "S3cret!pass",
            "confirm_password": "S3cret!pass",
        }
        data.update(over)
        return data

    def test_valid_credentials_saved_hashed(self):
        form = AccCredentialsForm(self._data(), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        form.apply()
        self.user.refresh_from_db()
        self.assertEqual(self.user.acc_username, "accali")
        # رمز خام هرگز ذخیره نمی‌شود — فقط هش
        self.assertNotIn("S3cret!pass", self.user.acc_password)
        self.assertTrue(self.user.acc_password.startswith("pbkdf2_sha256"))
        self.assertTrue(self.user.check_acc_password("S3cret!pass"))
        self.assertFalse(self.user.check_acc_password("wrong"))
        self.assertTrue(self.user.has_acc_credentials())

    def test_username_only_latin_letters_and_digits(self):
        """نام کاربری فقط ترکیب حروف لاتین و اعداد است؛ نقطه/زیرخط/فاصله/فارسی ممنوع."""
        for bad in ["acc.ali", "acc_ali", "acc-ali", "acc ali", "علی1284",
                    "ali!", "ali@1284"]:
            form = AccCredentialsForm(self._data(username=bad), user=self.user)
            self.assertFalse(form.is_valid(), bad)
            self.assertIn("username", form.errors)
        # ارقام فارسی به لاتین تبدیل و پذیرفته می‌شود
        form = AccCredentialsForm(self._data(username="ali۱۲۸۴"), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["username"], "ali1284")

    def test_username_case_insensitive_saved_lowercase(self):
        """بزرگی/کوچکی حروف بی‌اثر است؛ مقدار ذخیره‌شده همیشه حروف کوچک است."""
        form = AccCredentialsForm(self._data(username="Ali1284"), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        form.apply()
        self.user.refresh_from_db()
        self.assertEqual(self.user.acc_username, "ali1284")

    def test_normalize_acc_username(self):
        self.assertEqual(normalize_acc_username("  Ali۱۲۸۴ "), "ali1284")
        self.assertEqual(normalize_acc_username("ACC.ALI"), "acc.ali")  # نرمال‌سازی ساده، اعتبارسنجی جدا انجام می‌شود

    def test_weak_passwords_rejected(self):
        for weak in ["short1x", "12345678", "password123"]:
            form = AccCredentialsForm(self._data(password=weak, confirm_password=weak),
                                      user=self.user)
            self.assertFalse(form.is_valid(), weak)
            self.assertIn("password", form.errors)

    def test_confirm_must_match(self):
        form = AccCredentialsForm(self._data(confirm_password="different123"), user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("confirm_password", form.errors)

    def test_duplicate_username_rejected_case_insensitive(self):
        other = User.objects.create_user(mobile_number="09121110002")
        form0 = AccCredentialsForm(self._data(), user=other)
        self.assertTrue(form0.is_valid(), form0.errors)
        form0.apply()
        form = AccCredentialsForm(self._data(username="ACCALI"), user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_username_cannot_be_own_mobile(self):
        form = AccCredentialsForm(self._data(username="09121110001"), user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_change_requires_current_password(self):
        form0 = AccCredentialsForm(self._data(), user=self.user)
        self.assertTrue(form0.is_valid(), form0.errors)
        form0.apply()
        form = AccCredentialsForm(self._data(username="accale2"), user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("current_password", form.errors)
        form = AccCredentialsForm(
            self._data(username="accali2", current_password="S3cret!pass",
                       password="N3wStrongPass", confirm_password="N3wStrongPass"),
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.apply()
        self.user.refresh_from_db()
        self.assertEqual(self.user.acc_username, "accali2")
        self.assertTrue(self.user.check_acc_password("N3wStrongPass"))


class ProfileAndLoginFlowTests(TestCase):
    """جریان کامل: تعریف از پروفایل → ورود به حسابداری با همان اعتبارنامه."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(mobile_number="09121110003")

    def test_profile_page_shows_form_and_saves(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("core:profile"))
        self.assertContains(resp, "نام کاربری و کلمه عبور ماژول حسابداری")
        resp = self.client.post(reverse("core:profile"), {
            "action": "acc_credentials",
            "username": "acchosein",
            "password": "S3cret!pass",
            "confirm_password": "S3cret!pass",
        }, follow=True)
        self.assertContains(resp, "اعتبارنامهٔ حسابداری ذخیره شد")
        self.user.refresh_from_db()
        self.assertEqual(self.user.acc_username, "acchosein")
        self.assertTrue(self.user.check_acc_password("S3cret!pass"))

    def test_login_with_profile_credentials(self):
        self.user.acc_username = "acchosein"
        self.user.set_acc_password("S3cret!pass")
        self.user.save()

        self.client.force_login(self.user)
        fy = services.create_fiscal_year(services.get_or_create_org(self.user), 1405,
                                         is_default=True)
        resp = self.client.post(reverse("accounting:login", args=[fy.id]),
                                {"username": "acchosein", "password": "S3cret!pass"},
                                follow=True)
        self.assertRedirects(resp, reverse("accounting:dashboard"))

        # کاربر حسابداری هم‌نام با نقش مدیر به‌طور خودکار همگام شد
        acc_user = AccountingUser.objects.get(org__owner=self.user, username="acchosein")
        self.assertEqual(acc_user.role, "manager")

    def test_login_case_insensitive_username(self):
        """ورود با هر ترکیبی از حروف بزرگ/کوچکِ نام کاربری امکان‌پذیر است."""
        self.user.acc_username = "acchosein"
        self.user.set_acc_password("S3cret!pass")
        self.user.save()

        self.client.force_login(self.user)
        fy = services.create_fiscal_year(services.get_or_create_org(self.user), 1405,
                                         is_default=True)
        for attempt in ("ACCHOSEIN", "AccHosein", "acchosein"):
            resp = self.client.post(reverse("accounting:login", args=[fy.id]),
                                    {"username": attempt, "password": "S3cret!pass"})
            self.assertEqual(resp.status_code, 302, (attempt, resp.context["form"].errors if resp.context else None))

        # یک سند واقعی ثبت شود تا مطمئن شویم نشست کامل است
        cash = fy.accounts.get(code="110101")
        capital = fy.accounts.get(code="3101")
        entry = services.create_journal_entry(fy, [
            {"account": cash, "debit": Decimal("1000"), "credit": Decimal("0")},
            {"account": capital, "debit": Decimal("0"), "credit": Decimal("1000")},
        ], date=fy.start_date)
        self.assertEqual(entry.status, "posted")

    def test_wrong_password_still_rejected_and_lockout_applies(self):
        self.user.acc_username = "acchosein"
        self.user.set_acc_password("S3cret!pass")
        self.user.save()
        org = services.get_or_create_org(self.user)
        fy = services.create_fiscal_year(org, 1405, is_default=True)

        self.client.force_login(self.user)
        url = reverse("accounting:login", args=[fy.id])
        for _ in range(5):
            resp = self.client.post(url, {"username": "acchosein", "password": "bad"})
        resp = self.client.post(url, {"username": "acchosein", "password": "S3cret!pass"})
        self.assertContains(resp, "قفل")
        self.assertTrue(LoginAttempt.objects.filter(success=False, username="acchosein").count() >= 5)

    def test_notice_shown_once_only_in_security_section(self):
        """اعلان ذخیره فقط یک‌بار و فقط در کارت حسابداری در بخش «اطلاعات امنیتی» دیده می‌شود، نه در سایر بخش‌ها."""
        self.client.force_login(self.user)
        resp = self.client.post(reverse("core:profile"), {
            "action": "acc_credentials",
            "username": "acconce",
            "password": "S3cret!pass",
            "confirm_password": "S3cret!pass",
        })
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("core:profile"))
        content = resp.content.decode("utf-8")
        # اعلان یک‌بارمصرف: فقط کارت اعلان اختصاصی کارت حسابداری (نه در بخش‌های دیگر)
        self.assertEqual(content.count("id='acc-credentials-notice'"), 1)
        self.assertIn("اعتبارنامهٔ حسابداری ذخیره شد", content)
        # در درخواست بعدی دیگر نباید نمایش داده شود (یک‌بارمصرف)
        resp2 = self.client.get(reverse("core:profile"))
        self.assertNotIn("id='acc-credentials-notice'", resp2.content.decode("utf-8"))

    def test_error_notice_shown_only_in_security_section(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("core:profile"), {
            "action": "acc_credentials",
            "username": "acconce2",
            "password": "S3cret!pass",
            "confirm_password": "different123",
        })
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("core:profile"))
        content = resp.content.decode("utf-8")
        self.assertEqual(content.count("id='acc-credentials-notice'"), 1)
        self.assertIn("کلمه عبور و تکرار آن یکسان نیستند", content)

    def test_credentials_scoped_only_to_accounting(self):
        """اعتبارنامهٔ حسابداری هیچ تاثیری روی ورود اصلی سایت ندارد."""
        self.user.acc_username = "acchosein"
        self.user.set_acc_password("S3cret!pass")
        self.user.save()
        # ورود اصلی سایت همچنان مستقل است: USERNAME_FIELD شماره موبایل است و
        # acc_username/acc_password در مسیر auth اصلی نقشی ندارند.
        self.assertEqual(User.USERNAME_FIELD, "mobile_number")
        self.assertFalse(self.user.check_password("S3cret!pass"))  # رمز اصلی usable نیست

    def test_audit_log_on_first_login(self):
        self.user.acc_username = "acchosein"
        self.user.set_acc_password("S3cret!pass")
        self.user.save()
        org = services.get_or_create_org(self.user)
        fy = services.create_fiscal_year(org, 1405, is_default=True)
        self.client.force_login(self.user)
        self.client.post(reverse("accounting:login", args=[fy.id]),
                         {"username": "acchosein", "password": "S3cret!pass"})
        self.assertTrue(AuditLog.objects.filter(action="login").exists())


class AccResetPasswordTests(TestCase):
    """دکمهٔ «ریست کلمهٔ عبور» (پروفایل ← اطلاعات امنیتی).

    برای کاربرِ دارای اعتبارنامه، کلمهٔ عبور فراموش‌شده بدون نیاز به رمز فعلی
    بازنشانی می‌شود؛ نام کاربری دست‌نخورده می‌ماند و در فرم نمایش داده می‌شود.
    دکمهٔ «ارسال کلمهٔ عبور به من» کاملاً حذف شده است.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(mobile_number="09121110021")
        cls.staff = User.objects.create_user(mobile_number="09121110022",
                                             is_staff=True)

    def _set_credentials(self):
        self.user.acc_username = "accforget"
        self.user.set_acc_password("S3cret!pass")
        self.user.save()

    def test_send_button_removed_and_reset_shown(self):
        """دکمهٔ «ارسال کلمهٔ عبور به من» حذف و ریست جایگزین آن شده است."""
        self._set_credentials()
        self.client.force_login(self.user)
        resp = self.client.get(reverse("core:profile"))
        content = resp.content.decode("utf-8")
        self.assertNotIn("acc_send_password", content)
        self.assertNotIn("ارسال کلمهٔ عبور به من", content)
        self.assertContains(resp, "acc-reset-btn")
        self.assertContains(resp, "ریست کلمهٔ عبور")

    def test_username_always_prefilled_and_readonly_in_reset(self):
        """نام کاربری در فرم ریست همیشه نمایش داده می‌شود (readonly)."""
        self._set_credentials()
        self.client.force_login(self.user)
        resp = self.client.get(reverse("core:profile"))
        content = resp.content.decode("utf-8")
        self.assertIn("accforget", content)
        self.assertIn("readonly", content)

    def test_reset_without_current_password(self):
        """ریست بدون کلمهٔ عبور فعلی: رمز جدید ثبت و رمز قبلی باطل می‌شود."""
        from tickets.models import Ticket

        self._set_credentials()
        self.client.force_login(self.user)
        resp = self.client.post(reverse("core:profile"), {
            "action": "acc_reset_password",
            "password": "BrandNewPass9",
            "confirm_password": "BrandNewPass9",
        }, follow=True)
        self.assertContains(resp, "بازنشانی شد")
        self.user.refresh_from_db()
        self.assertEqual(self.user.acc_username, "accforget")  # نام کاربری ثابت
        self.assertTrue(self.user.check_acc_password("BrandNewPass9"))
        self.assertFalse(self.user.check_acc_password("S3cret!pass"))  # قبلی باطل
        # هیچ تیکتی ساخته نشده
        self.assertFalse(Ticket.objects.filter(author=self.user).exists())

    def test_reset_rejected_without_credentials(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("core:profile"), {
            "action": "acc_reset_password",
            "password": "BrandNewPass9",
            "confirm_password": "BrandNewPass9",
        }, follow=True)
        self.assertContains(resp, "اعتبارنامهٔ حسابداری تعریف نکرده")

    def test_reset_rejects_weak_password(self):
        self._set_credentials()
        self.client.force_login(self.user)
        resp = self.client.post(reverse("core:profile"), {
            "action": "acc_reset_password",
            "password": "short1x",
            "confirm_password": "short1x",
        }, follow=True)
        self.assertContains(resp, "حداقل ۸ کاراکتر")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_acc_password("S3cret!pass"))  # دست‌نخورده

    def test_reset_rejects_mismatch(self):
        self._set_credentials()
        self.client.force_login(self.user)
        resp = self.client.post(reverse("core:profile"), {
            "action": "acc_reset_password",
            "password": "BrandNewPass9",
            "confirm_password": "Different999",
        }, follow=True)
        self.assertContains(resp, "یکسان نیستند")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_acc_password("S3cret!pass"))
