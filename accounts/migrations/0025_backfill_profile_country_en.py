# -*- coding: utf-8 -*-
"""پُرکردن نام انگلیسیِ کشورها برای پروفایل‌های موجود (دوزبانه‌سازی نمایش).

فیلدهای کشور (country و تابعیت/ملیت/اقامت دائم) همیشه مقدارِ رسمی فارسی را
نگه می‌دارند؛ از این پس نسخهٔ انگلیسیِ هم‌ارز هنگام ذخیره کنارشان در
extra_data («*_en») نوشته می‌شود تا بج‌های خلاصه و انتخاب‌گرها با زبانِ فعالِ
رابط نمایش داده شوند. این مهاجرت همان کلیدها را برای پروفایل‌های قدیمی (که پیش
از این قابلیت ذخیره شده‌اند) از جدول مرجع CountryTbl پُر می‌کند؛ رکوردهای بدون
رکورد مرجع یا بدون نام انگلیسی دست‌نخورده می‌مانند (نمایش با fallback فارسی است).
"""

from django.db import migrations


def backfill_country_en(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    CountryTbl = apps.get_model("accounts", "CountryTbl")

    en_by_fa = {
        row.country_fa: (row.country_en or "").strip()
        for row in CountryTbl.objects.all()
        if (row.country_en or "").strip()
    }
    if not en_by_fa:
        return

    fields = ("country", "citizenship", "nationality", "permanent_residence")
    batch = []
    for profile in Profile.objects.all().only("pk", "extra_data", *fields).iterator():
        extra = dict(profile.extra_data or {})
        changed = False
        for f in fields:
            fa = (getattr(profile, f) or "").strip()
            if fa and not (extra.get(f"{f}_en") or "").strip():
                mapped = en_by_fa.get(fa)
                if mapped:
                    extra[f"{f}_en"] = mapped
                    changed = True
        if changed:
            profile.extra_data = extra
            batch.append(profile)
        if len(batch) >= 500:
            Profile.objects.bulk_update(batch, ["extra_data"])
            batch = []
    if batch:
        Profile.objects.bulk_update(batch, ["extra_data"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0024_seed_countries"),
    ]

    operations = [
        migrations.RunPython(backfill_country_en, migrations.RunPython.noop),
    ]