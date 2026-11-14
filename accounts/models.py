# -*- coding: utf-8 -*-
import os
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone


BASE_DIR = Path(__file__).resolve().parent.parent


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, mobile_number, password, **extra_fields):
        if not mobile_number:
            raise ValueError('شماره موبایل الزامی است')
        user = self.model(mobile_number=mobile_number, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, mobile_number, password=None, **extra_fields):
        return self._create_user(mobile_number, password, **extra_fields)

    def create_superuser(self, mobile_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('سوپریوزر باید is_staff=True داشته باشد')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('سوپریوزر باید is_superuser=True داشته باشد')
        return self._create_user(mobile_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    mobile_number = models.CharField(max_length=11, unique=True, verbose_name='شماره موبایل')
    referrer_national_id = models.CharField(blank=True, null=True, max_length=50, verbose_name='کد ملی معرف', help_text='کد ملی ۱۰ رقمی کاربری که این کاربر را معرفی کرده است (فقط کد ملیِ ثبت‌شدهٔ یک عضو فعال).')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_staff = models.BooleanField(default=False, verbose_name='دسترسی ادمین')
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ عضویت')
    last_login_at = models.DateTimeField(auto_now=True, verbose_name='آخرین ورود')
    acc_password = models.CharField(blank=True, help_text='هش‌شده ذخیره می‌شود (هرگز رمز خام ذخیره نمی‌شود).', max_length=255, verbose_name='کلمه عبور حسابداری (هش)')
    acc_password_updated_at = models.DateTimeField(blank=True, null=True, verbose_name='تاریخ آخرین تغییر رمز حسابداری')
    acc_username = models.CharField(blank=True, error_messages={'unique': 'این نام کاربری قبلاً توسط کاربر دیگری انتخاب شده است.'}, help_text='فقط برای ورود به ماژول حسابداری کاربرد دارد.', max_length=100, null=True, unique=True, verbose_name='نام کاربری حسابداری')
    groups = models.ManyToManyField('auth.Group', blank=True, related_name='user_set', related_query_name='user', verbose_name='groups')
    user_permissions = models.ManyToManyField('auth.Permission', blank=True, related_name='user_set', related_query_name='user', verbose_name='user permissions')
    USERNAME_FIELD = 'mobile_number'
    REQUIRED_FIELDS = ['email']

    objects = UserManager()

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'

    def __str__(self):
        return self.mobile_number

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return True

    def get_username(self):
        return self.mobile_number

    @property
    def referrer(self):
        """کاربر معرِف بر اساس «کد ملی معرف» (فقط عضوی که کد ملی‌اش ثبت شده).

        فقط برای نمایش در قالب‌ها و منطق پاداش معرفی استفاده می‌شود؛ ستون دیتابیس
        ندارد (کد ملی معرف در `referrer_national_id` نگه‌داری می‌شود).
        """
        nid = (self.referrer_national_id or '').strip()
        if not nid:
            return None
        return (
            User.objects.filter(profile__national_id=nid, is_active=True)
            .select_related('profile')
            .first()
        )

    # ---- اعتبارنامهٔ مجزای ماژول حسابداری (accounts/acc_credentials.py) ----
    def has_acc_credentials(self):
        """آیا کاربر نام کاربری حسابداری تعریف کرده است؟"""
        return bool((self.acc_username or '').strip())

    def set_acc_password(self, raw_password):
        """ذخیرهٔ هش کلمهٔ عبور حسابداری (هرگز رمز خام ذخیره نمی‌شود)."""
        self.acc_password = make_password(raw_password)

    def check_acc_password(self, raw_password):
        """تطبیق کلمهٔ عبور حسابداری با هش ذخیره‌شده."""
        from django.contrib.auth.hashers import check_password

        stored = self.acc_password or ''
        if not stored:
            return False
        return check_password(raw_password, stored)


class Profile(models.Model):
    id = models.BigAutoField(primary_key=True, serialize=False)
    avatar = models.FileField(blank=True, null=True, upload_to='avatars/')
    user = models.OneToOneField('User', on_delete=models.CASCADE, related_name='profile')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    first_name = models.ForeignKey('FirstnameTbl', blank=True, null=True, on_delete=models.SET_NULL, related_name='profiles_first_name', verbose_name='نام')
    last_name = models.ForeignKey('FamilynameTbl', blank=True, null=True, on_delete=models.SET_NULL, related_name='profiles_last_name', verbose_name='نام خانوادگی')
    father_name = models.ForeignKey('FirstnameTbl', blank=True, null=True, on_delete=models.SET_NULL, related_name='profiles_father_name', verbose_name='نام پدر')
    mother_name = models.ForeignKey('FirstnameTbl', blank=True, null=True, on_delete=models.SET_NULL, related_name='profiles_mother_name', verbose_name='نام مادر')
    national_id = models.CharField(blank=True, max_length=10, null=True, unique=True, verbose_name='کد ملی', error_messages={'unique': 'این کد ملی قبلاً ثبت شده است.'})
    date_of_birth = models.DateField(blank=True, null=True, verbose_name='تاریخ تولد')
    gender = models.CharField(blank=True, max_length=10, choices=[('male', 'مرد'), ('female', 'زن')], verbose_name='جنسیت')
    family_suffix = models.CharField(blank=True, max_length=50, verbose_name='پسوند فامیل')
    bio = models.TextField(blank=True, verbose_name='بیوگرافی')
    citizenship = models.CharField(blank=True, default='ایران', max_length=100, verbose_name='تابعیت')
    nationality = models.CharField(blank=True, default='ایران', max_length=100, verbose_name='ملیت')
    permanent_residence = models.CharField(blank=True, default='ایران', max_length=100, verbose_name='اقامت دائم')
    religion = models.CharField(blank=True, max_length=20, choices=[('islam', 'اسلام'), ('christianity', 'مسیحیت'), ('judaism', 'یهودیت'), ('zoroastrianism', 'زرتشتی'), ('buddhism', 'بودیسم'), ('hinduism', 'هندوئیسم'), ('sikhism', 'سیکیسم'), ('atheism', 'بی‌دین'), ('other', 'سایر')], verbose_name='دین')
    sect = models.CharField(blank=True, max_length=20, choices=[('shia', 'شیعه'), ('sunni', 'سنی'), ('sufi', 'صوفی'), ('catholic', 'کاتولیک'), ('protestant', 'پروتستان'), ('orthodox', 'ارتدکس'), ('sunni_hanafi', 'حنفی'), ('sunni_shafei', 'شافعی'), ('sunni_maliki', 'مالکی'), ('sunni_hanbali', 'حنبلی'), ('zaydi', 'زیدی'), ('ismaili', 'اسماعیلی'), ('other', 'سایر')], verbose_name='مذهب')
    fame_name = models.ForeignKey('FameNameTbl', blank=True, null=True, on_delete=models.SET_NULL, related_name='profiles_fame_name', verbose_name='شهرت')
    job_title = models.CharField(blank=True, max_length=150, verbose_name='عنوان شغلی')
    department = models.CharField(blank=True, max_length=150, verbose_name='بخش')
    employment_type = models.CharField(blank=True, max_length=100, verbose_name='نوع همکاری')
    hire_date = models.DateField(blank=True, null=True, verbose_name='تاریخ استخدام')
    personnel_id = models.CharField(blank=True, max_length=50, verbose_name='شماره پرسنلی')
    org_code = models.CharField(blank=True, max_length=50, verbose_name='کد سازمانی')
    branch = models.CharField(blank=True, max_length=150, verbose_name='شعبه')
    work_group = models.CharField(blank=True, max_length=150, verbose_name='گروه کاری')
    status = models.CharField(blank=True, max_length=10, choices=[('active', 'فعال'), ('inactive', 'غیرفعال')], default='active', verbose_name='وضعیت')
    degree = models.CharField(blank=True, max_length=100, verbose_name='مدرک تحصیلی')
    field_of_study = models.CharField(blank=True, max_length=150, verbose_name='رشته تحصیلی')
    university = models.CharField(blank=True, max_length=150, verbose_name='دانشگاه')
    graduation_year = models.PositiveIntegerField(blank=True, null=True, verbose_name='سال فارغ‌التحصیلی')
    gpa = models.DecimalField(blank=True, null=True, max_digits=4, decimal_places=2, verbose_name='معدل')
    account_number = models.CharField(blank=True, max_length=50, verbose_name='شماره حساب')
    iban = models.CharField(blank=True, max_length=34, verbose_name='شبا')
    bank_name = models.CharField(blank=True, default='بانک ملی ایران', max_length=100, verbose_name='نام بانک', help_text='بانک پیش‌فرض «بانک ملی ایران» است؛ کیف پول شبای ثبت‌شده را از همین‌جا می‌خواند.')
    salary = models.DecimalField(blank=True, null=True, max_digits=14, decimal_places=0, verbose_name='حقوق پایه')
    email = models.EmailField(blank=True, max_length=254, verbose_name='ایمیل')
    phone = models.CharField(blank=True, max_length=20, verbose_name='تلفن ثابت')
    emergency_contact = models.CharField(blank=True, max_length=20, verbose_name='تماس اضطراری')
    address = models.CharField(blank=True, max_length=255, verbose_name='آدرس')
    city = models.CharField(blank=True, max_length=100, verbose_name='شهر')
    province = models.CharField(blank=True, max_length=100, verbose_name='استان')
    country = models.CharField(blank=True, default='ایران', max_length=100, verbose_name='کشور')
    postal_code = models.CharField(blank=True, max_length=10, verbose_name='کد پستی')
    extra_data = models.JSONField(blank=True, default=dict, verbose_name='داده‌های تکمیلی')
    marital_status = models.CharField(blank=True, max_length=10, choices=[('single', 'مجرد'), ('married', 'متاهل'), ('separated', 'جداشده')], verbose_name='وضعیت تاهل')
    manager = models.ForeignKey('self', blank=True, null=True, on_delete=models.SET_NULL, related_name='team_members', verbose_name='مدیر مستقیم')
    transfer_pin = models.CharField(blank=True, max_length=128, verbose_name='رمز انتقال (هش‌شده)', help_text='در صورت تنظیم، انتقال سکه به رمز نیاز دارد. مقدار اصلی هرگز ذخیره نمی‌شود.')
    personal_phone = models.CharField(blank=True, max_length=20, verbose_name='تلفن شخصی')
    education_institution = models.ForeignKey('EducationInstitution', blank=True, null=True, on_delete=models.PROTECT, related_name='profiles', verbose_name='مرکز دانشگاهی')
    study_field = models.ForeignKey('StudyField', blank=True, null=True, on_delete=models.PROTECT, related_name='profiles', verbose_name='رشته تحصیلی مرجع')
    study_specialization = models.ForeignKey('StudySpecialization', blank=True, null=True, on_delete=models.PROTECT, related_name='profiles', verbose_name='گرایش تحصیلی')
    latitude = models.FloatField(blank=True, null=True, verbose_name='عرض جغرافیایی')
    longitude = models.FloatField(blank=True, null=True, verbose_name='طول جغرافیایی')
    user_level = models.PositiveSmallIntegerField(default=1, verbose_name='سطح کاربر')
    user_score = models.PositiveIntegerField(default=0, verbose_name='امتیاز کاربر')
    last_ip = models.CharField(blank=True, max_length=64, verbose_name='آخرین IP')
    location_updated_at = models.DateTimeField(blank=True, null=True, verbose_name='آخرین به‌روزرسانی موقعیت')

    class Meta:
        verbose_name = 'پروفایل'
        verbose_name_plural = 'پروفایل‌ها'
        indexes = [
            models.Index(fields=['city'], name='prof_city_idx'),
            models.Index(fields=['province'], name='prof_province_idx'),
            models.Index(fields=['country'], name='prof_country_idx'),
            models.Index(fields=['job_title'], name='prof_job_idx'),
            models.Index(fields=['latitude', 'longitude'], name='prof_geo_idx'),
            models.Index(fields=['user_score'], name='prof_score_idx'),
            models.Index(fields=['user_level'], name='prof_level_idx'),
        ]

    def __str__(self):
        return f"{self.first_name.first_name_fa if self.first_name else ''} {self.last_name.familyname_fa if self.last_name else ''}".strip() or self.national_id

    @property
    def full_name(self):
        """نام و نام‌خانوادگی فارسی (برای نمایش در سایدبار/داشبورد/پروفایل).

        اگر نام ثبت نشده باشد، کد ملی به‌عنوان جایگزین نمایشی برمی‌گردد
        (همان رفتار __str__) تا لیست‌ها و جست‌وجوهای «نام گیرنده» خالی نمانند.
        """
        return (
            f"{self.first_name.first_name_fa if self.first_name else ''} "
            f"{self.last_name.familyname_fa if self.last_name else ''}"
        ).strip() or (self.national_id or '')

    # نام‌های انگلیسیِ موقعیت همیشه در extra_data نگه‌داری می‌شوند (طرح مهاجرت 0025).
    # این پراپرتی‌ها فقط خواندنی‌اند و ستون دیتابیس ندارند؛ اول مقدار ذخیره‌شده را
    # می‌خوانند و اگر خالی بود از جدول مرجع (کشور/استان/شهرستان) فالبک می‌گیرند.
    def _lookup_en(self, model, fa_field, fa_value, en_field):
        fa = (fa_value or '').strip()
        if not fa:
            return ''
        try:
            row = model.objects.filter(**{fa_field: fa}).only(en_field).first()
        except Exception:
            return ''
        return (getattr(row, en_field, '') or '').strip() if row else ''

    def _en_with_fallback(self, key, fa_value, model=None, fa_field=None, en_field=None):
        en = ((self.extra_data or {}).get(key) or '').strip()
        if en or model is None:
            return en
        return self._lookup_en(model, fa_field, fa_value, en_field)

    @property
    def country_en(self):
        return self._en_with_fallback('country_en', self.country, CountryTbl, 'country_fa', 'country_en')

    @property
    def province_en(self):
        return self._en_with_fallback('province_en', self.province, ProvinceTbl, 'province_fa', 'province_en')

    @property
    def city_en(self):
        return self._en_with_fallback('city_en', self.city, CityTbl, 'city_fa', 'city_en')

    @property
    def citizenship_en(self):
        return self._en_with_fallback('citizenship_en', self.citizenship, CountryTbl, 'country_fa', 'country_en')

    @property
    def nationality_en(self):
        return self._en_with_fallback('nationality_en', self.nationality, CountryTbl, 'country_fa', 'country_en')

    @property
    def permanent_residence_en(self):
        return self._en_with_fallback('permanent_residence_en', self.permanent_residence, CountryTbl, 'country_fa', 'country_en')

    def save(self, *args, **kwargs):
        # لایهٔ دفاعی دوم «کنترل کد ملی»: حتی ذخیرهٔ مستقیمِ پروفایل هم کد ملی
        # رزروشده را برای کاربر عادی رد می‌کند (اول لایهٔ فرم‌ها است).
        is_staff = False
        if self.user_id:
            is_staff = User.objects.filter(pk=self.user_id, is_staff=True).exists()
        denied = national_code_denied(self.national_id, is_staff=is_staff)
        if denied:
            raise ValidationError({'national_id': denied})
        super().save(*args, **kwargs)


class Job(models.Model):
    # حداکثر تعداد شغلی که هر پروفایل می‌تواند ثبت کند (در ویوها و قالب‌ها استفاده می‌شود)
    MAX_PER_PROFILE = 3

    title = models.CharField(max_length=150, verbose_name='عنوان شغلی')
    organization = models.CharField(blank=True, max_length=150, verbose_name='سازمان / شرکت')
    department = models.CharField(blank=True, max_length=150, verbose_name='واحد سازمانی')
    employment_type = models.CharField(
        blank=True,
        max_length=20,
        choices=[
            ('official', 'رسمی'),
            ('contractual', 'قراردادی'),
            ('project', 'پروژه‌ای'),
            ('part_time', 'پاره‌وقت'),
            ('freelance', 'آزاد'),
        ],
        verbose_name='نوع استخدام',
    )
    hire_date = models.DateField(blank=True, null=True, verbose_name='تاریخ شروع')
    is_current = models.BooleanField(default=True, verbose_name='شغل فعلی')
    field_of_activity = models.CharField(blank=True, max_length=150, verbose_name='حوزه فعالیت')
    skills = models.CharField(blank=True, help_text='با کاما جدا کنید', max_length=255, verbose_name='مهارت‌های تخصصی')
    order = models.PositiveSmallIntegerField(default=0, verbose_name='ترتیب نمایش')
    created_at = models.DateTimeField(auto_now_add=True)
    job_code = models.CharField(
        blank=True,
        max_length=30,
        null=True,
        verbose_name='کد اختصاصی شغل',
        help_text='کد یکتای این شغل برای همین کاربر؛ در سراسل برنامه استفاده می‌شود و می‌تواند بین کاربران دیگر تکرار شود.',
    )
    is_unemployed = models.BooleanField(default=False, verbose_name='بدون شغل / بیکار')
    photo = models.FileField(blank=True, null=True, upload_to='jobs/', verbose_name='عکس پروفایل شغل')
    work_gps_accuracy = models.PositiveIntegerField(blank=True, null=True, verbose_name='دقت GPS محل کار (متر)')
    work_gps_latitude = models.FloatField(blank=True, null=True, verbose_name='عرض جغرافیایی محل کار (GPS)')
    work_gps_longitude = models.FloatField(blank=True, null=True, verbose_name='طول جغرافیایی محل کار (GPS)')
    work_gps_updated_at = models.DateTimeField(blank=True, null=True, verbose_name='آخرین دریافت GPS محل کار')
    sector = models.ForeignKey('jobs.sector', blank=True, null=True, on_delete=models.PROTECT, related_name='user_jobs', verbose_name='حوزه (کاتالوگ)')
    industry = models.ForeignKey('jobs.industry', blank=True, null=True, on_delete=models.PROTECT, related_name='user_jobs', verbose_name='صنعت (کاتالوگ)')
    category = models.ForeignKey('jobs.jobcategory', blank=True, null=True, on_delete=models.PROTECT, related_name='user_jobs', verbose_name='دسته شغلی (کاتالوگ)')
    occupation_title = models.ForeignKey('jobs.jobtitle', blank=True, null=True, on_delete=models.PROTECT, related_name='user_jobs', verbose_name='عنوان شغلی (کاتالوگ)')
    specialization = models.ForeignKey('jobs.jobspecialization', blank=True, null=True, on_delete=models.PROTECT, related_name='user_jobs', verbose_name='تخصص‌های مرتبط (کاتالوگ)')
    work_address = models.CharField(blank=True, max_length=255, verbose_name='آدرس محل کار')
    work_city = models.CharField(blank=True, max_length=100, verbose_name='شهر/شهرستان محل کار')
    work_province = models.CharField(blank=True, max_length=100, verbose_name='استان محل کار')
    work_country = models.CharField(blank=True, max_length=100, verbose_name='کشور محل کار (ج)')
    work_same_as_residence = models.BooleanField(default=True, verbose_name='موقعیت مکانی شغلی همان محل سکونت است (Current Location)')
    free_address = models.CharField(blank=True, max_length=255, verbose_name='آدرس کامل محل کار (ب — شغل آزاد)')
    free_city = models.CharField(blank=True, max_length=100, verbose_name='شهر/شهرستان محل کار (ب — شغل آزاد)')
    free_province = models.CharField(blank=True, max_length=100, verbose_name='استان محل کار (ب — شغل آزاد)')
    free_country = models.CharField(blank=True, default='ایران', max_length=100, verbose_name='کشور محل کار (ب — شغل آزاد)')
    employment_mode = models.CharField(blank=True, choices=[('free', 'ب) شغل آزاد'), ('employee', 'ج) شغل وابسته (کارمندی)'), ('unemployed', 'الف) بدون شغل / بیکار')], max_length=20, verbose_name='نوع ثبت شغل')
    free_gps_latitude = models.FloatField(blank=True, null=True, verbose_name='عرض جغرافیایی محل کارِ شغل آزاد (GPS)')
    free_gps_longitude = models.FloatField(blank=True, null=True, verbose_name='طول جغرافیایی محل کارِ شغل آزاد (GPS)')
    free_gps_accuracy = models.PositiveIntegerField(blank=True, null=True, verbose_name='دقت GPS محل کارِ شغل آزاد (متر)')
    free_gps_updated_at = models.DateTimeField(blank=True, null=True, verbose_name='آخرین دریافت GPS محل کارِ شغل آزاد')
    profile = models.ForeignKey('Profile', on_delete=models.CASCADE, related_name='jobs')

    class Meta:
        verbose_name = 'شغل'
        verbose_name_plural = 'مشاغل'
        ordering = ['order', 'created_at']
        constraints = [
            models.UniqueConstraint(fields=('profile', 'job_code'), name='uniq_profile_job_code'),
        ]
        indexes = [
            models.Index(fields=['sector', 'industry', 'category', 'occupation_title', 'specialization'], name='jb_job_chain_idx'),
        ]

    def __str__(self):
        return self.title or 'شغل بدون عنوان'

    @property
    def catalog_breadcrumb(self):
        """مسیر نمایشی شغل از فهرست سلسله‌مراتبی: حوزه › صنعت › دسته › عنوان › تخصص."""
        from jobs.models import breadcrumb

        return breadcrumb({
            'sector': self.sector,
            'industry': self.industry,
            'category': self.category,
            'occupation_title': self.occupation_title,
            'specialization': self.specialization,
        })

    @property
    def has_free_gps(self):
        return self.free_gps_latitude is not None and self.free_gps_longitude is not None

    @property
    def has_work_gps(self):
        return self.work_gps_latitude is not None and self.work_gps_longitude is not None

    @property
    def has_gps(self):
        """آیا برای «نوع ثبت» این شغل مختصات GPS ثبت شده است؟"""
        if self.employment_mode == 'unemployed':
            return False
        if self.employment_mode == 'free':
            return self.has_free_gps
        if self.employment_mode == 'employee':
            return self.has_work_gps
        return self.has_free_gps or self.has_work_gps

    @property
    def active_statuses(self):
        """استتوس‌های هنوز منقضی‌نشده (هر استتوس ۲۴ ساعت زنده است)."""
        return self.statuses.filter(expires_at__gt=timezone.now())

    @property
    def job_logo_doc(self):
        """لوگوی/مستندات این شغل (فقط یکی): فایلِ پوشهٔ «jobs/<رتبه>/photos» این شغل.

        UserDocument با «doc_type='job_photo'» و مسیرِ «jobs/<order>/photos/»
        ذخیره می‌شود؛ این ویژگی بدون کوئری اضافه در کارت شغل، فایلِ همان پوشه را
        برمی‌گرداند (None اگر هنوز لوگویی ثبت نشده باشد).
        """
        if self.profile_id is None:
            return None
        return self.profile.documents.filter(
            doc_type="job_photo",
            file__startswith=f"jobs/{self.order}/photos",
        ).first()

    def _work_en(self, model, fa_field, en_field, fa_value):
        """نام انگلیسی از جدول مرجع برای نمایش با زبان فعال رابط."""
        fa = (fa_value or '').strip()
        if not fa:
            return ''
        row = model.objects.filter(**{fa_field: fa}).only(en_field).first()
        return (getattr(row, en_field, '') or '').strip() if row else ''

    @property
    def work_country_en(self):
        return self._work_en(CountryTbl, 'country_fa', 'country_en', self.work_country)

    @property
    def work_province_en(self):
        return self._work_en(ProvinceTbl, 'province_fa', 'province_en', self.work_province)

    @property
    def work_city_en(self):
        return self._work_en(CityTbl, 'city_fa', 'city_en', self.work_city)

class FirstnameTbl(models.Model):
    first_name_fa = models.CharField(max_length=100, unique=True, verbose_name='نام فارسی', error_messages={'unique': 'این نام (فارسی) قبلاً در جدول نام‌ها ثبت شده است.'})
    first_name_en = models.CharField(blank=True, max_length=100, verbose_name='نام انگلیسی')
    gender = models.CharField(blank=True, max_length=10, choices=[('', 'نامشخص'), ('male', 'مردانه'), ('female', 'زنانه')], default='', help_text='مردانه برای فهرست «نام پدر» و زنانه برای فهرست «نام مادر».', verbose_name='جنسیت')

    class Meta:
        verbose_name = 'نام'
        verbose_name_plural = 'نام‌ها'
        ordering = ['first_name_fa']

    def __str__(self):
        return self.first_name_fa


class FamilynameTbl(models.Model):
    familyname_fa = models.CharField(max_length=100, unique=True, verbose_name='نام خانوادگی فارسی', error_messages={'unique': 'این نام خانوادگی قبلاً در جدول ثبت شده است.'})
    familyname_en = models.CharField(blank=True, max_length=100, verbose_name='نام خانوادگی انگلیسی')

    class Meta:
        verbose_name = 'نام خانوادگی'
        verbose_name_plural = 'نام‌های خانوادگی'
        ordering = ['familyname_fa']

    def __str__(self):
        return self.familyname_fa


class UserGroup(models.Model):
    name = models.CharField(max_length=120, verbose_name='نام گروه')
    code = models.CharField(max_length=60, unique=True, verbose_name='کد گروه')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField('User', blank=True, related_name='user_groups', verbose_name='اعضا')

    class Meta:
        verbose_name = 'گروه کاربری'
        verbose_name_plural = 'گروه‌های کاربری'
        ordering = ['name']

    def __str__(self):
        return self.name


class CountryTbl(models.Model):
    country_fa = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='نام کشور (فارسی)',
        error_messages={'unique': 'این کشور قبلاً در جدول کشورها ثبت شده است.'},
    )
    country_en = models.CharField(blank=True, max_length=100, verbose_name='نام کشور (انگلیسی)')

    class Meta:
        verbose_name = 'کشور'
        verbose_name_plural = 'کشورها'
        ordering = ['country_fa']

    def __str__(self):
        return self.country_fa


class ProvinceTbl(models.Model):
    province_fa = models.CharField(
        max_length=100,
        verbose_name='نام استان (فارسی)',
    )
    province_en = models.CharField(blank=True, max_length=100, verbose_name='نام استان (انگلیسی)')
    country = models.ForeignKey('CountryTbl', on_delete=models.CASCADE, related_name='provinces', verbose_name='کشور')

    class Meta:
        verbose_name = 'استان'
        verbose_name_plural = 'استان‌ها'
        ordering = ['province_fa']
        indexes = [
            models.Index(fields=['country'], name='prov_tbl_country_idx'),
        ]
        constraints = [
            models.UniqueConstraint(fields=('country', 'province_fa'), name='uniq_country_province_fa', violation_error_message='این استان برای همین کشور قبلاً در جدول استان‌ها ثبت شده است.'),
        ]

    def __str__(self):
        return self.province_fa


class CityTbl(models.Model):
    city_fa = models.CharField(max_length=100, verbose_name='نام شهرستان (فارسی)')
    city_en = models.CharField(blank=True, max_length=100, verbose_name='نام شهرستان (انگلیسی)')
    province = models.ForeignKey('ProvinceTbl', on_delete=models.CASCADE, related_name='cities', verbose_name='استان')

    class Meta:
        verbose_name = 'شهرستان'
        verbose_name_plural = 'شهرستان‌ها'
        ordering = ['city_fa']
        indexes = [
            models.Index(fields=['province'], name='city_tbl_province_idx'),
            models.Index(fields=['city_fa'], name='city_tbl_name_idx'),
        ]
        constraints = [
            models.UniqueConstraint(fields=('province', 'city_fa'), name='uniq_province_city_fa', violation_error_message='این شهرستان قبلاً برای همین استان ثبت شده است.'),
        ]

    def __str__(self):
        return self.city_fa


class LocationSetting(models.Model):
    @classmethod
    def get(cls):
        """نمونهٔ تک‌رکوردی تنظیمات سرویس موقعیت (در صورت نبود می‌سازد)."""
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj

    map_provider = models.CharField(
        max_length=12,
        choices=[('neshan', 'نشان (Neshan)'), ('osm', 'OpenStreetMap'), ('google', 'گوگل (Google Maps)')],
        default='neshan',
        help_text='نقشه‌ای که کاربران در بخش «اطلاعات مکانی» می‌بینند. نشان و گوگل فقط وقتی کلیدشان روی سرور تنظیم شده باشد نمایش داده می‌شود؛ OpenStreetMap بدون کلید در دسترس است و در نبودِ کلیدِ انتخابِ فعلی به‌عنوان جایگزین نمایش داده می‌شود تا همیشه نقشه‌ای برای کاربر باقی بماند.',
        verbose_name='ارائه‌دهندهٔ نقشه (Map Provider)',
    )
    location_provider = models.CharField(
        max_length=12,
        choices=[('all', 'همه (GPS + جایگزین IP)'), ('browser', 'فقط GPS مرورگر'), ('mobile', 'موبایل (GPS بومی + GPS مرورگر)')],
        default='all',
        help_text='موقعیت کاربر هنگام «دریافت خودکار موقعیت» از کجا استخراج شود: «همه» = GPS مرورگر/دستگاه و در نبودش موقعیت تقریبی IP؛ «فقط GPS مرورگر» = صرفاً navigator.geolocation و بدون جایگزین IP؛ «موبایل» = ابتدا از پلِ اپلیکیشن بومی (window.HabibNative.getLocation) و اگر موجود نبود مثل «همه».',
        verbose_name='منبع موقعیت (Location Provider)',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'تنظیمات سرویس موقعیت'
        verbose_name_plural = 'تنظیمات سرویس موقعیت'

    def __str__(self):
        return f'تنظیمات مکانی ({self.map_provider})'


class ReservedNationalCode(models.Model):
    ACCESS_ADMIN_ONLY = 'admin_only'
    ACCESS_BLOCKED = 'blocked'
    ACCESS_CHOICES = [
        (ACCESS_ADMIN_ONLY, 'فقط ادمین (is_staff)'),
        (ACCESS_BLOCKED, 'ممنوع برای همه'),
    ]

    national_id = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='کد ملی رزروشده',
        help_text='کد ملی ۱۰ رقمی که می‌خواهید از دسترس کاربران عادی خارج شود.',
    )
    access_level = models.CharField(
        max_length=12,
        choices=ACCESS_CHOICES,
        default='admin_only',
        help_text='«فقط ادمین»: فقط کاربران با دسترسی ادمین می‌توانند این کد را ثبت کنند؛ «ممنوع برای همه»: هیچ‌کس نمی‌تواند.',
        verbose_name='سطح دسترسی',
    )
    title = models.CharField(
        blank=True,
        max_length=200,
        verbose_name='عنوان / توضیح',
        help_text='اختیاری؛ مثلاً «کد اختصاصی مدیر ارشد» تا در فهرست مشخص باشد.',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='با غیرفعال‌کردن، محدودیت بدون حذف رکورد برداشته می‌شود.',
        verbose_name='فعال',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین به‌روزرسانی')

    class Meta:
        verbose_name = 'کد ملی رزروشده'
        verbose_name_plural = 'کدهای ملی رزروشده'
        ordering = ['national_id']

    def __str__(self):
        return self.national_id


def reserved_national_code(national_id):
    """اگر کد ملی در فهرست «کدهای رزروشدهٔ» فعال باشد، رکورد آن را برمی‌گرداند.

    خروجی به‌صورت truthy کنترل می‌شود (مثلاً برای جلوگیری از استفادهٔ کد رزروشده
    به‌عنوان «کد ملی معرف»)؛ کد غیررزروشده → None.
    """
    nid = (national_id or '').strip()
    if not nid:
        return None
    return ReservedNationalCode.objects.filter(national_id=nid, is_active=True).first()


def national_code_denied(national_id, is_staff=False):
    """کنترل کدهای ملی رزروشدهٔ پنل مدیریت.

    خروجی: پیام خطا اگر ثبت برای این کاربر ممنوع باشد، وگرنه None.
    - «فقط ادمین»: کاربر با دسترسی ادمین (is_staff) مجاز، بقیه ممنوع.
    - «ممنوع برای همه»: هیچ‌کس مجاز نیست.
    """
    nid = (national_id or '').strip()
    if not nid:
        return None
    rule = ReservedNationalCode.objects.filter(national_id=nid, is_active=True).first()
    if rule is None:
        return None
    if rule.access_level == ReservedNationalCode.ACCESS_ADMIN_ONLY:
        if is_staff:
            return None
        return 'این کد ملی رزرو شده از قبل است و فقط توسط ادمین قابل ثبت است.'
    return 'این کد ملی رزرو شده است و امکان ثبت آن برای هیچ کاربری وجود ندارد.'


class EducationInstitution(models.Model):
    TYPE_GOVERNMENT = 'government'
    TYPE_AZAD = 'azad'
    TYPE_OTHER_PROFIT = 'other_profit'
    TYPE_NON_PROFIT = 'non_profit'
    TYPE_CHOICES = [
        (TYPE_GOVERNMENT, 'دولتی'),
        (TYPE_AZAD, 'دانشگاه آزاد اسلامی'),
        (TYPE_OTHER_PROFIT, 'سایر دانشگاه‌های انتفاعی'),
        (TYPE_NON_PROFIT, 'غیرانتفاعی'),
    ]

    name = models.CharField(max_length=250, verbose_name='نام مرکز')
    name_en = models.CharField(blank=True, max_length=250, verbose_name='نام مرکز (انگلیسی)')
    code = models.CharField(max_length=40, unique=True, verbose_name='کد مرکز')
    institution_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='government',
        verbose_name='نوع مرکز',
    )
    province = models.CharField(blank=True, max_length=100, verbose_name='استان')
    city = models.CharField(blank=True, max_length=100, verbose_name='شهر')
    source = models.CharField(blank=True, max_length=300, verbose_name='منبع فهرست')
    source_year = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='سال منبع')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'مرکز دانشگاهی'
        verbose_name_plural = 'مراکز دانشگاهی'
        ordering = ['institution_type', 'name']
        indexes = [
            models.Index(fields=['institution_type', 'is_active'], name='edu_inst_type_active_idx'),
            models.Index(fields=['name'], name='edu_inst_name_idx'),
        ]

    def __str__(self):
        return self.name


