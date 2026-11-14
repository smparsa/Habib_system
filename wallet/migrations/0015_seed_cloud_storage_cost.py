"""seed: تعرفهٔ «هزینهٔ فضای ابری (هر GB / هر 24 ساعت)» — کد cloud_storage.

ادمین می‌تواند مقدار سکه (پیش‌فرض 50) را در «پنل مدیریت ← هزینه‌های سکهٔ ماژول‌ها»
ویرایش، غیرفعال یا حذف کند؛ فرایند خرید فضای ابری کاربر همین تعرفه را می‌خواند.
"""

from django.db import migrations

CLOUD_STORAGE_COST = {
    "code": "cloud_storage",
    "title": "هزینهٔ فضای ابری (هر GB / هر 24 ساعت)",
    "description": "تعرفهٔ خرید/گسترش فضای ابری توسط کاربر؛ مبلغ = این تعرفه × حجم (GB) × تعداد روزها.",
    "coins": "50",
}


def seed(apps, schema_editor):
    FeatureCost = apps.get_model("wallet", "FeatureCost")
    FeatureCost.objects.update_or_create(
        code=CLOUD_STORAGE_COST["code"],
        defaults={
            "title": CLOUD_STORAGE_COST["title"],
            "description": CLOUD_STORAGE_COST["description"],
            "coins": CLOUD_STORAGE_COST["coins"],
            "is_active": True,
        },
    )


def unseed(apps, schema_editor):
    FeatureCost = apps.get_model("wallet", "FeatureCost")
    FeatureCost.objects.filter(code=CLOUD_STORAGE_COST["code"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("wallet", "0014_convert_existing_points_to_coins"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
