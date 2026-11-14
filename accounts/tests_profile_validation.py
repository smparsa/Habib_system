"""تست‌های کنترل‌های اعتبارسنجی و امنیتی پروفایل.

پوشش:
1. رادیوی «الف) بدون شغل / بیکار هستم» وقتی کاربر حداقل یک شغل دارد:
   - در قالب پروفایل غیرفعال (disabled) رندر می‌شود
   - نشانهٔ data-has-jobs='1' روی body گذاشته می‌شود
   - ارسال دستکاری‌شدهٔ is_unemployed سمت سرور رد می‌شود
2. کنترل شماره شبا با نام و نام‌خانوادگی کاربر در بخش اطلاعات مالی:
   - مغایرت → شبا تأیید و ذخیره نمی‌شود + پیام «شبا تأیید نمی‌باشد»
   - تطبیق → ذخیره و پیام موفقیت
   - بدون سرویس → هشدار (شبا ذخیره می‌شود)
3. کنترل کد ملی با نام و نام‌خانوادگی در پروفایل:
   - مغایرت → کد ملی ثبت نمی‌شود
   - تطبیق → ثبت + ثبت نتیجه در extra_data
4. قفل کد ملی پس از گرفتن پاداش تکمیل اطلاعات شخصی:
   - فیلد disabled در فرم
   - تغییر دستکاری‌شده در POST رد می‌شود و کد قدیم می‌ماند
"""

import re
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from accounts.forms import PersonalInfoForm
from accounts.models import FamilynameTbl, FirstnameTbl, Job, User
from jobs.models import Industry, JobCategory, JobSpecialization, JobTitle, Sector

# شبای نمونهٔ معتبر (۲۶ نویسه، IR + ۲۴ رقم)
VALID_IBAN = "IR820170000000000000000017"


