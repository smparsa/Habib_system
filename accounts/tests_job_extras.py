"""تست‌های فیلد جدید GPS محل کار، عکس پروفایل شغل و استتوس‌های ۲۴ ساعته.

پوشش:
- ثبت مختصات GPS به‌صورت مجزا برای هر شغل (job_add و job_edit)
- شغل «بدون شغل / بیکار» GPS ندارد
- مختصات نامعتبر ثبت نمی‌شود ولی شغل ذخیره می‌شود
- آپلود عکس پروفایل شغل (فقط یکی) و حذف آن با پاک‌شدن فایل
- انتشار چند استتوس برای هر شغل + انقضای خودکار پس از ۲۴ ساعت + حذف دستی
- پاک‌سازی تنبل استتوس‌های منقضی (JobStatus.purge_expired)
"""

import os
import shutil
import tempfile
from datetime import timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Job, JobStatus, User
from jobs.models import Industry, JobCategory, JobSpecialization, JobTitle, Sector

_MEDIA_TMP = tempfile.mkdtemp(prefix="habib_media_test_")


@override_settings(MEDIA_ROOT=_MEDIA_TMP)
class JobExtraFeaturesTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_TMP, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09129990010")
        self.profile = self.user.profile
        self.client.force_login(self.user)
        self.sector = Sector.objects.create(name="فناوری اطلاعات", code="IT2")
        self.industry = Industry.objects.create(
            sector=self.sector, name="نرم‌افزار", code="SW2"
        )
        self.category = JobCategory.objects.create(
            industry=self.industry, name="توسعه", code="DEV2"
        )
        self.title = JobTitle.objects.create(
            category=self.category, name="برنامه‌نویس", code="PRG2"
        )
        self.spec = JobSpecialization.objects.create(
            title=self.title, name="توسعه‌دهندهٔ وب", code="WEB2"
        )

    def png(self, name="photo.png"):
        payload = bytes.fromhex(
            "89504e470d0a1a0a0000000d494844520000000100000001080600000"
            "01f15c4890000000d4944415478da63fcffff3f030005020100b9a1db"
            "690d0000000049454e44ae426082"
        )
        return SimpleUploadedFile(name, payload, content_type="image/png")

    def _payload(self, **overrides):
        data = {
            "sector_id": str(self.sector.pk),
            "industry_id": str(self.industry.pk),
            "category_id": str(self.category.pk),
            "occupation_title_id": str(self.title.pk),
            "specialization_id": str(self.spec.pk),
            "work_same_as_residence": "",
            "work_country": "ایران",
            "work_province": "تهران",
            "work_city": "تهران",
            "work_address": "خیابان آزادی ۱۲",
            "free_country": "ایران",
            "free_province": "تهران",
            "free_city": "تهران",
            "free_address": "کارگاه آزاد، خیابان کار ۵",
            "work_gps_latitude": "",
            "work_gps_longitude": "",
            "work_gps_accuracy": "",
            "free_gps_latitude": "",
            "free_gps_longitude": "",
            "free_gps_accuracy": "",
        }
        data.update(overrides)
        return data

    # --- GPS -------------------------------------------------------------- #
    def test_job_add_with_gps(self):
        # حالت پیش‌فرض (ب — شغل آزاد): مختصات در فیلدهای مجزای free_gps_* ثبت می‌شود
        resp = self.client.post(
            reverse("accounts:job_add"),
            self._payload(
                free_gps_latitude="35.6892",
                free_gps_longitude="51.3890",
                free_gps_accuracy="12",
            ),
        )
        self.assertEqual(self.profile.jobs.count(), 1, resp)
        job = self.profile.jobs.get()
        self.assertEqual(job.free_gps_latitude, 35.6892)
        self.assertEqual(job.free_gps_longitude, 51.3890)
        self.assertEqual(job.free_gps_accuracy, 12)
        self.assertIsNotNone(job.free_gps_updated_at)
        self.assertTrue(job.has_gps)
        self.assertTrue(job.has_free_gps)
        # GPS بخش «ج» در حالت «ب» پاک است (بخش‌ها مجزا هستند)
        self.assertIsNone(job.work_gps_latitude)

    def test_job_add_without_gps_keeps_previous_gps_on_edit(self):
        self.client.post(
            reverse("accounts:job_add"),
            self._payload(free_gps_latitude="35.6892", free_gps_longitude="51.3890"),
        )
        job = self.profile.jobs.get()
        first_saved_at = job.free_gps_updated_at
        # ویرایش بدون ارسال GPS → مختصات قبلی دست‌نخورده می‌ماند
        resp = self.client.post(
            reverse("accounts:job_edit", args=[job.id]),
            self._payload(free_gps_latitude="", free_gps_longitude=""),
        )
        job.refresh_from_db()
        self.assertEqual(job.free_gps_latitude, 35.6892, resp)
        self.assertEqual(job.free_gps_updated_at, first_saved_at)

    def test_invalid_gps_is_ignored(self):
        resp = self.client.post(
            reverse("accounts:job_add"),
            self._payload(
                free_gps_latitude="200.0",  # خارج از بازهٔ ۹۰-
                free_gps_longitude="not-a-number",
            ),
        )
        self.assertEqual(self.profile.jobs.count(), 1, resp)
        job = self.profile.jobs.get()
        self.assertIsNone(job.free_gps_latitude)
        self.assertIsNone(job.free_gps_longitude)
        self.assertFalse(job.has_gps)

    def test_unemployed_job_has_no_gps(self):
        # ثبت واقعی «بدون شغل»: طبق رفتار فرم/JS، تیک «بدون شغل» یعنی هیچ انتخابی
        # از فهرست سلسله‌مراتبی (و جزئیات شغلی) ارسال نمی‌شود.
        resp = self.client.post(
            reverse("accounts:job_add"),
            self._payload(
                is_unemployed="on",
                employment_mode="unemployed",
                sector_id="",
                industry_id="",
                category_id="",
                occupation_title_id="",
                specialization_id="",
                free_gps_latitude="35.6892",
                free_gps_longitude="51.3890",
            ),
        )
        self.assertEqual(self.profile.jobs.count(), 1, resp)
        job = self.profile.jobs.get()
        self.assertTrue(job.is_unemployed)
        self.assertIsNone(job.free_gps_latitude)
        self.assertIsNone(job.free_gps_longitude)
        self.assertIsNone(job.work_gps_latitude)

    # --- موقعیت مکانی بخش «ب» (شغل آزاد) ----------------------------------- #
    def test_free_location_saved_independently_from_employee_location(self):
        """حالت رادیوی «ج»: فقط مقادیر بخش ج ذخیره می‌شود و بخش ب پاک می‌ماند."""
        resp = self.client.post(
            reverse("accounts:job_add"),
            self._payload(
                employment_mode="employee",
                work_province="تهران", work_city="تهران", work_address="آدرس سازمان کارفرما",
                free_province="", free_city="", free_address="",
            ),
        )
        self.assertEqual(self.profile.jobs.count(), 1, resp)
        job = self.profile.jobs.get()
        # بخش «ج»
        self.assertEqual(job.work_province, "تهران")
        self.assertEqual(job.work_city, "تهران")
        self.assertEqual(job.work_address, "آدرس سازمان کارفرما")
        # بخش «ب» در حالت «ج» پاک است (بخش‌ها مجزا هستند)
        self.assertEqual(job.free_province, "")
        self.assertEqual(job.free_city, "")
        self.assertEqual(job.free_address, "")

    def test_free_mode_saves_only_free_location(self):
        """حالت رادیوی «ب»: فقط مقادیر بخش ب ذخیره می‌شود و بخش ج پاک می‌ماند."""
        resp = self.client.post(
            reverse("accounts:job_add"),
            self._payload(
                employment_mode="free",
                work_province="", work_city="", work_address="",
                free_province="البرز", free_city="کرج", free_address="آدرس کارگاه آزاد",
            ),
        )
        self.assertEqual(self.profile.jobs.count(), 1, resp)
        job = self.profile.jobs.get()
        # بخش «ب»
        self.assertEqual(job.free_province, "البرز")
        self.assertEqual(job.free_city, "کرج")
        self.assertEqual(job.free_address, "آدرس کارگاه آزاد")
        self.assertEqual(job.free_country, "ایران")
        # بخش «ج» در حالت «ب» پاک است (بخش‌ها مجزا هستند)
        self.assertEqual(job.work_province, "")
        self.assertEqual(job.work_city, "")
        self.assertEqual(job.work_address, "")
        self.assertFalse(job.work_same_as_residence)

    def test_free_address_required_in_free_mode(self):
        """«آدرس کامل» در بخش ب الزامی است (حالت رادیوی «ب»)."""
        self.client.post(
            reverse("accounts:job_add"),
            self._payload(employment_mode="free", free_address=""),
        )
        self.assertEqual(self.profile.jobs.count(), 0)
        self.assertContains(
            self.client.get(reverse("core:profile")),
            "تکمیل «آدرس کامل محل کار» در بخش «ب) شغل آزاد» الزامی است.",
        )

    def test_free_province_city_required_in_free_mode(self):
        """استان و شهرِ محل کارِ بخش ب هم در حالت «ب» الزامی‌اند (هیچ ارتباطی با ج)."""
        self.client.post(
            reverse("accounts:job_add"),
            self._payload(employment_mode="free", free_province="", free_city=""),
        )
        self.assertEqual(self.profile.jobs.count(), 0)
        self.assertContains(
            self.client.get(reverse("core:profile")),
            "تکمیل «استان» و «شهر/شهرستان» محل کارِ بخش «ب) شغل آزاد» الزامی است.",
        )

    def test_employee_mode_requires_employee_location(self):
        """در حالت رادیوی «ج»، الزامِ مکان فقط روی بخش «ج» است؛ مقادیر ب نقشی ندارند."""
        resp = self.client.post(
            reverse("accounts:job_add"),
            self._payload(
                employment_mode="employee",
                work_province="", work_city="",
                free_province="البرز", free_city="کرج", free_address="آدرس کارگاه آزاد",
            ),
        )
        self.assertEqual(self.profile.jobs.count(), 0, resp)
        self.assertContains(
            self.client.get(reverse("core:profile")),
            "تکمیل «استان» و «شهر/شهرستان» محل کار برای ذخیرهٔ شغل الزامی است.",
        )

    def test_employee_mode_without_catalog_is_allowed(self):
        """حالت «ج» بدون انتخاب از فهرست سلسله‌مراتبی هم ثبت می‌شود؛ عنوان از سازمان.

        قبلاً در این حالت پیام خطای «شغل را از فهرست سلسله‌مراتبی انتخاب کنید…»
        اشتباهی نمایش داده می‌شد؛ اکنون شغل ذخیره و نوع ثبت «employee» روی مدل
        نگه داشته می‌شود تا در کارت شغل نمایش داده شود.
        """
        resp = self.client.post(
            reverse("accounts:job_add"),
            self._payload(
                employment_mode="employee",
                organization="شرکت فولاد",
                sector_id="", industry_id="", category_id="",
                occupation_title_id="", specialization_id="",
            ),
        )
        self.assertEqual(self.profile.jobs.count(), 1, resp)
        job = self.profile.jobs.get()
        self.assertEqual(job.employment_mode, "employee")
        self.assertFalse(job.is_unemployed)
        self.assertIsNone(job.sector_id)
        self.assertEqual(job.title, "شرکت فولاد — کارمند")
        # پیام خطای کاتالوگ نباید ظاهر شود
        page = self.client.get(reverse("core:profile"))
        self.assertNotContains(
            page, "شغل را از فهرست سلسله‌مراتبی انتخاب کنید",
        )
        # کارت شغل بِجِ «ج) شغل وابسته (کارمندی)» دارد
        self.assertContains(page, "ج) شغل وابسته (کارمندی)")
        # دکمهٔ «انتشار استتوس» از کارت شغل حذف شده است
        self.assertNotContains(page, "انتشار استتوس")

    def test_employment_mode_badge_on_job_card(self):
        """کارت شغلِ بخش «ب» بِج «ب) شغل آزاد» دارد و mode روی مدل ذخیره شده است."""
        self.client.post(
            reverse("accounts:job_add"),
            self._payload(employment_mode="free"),
        )
        job = self.profile.jobs.get()
        self.assertEqual(job.employment_mode, "free")
        page = self.client.get(reverse("core:profile"))
        self.assertContains(page, "ب) شغل آزاد")

    def test_free_location_never_copied_from_residence(self):
        """پیش‌فرض «همان محل سکونت» فقط بخش «ج» را پر می‌کند؛ بخش ب مستقل می‌ماند."""
        self.profile.province = "تهران"
        self.profile.city = "کرج"
        self.profile.address = "آدرس محل زندگی"
        self.profile.save()
        resp = self.client.post(
            reverse("accounts:job_add"),
            self._payload(
                work_same_as_residence="on",
                work_province="", work_city="", work_address="",
                free_province="", free_city="", free_address="",  # بخش ب تکمیل نشده → رد می‌شود
            ),
        )
        self.assertEqual(self.profile.jobs.count(), 0)
        self.assertContains(
            self.client.get(reverse("core:profile")),
            "تکمیل «آدرس کامل محل کار» در بخش «ب) شغل آزاد» الزامی است.",
        )

    def test_unemployed_job_clears_free_location_too(self):
        resp = self.client.post(
            reverse("accounts:job_add"),
            self._payload(
                is_unemployed="on",
                employment_mode="unemployed",
                sector_id="",
                industry_id="",
                category_id="",
                occupation_title_id="",
                specialization_id="",
                free_province="البرز",
                free_city="کرج",
                free_address="آدرس آزاد",
            ),
        )
        self.assertEqual(self.profile.jobs.count(), 1, resp)
        job = self.profile.jobs.get()
        self.assertTrue(job.is_unemployed)
        self.assertEqual(job.free_province, "")
        self.assertEqual(job.free_city, "")
        self.assertEqual(job.free_address, "")

    # --- عکس پروفایل شغل --------------------------------------------------- #
    def test_job_photo_upload_and_delete(self):
        # آپلود با فایل (فرم شغل با enctype='multipart/form-data' ارسال می‌شود)
        resp = self.client.post(
            reverse("accounts:job_add"),
            {**self._payload(), "photo": self.png("job.png")},
        )
        self.assertEqual(self.profile.jobs.count(), 1, resp)
        job = self.profile.jobs.get()
        self.assertTrue(job.photo)
        saved_path = job.photo.path
        self.assertTrue(os.path.exists(saved_path))
        self.assertIn("jobs/", job.photo.name)

        # حذف عکس: فایل هم از دیسک پاک می‌شود
        resp = self.client.post(reverse("accounts:job_photo_delete", args=[job.id]))
        self.assertEqual(resp.status_code, 302)
        job.refresh_from_db()
        self.assertFalse(job.photo)
        self.assertFalse(os.path.exists(saved_path))

    def test_job_photo_add_from_card(self):
        """بارگذاری عکس پروفایل مستقیماً از کارت شغل (مشابه «افزودن استتوس")."""
        job = self._create_job()
        self.assertFalse(job.photo)
        resp = self.client.post(
            reverse("accounts:job_photo_add", args=[job.id]),
            {"photo": self.png("fromcard.png")},
        )
        self.assertEqual(resp.status_code, 302, resp)
        job.refresh_from_db()
        self.assertTrue(job.photo)
        old_path = job.photo.path
        # تعویض: فایل قبلی حذف و نسخهٔ جدید ذخیره می‌شود (فقط یک عکس برای هر شغل)
        resp = self.client.post(
            reverse("accounts:job_photo_add", args=[job.id]),
            {"photo": self.png("replaced.png")},
        )
        self.assertEqual(resp.status_code, 302, resp)
        job.refresh_from_db()
        self.assertTrue(job.photo)
        self.assertEqual(os.path.basename(job.photo.name), "replaced.png")
        self.assertFalse(os.path.exists(old_path))
        self.assertTrue(os.path.exists(job.photo.path))

    def test_job_photo_add_from_card_requires_file(self):
        job = self._create_job()
        resp = self.client.post(reverse("accounts:job_photo_add", args=[job.id]), {})
        self.assertEqual(resp.status_code, 302)
        job.refresh_from_db()
        self.assertFalse(job.photo)

    def test_job_photo_add_owner_only(self):
        job = self._create_job()
        other = User.objects.create_user(mobile_number="09129990012")
        self.client.force_login(other)
        resp = self.client.post(
            reverse("accounts:job_photo_add", args=[job.id]),
            {"photo": self.png()},
        )
        self.assertEqual(resp.status_code, 404)
        job.refresh_from_db()
        self.assertFalse(job.photo)

    def test_employee_job_photo_and_gps_in_card(self):
        """شغل «ج»: عکس پروفایل + مختصات GPS هم برای آن قابل ثبت است (مثل «ب")."""
        resp = self.client.post(
            reverse("accounts:job_add"),
            self._payload(
                employment_mode="employee",
                organization="شرکت برق",
                sector_id="", industry_id="", category_id="",
                occupation_title_id="", specialization_id="",
                work_gps_latitude="35.6892",
                work_gps_longitude="51.3890",
                work_gps_accuracy="8",
                photo=self.png("emp.png"),
            ),
        )
        self.assertEqual(self.profile.jobs.count(), 1, resp)
        job = self.profile.jobs.get()
        self.assertEqual(job.employment_mode, "employee")
        self.assertTrue(job.has_gps)
        self.assertTrue(job.photo)
        # کارت شغل در پروفایل: بِج GPS؛ دکمه‌های تعویض/انتشار عکس و استتوس حذف شده‌اند
        page = self.client.get(reverse("core:profile"))
        self.assertContains(page, "GPS: 35.689200, 51.389000")
        self.assertNotContains(page, "تعویض عکس پروفایل")

    def test_free_mode_gps_saved(self):
        """در حالت «ب» (شغل آزاد) مختصات در فیلد مجزای free_gps_* ذخیره می‌شود."""
        resp = self.client.post(
            reverse("accounts:job_add"),
            self._payload(
                employment_mode="free",
                work_province="", work_city="", work_address="",
                free_gps_latitude="34.5",
                free_gps_longitude="50.2",
                free_gps_accuracy="20",
            ),
        )
        self.assertEqual(self.profile.jobs.count(), 1, resp)
        job = self.profile.jobs.get()
        self.assertEqual(job.employment_mode, "free")
        self.assertEqual(job.free_gps_latitude, 34.5)
        self.assertEqual(job.free_gps_longitude, 50.2)
        self.assertEqual(job.free_gps_accuracy, 20)
        # GPS بخش «ج» در حالت «ب» پاک است
        self.assertIsNone(job.work_gps_latitude)
        self.assertIsNone(job.work_gps_longitude)

    def test_free_and_work_gps_are_independent(self):
        """GPS بخش «ب» و «ج» کاملاً مجزا هستند: هر بخش مختصات خودش را می‌گیرد و
        بخشِ غیرفعال پاک می‌شود (انتقال GPS از یک بخش به بخش دیگر ممنوع است)."""
        self.client.post(
            reverse("accounts:job_add"),
            self._payload(
                employment_mode="employee",
                organization="شرکت گاز",
                sector_id="", industry_id="", category_id="",
                occupation_title_id="", specialization_id="",
                work_gps_latitude="35.7",
                work_gps_longitude="51.4",
                work_gps_accuracy="10",
                free_gps_latitude="34.6",
                free_gps_longitude="50.3",
            ),
        )
        job = self.profile.jobs.get()
        # فقط GPS بخش «ج» ذخیره شده است
        self.assertEqual(job.work_gps_latitude, 35.7)
        self.assertEqual(job.work_gps_longitude, 51.4)
        self.assertIsNone(job.free_gps_latitude)
        self.assertIsNone(job.free_gps_longitude)

    def test_each_job_has_independent_gps(self):
        """GPS برای هر شغل (۱/۲/۳) مجزا ثبت می‌شود — شغل جدید، مختصات جدید."""
        self.client.post(
            reverse("accounts:job_add"),
            self._payload(free_gps_latitude="35.0", free_gps_longitude="51.0"),
        )
        # شغل دوم با زنجیرهٔ کاتالوگ متفاوت (کد اختصاصی تکراری رد می‌شود)؛
        # تخصصِ پیش‌فرض به عنوان اول تعلق دارد و باید حذف شود تا زنجیره سازگار بماند
        title2 = JobTitle.objects.create(
            category=self.category, name="طراح", code="DSN2"
        )
        self.client.post(
            reverse("accounts:job_add"),
            self._payload(
                occupation_title_id=str(title2.pk),
                specialization_id="",
                free_gps_latitude="36.5", free_gps_longitude="52.5",
            ),
        )
        jobs = list(self.profile.jobs.order_by("created_at"))
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0].free_gps_latitude, 35.0)
        self.assertEqual(jobs[1].free_gps_latitude, 36.5)

    def test_job_edit_mode_context(self):
        """?edit=<id>: فرم پروفایل به حالت ویرایش می‌رود (بنر + دادهٔ JSON برای JS)."""
        job = self._create_job()
        resp = self.client.get(reverse("core:profile"), {"edit": job.id})
        self.assertContains(resp, "ویرایش شغل:")
        self.assertContains(resp, "hb-job-edit-data")
        # شغلِ بیکار قابل ویرایش نیست → حالت عادی می‌ماند.
        # (گزینهٔ «بدون شغل» فقط وقتی مجاز است که کاربر شغلی نداشته باشد؛
        # پس ابتدا شغل فعلی حذف می‌شود.)
        self.client.post(reverse("accounts:job_delete", args=[job.id]))
        self.client.post(
            reverse("accounts:job_add"),
            self._payload(
                is_unemployed="on", employment_mode="unemployed",
                sector_id="", industry_id="", category_id="",
                occupation_title_id="", specialization_id="",
            ),
        )
        uj = self.profile.jobs.filter(is_unemployed=True).first()
        self.assertIsNotNone(uj)
        resp = self.client.get(reverse("core:profile"), {"edit": uj.id})
        self.assertNotContains(resp, "ویرایش شغل:")

    def test_job_delete_removes_photo_file(self):
        resp = self.client.post(
            reverse("accounts:job_add"),
            {**self._payload(), "photo": self.png()},
        )
        self.assertEqual(self.profile.jobs.count(), 1, resp)
        job = self.profile.jobs.get()
        saved_path = job.photo.path
        self.client.post(reverse("accounts:job_delete", args=[job.id]))
        self.assertEqual(self.profile.jobs.count(), 0)
        self.assertFalse(os.path.exists(saved_path))

    # --- استتوس ۲۴ ساعته --------------------------------------------------- #
    def _create_job(self):
        self.client.post(reverse("accounts:job_add"), self._payload())
        return self.profile.jobs.get()

    def test_status_add_multiple(self):
        job = self._create_job()
        for i in range(3):
            resp = self.client.post(
                reverse("accounts:job_status_add", args=[job.id]),
                {"caption": f"استتوس {i}", "image": self.png(f"s{i}.png")},
            )
            self.assertEqual(resp.status_code, 302)
        self.assertEqual(job.statuses.count(), 3)
        st = job.statuses.first()
        self.assertEqual(st.caption, "استتوس 2")
        # انقضا = اکنون + ۲۴ ساعت (با حاشیهٔ ۲ دقیقه‌ای)
        delta = st.expires_at - timezone.now()
        self.assertTrue(timedelta(hours=23, minutes=58) < delta <= timedelta(hours=24))

    def test_status_requires_image(self):
        job = self._create_job()
        resp = self.client.post(
            reverse("accounts:job_status_add", args=[job.id]),
            {"caption": "بی‌عکس"},
        )
        self.assertEqual(job.statuses.count(), 0, resp)

    def test_status_auto_expires_after_24h(self):
        job = self._create_job()
        self.client.post(
            reverse("accounts:job_status_add", args=[job.id]),
            {"caption": "سلام", "image": self.png()},
        )
        st = job.statuses.get()
        # هنوز زنده است
        self.assertFalse(st.is_expired)
        self.assertEqual(job.active_statuses.count(), 1)
        # ۲۵ ساعت بعد → منقضی و از فهرستِ فعال خارج می‌شود
        # صریح با «زمانِ واقعی + ۲۵ ساعت» مقایسه می‌کنیم (بدون mock؛ مقایسهٔ datetime)
        st.refresh_from_db()
        future = timezone.now() + timedelta(hours=25)
        self.assertLess(st.expires_at, future)  # انقضا حتماً پیش از «۲۵ ساعت بعد» است
        self.assertEqual(job.active_statuses.count(), 1)  # اکنون هنوز فعال است
        # پس از انقضا، از active_statuses خارج می‌شود (فیلتر expires_at__gt=اکنون)
        st.refresh_from_db()
        JobStatus.objects.filter(pk=st.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.assertEqual(job.active_statuses.count(), 0)

    def test_status_delete(self):
        job = self._create_job()
        self.client.post(
            reverse("accounts:job_status_add", args=[job.id]),
            {"caption": "", "image": self.png()},
        )
        st = job.statuses.get()
        saved_path = st.image.path
        self.assertTrue(os.path.exists(saved_path))
        resp = self.client.post(
            reverse("accounts:job_status_delete", args=[job.id, st.id])
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(JobStatus.objects.count(), 0)
        self.assertFalse(os.path.exists(saved_path))

    def test_purge_expired_removes_old_rows_only(self):
        job = self._create_job()
        self.client.post(
            reverse("accounts:job_status_add", args=[job.id]),
            {"caption": "", "image": self.png("old.png")},
        )
        old = job.statuses.get()
        old_path = old.image.path
        # تازه: منقضی‌شده ولی جوان (کمتر از ۲ ساعت) → پاک نمی‌شود
        fresh = JobStatus.objects.create(
            job=job,
            image=self.png("fresh.png"),
            expires_at=timezone.now() - timedelta(minutes=30),
        )
        fresh_path = fresh.image.path
        # «old» را هم به ۳ ساعت پیشِ منقضی می‌بریم (بیش از سقف ۲ ساعت پاک‌سازی)
        JobStatus.objects.filter(pk=old.pk).update(
            expires_at=timezone.now() - timedelta(hours=3)
        )
        old.refresh_from_db()
        # قدیمی: منقضی‌شدهٔ بیش از ۲ ساعت → پاک می‌شود؛ «تازه» فقط ۳۰ دقیقه منقضی
        # شده و با پیش‌فرض ۲ ساعتِ پاک‌سازی حذف نمی‌شود.
        JobStatus.purge_expired()
        self.assertFalse(JobStatus.objects.filter(pk=old.pk).exists())
        self.assertFalse(os.path.exists(old_path))
        self.assertTrue(JobStatus.objects.filter(pk=fresh.pk).exists())
        self.assertTrue(os.path.exists(fresh_path))

    def test_status_owner_only(self):
        job = self._create_job()
        other = User.objects.create_user(mobile_number="09129990011")
        self.client.force_login(other)
        resp = self.client.post(
            reverse("accounts:job_status_add", args=[job.id]),
            {"caption": "", "image": self.png()},
        )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(job.statuses.count(), 0)