class StudyField(models.Model):
    name = models.CharField(max_length=250, verbose_name='نام رشته')
    name_en = models.CharField(blank=True, max_length=250, verbose_name='نام رشته (انگلیسی)')
    code = models.CharField(max_length=40, unique=True, verbose_name='کد رشته')
    study_group = models.ForeignKey('StudyGroup', on_delete=models.PROTECT, related_name='fields', verbose_name='گروه امتحانی')
    source = models.CharField(blank=True, max_length=300, verbose_name='منبع فهرست')
    source_year = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='سال منبع')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'رشته تحصیلی'
        verbose_name_plural = 'رشته‌های تحصیلی'
        ordering = ['study_group__code', 'name']
        indexes = [
            models.Index(fields=['study_group', 'is_active'], name='edu_field_group_active_idx'),
            models.Index(fields=['name'], name='edu_field_name_idx'),
        ]

    def __str__(self):
        return self.name


class StudySpecialization(models.Model):
    name = models.CharField(max_length=250, verbose_name='نام گرایش')
    name_en = models.CharField(blank=True, max_length=250, verbose_name='نام گرایش (انگلیسی)')
    code = models.CharField(max_length=40, unique=True, verbose_name='کد گرایش')
    source = models.CharField(blank=True, max_length=300, verbose_name='منبع فهرست')
    source_year = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='سال منبع')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    field = models.ForeignKey('StudyField', on_delete=models.PROTECT, related_name='specializations', verbose_name='رشتهٔ مادر')

    class Meta:
        verbose_name = 'گرایش تحصیلی'
        verbose_name_plural = 'گرایش‌های تحصیلی'
        ordering = ['field__name', 'name']
        indexes = [
            models.Index(fields=['field', 'is_active'], name='edu_spec_field_active_idx'),
            models.Index(fields=['name'], name='edu_spec_name_idx'),
        ]

    def __str__(self):
        return self.name