class UnemployedRadioLockTest(TestCase):
    """رادیوی «بدون شغل» با وجود حداقل یک شغل ثبت‌شده غیرفعال است."""

    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09129990030")
        self.profile = self.user.profile

    def _add_job(self, unemployed=False):
        sector = Sector.objects.create(name="سکتا", code="TS1")
        industry = Industry.objects.create(
            sector=sector, name="صنعت", code="TI1"
        )
        category = JobCategory.objects.create(
            industry=industry, name="دسته", code="TC1"
        )
        title = JobTitle.objects.create(
            category=category, name="عنوان", code="TT1"
        )
        spec = JobSpecialization.objects.create(
            title=title, name="تخصص مرتبط", code="TW1"
        )
        Job.objects.create(
            profile=self.profile,
            sector=sector, industry=industry, category=category,
            occupation_title=title, specialization=spec,
            is_unemployed=unemployed,
            title="عنوان" if not unemployed else "",
            employment_mode="free" if not unemployed else "unemployed",
        )

    def test_radio_disabled_when_user_has_jobs(self):
        self._add_job()
        self.client.force_login(self.user)
        resp = self.client.get(reverse("core:profile"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'data-has-jobs="1"')
        html = resp.content.decode("utf-8")
        # رادیوی unemployed باید disabled باشد
        m = re.search(
            r"<input[^>]*data-job-kind-radio='unemployed'[^>]*>", html
        )
        self.assertIsNotNone(m)
        self.assertIn("disabled", m.group(0))

    def test_radio_enabled_when_user_has_no_jobs(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("core:profile"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'data-has-jobs="0"')
        html = resp.content.decode("utf-8")
        m = re.search(
            r"<input[^>]*data-job-kind-radio='unemployed'[^>]*>", html
        )
        self.assertIsNotNone(m)
        self.assertNotIn("disabled", m.group(0))

    def test_forged_unemployed_submission_is_rejected_when_jobs_exist(self):
        # کاربرِ شغل‌دار با دستکاری فرم رادیوی الف را POST می‌کند → رد می‌شود
        self._add_job()
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("accounts:job_add"),
            {
                "is_unemployed": "on",
                "employment_mode": "unemployed",
                "sector_id": "", "industry_id": "", "category_id": "",
                "occupation_title_id": "", "specialization_id": "",
                "free_province": "", "free_city": "", "free_address": "",
            },
        )
        self.assertEqual(self.profile.jobs.count(), 1)
        self.assertFalse(
            self.profile.jobs.filter(is_unemployed=True).exists(), resp
        )

    def _employee_payload(self, **overrides):
        """POST معتبر بخش «ج» (کارمندی) برای تست‌های ویرایش/حذف."""
        data = {
            "employment_mode": "employee",
            "organization": "سازمان تست",
            "work_province": "تهران",
            "work_city": "تهران",
            "work_address": "خیابان تست ۱",
            "free_province": "", "free_city": "", "free_address": "",
            "is_current": "on",
        }
        data.update(overrides)
        return data

    def _add_employee_job(self, **kwargs):
        suffix = str(getattr(self, "_job_seq", 0))
        self._job_seq = getattr(self, "_job_seq", 0) + 1
        sector = Sector.objects.create(name="سکتا۲" + suffix, code="TS2" + suffix)
        industry = Industry.objects.create(sector=sector, name="صنعت۲" + suffix, code="TI2" + suffix)
        category = JobCategory.objects.create(industry=industry, name="دسته۲" + suffix, code="TC2" + suffix)
        title = JobTitle.objects.create(category=category, name="عنوان۲" + suffix, code="TT2" + suffix)
        spec = JobSpecialization.objects.create(title=title, name="تخصص مرتبط۲" + suffix, code="TW2" + suffix)
        defaults = dict(
            profile=self.profile,
            sector=sector, industry=industry, category=category,
            occupation_title=title, specialization=spec,
            title="عنوان۲", employment_mode="employee",
            work_province="تهران", work_city="تهران", work_address="آدرس",
            is_current=True,
        )
        defaults.update(kwargs)
        return Job.objects.create(**defaults)

    def test_unemployed_default_checked_for_new_user(self):
        """کاربر جدید بدون شغل: رادیوی «الف» به‌صورت پیش‌فرض فعال (checked) است."""
        self.client.force_login(self.user)
        html = self.client.get(reverse("core:profile")).content.decode("utf-8")
        m = re.search(
            r"<input[^>]*data-job-kind-radio='unemployed'[^>]*>", html
        )
        self.assertIsNotNone(m)
        self.assertIn("checked", m.group(0))

    def test_unemployed_not_default_checked_when_user_has_jobs(self):
        """کاربر شغل‌دار: پیش‌فرض روی «ب» است و «الف» غیرفعال می‌ماند."""
        self._add_job()
        self.client.force_login(self.user)
        html = self.client.get(reverse("core:profile")).content.decode("utf-8")
        m = re.search(
            r"<input[^>]*data-job-kind-radio='unemployed'[^>]*>", html
        )
        self.assertIsNotNone(m)
        self.assertNotIn("checked", m.group(0))

    def test_forged_unemployed_edit_is_rejected_when_other_jobs_exist(self):
        """ویرایش شغل با دستکاری رادیوی الف وقتی شغل دیگری باقی است → رد می‌شود."""
        job = self._add_employee_job()
        other = self._add_employee_job()
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("accounts:job_edit", args=[job.id]),
            {
                "is_unemployed": "on",
                "employment_mode": "unemployed",
                "sector_id": "", "industry_id": "", "category_id": "",
                "occupation_title_id": "", "specialization_id": "",
                "free_province": "", "free_city": "", "free_address": "",
            },
        )
        job.refresh_from_db()
        self.assertFalse(job.is_unemployed)
        self.assertTrue(
            self.profile.jobs.filter(pk=other.pk).exists(), resp
        )

    def test_edit_without_catalog_touch_keeps_existing_chain(self):
        """ویرایش بدون تغییر فهرست (keep_chain=1): زنجیرهٔ قبلی حذف نمی‌شود."""
        job = self._add_employee_job()
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("accounts:job_edit", args=[job.id]),
            self._employee_payload(
                organization="سازمان ویرایش‌شده",
                sector_id="", industry_id="", category_id="",
                occupation_title_id="", specialization_id="",
                title="",
                keep_chain="1",
            ),
        )
        job.refresh_from_db()
        self.assertIsNotNone(job.sector_id, resp)
        self.assertIsNotNone(job.occupation_title_id)
        self.assertEqual(job.organization, "سازمان ویرایش‌شده")
        self.assertEqual(job.title, "عنوان۲")

    def test_deleting_last_current_job_reassigns_current_to_remaining(self):
        """حذفِ تنها «شغل فعلی»: یکی از مشاغل باقی‌مانده «شغل فعلی» می‌شود."""
        first = self._add_employee_job()
        second = self._add_employee_job(is_current=False)
        self.client.force_login(self.user)
        self.client.post(reverse("accounts:job_delete", args=[first.id]))
        second.refresh_from_db()
        self.assertTrue(second.is_current)
        self.assertEqual(self.profile.jobs.filter(is_current=True).count(), 1)

    def test_edit_mode_includes_catalog_chain_json(self):
        """حالت ویرایش: زنجیرهٔ کاتالوگ در JSON سمت کلاینت هم هست."""
        job = self._add_employee_job()
        self.client.force_login(self.user)
        resp = self.client.get(reverse("core:profile"), {"edit": job.id})
        self.assertContains(resp, """"sector_id": %d""" % job.sector_id)
        self.assertContains(resp, """"occupation_title_id": %d""" % job.occupation_title_id)

    def test_hire_date_uses_jalali_picker_markup(self):
        """تاریخ استخدام: ورودی شمسی + فیلد پنهانِ میلادی (تقویم شمسی)."""
        self.client.force_login(self.user)
        html = self.client.get(reverse("core:profile")).content.decode("utf-8")
        self.assertIn('data-hire-date-gregorian', html)
        self.assertIn('data-shamsi-no-age', html)


