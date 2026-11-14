"""Seed کد ملی نمونهٔ «رزروشده» برای ماژول کنترل کد ملی.

مطابق درخواست، کد اختصاصی مدیر ارشد (مثلاً ۹۹۹۹۹۹۹۹۹۹) از بدو نصب در فهرست
کدهای رزروشده با سطح «فقط ادمین» قرار می‌گیرد تا کاربران عادی نتوانند آن را
در پروفایل خود ثبت کنند. کد ملی در سامانه ۱۰ رقمی است (مثل Profile.national_id)؛
بنابراین نمونهٔ رزروشده ۹۹۹۹۹۹۹۹۹۹ است. عملیات idempotent است (get_or_create)
و رکوردِ از پیش موجود دست‌نخورده می‌ماند.
"""

from django.db import migrations


def seed_reserved_national_code(apps, schema_editor):
    ReservedNationalCode = apps.get_model("accounts", "ReservedNationalCode")
    ReservedNationalCode.objects.get_or_create(
        national_id="9999999999",
        defaults={
            "access_level": "admin_only",
            "title": "کد اختصاصی مدیر ارشد",
            "is_active": True,
        },
    )


def unseed_reserved_national_code(apps, schema_editor):
    """حذف رکورد نمونه (فقط اگر همان رکوردِ seeded باشد)."""
    ReservedNationalCode = apps.get_model("accounts", "ReservedNationalCode")
    ReservedNationalCode.objects.filter(
        national_id="9999999999", title="کد اختصاصی مدیر ارشد"
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0028_reservednationalcode"),
    ]

    operations = [
        migrations.RunPython(
            seed_reserved_national_code, unseed_reserved_national_code
        ),
    ]