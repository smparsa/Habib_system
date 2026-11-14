"""seed: تعرفهٔ «هزینهٔ ثبت اسلایدشوی آمار (هر باکس / هر 24 ساعت)» — کد stat_slide_submission.

ردیف به‌صورت «غیرفعال» ساخته می‌شود تا رفتار فعلی (پیروی از تعرفهٔ تبلیغات) تغییر نکند؛
ادمین در «پنل مدیریت ← هزینه‌های سکهٔ ماژول‌ها» مقدار را تنظیم و فعال می‌کند.
اگر ردیفی با این کد از قبل وجود داشته باشد، دست‌نخورده می‌ماند.
"""

from django.db import migrations

CODE = "stat_slide_submission"


def seed(apps, schema_editor):
    FeatureCost = apps.get_model("wallet", "FeatureCost")
    if FeatureCost.objects.filter(code=CODE).exists():
        return
    ad = FeatureCost.objects.filter(code="ad_submission").first()
    FeatureCost.objects.create(
        code=CODE,
        title="هزینهٔ ثبت اسلایدشوی آمار (هر باکس / هر 24 ساعت)",
        description="مبلغ = این تعرفه × تعداد روز × تعداد باکس‌های انتخابی (A تا D). غیرفعال = طبق تعرفهٔ تبلیغات.",
        coins=ad.coins if ad else 0,
        is_active=False,
    )


def unseed(apps, schema_editor):
    FeatureCost = apps.get_model("wallet", "FeatureCost")
    FeatureCost.objects.filter(code=CODE, is_active=False).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("wallet", "0015_seed_cloud_storage_cost"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