class IbanNameVerificationTest(TestCase):
    """کنترل شماره شبا با نام و نام‌خانوادگی کاربر در بخش اطلاعات مالی."""

    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09129990031")
        self.first = FirstnameTbl.objects.create(first_name_fa="علی")
        self.family = FamilynameTbl.objects.create(familyname_fa="احمدی")
        p = self.user.profile
        p.first_name = self.first
        p.last_name = self.family
        p.save()

    def _post(self, **extra):
        self.client.force_login(self.user)
        return self.client.post(
            reverse("core:profile"),
            {"action": "financial", "iban": VALID_IBAN, **extra},
            follow=True,
        )

    @mock.patch("accounts.iban_verify.verify")
    def test_mismatched_iban_is_rejected_and_not_saved(self, verify_mock):
        verify_mock.return_value = {
            "available": True, "match": False,
            "message": "نام دارندهٔ این شبا با نام شما هم‌خوانی ندارد.",
            "checked_at": "2026-01-01T00:00:00",
        }
        resp = self._post()
        self.user.profile.refresh_from_db()
        self.assertNotEqual(self.user.profile.iban, VALID_IBAN)
        self.assertEqual(
            self.user.profile.extra_data.get("iban_verify", {}).get("match"),
            False,
        )
        self.assertContains(resp, "شبا تأیید نمی‌باشد")

    @mock.patch("accounts.iban_verify.verify")
    def test_matching_iban_is_saved(self, verify_mock):
        verify_mock.return_value = {
            "available": True, "match": True,
            "message": "نام دارندهٔ حساب با نام شما هم‌خوانی دارد.",
            "checked_at": "2026-01-01T00:00:00",
        }
        resp = self._post()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.iban, VALID_IBAN)
        self.assertContains(resp, "تطبیق داده شد")

    @mock.patch("accounts.iban_verify.verify")
    def test_without_service_iban_saved_with_warning(self, verify_mock):
        verify_mock.return_value = {
            "available": False, "match": None,
            "message": "سرویس استعلام شبا پیکربندی نشده است.",
            "checked_at": "2026-01-01T00:00:00",
        }
        resp = self._post()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.iban, VALID_IBAN)
        self.assertContains(resp, "پس از فعال‌شدن سرویس استعلام")


