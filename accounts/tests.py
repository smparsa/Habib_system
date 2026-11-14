from decimal import Decimal

from django.core.exceptions import FieldDoesNotExist
from django.db import connection, migrations
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase
from django.urls import reverse

from django.core.exceptions import ValidationError

from accounts.forms import (
    ContactInfoForm,
    FamilyInfoForm,
    LocationForm,
    PersonalInfoForm,
    UiSettingsForm,
    profile_ui_appearance,
)
from adminpanel.forms import FameNameForm
from accounts.models import (
    CityTbl,
    CountryTbl,
    FameNameTbl,
    FamilynameTbl,
    FirstnameTbl,
    Job,
    Profile,
    ProvinceTbl,
    ReservedNationalCode,
    User,
)
from jobs.models import (
    Industry,
    JobCategory,
    JobSpecialization,
    JobTitle,
    Sector,
)


class JobCoordinateRemovalTest(TestCase):
    """
    فیلدهای مختصات شغلی (عرض/طول جغرافیایی) به‌کلی از مدل و تاریخچهٔ مهاجرت
    حذف شده‌اند (جایگزین مهاجرتِ حذفِ 0023 شدند). این تست تضمین می‌کند
    بازگرداندن آن‌ها در آینده در CI شکست بخورد.
    """

    COORD_FIELDS = ("work_latitude", "work_longitude")

    def test_job_model_exposes_no_coordinate_fields(self):
        for name in self.COORD_FIELDS:
            with self.assertRaises(FieldDoesNotExist):
                Job._meta.get_field(name)
            self.assertFalse(hasattr(Job, name))

    def test_no_migration_ever_creates_job_coordinate_columns(self):
        loader = MigrationLoader(connection)
        for (app_label, migration_name), migration in loader.disk_migrations.items():
            if app_label != "accounts":
                continue
            for op in migration.operations:
                if (
                    isinstance(op, migrations.AddField)
                    and op.model_name == "job"
                    and op.name in self.COORD_FIELDS
                ):
                    self.fail(
                        f"Migration {migration_name} re-adds the removed "
                        f"column job.{op.name}"
                    )


class JobLocationRequiredTest(TestCase):
    """
    تکمیل استان و شهر/شهرستان محل کار در هر صورت (پیش‌فرض «همان محل سکونت» یا
    آدرس مجزا) برای ذخیرهٔ شغل الزامی است. وقتی «اطلاعات مکانی» پروفایل کامل است،
    محل زندگی کپی می‌شود (فقط تأیید)؛ اگر کامل نباشد، کاربر باید در همین فرم دستی
    پر کند و مقادیرِ واردشده (حتی با تیکِ «همان محل سکونت») ذخیره می‌شوند.
    """

    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09120000001")
        self.profile = self.user.profile
        self.sector = Sector.objects.create(name="فناوری اطلاعات", code="IT")
        self.industry = Industry.objects.create(
            sector=self.sector, name="نرم‌افزار", code="SW"
        )
        self.category = JobCategory.objects.create(
            industry=self.industry, name="توسعه", code="DEV"
        )
        self.title = JobTitle.objects.create(
            category=self.category, name="برنامه‌نویس", code="PRG"
        )
        self.spec = JobSpecialization.objects.create(
            title=self.title, name="توسعه‌دهندهٔ وب", code="WEB"
        )
        self.client.force_login(self.user)

    def _payload(self, **overrides):
        data = {
            "sector_id": str(self.sector.pk),
            "industry_id": str(self.industry.pk),
            "category_id": str(self.category.pk),
            "occupation_title_id": str(self.title.pk),
            "specialization_id": str(self.spec.pk),
            "organization": "شرکت نمونه",
            # رادیوی «نوع ثبت شغل»: این کلاس الزاماتِ بخش «ج» (کارمندی) را بررسی می‌کند
            "employment_mode": "employee",
            "work_same_as_residence": "",
            "work_country": "ایران",
            "work_province": "",
            "work_city": "",
            "work_address": "",
            # بخش «ب» (شغل آزاد) با فرم ارسال نمی‌شود (مجرا از بخش ج)
            "free_country": "",
            "free_province": "",
            "free_city": "",
            "free_address": "",
        }
        data.update(overrides)
        return data

    def _add(self, **overrides):
        resp = self.client.post(reverse("accounts:job_add"), self._payload(**overrides))
        # پیام خطا/تأیید بعد از ریدایرکت در صفحهٔ پروفایل رندر می‌شود
        return self.client.get(reverse("core:profile")), resp

    def test_job_requires_province_and_city(self):
        page, _ = self._add()
        self.assertEqual(self.profile.jobs.count(), 0)
        self.assertContains(
            page, "تکمیل «استان» و «شهر/شهرستان» محل کار برای ذخیرهٔ شغل الزامی است."
        )

    def test_job_saved_with_manual_province_city(self):
        page, _ = self._add(
            work_province="تهران", work_city="تهران", work_address="خیابان آزادی ۱۲",
        )
        self.assertEqual(self.profile.jobs.count(), 1)
        job = self.profile.jobs.get()
        self.assertEqual(job.work_province, "تهران")
        self.assertEqual(job.work_city, "تهران")
        self.assertEqual(job.work_address, "خیابان آزادی ۱۲")
        self.assertFalse(job.work_same_as_residence)

    def test_same_as_residence_copies_complete_profile_location(self):
        # اطلاعات مکانی پروفایل کامل است → کپی و فقط تأیید (مقادیر فرم نادیده گرفته می‌شود)
        self.profile.province = "تهران"
        self.profile.city = "کرج"
        self.profile.address = "خیابان اصلی"
        self.profile.save()
        page, _ = self._add(
            work_same_as_residence="on",
            work_province="اصفهان", work_city="اصفهان",  # باید نادیده گرفته شود
        )
        self.assertEqual(self.profile.jobs.count(), 1)
        job = self.profile.jobs.get()
        self.assertTrue(job.work_same_as_residence)
        self.assertEqual(job.work_province, "تهران")
        self.assertEqual(job.work_city, "کرج")
        self.assertEqual(job.work_address, "خیابان اصلی")

    def test_same_as_residence_with_empty_profile_uses_manual_values(self):
        # اطلاعات مکانی پروفایل خالی است؛ فیلدهای فرم خالی‌اند و کاربر دستی پر می‌کند
        page, _ = self._add(
            work_same_as_residence="on",
            work_province="اصفهان", work_city="اصفهان",
        )
        self.assertEqual(self.profile.jobs.count(), 1)
        job = self.profile.jobs.get()
        self.assertTrue(job.work_same_as_residence)
        self.assertEqual(job.work_province, "اصفهان")
        self.assertEqual(job.work_city, "اصفهان")

    def test_same_as_residence_with_empty_profile_still_requires_location(self):
        page, _ = self._add(work_same_as_residence="on")
        self.assertEqual(self.profile.jobs.count(), 0)
        self.assertContains(
            page, "تکمیل «استان» و «شهر/شهرستان» محل کار برای ذخیرهٔ شغل الزامی است."
        )

    def test_job_work_location_en_properties(self):
        # نام انگلیسیِ کشور/استان/شهرستان محل کار از جدول مرجع خوانده می‌شود تا
        # فهرستِ محل کارِ شغل‌ها با زبانِ فعالِ رابط نمایش داده شود.
        iran = CountryTbl.objects.get(country_fa="ایران")
        prov = ProvinceTbl.objects.create(
            country=iran, province_fa="تهران", province_en="Tehran"
        )
        CityTbl.objects.create(province=prov, city_fa="تهران", city_en="Tehran")
        page, _ = self._add(
            work_province="تهران", work_city="تهران", work_address="خیابان آزادی ۱۲",
        )
        self.assertEqual(self.profile.jobs.count(), 1)
        job = self.profile.jobs.get()
        self.assertEqual(job.work_country, "ایران")
        self.assertEqual(job.work_country_en, "Iran")
        self.assertEqual(job.work_province_en, "Tehran")
        self.assertEqual(job.work_city_en, "Tehran")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "data-loc-fa='تهران'")
        self.assertContains(page, "data-loc-en='Tehran'")


