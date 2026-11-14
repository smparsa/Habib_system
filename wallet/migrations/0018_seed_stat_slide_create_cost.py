"""seed: تعرفهٔ «ساخت اسلایدشو (Create Slideshow)» — کد stat_slide_create.

هزینهٔ دوم ماژول اسلایدشو (غیر از هزینهٔ آپلود/نمایش با کد stat_slide_submission): وقتی تصویر
کاربر با مشخصات بنر سازگار نباشد، می‌تواند با پرداخت این مبلغ بنرِ مناسب بسازد. ردیف
«غیرفعال» و با مبلغ ۰ ساخته می‌شود؛ ادمین در «پنل مدیریت ← هزینه‌های سکهٔ ماژول‌ها» مبلغ را
تعیین و فعال می‌کند (تا آن موقع دکمهٔ «ساخت اسلایدشو» برای کاربر نمایش داده نمی‌شود).
ردیف موجود با همین کد دست‌نخورده می‌ماند.
"""

from django.db import migrations

CODE = "stat_slide_create"


def seed(apps, schema_editor):
    FeatureCost = apps.get_model("wallet", "FeatureCost")
    if FeatureCost.objects.filter(code=CODE).exists():
        return
    FeatureCost.objects.create(
        code=CODE,
        title="هزینهٔ ساخت اسلایدشو (Create Slideshow)",
        description=("یک‌بار به‌ازای هر ساخت: تبدیل تصویر ناسازگار به بنر ۲۴۰۰×۶۰۰ مناسب. "
                     "غیرفعال یا صفر = دکمهٔ ساخت برای کاربر نمایش داده نمی‌شود."),
        coins=0,
        is_active=False,
    )


def unseed(apps, schema_editor):
    FeatureCost = apps.get_model("wallet", "FeatureCost")
    FeatureCost.objects.filter(code=CODE, is_active=False, coins=0).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("wallet", "0017_slide_cost_single_box_text"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