class NationalIdNameVerificationTest(TestCase):
    """کنترل کد ملی با نام و نام‌خانوادگی: مغایرت = عدم ثبت."""

    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09129990032")
        self.profile = self.user.profile
        self.first = FirstnameTbl.objects.create(first_name_fa="علی")
        self.family = FamilynameTbl.objects.create(familyname_fa="احمدی")

    def _form_data(self):
        return {
            "first_name": str(self.first.pk),
            "last_name": str(self.family.pk),
            "national_id": "1234567890",
            "date_of_birth": "1991-05-05",
            "gender": "male",
            "citizenship": "ایران",
            "nationality": "ایران",
            "permanent_residence": "ایران",
            "religion": "islam",
            "sect": "shia",
        }

    @mock.patch("accounts.iban_verify.verify")
    def test_mismatched_national_id_is_not_saved(self, verify_mock):
        verify_mock.return_value = {
            "available": True, "match": False,
            "message": "مشخصات واردشده با کد ملی هم‌خوانی ندارد.",
            "checked_at": "2026-01-01T00:00:00",
        }
        form = PersonalInfoForm(data=self._form_data(), instance=self.profile)
        self.assertFalse(form.is_valid())
        self.assertIn("national_id", form.errors)
        self.assertIn("تأیید نمی‌شود", form.errors["national_id"][0])
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.national_id)

    @mock.patch("accounts.iban_verify.verify")
    def test_matching_national_id_is_saved_with_result(self, verify_mock):
        verify_mock.return_value = {
            "available": True, "match": True,
            "message": "هم‌خوانی دارد.",
            "checked_at": "2026-01-01T00:00:00",
        }
        form = PersonalInfoForm(data=self._form_data(), instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        profile = form.save()
        self.assertEqual(profile.national_id, "1234567890")
        self.assertEqual(
            profile.extra_data.get("national_id_verify", {}).get("match"), True
        )

    @mock.patch("accounts.iban_verify.verify")
    def test_without_service_no_record_is_kept(self, verify_mock):
        # بدون سرویس: کنترل انجام نمی‌شود و ردی در extra_data ثبت نمی‌شود
        verify_mock.return_value = {
            "available": False, "match": None,
            "message": "سرویس پیکربندی نشده است.",
            "checked_at": "2026-01-01T00:00:00",
        }
        form = PersonalInfoForm(data=self._form_data(), instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        profile = form.save()
        self.assertEqual(profile.national_id, "1234567890")
        self.assertNotIn("national_id_verify", profile.extra_data)


class NationalIdLockTest(TestCase):
    """کد ملی پس از پاداشِ تکمیل اطلاعات شخصی دیگر قابل تغییر نیست."""

    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09129990033")
        self.profile = self.user.profile
        self.first = FirstnameTbl.objects.create(first_name_fa="علی")
        self.family = FamilynameTbl.objects.create(familyname_fa="احمدی")
        self.profile.national_id = "1234567890"
        self.profile.extra_data = {"profile_completion_rewarded": True}
        self.profile.save()

    def _form_data(self, nid="1234567890"):
        return {
            "first_name": str(self.first.pk),
            "last_name": str(self.family.pk),
            "national_id": nid,
            "date_of_birth": "1991-05-05",
            "gender": "male",
            "citizenship": "ایران",
            "nationality": "ایران",
            "permanent_residence": "ایران",
            "religion": "islam",
            "sect": "shia",
        }

    def test_field_disabled_in_form_after_reward(self):
        form = PersonalInfoForm(instance=self.profile)
        self.assertTrue(form.national_id_locked)
        self.assertTrue(form.fields["national_id"].disabled)

    def test_field_not_locked_before_reward(self):
        self.profile.extra_data = {}
        self.profile.save()
        form = PersonalInfoForm(instance=self.profile)
        self.assertFalse(form.national_id_locked)
        self.assertFalse(form.fields["national_id"].disabled)

    @mock.patch("accounts.iban_verify.verify")
    def test_changed_nid_via_post_is_ignored_after_reward(self, verify_mock):
        # حتی با دستکاری POST، مقدار قدیم حفظ می‌شود
        form = PersonalInfoForm(
            data=self._form_data(nid="0987654321"), instance=self.profile
        )
        self.assertTrue(form.is_valid(), form.errors)
        profile = form.save()
        self.assertEqual(profile.national_id, "1234567890")

    def test_profile_view_rejects_forged_nid_change(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("core:profile"), self._form_data(nid="0987654321"),
            follow=True,
        )
        self.assertContains(resp, "دیگر قابل تغییر نیست")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.national_id, "1234567890")

    def test_lock_note_rendered_in_template(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("core:profile"))
        self.assertContains(resp, "دیگر قابل تغییر نیست")