class PersonalInfoCountryFieldsTest(TestCase):
    """
    فیلدهای «تابعیت»، «ملیت» و «اقامت دائم» در بخش اطلاعات شخصی پروفایل: منوی
    کشویی نام کشورها از جدول مرجع CountryTbl، پیش‌فرض هر سه «ایران». «ایران» حتی
    وقتی جدول مرجع هنوز seed نشده باشد هم در فهرست حاضر است تا پیش‌فرض همیشه
    قابل انتخاب/ذخیره باشد.
    """

    FIELDS = ("citizenship", "nationality", "permanent_residence")

    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09120000002")
        self.profile = self.user.profile
        self.first = FirstnameTbl.objects.create(first_name_fa="علی")
        self.family = FamilynameTbl.objects.create(familyname_fa="احمدی")

    def _form_data(self, **overrides):
        data = {
            "first_name": str(self.first.pk),
            "last_name": str(self.family.pk),
            "father_name": str(self.first.pk),
            "mother_name": str(self.first.pk),
            "national_id": "1234567890",
            "date_of_birth": "1991-05-05",
            "gender": "male",
            "marital_status": "single",
            "citizenship": "ایران",
            "nationality": "ایران",
            "permanent_residence": "ایران",
            "religion": "islam",
            "sect": "shia",
        }
        data.update(overrides)
        return data

    def test_new_profile_defaults_to_iran(self):
        # فیلدهای مدل برای پروفایل تازه‌ساخته پیش‌فرض «ایران» دارند
        self.profile.refresh_from_db()
        for name in self.FIELDS:
            self.assertEqual(getattr(self.profile, name), "ایران")

    def test_form_initial_defaults_to_iran(self):
        form = PersonalInfoForm(instance=self.profile)
        for name in self.FIELDS:
            self.assertEqual(form.initial.get(name), "ایران")

    def test_country_table_seeded_with_full_list(self):
        # مهاجرت داده‌ای 0024 جدول مرجع را با فهرست کامل کشورها پر کرده است
        self.assertTrue(CountryTbl.objects.filter(country_fa="ایران").exists())
        self.assertGreaterEqual(CountryTbl.objects.count(), 150)
        form = PersonalInfoForm(instance=self.profile)
        for name in self.FIELDS:
            self.assertIn("ایران", dict(form.fields[name].widget.choices))

    def test_form_saves_country_fields(self):
        form = PersonalInfoForm(
            data=self._form_data(), instance=self.profile
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        for name in self.FIELDS:
            self.assertEqual(getattr(self.profile, name), "ایران")

    def test_form_saves_chosen_country(self):
        CountryTbl.objects.get_or_create(
            country_fa="امارات متحده عربی", defaults={"country_en": "UAE"}
        )
        form = PersonalInfoForm(
            data=self._form_data(nationality="امارات متحده عربی"),
            instance=self.profile,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.nationality, "امارات متحده عربی")
        self.assertEqual(self.profile.citizenship, "ایران")

    def test_form_saves_bilingual_country_en(self):
        # «کشور» به‌صورت دوزبانه ذخیره می‌شود: مقدار رسمی فارسی در خودِ فیلد و
        # نام انگلیسیِ هم‌ارز در extra_data («*_en») تا بج‌های خلاصه با زبانِ فعال
        # رابط نمایش داده شوند (هدف‌گیری تیکت‌ها روی مقدار فارسی دست‌نخورده می‌ماند).
        CountryTbl.objects.get_or_create(
            country_fa="امارات متحده عربی", defaults={"country_en": "UAE"}
        )
        form = PersonalInfoForm(
            data=self._form_data(
                nationality="امارات متحده عربی", permanent_residence="امارات متحده عربی"
            ),
            instance=self.profile,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        self.assertEqual(
            (self.profile.extra_data or {}).get("nationality_en"), "United Arab Emirates"
        )
        self.assertEqual(
            (self.profile.extra_data or {}).get("permanent_residence_en"), "United Arab Emirates"
        )
        # تابعیت همچنان ایران → نسخهٔ انگلیسی‌اش هم ذخیره می‌شود
        self.assertEqual(
            (self.profile.extra_data or {}).get("citizenship_en"), "Iran"
        )

    def test_country_en_properties_fallback_to_reference_table(self):
        # دادهٔ قدیمی که extra_data ندارد: نام انگلیسی از جدول مرجع خوانده می‌شود
        self.profile.country = "آلمان"
        self.profile.citizenship = "آلمان"
        self.profile.nationality = ""
        self.profile.extra_data = {}
        self.profile.save()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.country_en, "Germany")
        self.assertEqual(self.profile.citizenship_en, "Germany")
        self.assertEqual(self.profile.nationality_en, "")

    def test_country_options_carry_bilingual_labels(self):
        # هر گزینه برچسب فارسی (data-fa) و انگلیسی (data-en) دارد تا app.js با
        # تغییر زبان برچسب‌ها را عوض کند و جستجوی تایپی به هر دو زبان کار کند
        form = PersonalInfoForm(instance=self.profile)
        html = str(form["citizenship"])
        self.assertIn('data-fa="ایران"', html)
        self.assertIn('data-en="Iran"', html)
        self.assertIn('data-en="Germany"', html)
        self.assertIn('value="آلمان"', html)

    def test_country_fields_are_required(self):
        form = PersonalInfoForm(
            data=self._form_data(
                citizenship="", nationality="", permanent_residence=""
            ),
            instance=self.profile,
        )
        self.assertFalse(form.is_valid())
        for name in self.FIELDS:
            self.assertIn(name, form.errors)
            self.assertEqual(
                form.errors[name][0], "کشور مورد نظر را از فهرست انتخاب کنید."
            )

    def test_backfill_migration_fills_country_en_for_existing_profiles(self):
        # دادهٔ قدیمی (بدون extra_data) با اجرای مهاجرت 0025 دوزبانه می‌شود:
        # نام انگلیسیِ کشور از جدول مرجع در extra_data («*_en») پُر می‌شود.
        import importlib

        from django.apps import apps

        self.profile.country = "آلمان"
        self.profile.citizenship = "آلمان"
        self.profile.nationality = ""
        self.profile.permanent_residence = ""
        self.profile.extra_data = {}
        self.profile.save()
        mod = importlib.import_module(
            "accounts.migrations.0025_backfill_profile_country_en"
        )
        mod.backfill_country_en(apps, None)
        self.profile.refresh_from_db()
        extra = self.profile.extra_data or {}
        self.assertEqual(extra.get("country_en"), "Germany")
        self.assertEqual(extra.get("citizenship_en"), "Germany")
        # فیلدهای خالی/بدون رکورد مرجع دست‌نخورده می‌مانند
        self.assertNotIn("nationality_en", extra)
        self.assertNotIn("permanent_residence_en", extra)

    def test_profile_summary_shows_country_fields_bilingually(self):
        form = PersonalInfoForm(data=self._form_data(), instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.client.force_login(self.user)
        resp = self.client.get(reverse("core:profile"))
        # بج‌های خلاصه: مقدار فارسی + نسخهٔ انگلیسی در data-loc-en تا app.js با
        # تغییر زبان رابط متن را عوض کند
        for label in ("تابعیت", "ملیت", "اقامت دائم"):
            self.assertContains(resp, label)
            self.assertContains(resp, "data-loc-fa='ایران'")
            self.assertContains(resp, "data-loc-en='Iran'")

    def test_location_form_saves_bilingual_country(self):
        # ذخیرهٔ «اطلاعات مکانی» (محل سکونت): Profile.country فارسی می‌ماند و
        # نام انگلیسیِ هم‌ارز در extra_data["country_en"] ذخیره می‌شود.
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("core:profile"),
            {
                "action": "location",
                "country": "ایران",
                "province": "تهران",
                "city": "تهران",
                "address": "خیابان آزادی ۱۲",
            },
        )
        self.assertIn(resp.status_code, (301, 302))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.country, "ایران")
        self.assertEqual(self.profile.province, "تهران")
        self.assertEqual((self.profile.extra_data or {}).get("country_en"), "Iran")

    def test_location_form_saves_bilingual_province_city(self):
        # استان/شهرستان هم دوزبانه ذخیره می‌شوند: مقدار فارسی در خودِ فیلد و نام
        # انگلیسیِ هم‌ارز در extra_data (province_en/city_en) تا ویجتِ موقعیت و
        # بج‌ها با زبانِ فعالِ رابط نمایش داده شوند.
        iran = CountryTbl.objects.get(country_fa="ایران")
        prov = ProvinceTbl.objects.create(
            country=iran, province_fa="تهران", province_en="Tehran"
        )
        CityTbl.objects.create(province=prov, city_fa="کرج", city_en="Karaj")
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("core:profile"),
            {
                "action": "location",
                "country": "ایران",
                "province": "تهران",
                "city": "کرج",
                "address": "خیابان آزادی ۱۲",
            },
        )
        self.assertIn(resp.status_code, (301, 302))
        self.profile.refresh_from_db()
        extra = self.profile.extra_data or {}
        self.assertEqual(self.profile.province, "تهران")
        self.assertEqual(self.profile.city, "کرج")
        self.assertEqual(extra.get("province_en"), "Tehran")
        self.assertEqual(extra.get("city_en"), "Karaj")

    def test_location_province_city_selects_are_bilingual(self):
        # گزینه‌های «استان» و «شهر/شهرستان» برچسب دوزبانه دارند (data-fa/data-en)
        # و روی گروه‌های <optgroup> شهرستان‌ها هم نام فارسی/انگلیسیِ استان می‌نشیند
        # تا app.js با تغییر زبان برچسب‌ها را عوض کند (مقدارِ ارسالی فارسی می‌ماند).
        iran = CountryTbl.objects.get(country_fa="ایران")
        prov = ProvinceTbl.objects.create(
            country=iran, province_fa="تهران", province_en="Tehran"
        )
        CityTbl.objects.create(province=prov, city_fa="تهران", city_en="Tehran")
        form = LocationForm(instance=self.profile)
        prov_html = str(form["province"])
        self.assertIn('data-fa="تهران"', prov_html)
        self.assertIn('data-en="Tehran"', prov_html)
        city_html = str(form["city"])
        self.assertIn('data-fa="تهران"', city_html)
        self.assertIn('data-en="Tehran"', city_html)
        # برچسبِ گروهِ <optgroup> همان نام فارسیِ استان است (آبشار با همین نام
        # کار می‌کند؛ ترجمهٔ برچسبِ گروه در JS از فهرستِ «استان» خوانده می‌شود)
        self.assertIn('<optgroup label="تهران">', city_html)