class StudyGroup(models.Model):
    name = models.CharField(max_length=150, verbose_name='نام گروه')
    name_en = models.CharField(blank=True, max_length=150, verbose_name='نام گروه (انگلیسی)')
    code = models.CharField(max_length=20, unique=True, verbose_name='کد')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'گروه امتحانی'
        verbose_name_plural = 'گروه‌های امتحانی'
        ordering = ['code']
        indexes = [
            models.Index(fields=['is_active'], name='edu_group_active_idx'),
        ]

    def __str__(self):
        return self.name


def user_docs_root():
    """ریشهٔ پوشهٔ مدارک کاربران (تنظیم DOCS_ROOT) به‌صورت pathlib.Path."""
    return Path(getattr(settings, 'DOCS_ROOT', BASE_DIR / 'Docs'))


class UserDocsStorage(FileSystemStorage):
    """استوریج مدارک کاربر با ریشهٔ پویا: همیشه DOCS_ROOTِ تنظیماتِ لحظه‌ای.

    FileField استوریج کال‌شونده را فقط یک‌بار هنگام لود اپ حل می‌کند؛ برای آنکه
    override_settings(DOCS_ROOT=...) در تست‌ها (یا تغییر تنظیمات در زمان اجرا)
    هم اعمال شود، محل ریشه در هر دسترسی از تنظیمات خوانده می‌شود.
    """

    @property
    def base_location(self):
        return str(user_docs_root())

    @property
    def location(self):
        return os.path.abspath(self.base_location)


