# -*- coding: utf-8 -*-
import os
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import models


BASE_DIR = Path(__file__).resolve().parent.parent
class User(models.Model):
    verbose_name = 'کاربر'
    verbose_name_plural = 'کاربران'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    password = models.CharField(max_length=128, verbose_name='password'
    last_login = models.DateTimeField(blank=True, null=True, verbose_name='last login'
    is_superuser = models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status'
    mobile_number = models.CharField(max_length=11, unique=True, verbose_name='شماره موبایل'
    referrer_username = models.CharField(blank=True, max_length=50, null=True, verbose_name='نام کاربری معرف'
    is_active = models.BooleanField(default=True, verbose_name='فعال'
    is_staff = models.BooleanField(default=False, verbose_name='دسترسی ادمین'
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ عضویت'
    last_login_at = models.DateTimeField(auto_now=True, verbose_name='آخرین ورود'
    groups = models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups'
    user_permissions = models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions'


class Profile(models.Model):
    verbose_name = 'پروفایل'
    verbose_name_plural = 'پروفایل\u200cها'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    avatar = models.FileField(blank=True, null=True, upload_to='avatars/'
    first_name = models.CharField(blank=True, max_length=100, verbose_name='نام'
    last_name = models.CharField(blank=True, max_length=100, verbose_name='نام خانوادگی'
    father_name = models.CharField(blank=True, max_length=100, verbose_name='نام پدر'
    national_id = models.CharField(blank=True, max_length=10, verbose_name='کد ملی'
    date_of_birth = models.DateField(blank=True, null=True, verbose_name='تاریخ تولد'
    gender = models.CharField(blank=True, choices=[('male', 'مرد'
    female = 'زن'


class Job(models.Model):
    verbose_name = 'شغل'
    verbose_name_plural = 'مشاغل'
    id = models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    title = models.CharField(max_length=150, verbose_name='عنوان شغلی'
    organization = models.CharField(blank=True, max_length=150, verbose_name='سازمان / شرکت'
    department = models.CharField(blank=True, max_length=150, verbose_name='واحد سازمانی'
    employment_type = models.CharField(blank=True, choices=[('official', 'رسمی'
    contractual = 'قراردادی'
    project = 'پروژه\u200cای'
    part_time = 'پاره\u200cوقت'
    freelance = 'آزاد'


class FirstnameTbl(models.Model):
    verbose_name = 'نام'
    verbose_name_plural = 'نام\u200cها'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    first_name_fa = models.CharField(max_length=100, unique=True, verbose_name='نام فارسی'
    first_name_en = models.CharField(blank=True, max_length=100, verbose_name='نام انگلیسی'


class FamilynameTbl(models.Model):
    verbose_name = 'نام خانوادگی'
    verbose_name_plural = 'نام\u200cهای خانوادگی'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    familyname_fa = models.CharField(max_length=100, unique=True, verbose_name='نام خانوادگی فارسی'
    familyname_en = models.CharField(blank=True, max_length=100, verbose_name='نام خانوادگی انگلیسی'


class UserGroup(models.Model):
    verbose_name = 'گروه کاربری'
    verbose_name_plural = 'گروه\u200cهای کاربری'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    name = models.CharField(max_length=120, verbose_name='نام گروه'
    code = models.CharField(max_length=60, unique=True, verbose_name='کد گروه'
    description = models.TextField(blank=True, verbose_name='توضیحات'
    is_active = models.BooleanField(default=True, verbose_name='فعال'
    created_at = models.DateTimeField(auto_now_add=True


class CountryTbl(models.Model):
    verbose_name = 'کشور'
    verbose_name_plural = 'کشورها'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    country_fa = models.CharField(error_messages={'unique': 'این کشور قبلاً در جدول کشورها ثبت شده است.'}, max_length=100, unique=True, verbose_name='نام کشور (فارسی
    country_en = models.CharField(blank=True, max_length=100, verbose_name='نام کشور (انگلیسی


class ProvinceTbl(models.Model):
    verbose_name = 'استان'
    verbose_name_plural = 'استان\u200cها'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    province_fa = models.CharField(error_messages={'unique': 'این استان قبلاً در جدول استان\u200cها ثبت شده است.'}, max_length=100, unique=True, verbose_name='نام استان (فارسی
    province_en = models.CharField(blank=True, max_length=100, verbose_name='نام استان (انگلیسی
    country = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='provinces', to='accounts.countrytbl', verbose_name='کشور'


class CityTbl(models.Model):
    verbose_name = 'شهرستان'
    verbose_name_plural = 'شهرستان\u200cها'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    city_fa = models.CharField(max_length=100, verbose_name='نام شهرستان (فارسی
    city_en = models.CharField(blank=True, max_length=100, verbose_name='نام شهرستان (انگلیسی
    province = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cities', to='accounts.provincetbl', verbose_name='استان'


class LocationSetting(models.Model):
    verbose_name = 'تنظیمات سرویس موقعیت'
    verbose_name_plural = 'تنظیمات سرویس موقعیت'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    map_provider = models.CharField(choices=[('neshan', 'نشان (Neshan
    osm = 'OpenStreetMap'
    google = 'گوگل (Google Maps


class ReservedNationalCode(models.Model):
    verbose_name = 'کد ملی رزروشده'
    verbose_name_plural = 'کدهای ملی رزروشده'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    national_id = models.CharField(help_text='کد ملی ۱۰ رقمی که می\u200cخواهید از دسترس کاربران عادی خارج شود.', max_length=10, unique=True, verbose_name='کد ملی رزروشده'
    access_level = models.CharField(choices=[('admin_only', 'فقط ادمین (is_staff
    blocked = 'ممنوع برای همه'


class EducationInstitution(models.Model):
    verbose_name = 'مرکز دانشگاهی'
    verbose_name_plural = 'مراکز دانشگاهی'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    name = models.CharField(max_length=250, verbose_name='نام مرکز'
    name_en = models.CharField(blank=True, max_length=250, verbose_name='نام مرکز (انگلیسی
    code = models.CharField(max_length=40, unique=True, verbose_name='کد مرکز'
    institution_type = models.CharField(choices=[('government', 'دولتی'
    azad = 'دانشگاه آزاد اسلامی'
    other_profit = 'سایر دانشگاه\u200cهای انتفاعی'
    non_profit = 'غیرانتفاعی'


class StudyField(models.Model):
    verbose_name = 'رشته تحصیلی'
    verbose_name_plural = 'رشته\u200cهای تحصیلی'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    name = models.CharField(max_length=250, verbose_name='نام رشته'
    name_en = models.CharField(blank=True, max_length=250, verbose_name='نام رشته (انگلیسی
    code = models.CharField(max_length=40, unique=True, verbose_name='کد رشته'
    education_group = models.CharField(blank=True, max_length=150, verbose_name='گروه آزمایشی/تحصیلی'
    source = models.CharField(blank=True, max_length=300, verbose_name='منبع فهرست'
    source_year = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='سال منبع'
    is_active = models.BooleanField(default=True, verbose_name='فعال'
    created_at = models.DateTimeField(auto_now_add=True
    updated_at = models.DateTimeField(auto_now=True


class StudySpecialization(models.Model):
    verbose_name = 'گرایش تحصیلی'
    verbose_name_plural = 'گرایش\u200cهای تحصیلی'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    name = models.CharField(max_length=250, verbose_name='نام گرایش'
    name_en = models.CharField(blank=True, max_length=250, verbose_name='نام گرایش (انگلیسی
    code = models.CharField(max_length=40, unique=True, verbose_name='کد گرایش'
    source = models.CharField(blank=True, max_length=300, verbose_name='منبع فهرست'
    source_year = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='سال منبع'
    is_active = models.BooleanField(default=True, verbose_name='فعال'
    created_at = models.DateTimeField(auto_now_add=True
    updated_at = models.DateTimeField(auto_now=True
    field = models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='specializations', to='accounts.studyfield', verbose_name='رشتهٔ مادر'


class UserDocument(models.Model):
    verbose_name = 'مدرک کاربر'
    verbose_name_plural = 'مدارک کاربران'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    doc_type = models.CharField(choices=[('personal_photo', 'تصویر پرسنلی'
    signature = 'امضا'
    national_card = 'کارت ملی'
    passport = 'گذرنامه'
    education_doc = 'مدارک تحصیلی'
    resume = 'رزومه'
    contract = 'قراردادها'
    attachment = 'فایل\u200cهای ضمیمه'


class FameNameTbl(models.Model):
    verbose_name = 'شهرت'
    verbose_name_plural = 'شهرت\u200cها'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    fame_name_fa = models.CharField(error_messages={'unique': 'این شهرت قبلاً در جدول ثبت شده است.'}, max_length=100, unique=True, verbose_name='شهرت (فارسی
    fame_name_en = models.CharField(blank=True, max_length=100, verbose_name='شهرت (انگلیسی


class JobStatus(models.Model):
    verbose_name = 'استتوس شغل'
    verbose_name_plural = 'استتوس\u200cهای شغل'
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
    image = models.FileField(max_length=500, upload_to=accounts.models.job_status_upload_to, verbose_name='عکس استتوس'
    caption = models.CharField(blank=True, max_length=200, verbose_name='توضیح استتوس'
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان انتشار'
    expires_at = models.DateTimeField(db_index=True, verbose_name='زمان انقضا'
    job = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='statuses', to='accounts.job', verbose_name='شغل'