class AdminPanelCountryFieldsTest(TestCase):
    """
    فیلدهای «تابعیت»، «ملیت» و «اقامت دائم» در صفحهٔ «ویرایش کاربر» پنل ادمین
    (بخش اطلاعات فردی) نمایش داده و ذخیره می‌شوند.
    """

    def setUp(self):
        self.admin = User.objects.create_user(mobile_number="09120000003")
        self.admin.is_staff = True
        self.admin.is_active = True
        self.admin.save(update_fields=["is_staff", "is_active"])
        self.target = User.objects.create_user(mobile_number="09120000004")
        self.client.force_login(self.admin)

    def test_user_edit_page_shows_country_fields(self):
        resp = self.client.get(
            reverse("adminpanel:user_edit", args=[self.target.pk])
        )
        self.assertEqual(resp.status_code, 200)
        for label in ("تابعیت", "ملیت", "اقامت دائم"):
            self.assertContains(resp, label)

    def _profile_payload(self, **overrides):
        first = FirstnameTbl.objects.create(first_name_fa="رضا")
        family = FamilynameTbl.objects.create(familyname_fa="کریمی")
        data = {
            "submit": "profile",
            "next": reverse("adminpanel:users_list"),
            "first_name": str(first.pk),
            "last_name": str(family.pk),
            "father_name": str(first.pk),
            "mother_name": str(first.pk),
            "national_id": "1234567890",
            "date_of_birth": "1991-05-05",
            "gender": "male",
            "marital_status": "single",
            "citizenship": "آلمان",
            "nationality": "آلمان",
            "permanent_residence": "آلمان",
            "religion": "islam",
            "sect": "shia",
        }
        data.update(overrides)
        return data

    def test_user_edit_saves_country_fields(self):
        url = reverse("adminpanel:user_edit", args=[self.target.pk])
        resp = self.client.post(url, self._profile_payload())
        self.assertIn(resp.status_code, (301, 302))
        self.target.profile.refresh_from_db()
        self.assertEqual(self.target.profile.citizenship, "آلمان")
        self.assertEqual(self.target.profile.nationality, "آلمان")
        self.assertEqual(self.target.profile.permanent_residence, "آلمان")

    def test_user_edit_requires_personal_info_fields(self):
        # فیلدهای «اطلاعات فردی» در پنل ادمین هم الزامی‌اند (بجز بیوگرافی)
        url = reverse("adminpanel:user_edit", args=[self.target.pk])
        resp = self.client.post(
            url,
            {
                "submit": "profile",
                "next": reverse("adminpanel:users_list"),
                "first_name": "",
                "last_name": "",
                "national_id": "",
            },
        )
        self.assertEqual(resp.status_code, 200)  # فرم معتبر نیست → بدون ریدایرکت
        self.target.profile.refresh_from_db()
        self.assertIn(self.target.profile.national_id, (None, ""))


