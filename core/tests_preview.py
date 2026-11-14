"""تست‌های صفحهٔ «پیش‌نمایش اطلاعات من».

- دکمهٔ پایین پروفایل به صفحهٔ پیش‌نمایش تبدیل شده است.
- صفحهٔ پیش‌نمایش همهٔ بخش‌های تکمیل‌شده را تفکیکی با چک‌باکسِ تیک‌خورده
  نمایش می‌دهد و فیلدهای خالی نمایش داده نمی‌شوند.
- ورود اجباری است؛ اطلاعات کاربر دیگران نمایش داده نمی‌شود.
"""

from django.test import TestCase
from django.urls import reverse

from accounts.models import Job, User


class ProfilePreviewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09129990077")
        self.profile = self.user.profile
        self.client.force_login(self.user)
        self.url = reverse("core:profile_preview")

    def _fill_profile(self):
        from accounts.models import FirstnameTbl, FamilynameTbl

        self.profile.first_name = FirstnameTbl.objects.create(
            first_name_fa="علی", first_name_en="Ali")
        self.profile.last_name = FamilynameTbl.objects.create(
            familyname_fa="رضایی", familyname_en="Rezaei")
        self.profile.national_id = "0012345678"
        self.profile.province = "تهران"
        self.profile.city = "تهران"
        self.profile.save()

    def test_profile_button_links_to_preview(self):
        resp = self.client.get(reverse("core:profile"))
        self.assertContains(resp, 'href="%s"' % self.url)
        self.assertContains(resp, "پیش\u200cنمایش اطلاعات من")

    def test_preview_requires_login(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_filled_fields_shown_with_checked_boxes(self):
        self._fill_profile()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "کد ملی")
        self.assertContains(resp, "0012345678")
        # چک‌باکس پیش‌فرض تیک‌خورده
        self.assertContains(resp, "checked data-pv-check")

    def test_empty_fields_are_hidden(self):
        self._fill_profile()
        resp = self.client.get(self.url)
        # بخش‌های کاملاً خالی اصلاً رندر نمی‌شوند (مثلاً مالی/سلامت)
        self.assertNotContains(resp, "اطلاعات مالی (بانکی)")
        self.assertNotContains(resp, "اطلاعات سلامت")
        # فیلد تکمیل‌نشدهٔ یک بخش فعال هم نمی‌آید (تلفن ثابت خالی است)
        self.assertNotContains(resp, "تلفن ثابت")

    def test_job_sections_appear_separately(self):
        Job.objects.create(
            profile=self.profile,
            employment_mode="free",
            title="طراح گرافیک",
            free_province="تهران",
            free_city="تهران",
            free_address="خیابان آزادی، پلاک ۱",
        )
        resp = self.client.get(self.url)
        self.assertContains(resp, "ب) شغل آزاد")
        self.assertContains(resp, "طراح گرافیک")
        self.assertContains(resp, "خیابان آزادی، پلاک ۱")
        self.assertContains(resp, "آدرس کامل محل کار (شغل آزاد)")
        # GPS ثبت نشده؛ ردیف GPS نباید بیاید
        self.assertNotContains(resp, "مختصات GPS محل کار (شغل آزاد)")

    def test_unemployed_job_section(self):
        Job.objects.create(profile=self.profile, employment_mode="unemployed",
                           is_unemployed=True)
        resp = self.client.get(self.url)
        self.assertContains(resp, "الف) بدون شغل / بیکار")
        self.assertContains(resp, "بدون شغل / بیکار هستم")

    def test_pdf_toolbar_present(self):
        resp = self.client.get(self.url)
        self.assertContains(resp, "تبدیل به PDF")
        self.assertContains(resp, "data-pv-pdf")
