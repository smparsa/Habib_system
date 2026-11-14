"""seed: هزینه‌های پیش‌فرض سکه برای ماژول‌های متصل‌شده به charge_module.

ادمین می‌تواند این رکوردها را در «پنل مدیریت ← هزینهٔ سکهٔ ماژول‌ها» ویرایش،
غیرفعال یا حذف کند (در صورت جایگزینی، با کد جدید بخش مربوطه هم‌اهنگ می‌شود).
"""

from django.db import migrations

DEFAULT_COSTS = [
    {
        "code": "bulk_ticket",
        "title": "ارسال تیکت به مخاطبین هدف (انبوه)",
        "description": "هنگام ارسال تیکت به یک جامعهٔ هدف، سکه کسر می‌شود.",
        "coins": "5",
    },
    {
        "code": "job_request",
        "title": "ثبت درخواست افزودن شغل به فهرست",
        "description": "هنگام ارسال تیکت «شغل مورد نظرم در فهرست نیست».",
        "coins": "2",
    },
    {
        "code": "magazine_forward",
        "title": "فوروارد مطلب مجله برای عضو دیگر",
        "description": "هر بار فوروارد یک مطلب به عضو دیگر.",
        "coins": "1",
    },
    {
        "code": "magazine_publish",
        "title": "انتشار مطلب در مجله",
        "description": "هزینهٔ انتشار مطلب (در صورت انتشار توسط کاربران غیرکارکن).",
        "coins": "10",
    },
]


def seed(apps, schema_editor):
    FeatureCost = apps.get_model("wallet", "FeatureCost")
    for item in DEFAULT_COSTS:
        FeatureCost.objects.update_or_create(
            code=item["code"],
            defaults={
                "title": item["title"],
                "description": item["description"],
                "coins": item["coins"],
                "is_active": True,
            },
        )


def unseed(apps, schema_editor):
    FeatureCost = apps.get_model("wallet", "FeatureCost")
    FeatureCost.objects.filter(
        code__in=[item["code"] for item in DEFAULT_COSTS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("wallet", "0002_walletsetting_max_transfer_coins_per_day_and_more"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]