class ReservedNationalCodeTest(TestCase):
    """
    ماژول «کنترل کد ملی»: کدهای رزروشدهٔ پنل مدیریت از دسترس کاربران عادی خارج
    می‌شوند. «فقط ادمین» فقط برای کاربران is_staff قابل ثبت است و «ممنوع برای همه»
    برای هیچ‌کس. اعمال می‌شود در فرم «اطلاعات شخصی» (accounts.forms) و لایهٔ دفاعی
    دوم در Profile.clean().
    """

    ADMIN_CODE = "9999999999"  # کد نمونهٔ seeded (کد اختصاصی مدیر ارشد)
    BLOCKED_CODE = "1111111111"
    NORMAL_CODE = "1234567890"

    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09120000010")
        self.profile = self.user.profile
        self.first = FirstnameTbl.objects.create(first_name_fa="علی")
        self.family = FamilynameTbl.objects.create(familyname_fa="احمدی")
        # کد «ممنوع برای همه» برای تست‌های صریح (مستقل از seed)
        ReservedNationalCode.objects.create(
            national_id=self.BLOCKED_CODE,
            access_level=ReservedNationalCode.ACCESS_BLOCKED,
            title="کد آزمایشی ممنوع",
        )

    def _form_data(self, national_id):
        return {
            "first_name": str(self.first.pk),
            "last_name": str(self.family.pk),
            "father_name": str(self.first.pk),
            "mother_name": str(self.first.pk),
            "national_id": national_id,
            "date_of_birth": "1991-05-05",
            "gender": "male",
            "marital_status": "single",
            "citizenship": "ایران",
            "nationality": "ایران",
            "permanent_residence": "ایران",
            "religion": "islam",
            "sect": "shia",
        }

    def test_seeded_admin_code_exists_and_is_admin_only(self):
        rule = ReservedNationalCode.objects.get(national_id=self.ADMIN_CODE)
        self.assertEqual(rule.access_level, ReservedNationalCode.ACCESS_ADMIN_ONLY)
        self.assertTrue(rule.is_active)

    def test_regular_user_cannot_register_admin_only_code(self):
        form = PersonalInfoForm(
            data=self._form_data(self.ADMIN_CODE), instance=self.profile
        )
        self.assertFalse(form.is_valid())
        self.assertIn(
            "رزرو شده از قبل", form.errors["national_id"][0]
        )
        self.profile.refresh_from_db()
        self.assertNotEqual(self.profile.national_id, self.ADMIN_CODE)

    def test_regular_user_cannot_register_blocked_code(self):
        form = PersonalInfoForm(
            data=self._form_data(self.BLOCKED_CODE), instance=self.profile
        )
        self.assertFalse(form.is_valid())
        self.assertIn(
            "این کد ملی رزرو شده است و امکان ثبت آن برای هیچ کاربری وجود ندارد.",
            form.errors["national_id"],
        )

    def test_staff_user_can_register_admin_only_code(self):
        staff = User.objects.create_user(mobile_number="09120000011")
        staff.is_staff = True
        staff.save(update_fields=["is_staff"])
        form = PersonalInfoForm(
            data=self._form_data(self.ADMIN_CODE), instance=staff.profile
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        staff.profile.refresh_from_db()
        self.assertEqual(staff.profile.national_id, self.ADMIN_CODE)

    def test_staff_user_cannot_register_blocked_code(self):
        staff = User.objects.create_user(mobile_number="09120000012")
        staff.is_staff = True
        staff.save(update_fields=["is_staff"])
        form = PersonalInfoForm(
            data=self._form_data(self.BLOCKED_CODE), instance=staff.profile
        )
        self.assertFalse(form.is_valid())
        self.assertIn("رزرو شده", form.errors["national_id"][0])

    def test_profile_save_rejects_reserved_code_for_regular_user(self):
        # لایهٔ دفاعی دوم (Profile.clean): ذخیرهٔ مستقیمِ کد رزروشده رد می‌شود
        self.profile.national_id = self.ADMIN_CODE
        with self.assertRaises(ValidationError):
            self.profile.save()
        self.profile.refresh_from_db()
        self.assertNotEqual(self.profile.national_id, self.ADMIN_CODE)

    def test_profile_save_allows_admin_code_for_staff_user(self):
        staff = User.objects.create_user(mobile_number="09120000013")
        staff.is_staff = True
        staff.save(update_fields=["is_staff"])
        staff.profile.national_id = self.ADMIN_CODE
        staff.profile.save()  # نباید خطا بدهد
        staff.profile.refresh_from_db()
        self.assertEqual(staff.profile.national_id, self.ADMIN_CODE)

    def test_inactive_rule_does_not_block(self):
        # غیرفعال‌کردن رکورد، محدودیت را بدون حذف برمی‌دارد
        ReservedNationalCode.objects.filter(national_id=self.BLOCKED_CODE).update(
            is_active=False
        )
        form = PersonalInfoForm(
            data=self._form_data(self.BLOCKED_CODE), instance=self.profile
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_other_codes_unaffected(self):
        form = PersonalInfoForm(
            data=self._form_data(self.NORMAL_CODE), instance=self.profile
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.national_id, self.NORMAL_CODE)

    def test_admin_panel_module_list_and_add(self):
        admin = User.objects.create_user(mobile_number="09120000014")
        admin.is_staff = True
        admin.is_active = True
        admin.save(update_fields=["is_staff", "is_active"])
        self.client.force_login(admin)

        # فهرست ماژول «کنترل کد ملی»
        resp = self.client.get(reverse("adminpanel:national_codes_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.ADMIN_CODE)

        # افزودن یک کد رزروشدهٔ جدید
        new_code = "2222222222"
        resp = self.client.post(
            reverse("adminpanel:national_code_add"),
            {
                "national_id": new_code,
                "access_level": ReservedNationalCode.ACCESS_ADMIN_ONLY,
                "title": "کد دوم مدیر",
                "is_active": "on",
            },
        )
        self.assertIn(resp.status_code, (301, 302))
        self.assertTrue(
            ReservedNationalCode.objects.filter(
                national_id=new_code, is_active=True
            ).exists()
        )

        # کد جدید حالا برای کاربر عادی ممنوع است
        self.profile.refresh_from_db()
        form = PersonalInfoForm(
            data=self._form_data(new_code), instance=self.profile
        )
        self.assertFalse(form.is_valid())

    def test_non_staff_cannot_access_module(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("adminpanel:national_codes_list"))
        self.assertIn(resp.status_code, (301, 302))

    def test_login_rejects_reserved_code_as_referrer(self):
        # کد رزروشده (حتی «فقط ادمین») نمی‌تواند «کد ملی معرف» در فرم ورود باشد
        resp = self.client.post(
            reverse("accounts:login"),
            {
                "mobile_number": "09120000020",
                "referrer_national_id": self.ADMIN_CODE,
            },
            follow=True,
        )
        self.assertContains(resp, "نمی‌تواند به‌عنوان «کد ملی معرف» استفاده شود")
        # کاربر ساخته نشده و معرفی ثبت نشده است
        self.assertFalse(User.objects.filter(mobile_number="09120000020").exists())

    def test_login_allows_normal_code_as_referrer(self):
        # عضوِ واقعی با کد ملیِ عادی همچنان می‌تواند «معرف» باشد
        referrer = User.objects.create_user(mobile_number="09120000021")
        referrer.profile.national_id = self.NORMAL_CODE
        referrer.profile.save()
        resp = self.client.post(
            reverse("accounts:login"),
            {
                "mobile_number": "09120000022",
                "referrer_national_id": self.NORMAL_CODE,
            },
            follow=True,
        )
        new_user = User.objects.get(mobile_number="09120000022")
        self.assertEqual(new_user.referrer_national_id, self.NORMAL_CODE)

    def test_admin_panel_list_shows_holders_of_reserved_code(self):
        admin = User.objects.create_user(mobile_number="09120000015")
        admin.is_staff = True
        admin.is_active = True
        admin.save(update_fields=["is_staff", "is_active"])
        self.client.force_login(admin)

        # کاربری که پیش از رزروشدنِ کد صاحبِ همین کد شده بود؛ دادهٔ او دست‌نخورده
        # می‌ماند (سناریوی پشتیبانی‌شده در مدل) و باید در فهرست نمایش داده شود.
        holder = User.objects.create_user(mobile_number="09120000023")
        Profile.objects.filter(pk=holder.profile.pk).update(
            national_id=self.ADMIN_CODE,
            first_name=self.first,
            last_name=self.family,
        )
        resp = self.client.get(reverse("adminpanel:national_codes_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "علی احمدی")
        self.assertContains(resp, "09120000023")


class PersonalInfoRequiredFieldsTest(TestCase):
    """
    فیلدهای الزامیِ «اطلاعات شخصی»: نام، نام خانوادگی، کد ملی، تاریخ تولد،
    جنسیت، تابعیت/ملیت/اقامت دائم، دین و مذهب. (نام پدر/مادر و وضعیت تأهل به
    بخش «اطلاعات خانواده» منتقل شده‌اند؛ «پسوند فامیل» و «شهرت» اختیاری‌اند.)
    """

    OPTIONAL = {"bio", "family_suffix", "fame_name"}

    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09120000040")
        self.profile = self.user.profile
        self.first = FirstnameTbl.objects.create(first_name_fa="علی")
        self.family = FamilynameTbl.objects.create(familyname_fa="احمدی")

    def _form_data(self, **overrides):
        data = {
            "first_name": str(self.first.pk),
            "last_name": str(self.family.pk),
            "father_name": str(self.first.pk),
            "mother_name": str(self.first.pk),
            "national_id": "1234567890",
            "date_of_birth": "1991-05-05",
            "gender": "male",
            "marital_status": "single",
            "citizenship": "ایران",
            "nationality": "ایران",
            "permanent_residence": "ایران",
            "religion": "islam",
            "sect": "shia",
        }
        data.update(overrides)
        return data

    def test_all_fields_required_except_bio(self):
        for name in PersonalInfoForm.Meta.fields:
            if name in self.OPTIONAL:
                continue
            data = self._form_data()
            data[name] = ""
            form = PersonalInfoForm(data=data, instance=self.profile)
            self.assertFalse(
                form.is_valid(), f"فیلد «{name}» باید الزامی باشد: {form.errors}"
            )
            self.assertIn(name, form.errors)

    def test_bio_is_optional(self):
        form = PersonalInfoForm(
            data=self._form_data(bio=""), instance=self.profile
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_profile_page_marks_required_fields_with_star(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("core:profile"))
        self.assertEqual(resp.status_code, 200)
        # هر فیلدِ الزامیِ اطلاعات شخصی در قالبِ صفحه برچسبِ ستاره‌دار دارد
        for label in ("نام", "نام خانوادگی", "کد ملی",
                      "تاریخ تولد", "جنسیت", "تابعیت", "ملیت",
                      "اقامت دائم", "دین", "مذهب"):
            self.assertContains(resp, label)
        self.assertContains(resp, "<span class='required'>")
        # فیلدهای منتقل‌شده به اطلاعات خانواده + فیلدهای اختیاریِ جدید
        self.assertContains(resp, "پسوند فامیل")
        self.assertContains(resp, "شهرت")
        self.assertContains(resp, "نام پدر")
        self.assertContains(resp, "نام مادر")
        self.assertContains(resp, "وضعیت تأهل")


class FamilyInfoFormTest(TestCase):
    """بخش «اطلاعات خانواده»: نام پدر/مادر و وضعیت تأهل الزامی (مجرد / متاهل /
    جداشده)؛ تعداد همسر و فرزندان **کلاً اختیاری** است و کد ملی برای همسر و
    فرزندان (پسر/دختر) هم **الزامی نیست** — هر ردیف کد ملی که خالی بماند نادیده
    گرفته می‌شود و فقط کد ملی‌های واردشده ذخیره می‌گردند؛ تعداد تعیین‌شده فقط
    سقفِ ردیف‌هاست. برای هر همسر/فرزند فقط «کد ملی» گرفته می‌شود و فقط همان در
    extra_data ذخیره می‌گردد — نمایش نام از سیستم فراخوانی می‌شود."""

    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09120000041")
        self.profile = self.user.profile
        self.first = FirstnameTbl.objects.create(
            first_name_fa="محمد", gender="male"
        )
        self.first_female = FirstnameTbl.objects.create(
            first_name_fa="فاطمه", gender="female"
        )
        self.family = FamilynameTbl.objects.create(familyname_fa="احمدی")

    def _form_data(self, **overrides):
        data = {
            "father_name": str(self.first.pk),
            "mother_name": str(self.first_female.pk),
            "marital_status": "married",
            "emergency_contact": "",
            "sons_count": "0",
            "daughters_count": "0",
            "dependents_count": "",
        }
        data.update(overrides)
        return data

    def _registered_person(self, mobile, nid):
        """فرد ثبت‌نام‌شده در سیستم برای آزمون فراخوانی از کد ملی."""
        u = User.objects.create_user(mobile_number=mobile)
        p = u.profile
        p.national_id = nid
        p.first_name = self.first
        p.last_name = self.family
        p.save()
        return p

    def test_required_fields_with_same_specs(self):
        # حذف هر یک از سه فیلدِ منتقل‌شده → فرم نامعتبر است (همان مشخصات قبلی)
        for name in ("father_name", "mother_name", "marital_status"):
            data = self._form_data()
            data[name] = ""
            form = FamilyInfoForm(data=data, instance=self.profile)
            self.assertFalse(form.is_valid(), f"{name} باید الزامی باشد")
            self.assertIn(name, form.errors)

    def test_marital_choices_three_states(self):
        # وضعیت تأهل باید سه گزینه داشته باشد: مجرد / متاهل / جداشده
        choices = dict(FamilyInfoForm().fields["marital_status"].choices)
        self.assertEqual(choices.get("single"), "مجرد")
        self.assertEqual(choices.get("married"), "متاهل")
        self.assertEqual(choices.get("separated"), "جداشده")

    def test_children_counts_optional(self):
        # تعداد فرزندان اختیاری است؛ خالی ماندن = بدون ثبت (کلیدها حذف می‌شوند)
        data = self._form_data()
        data["sons_count"] = ""
        data["daughters_count"] = ""
        form = FamilyInfoForm(data=data, instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        fam = (self.profile.extra_data or {}).get("family", {})
        self.assertNotIn("sons_count", fam)
        self.assertNotIn("daughters_count", fam)
        self.assertNotIn("sons", fam)
        self.assertNotIn("daughters", fam)

    def test_married_spouses_optional_count_not_required(self):
        # متاهل بدون تعداد همسر → معتبر (ثبت همسر اختیاری است)
        form = FamilyInfoForm(data=self._form_data(), instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        self.assertNotIn("spouses", self.profile.extra_data["family"])

    def test_married_spouse_count_with_empty_nid_row_valid(self):
        # متاهل با تعداد ۱ ولی بدون کد ملی → معتبر (کد ملی الزامی نیست)
        form = FamilyInfoForm(
            data=self._form_data(spouses_count="1"), instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        fam = self.profile.extra_data["family"]
        self.assertEqual(fam["spouses_count"], 1)
        self.assertNotIn("spouses", fam)

    def test_children_count_with_empty_nid_rows_valid(self):
        # تعداد پسر/دختر وارد شده ولی همهٔ کد ملی‌ها خالی → معتبر (بدون ثبت کد ملی)
        data = self._form_data(sons_count="2", daughters_count="1")
        form = FamilyInfoForm(data=data, instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        fam = self.profile.extra_data["family"]
        self.assertEqual(fam["sons_count"], 2)
        self.assertEqual(fam["daughters_count"], 1)
        self.assertNotIn("sons", fam)
        self.assertNotIn("daughters", fam)

    def test_married_with_registered_spouse_nid(self):
        # کد ملی همسرِ ثبت‌نام‌شده → فراخوانی خودکار نام (matched)؛ فقط nid ذخیره می‌شود
        self._registered_person("09120000201", "1234567891")
        data = self._form_data(
            spouses_count="1", spouse_00_national_id="1234567891")
        form = FamilyInfoForm(data=data, instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        fam = self.profile.extra_data["family"]
        self.assertEqual(fam["spouses_count"], 1)
        self.assertEqual(fam["spouses"], [
            {"national_id": "1234567891", "matched": True}])

    def test_married_with_unregistered_spouse_nid(self):
        # کد ملیِ ثبت‌نام‌نشده هم پذیرفته و فقط ذخیره می‌شود (بدون matched)
        data = self._form_data(
            spouses_count="1", spouse_00_national_id="9121110000")
        form = FamilyInfoForm(data=data, instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        fam = self.profile.extra_data["family"]
        self.assertEqual(fam["spouses"], [{"national_id": "9121110000"}])

    def test_multiple_spouses_with_distinct_nids(self):
        self._registered_person("09120000202", "1234567892")
        data = self._form_data(
            spouses_count="2",
            spouse_00_national_id="1234567892",
            spouse_01_national_id="9121110001",
        )
        form = FamilyInfoForm(data=data, instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        fam = self.profile.extra_data["family"]
        self.assertEqual(len(fam["spouses"]), 2)
        self.assertTrue(fam["spouses"][0]["matched"])
        self.assertNotIn("matched", fam["spouses"][1])

    def test_duplicate_spouse_nids_rejected(self):
        data = self._form_data(
            spouses_count="2",
            spouse_00_national_id="1234567890",
            spouse_01_national_id="1234567890",
        )
        form = FamilyInfoForm(data=data, instance=self.profile)
        self.assertFalse(form.is_valid())
        self.assertTrue(any("تکراری" in e for e in form.non_field_errors()), form.errors)

    def test_single_ignores_spouse_and_children(self):
        # مجرد: همسر غیرفعال است؛ ردیف‌های ارسالی نادیده گرفته و پاک می‌شوند
        self.profile.extra_data = {
            "family": {"spouses_count": 1, "spouses": [{"national_id": "1234567890"}],
                       "sons_count": 2, "sons": [{"national_id": "1234567891"}]}}
        self.profile.save()
        data = self._form_data(marital_status="single",
                               spouse_00_national_id="1234567890",
                               sons_count="1", sons_00_national_id="1234567892")
        form = FamilyInfoForm(data=data, instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        fam = (self.profile.extra_data or {}).get("family", {})
        self.assertNotIn("spouses", fam)
        self.assertNotIn("spouses_count", fam)
        self.assertNotIn("sons", fam)
        self.assertNotIn("sons_count", fam)

    def test_separated_keeps_children_but_clears_spouses(self):
        # جداشده: فرزندان قابل ثبت‌اند؛ همسر(های) قانونی پاک می‌شود
        self._registered_person("09120000101", "1234567893")
        data = self._form_data(
            marital_status="separated",
            sons_count="1", daughters_count="0",
            sons_00_national_id="1234567893",
        )
        form = FamilyInfoForm(data=data, instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        fam = self.profile.extra_data["family"]
        self.assertNotIn("spouses", fam)
        self.assertNotIn("spouses_count", fam)
        self.assertEqual(fam["sons"], [{"national_id": "1234567893", "matched": True}])
        self.assertEqual(fam["sons_count"], 1)

    def test_children_rows_with_registered_nid_match(self):
        # یک پسر با کد ملیِ ثبت‌نام‌شده (فراخوانی خودکار نام) + یک دخترِ ثبت‌نام‌نشده
        self._registered_person("09120000100", "1234567890")
        data = self._form_data(
            spouses_count="1", spouse_00_national_id="9121110000",
            sons_count="1", daughters_count="1",
            sons_00_national_id="1234567890",
            daughters_00_national_id="9121110002",
        )
        form = FamilyInfoForm(data=data, instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        fam = self.profile.extra_data["family"]
        self.assertEqual(fam["sons_count"], 1)
        self.assertEqual(fam["daughters_count"], 1)
        # فقط کد ملی (+ نشانهٔ فراخوانی) ذخیره می‌شود — نام ذخیره نمی‌شود
        self.assertEqual(
            fam["sons"], [{"national_id": "1234567890", "matched": True}])
        self.assertEqual(fam["daughters"], [{"national_id": "9121110002"}])

    def test_child_nids_below_count_accepted(self):
        # کد ملی اختیاری است: تعداد ۲ پسر ولی فقط یک کد ملی → معتبر (یک ردیف خالی نادیده گرفته می‌شود)
        data = self._form_data(
            spouses_count="1", spouse_00_national_id="9121110000",
            sons_count="2", daughters_count="0",
            sons_00_national_id="1234567890",
        )
        form = FamilyInfoForm(data=data, instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        fam = self.profile.extra_data["family"]
        self.assertEqual(fam["sons_count"], 2)
        self.assertEqual(fam["sons"], [{"national_id": "1234567890"}])

    def test_children_exceeding_count_rejected(self):
        # کد ملی‌های واردشده نباید از تعداد تعیین‌شده بیشتر باشند
        data = self._form_data(
            sons_count="1", daughters_count="0",
            sons_00_national_id="1234567890",
            sons_01_national_id="1234567891",
        )
        form = FamilyInfoForm(data=data, instance=self.profile)
        self.assertFalse(form.is_valid())
        self.assertTrue(any("حداکثر" in e for e in form.non_field_errors()), form.errors)

    def test_empty_child_nid_row_skipped(self):
        # ردیف خالی کد ملی نادیده گرفته می‌شود (الزامی نیست)
        data = self._form_data(
            spouses_count="1", spouse_00_national_id="9121110000",
            sons_count="1", daughters_count="0",
            sons_00_national_id="",
        )
        form = FamilyInfoForm(data=data, instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        fam = self.profile.extra_data["family"]
        self.assertEqual(fam["sons_count"], 1)
        self.assertNotIn("sons", fam)

    def test_invalid_nid_rejected(self):
        data = self._form_data(
            spouses_count="1", spouse_00_national_id="9121110000",
            sons_count="1", daughters_count="0",
            sons_00_national_id="12345",
        )
        form = FamilyInfoForm(data=data, instance=self.profile)
        self.assertFalse(form.is_valid())
        self.assertTrue(any("۱۰ رقم" in e for e in form.non_field_errors()), form.errors)

    def test_optional_fields_accepted_and_saved(self):
        form = FamilyInfoForm(
            data=self._form_data(
                spouses_count="1", spouse_00_national_id="9121110000",
                dependents_count="1", emergency_contact="09121110003"),
            instance=self.profile,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        family = self.profile.extra_data["family"]
        self.assertEqual(family["dependents_count"], 1)
        self.assertEqual(self.profile.emergency_contact, "09121110003")

    def test_clearing_optional_fields_removes_extra_keys(self):
        # داده‌های اختیاریِ قبلی (تکفل/همسر) پاک می‌شوند؛ خالی‌گذاشتن تعداد
        # فرزندان هم یعنی بدون ثبت.
        self.profile.extra_data = {
            "family": {"dependents_count": 3,
                       "spouses_count": 1, "spouses": [{"national_id": "1234567890"}]}}
        self.profile.save()
        data = self._form_data(marital_status="single")
        data["sons_count"] = ""
        data["daughters_count"] = ""
        form = FamilyInfoForm(data=data, instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        # تکفل/همسر پاک شده‌اند و چون تعداد فرزندان هم خالی مانده،
        # بخش «family» به‌کلی از extra_data حذف می‌شود.
        self.assertEqual((self.profile.extra_data or {}).get("family", {}), {})

    def test_saved_nids_exposed_to_template_json(self):
        # دادهٔ ذخیره‌شده برای بازسازی ردیف‌ها و فراخوانی نمایش نام در قالب
        self.profile.extra_data = {
            "family": {"spouses_count": 1, "spouses": [{"national_id": "1234567890"}]}}
        self.profile.save()
        form = FamilyInfoForm(instance=self.profile)
        self.assertIn("1234567890", form.family_data_json)
        self.assertEqual(form.initial.get("spouses_count"), 1)

    def test_family_section_saves_independently_via_profile_page(self):
        # ذخیرهٔ بخش خانواده نباید اطلاعات شخصی را بیازارد و برعکس
        self.profile.extra_data = {"health": {"blood_group": "O+"}}
        self.profile.save()
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("core:profile"),
            {
                "action": "family",
                "father_name": str(self.first.pk),
                "mother_name": str(self.first_female.pk),
                "marital_status": "single",
                "sons_count": "0",
                "daughters_count": "0",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].endswith("#family"))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.extra_data["health"], {"blood_group": "O+"})
        self.assertEqual(self.profile.father_name, self.first)

    def test_family_success_message_scoped_to_family_section(self):
        # اعلان «اطلاعات خانواده با موفقیت ذخیره شد» فقط باید داخل کارت
        # «اطلاعات خانواده» بیاید — نه در فریم‌ورک سراسری messages که در همهٔ
        # بخش‌های صفحه (شخصی، شغلی، سلامت، …) تکرار می‌شود.
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("core:profile"),
            {
                "action": "family",
                "father_name": str(self.first.pk),
                "mother_name": str(self.first_female.pk),
                "marital_status": "single",
                "sons_count": "0",
                "daughters_count": "0",
            },
        )
        self.assertEqual(resp.status_code, 302)
        # پرچم یک‌بارمصرف در session، به‌جای messages سراسری
        self.assertTrue(self.client.session.get("family_saved"))
        self.assertNotIn("messages", getattr(resp, "cookies", {}))
        # صفحهٔ بعد: باکس موفقیت فقط یک‌بار و فقط در کارت خانواده
        page = self.client.get(reverse("core:profile"))
        html = page.content.decode("utf-8")
        self.assertEqual(html.count("اطلاعات خانواده با موفقیت ذخیره شد"), 1)
        self.assertIn("hb-family-saved-msg", html)
        self.assertNotContains(page, 'name="messages"')
        # پرچم مصرف شده — رفرش بعدی اعلان را نشان نمی‌دهد
        self.assertIsNone(self.client.session.get("family_saved"))
        page2 = self.client.get(reverse("core:profile"))
        self.assertNotContains(page2, "hb-family-saved-msg")

    def test_other_section_save_does_not_show_family_success_box(self):
        # ذخیرهٔ بخش سلامت نباید اعلان موفقیت خانواده را بیاورد (جداسازی کامل)
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("core:profile"),
            {"action": "health", "blood_group": "O+"},
        )
        self.assertIn(resp.status_code, (301, 302))
        page = self.client.get(reverse("core:profile"))
        self.assertNotContains(page, "hb-family-saved-msg")


class UiSettingsFormTest(TestCase):
    """بخش «تنظیمات شخصی سیستم»: فقط «تم نرم‌افزار» و «رنگ رابط کاربری»
    قابل تغییرند؛ سایر موارد پیش‌فرض و ثابت‌اند. ذخیره در extra_data["ui_settings"]."""

    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09120000071")
        self.profile = self.user.profile

    def test_only_theme_and_accent_fields_exist(self):
        # فرم فقط دو فیلد دارد — هیچ فیلد دیگری (زبان/تقویم/فونت/…) رندر نمی‌شود
        form = UiSettingsForm(profile=self.profile)
        self.assertEqual(set(form.fields.keys()), {"ui_theme", "ui_accent"})

    def test_defaults_when_nothing_saved(self):
        form = UiSettingsForm(profile=self.profile)
        self.assertEqual(form["ui_theme"].value(), "dark")
        self.assertEqual(form["ui_accent"].value(), "#c9a227")
        self.assertEqual((self.profile.extra_data or {}).get("ui_settings", {}), {})

    def test_save_light_theme_and_custom_accent(self):
        form = UiSettingsForm(
            data={"ui_theme": "light", "ui_accent": "#3B82F6"},
            profile=self.profile,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.apply()
        self.profile.save(update_fields=["extra_data"])
        self.profile.refresh_from_db()
        sub = self.profile.extra_data["ui_settings"]
        self.assertEqual(sub["ui_theme"], "light")
        self.assertEqual(sub["ui_accent"], "#3b82f6")  # نرمال‌سازی حروف کوچک
        # ظاهر فعال از هلپر خوانده می‌شود
        theme, accent = profile_ui_appearance(self.profile)
        self.assertEqual(theme, "light")
        self.assertEqual(accent, "#3b82f6")

    def test_back_to_defaults_removes_key(self):
        self.profile.extra_data = {"ui_settings": {"ui_theme": "light", "ui_accent": "#3b82f6"}}
        self.profile.save(update_fields=["extra_data"])
        # انتخاب پیش‌فرض‌ها → کلید ui_settings حذف می‌شود
        form = UiSettingsForm(
            data={"ui_theme": "dark", "ui_accent": "#c9a227"},
            profile=self.profile,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.apply()
        self.profile.save(update_fields=["extra_data"])
        self.profile.refresh_from_db()
        self.assertNotIn("ui_settings", self.profile.extra_data)

    def test_invalid_accent_rejected(self):
        form = UiSettingsForm(
            data={"ui_theme": "dark", "ui_accent": "red"},
            profile=self.profile,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("ui_accent", form.errors)

    def test_other_extra_sections_not_touched(self):
        # ذخیرهٔ تنظیمات ظاهر نباید دادهٔ بخش‌های دیگر (سلامت) را از بین ببرد
        self.profile.extra_data = {"health": {"blood_group": "O+"}}
        self.profile.save(update_fields=["extra_data"])
        form = UiSettingsForm(
            data={"ui_theme": "light", "ui_accent": "#3b82f6"},
            profile=self.profile,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.apply()
        self.profile.save(update_fields=["extra_data"])
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.extra_data["health"], {"blood_group": "O+"})

    def test_profile_page_renders_appearance_meta_and_fixed_note(self):
        # قالب: متای ظاهر + فیلد رنگ + یادداشتِ ثابت‌بودن سایر موارد + دکمهٔ ذخیره
        self.client.force_login(self.user)
        page = self.client.get(reverse("core:profile"))
        self.assertContains(page, "data-hb-accent='#c9a227'")
        self.assertContains(page, "data-hb-theme='dark'")
        self.assertContains(page, 'name="ui_accent"')
        self.assertContains(page, "ذخیره تنظیمات شخصی")
        self.assertNotContains(page, "<option>\nفارسی</option>")

    def test_save_via_profile_page_persists_and_applies(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("core:profile"),
            {"action": "ui_settings", "ui_theme": "light", "ui_accent": "#3b82f6"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].endswith("#ui_settings"))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.extra_data["ui_settings"]["ui_theme"], "light")
        page = self.client.get(reverse("core:profile"))
        self.assertContains(page, "data-hb-theme='light'")
        self.assertContains(page, "data-hb-accent='#3b82f6'")
        # فرمِ دوباره‌رندرشده انتخاب‌های ذخیره‌شده را نشان می‌دهد
        self.assertContains(page, '<option value="light" selected>')


class FamilyNidLookupTest(TestCase):
    """فراخوانی خودکار نام از کد ملی (endpoint کمکیِ بخش اطلاعات خانواده)."""

    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09120000043")
        self.first = FirstnameTbl.objects.create(first_name_fa="محمد", gender="male")
        self.family = FamilynameTbl.objects.create(familyname_fa="احمدی")
        self.url = reverse("accounts:family_nid_lookup")

    def test_requires_login(self):
        resp = self.client.get(self.url, {"nid": "1234567890"})
        self.assertEqual(resp.status_code, 302)

    def test_invalid_nid(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url, {"nid": "12345"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["found"])
        self.assertIn("error", resp.json())

    def test_registered_nid_returns_names(self):
        other = User.objects.create_user(mobile_number="09120000101")
        p = other.profile
        p.national_id = "1234567890"
        p.first_name = self.first
        p.last_name = self.family
        p.save()
        self.client.force_login(self.user)
        resp = self.client.get(self.url, {"nid": "1234567890"}
        )
        data = resp.json()
        self.assertTrue(data["found"])
        self.assertEqual(data["first_name_id"], self.first.pk)
        self.assertEqual(data["family_name_id"], self.family.pk)
        self.assertEqual(data["first_name_fa"], "محمد")

    def test_unknown_nid_not_found(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url, {"nid": "1111111111"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["found"])

    def test_lookup_finds_own_profile(self):
        # کد ملی خود کاربر هم قابل فراخوانی است
        p = self.user.profile
        p.national_id = "2222222222"
        p.save()
        self.client.force_login(self.user)
        resp = self.client.get(self.url, {"nid": "2222222222"})
        self.assertTrue(resp.json()["found"])


class FameNameFieldTest(TestCase):
    """فیلد اختیاریِ «شهرت»: انتخاب فقط از جدول مرجع FameNameTbl (مدیریت از پنل)."""

    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09120000042")
        self.profile = self.user.profile
        self.first = FirstnameTbl.objects.create(first_name_fa="علی")
        self.family = FamilynameTbl.objects.create(familyname_fa="احمدی")
        self.fame = FameNameTbl.objects.create(
            fame_name_fa="پدر فلسفه", fame_name_en="Father of Philosophy"
        )

    def _info_data(self):
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

    def test_fame_name_and_suffix_optional(self):
        form = PersonalInfoForm(
            data=self._info_data(), instance=self.profile
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_fame_name_saved_from_reference_table(self):
        form = PersonalInfoForm(
            data={**self._info_data(), "fame_name": str(self.fame.pk),
                  "family_suffix": "رود"},
            instance=self.profile,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.fame_name, self.fame)
        self.assertEqual(self.profile.family_suffix, "رود")

    def test_fame_name_search_endpoint(self):
        self.client.force_login(self.user)
        resp = self.client.get(
            reverse("accounts:name_search"), {"q": "فلسفه", "kind": "fame"}
        )
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        self.assertTrue(any(r["id"] == self.fame.pk for r in results))
        self.assertTrue(any("Father of Philosophy" in r["label"] for r in results))

    def test_adminpanel_fame_tab_lists_and_creates(self):
        staff = User.objects.create_user(
            mobile_number="09120000043", is_staff=True, is_superuser=True
        )
        self.client.force_login(staff)
        resp = self.client.get(reverse("adminpanel:names_list"), {"kind": "fame"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "پدر فلسفه")

        resp = self.client.post(
            reverse("adminpanel:name_add", args=["fame"]),
            {"fame_name_fa": "قهرمان ملی", "fame_name_en": "National Hero"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            FameNameTbl.objects.filter(fame_name_fa="قهرمان ملی").exists()
        )

    def test_adminpanel_fame_add_with_description(self):
        staff = User.objects.create_user(
            mobile_number="09120000044", is_staff=True, is_superuser=True
        )
        self.client.force_login(staff)
        # فیلد توضیحات در فرم افزودن شهرت نمایش داده می‌شود
        resp = self.client.get(reverse("adminpanel:name_add", args=["fame"]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "توضیحات")

        resp = self.client.post(
            reverse("adminpanel:name_add", args=["fame"]),
            {
                "fame_name_fa": "ستارهٔ علم",
                "fame_name_en": "Science Star",
                "description": "لقبی که به پژوهشگران برجستهٔ حوزهٔ نجوم داده می‌شود.",
            },
        )
        self.assertEqual(resp.status_code, 302)
        obj = FameNameTbl.objects.get(fame_name_fa="ستارهٔ علم")
        self.assertEqual(
            obj.description, "لقبی که به پژوهشگران برجستهٔ حوزهٔ نجوم داده می‌شود."
        )
        # ستون توضیحات در فهرست شهرت‌ها نمایش داده می‌شود
        resp = self.client.get(reverse("adminpanel:names_list"), {"kind": "fame"})
        self.assertContains(resp, "پژوهشگران برجستهٔ حوزهٔ نجوم")

    def test_adminpanel_fame_edit_updates_description(self):
        staff = User.objects.create_user(
            mobile_number="09120000045", is_staff=True, is_superuser=True
        )
        self.client.force_login(staff)
        resp = self.client.post(
            reverse("adminpanel:name_edit", args=["fame", self.fame.pk]),
            {
                "fame_name_fa": "پدر فلسفه",
                "fame_name_en": "Father of Philosophy",
                "description": "توضیح ویرایش‌شده.",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.fame.refresh_from_db()
        self.assertEqual(self.fame.description, "توضیح ویرایش‌شده.")

    def test_description_optional_and_blank_default(self):
        # بدون توضیحات هم می‌توان شهرت ثبت کرد و توضیحات خالی می‌ماند
        obj = FameNameTbl.objects.create(fame_name_fa="بدون توضیح")
        self.assertEqual(obj.description, "")
        form = FameNameForm(instance=obj)
        html = str(form)
        self.assertIn("name=\"description\"", html)
        # حذف توضیحات در ویرایش آن را خالی می‌کند
        form = FameNameForm(
            data={"fame_name_fa": "بدون توضیح", "fame_name_en": "", "description": ""},
            instance=obj,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        obj.refresh_from_db()
        self.assertEqual(obj.description, "")


class ReferralDisplayTest(TestCase):
    """
    «کد ملی معرف» که هنگام ورود وارد شده است، در بخش اطلاعات شخصی پروفایل با
    مقدارش نمایش داده می‌شود (فقط نمایشی و غیرقابل ویرایش)؛ اگر وارد نشده باشد
    این بلوکِ نمایشی اصلاً نمایش داده نمی‌شود. در بخش «اطلاعات ارتباطی» همین
    فیلد همیشه حضور دارد و قابل تغییر است (قابلیت ویرایش «کد ملی معرف»).
    """

    def setUp(self):
        self.first = FirstnameTbl.objects.create(first_name_fa="علی")
        self.family = FamilynameTbl.objects.create(familyname_fa="احمدی")
        self.referrer = User.objects.create_user(mobile_number="09120000050")
        self.referrer.profile.national_id = "1111111112"
        self.referrer.profile.first_name = self.first
        self.referrer.profile.last_name = self.family
        self.referrer.profile.save()

    def test_profile_shows_referrer_when_entered(self):
        user = User.objects.create_user(
            mobile_number="09120000051", referrer_national_id="1111111112"
        )
        self.client.force_login(user)
        resp = self.client.get(reverse("core:profile"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "کد ملی معرف")
        self.assertContains(resp, "1111111112")
        # نام و شمارهٔ معرف هم کنار کد ملی نمایش داده می‌شود
        self.assertContains(resp, "علی احمدی")
        self.assertContains(resp, "09120000050")

    def test_profile_hides_referrer_when_not_entered(self):
        user = User.objects.create_user(mobile_number="09120000052")
        self.client.force_login(user)
        resp = self.client.get(reverse("core:profile"))
        self.assertEqual(resp.status_code, 200)
        # در بخش اطلاعات شخصی، بلوکِ نمایشیِ «کد ملی معرف» وقتی معرف وارد نشده
        # باشد نمایش داده نمی‌شود (راهنمایِ همان بلوک در صفحه نیست)
        self.assertNotContains(resp, "از صفحهٔ ورود ثبت شده و در این بخش قابل ویرایش نیست")
        # اما در بخش «اطلاعات ارتباطی» فیلدِ قابل ویرایشِ «کد ملی معرف» همیشه
        # حضور دارد تا کاربر بتواند کد ملی معرف را تغییر دهد
        self.assertContains(resp, 'name="referrer_national_id"')


class ContactInfoFormTest(TestCase):
    """
    بخش «اطلاعات ارتباطی»: شماره موبایل الزامی/نمایشی (غیرقابل ویرایش) و همهٔ
    فیلدهای دیگر اختیاری؛ هر شبکهٔ اجتماعی یک فیلد جداگانه دارد (ذخیره در
    extra_data["social"]) و وب‌سایت در extra_data["website"]. «کد ملی معرف» که در
    بخش اطلاعات شخصی فقط نمایشی است، اینجا قابل تغییر است (با همان اعتبارسنجیِ
    صفحهٔ ورود: ۱۰ رقم، متعلق به عضوِ ثبت‌شده و نه خودِ کاربر).
    """

    def setUp(self):
        self.first = FirstnameTbl.objects.create(first_name_fa="علی")
        self.family = FamilynameTbl.objects.create(familyname_fa="احمدی")
        self.referrer = User.objects.create_user(mobile_number="09120000070")
        self.referrer.profile.national_id = "1111111113"
        self.referrer.profile.save()
        self.user = User.objects.create_user(mobile_number="09120000071")
        self.profile = self.user.profile

    def _payload(self, **overrides):
        data = {
            "email": "ali@example.com",
            "phone": "021-12345678",
            "personal_phone": "09350000000",
            "website": "https://example.com",
            "social_telegram": "@ali",
            "social_bale": "ali_bale",
            "social_youtube": "https://youtube.com/@ali",
            "referrer_national_id": "1111111113",
        }
        data.update(overrides)
        return data

    def test_saves_contact_fields_and_social_networks(self):
        form = ContactInfoForm(self._payload(), instance=self.profile, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.email, "ali@example.com")
        self.assertEqual(self.profile.phone, "021-12345678")
        self.assertEqual(self.profile.personal_phone, "09350000000")
        self.assertEqual(self.profile.extra_data["website"], "https://example.com")
        self.assertEqual(self.profile.extra_data["social"], {
            "telegram": "@ali",
            "bale": "ali_bale",
            "youtube": "https://youtube.com/@ali",
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.referrer_national_id, "1111111113")

    def test_all_fields_optional_except_mobile(self):
        form = ContactInfoForm({}, instance=self.profile, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_self_as_referrer(self):
        self.profile.national_id = "2222222222"
        self.profile.save()
        form = ContactInfoForm(
            self._payload(referrer_national_id="2222222222"),
            instance=self.profile, user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn(
            "نمی‌توانید خودتان را معرفی کنید",
            form.errors["referrer_national_id"][0],
        )

    def test_rejects_unknown_referrer_code(self):
        # ۸۸۸۸۸۸۸۸۸۸: ۱۰ رقم و نه کدِ رزروشده (رزروی‌ها مثل ۹۹۹۹۹۹۹۹۹۹ هستند)
        form = ContactInfoForm(
            self._payload(referrer_national_id="8888888888"),
            instance=self.profile, user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("یافت نشد", form.errors["referrer_national_id"][0])

    def test_clearing_referrer_allowed(self):
        self.user.referrer_national_id = "1111111113"
        self.user.save(update_fields=["referrer_national_id"])
        form = ContactInfoForm(
            self._payload(referrer_national_id=""),
            instance=self.profile, user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.refresh_from_db()
        self.assertIsNone(self.user.referrer_national_id)

    def test_profile_view_saves_contact_info(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("core:profile"), {
            "action": "contact",
            "email": "a@b.com",
            "personal_phone": "09350000000",
            "website": "https://example.com",
            "social_eitaa": "eitaa_id",
            "referrer_national_id": "1111111113",
        })
        self.assertRedirects(resp, f"{reverse('core:profile')}#communication")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.email, "a@b.com")
        self.assertEqual(self.profile.personal_phone, "09350000000")
        self.assertEqual(self.profile.extra_data["website"], "https://example.com")
        self.assertEqual(self.profile.extra_data["social"], {"eitaa": "eitaa_id"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.referrer_national_id, "1111111113")


class ReferralRewardTest(TestCase):
    """
    پس از تکمیل اطلاعات شخصی:
    - به خودِ کاربر (حتی بدون معرف) بر اساس سرفصل «profile_completion» امتیاز
      تعلق می‌گیرد (فقط یک‌بار برای هر کاربر، با رعایت سقف) — و معادل سکهٔ
      امتیازها نیز بر اساس «ارزش هر سکه (امتیاز)» به‌صورت خودکار به کیف پول
      تجمیع می‌شود (نرخ پیش‌فرض: هر سکه = ۱ امتیاز).
    - اگر کاربرِ معرفی‌شده باشد، به معرف هم بر اساس قانون «referral» امتیاز می‌رسد
      (با رعایت سقفِ ادمین برای معرف).
    - برای کاربر، معرف و ادمین هرکدام جداگانه تیکت ساخته می‌شود.
    """

    REFERRER_NID = "1111111112"

    def setUp(self):
        from wallet.models import RewardRule

        self.completion_rule, _ = RewardRule.objects.update_or_create(
            code="profile_completion",
            defaults={
                "title": "تکمیل اطلاعات شخصی", "coins": 5, "is_active": True,
            },
        )
        self.referral_rule, _ = RewardRule.objects.update_or_create(
            code="referral",
            defaults={"title": "معرفی کاربر جدید", "coins": 5, "is_active": True},
        )
        # فیلد «میزان» قانون، مستقیم به‌عنوان امتیاز اعمال می‌شود
        self.completion_points = 5
        self.referral_points = 5
        self.first = FirstnameTbl.objects.create(first_name_fa="علی")
        self.family = FamilynameTbl.objects.create(familyname_fa="احمدی")
        self.referrer = User.objects.create_user(mobile_number="09120000060")
        self.referrer.profile.national_id = self.REFERRER_NID
        self.referrer.profile.save()
        self.admin = User.objects.create_user(mobile_number="09120000061")
        self.admin.is_staff = True
        self.admin.is_active = True
        self.admin.save(update_fields=["is_staff", "is_active"])

    def _form_data(self):
        return {
            "first_name": str(self.first.pk),
            "last_name": str(self.family.pk),
            "father_name": str(self.first.pk),
            "mother_name": str(self.first.pk),
            "national_id": "1234567890",
            "date_of_birth": "1991-05-05",
            "gender": "male",
            "marital_status": "single",
            "citizenship": "ایران",
            "nationality": "ایران",
            "permanent_residence": "ایران",
            "religion": "islam",
            "sect": "shia",
        }

    def _complete_personal_info(self, mobile, referrer=True):
        from accounts.models import User as UserModel

        kwargs = {"mobile_number": mobile}
        if referrer:
            kwargs["referrer_national_id"] = self.REFERRER_NID
        user = UserModel.objects.create_user(**kwargs)
        self.client.force_login(user)
        resp = self.client.post(reverse("core:profile"), self._form_data(), follow=True)
        self.assertEqual(resp.status_code, 200)
        return user

    def test_user_and_referrer_both_receive_coins_points_and_separate_tickets(self):
        from tickets.models import Ticket, TicketRecipient
        from wallet.models import CoinLedger, Wallet

        user = self._complete_personal_info("09120000062")

        # امتیاز هر دو طرف طبق سرفصل خودشان؛ معادل سکهٔ امتیازها نیز بر اساس
        # «ارزش هر سکه (امتیاز)» (نرخ پیش‌فرض ۱) به کیف پول هر طرف تجمیع می‌شود
        user.profile.refresh_from_db()
        self.referrer.profile.refresh_from_db()
        self.assertEqual(user.profile.user_score, self.completion_rule.coins)
        self.assertEqual(self.referrer.profile.user_score, self.referral_rule.coins)
        self.assertEqual(Wallet.objects.get(user=user).balance, Decimal("5.00"))
        self.assertEqual(
            Wallet.objects.get(user=self.referrer).balance, Decimal("5.00")
        )
        self.assertEqual(
            CoinLedger.objects.filter(user__in=[user, self.referrer],
                                      kind=CoinLedger.KIND_REWARD,
                                      ref_code="PTS").count(), 2,
        )

        # سه تیکتِ جداگانه: به کاربر، به معرف و به ادمین
        tickets = Ticket.objects.filter(author=user)
        self.assertEqual(tickets.count(), 3)
        subjects = set(tickets.values_list("subject", flat=True))
        self.assertIn("دریافت امتیاز پاداش تکمیل اطلاعات شخصی", subjects)
        self.assertIn("پاداش معرفی کاربر جدید", subjects)
        self.assertIn("گزارش پاداش تکمیل اطلاعات شخصی و معرفی", subjects)

        user_ticket = tickets.get(subject="دریافت امتیاز پاداش تکمیل اطلاعات شخصی")
        self.assertIn(user.pk, TicketRecipient.objects.filter(
            ticket=user_ticket).values_list("user_id", flat=True))
        self.assertNotIn(self.referrer.pk, TicketRecipient.objects.filter(
            ticket=user_ticket).values_list("user_id", flat=True))
        self.assertNotIn(self.admin.pk, TicketRecipient.objects.filter(
            ticket=user_ticket).values_list("user_id", flat=True))

        referrer_ticket = tickets.get(subject="پاداش معرفی کاربر جدید")
        self.assertIn(self.referrer.pk, TicketRecipient.objects.filter(
            ticket=referrer_ticket).values_list("user_id", flat=True))
        self.assertNotIn(self.admin.pk, TicketRecipient.objects.filter(
            ticket=referrer_ticket).values_list("user_id", flat=True))

        admin_ticket = tickets.get(subject="گزارش پاداش تکمیل اطلاعات شخصی و معرفی")
        self.assertIn(self.admin.pk, TicketRecipient.objects.filter(
            ticket=admin_ticket).values_list("user_id", flat=True))
        self.assertNotIn(self.referrer.pk, TicketRecipient.objects.filter(
            ticket=admin_ticket).values_list("user_id", flat=True))

    def test_reward_granted_only_once(self):
        from wallet.models import Wallet

        user = self._complete_personal_info("09120000063")
        # ذخیرهٔ مجدد اطلاعات شخصی → پاداش تکراری داده نمی‌شود
        self.client.post(reverse("core:profile"), self._form_data(), follow=True)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.user_score, self.completion_rule.coins)
        # پاداش تکراری داده نمی‌شود: موجودی سکه هم بیش از یک‌بار تجمیع نشده است
        self.assertEqual(Wallet.objects.get(user=user).balance, Decimal("5.00"))

    def test_profile_completion_reward_without_referrer(self):
        # تکمیل اطلاعات شخصی حتی بدون معرف هم به خودِ کاربر امتیاز می‌دهد (فقط امتیاز)
        from tickets.models import Ticket
        from wallet.models import Wallet

        user = self._complete_personal_info("09120000064", referrer=False)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.user_score, self.completion_rule.coins)
        # معادل سکهٔ امتیاز (نرخ پیش‌فرض ۱) به کیف پول کاربر تجمیع شده است
        self.assertEqual(Wallet.objects.get(user=user).balance, Decimal("5.00"))
        # فقط دو تیکت: به خودِ کاربر و گزارش به ادمین (تیکتِ معرفی وجود ندارد)
        tickets = Ticket.objects.filter(author=user)
        self.assertEqual(tickets.count(), 2)
        subjects = set(tickets.values_list("subject", flat=True))
        self.assertIn("دریافت امتیاز پاداش تکمیل اطلاعات شخصی", subjects)
        self.assertIn("گزارش پاداش تکمیل اطلاعات شخصی و معرفی", subjects)
        self.assertNotIn("پاداش معرفی کاربر جدید", subjects)

    def test_referrer_cap_does_not_block_user_reward(self):
        from accounts.scoring import award as award_score
        from tickets.models import Ticket
        from wallet.models import RewardRule

        RewardRule.objects.filter(code="referral").update(max_per_user=1)
        # معرف قبلاً یک بار پاداشِ معرفی گرفته است → به سقف رسیده
        # (commit=False تا در همان تست — بدون on_commit — ثبت شود)
        award_score(self.referrer.profile, 5, "پاداش معرفی قبلی",
                    rule_code="referral", commit=False)
        self.referrer.profile.refresh_from_db()
        self.assertEqual(self.referrer.profile.user_score, 5)

        user = self._complete_personal_info("09120000065")
        # پاداشِ خودِ کاربر همچنان پرداخت می‌شود؛ معرف پاداشِ تازه نمی‌گیرد
        user.profile.refresh_from_db()
        self.referrer.profile.refresh_from_db()
        self.assertEqual(user.profile.user_score, self.completion_rule.coins)
        self.assertEqual(self.referrer.profile.user_score, 5)
        # در گزارش ادمین به سقفِ معرف اشاره شده است
        admin_ticket = Ticket.objects.filter(
            author=user, subject="گزارش پاداش تکمیل اطلاعات شخصی و معرفی"
        ).first()
        self.assertIsNotNone(admin_ticket)
        self.assertIn("به سقف پاداش رسیده بود", admin_ticket.description)