def user_docs_storage():
    """استوریج مخصوص فایل‌های مدرک کاربر: ریشهٔ آن DOCS_ROOT است."""
    return UserDocsStorage()


def user_docs_upload_to(instance, filename):
    """پوشه ذخیره فایل مدرک: «<کد ملی پروفایل>/<نام فایل>» زیر DOCS_ROOT."""
    return f"{instance.profile.national_id}/{filename}"


class UserDocument(models.Model):
    TYPE_HINTS = {
        'personal_photo': 'تصویر پرسنلی (جعبهً به طول ۴×۶ یا معادل)' ,
        'signature': 'امضا (عکس یا فایل تصویری)' ,
        'national_card': 'کارت ملی (عکس frente/back)' ,
        'passport': 'گذرنامه (عکس amid / صفحه مجاز)' ,
        'education_doc': 'مدارک تحصیلی (شبا / اسناد دانشجویی)' ,
        'resume': 'رزومه (PDF / Word)' ,
        'contract': 'قراردادها (PDF / Word)' ,
        'attachment': 'فایل‌های ضمیمه (PDF / Excel / صورتی)' ,
    }
    TYPE_EXTENSIONS = {
        'resume': ('.pdf', '.doc', '.docx', '.txt'),
        'contract': ('.pdf', '.doc', '.docx', '.txt'),
        'attachment': ('.pdf', '.xls', '.xlsx', '.doc', '.docx', '.ppt', '.pptx', '.txt'),
        'personal_photo': ('.jpg', '.jpeg', '.png', '.webp'),
        'signature': ('.jpg', '.jpeg', '.png', '.webp'),
        'national_card': ('.jpg', '.jpeg', '.png', '.webp'),
        'passport': ('.jpg', '.jpeg', '.png', '.webp'),
        'education_doc': ('.pdf', '.jpg', '.jpeg', '.png', '.webp'),
    }
    doc_type = models.CharField(
        max_length=30,
        choices=[
            ('personal_photo', 'تصویر پرسنلی'),
            ('signature', 'امضا'),
            ('national_card', 'کارت ملی'),
            ('passport', 'گذرنامه'),
            ('education_doc', 'مدارک تحصیلی'),
            ('resume', 'رزومه'),
            ('contract', 'قراردادها'),
            ('attachment', 'فایل‌های ضمیمه'),
        ],
        verbose_name='نوع مدرک',
    )
    file = models.FileField(max_length=500, storage=user_docs_storage(), upload_to=user_docs_upload_to, verbose_name='فایل')
    original_name = models.CharField(blank=True, max_length=255, verbose_name='نام اصلی فایل')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ بارگذاری')
    profile = models.ForeignKey('Profile', on_delete=models.CASCADE, related_name='documents', verbose_name='پروفایل')

    class Meta:
        verbose_name = 'مدرک کاربر'
        verbose_name_plural = 'مدارک کاربران'
        ordering = ['doc_type', '-uploaded_at']

    def __str__(self):
        return f"{self.get_doc_type_display()} ({self.profile})"


class FameNameTbl(models.Model):
    fame_name_fa = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='شهرت (فارسی)',
        error_messages={'unique': 'این شهرت قبلاً در جدول ثبت شده است.'},
    )
    fame_name_en = models.CharField(blank=True, max_length=100, verbose_name='شهرت (انگلیسی)')
    description = models.TextField(blank=True, default='', help_text='اختیاری؛ توضیح دربارهٔ منشأ یا کاربرد این شهرت (فقط نمایشی در پنل مدیریت).', verbose_name='توضیحات')

    class Meta:
        verbose_name = 'شهرت'
        verbose_name_plural = 'شهرت‌ها'
        ordering = ['fame_name_fa']

    def __str__(self):
        return self.fame_name_fa


class JobStatus(models.Model):
    image = models.FileField(max_length=500, upload_to='job_status/', verbose_name='عکس استتوس')
    caption = models.CharField(blank=True, max_length=200, verbose_name='توضیح استتوس')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان انتشار')
    expires_at = models.DateTimeField(db_index=True, verbose_name='زمان انقضا')
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='statuses', verbose_name='شغل')

    class Meta:
        verbose_name = 'استتوس شغل'
        verbose_name_plural = 'استتوس‌های شغل'
        ordering = ['-created_at']

    def __str__(self):
        return f'استتوس شغل {self.job_id}'

    def save(self, *args, **kwargs):
        # انقضای ۲۴ ساعته سمت مدل محاسبه می‌شود (فیلد expires_at در فرم نیست).
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        if not self.expires_at:
            return True
        return self.expires_at <= timezone.now()

    @classmethod
    def purge_expired(cls, max_age_hours=2):
        """پاک‌سازی تنبل استتوس‌های منقضی: فقط منقضی‌شده‌هایِ قدیمی‌تر از سقف ۲ ساعت.

        فایل عکس هر رکورد هم از دیسک حذف می‌شود؛ منقضی‌شده‌هایِ تازه (کمتر از سقف)
        باقی می‌مانند تا در پاک‌سازی بعدی حذف شوند.
        """
        cutoff = timezone.now() - timedelta(hours=max_age_hours)
        stale = cls.objects.filter(expires_at__lt=cutoff)
        for status in stale:
            if status.image:
                status.image.delete(save=False)
        stale.delete()
