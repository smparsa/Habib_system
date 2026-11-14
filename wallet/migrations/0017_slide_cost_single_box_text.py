"""متن تعرفهٔ اسلایدشو پس از تک‌باکس شدن: «(هر 24 ساعت)» بدون ضرب در باکس.

فقط ردیفی که هنوز عنوان/توضیح اولیهٔ seed را دارد به‌روز می‌شود؛ ویرایش‌های ادمین دست‌نخورده می‌ماند.
"""

from django.db import migrations

CODE = "stat_slide_submission"
OLD_TITLE = "هزینهٔ ثبت اسلایدشوی آمار (هر باکس / هر 24 ساعت)"
NEW_TITLE = "هزینهٔ ثبت اسلایدشوی آمار (هر 24 ساعت)"
NEW_DESC = "مبلغ = این تعرفه × تعداد روز. غیرفعال = طبق تعرفهٔ تبلیغات."


def update(apps, schema_editor):
    FeatureCost = apps.get_model("wallet", "FeatureCost")
    FeatureCost.objects.filter(code=CODE, title=OLD_TITLE).update(title=NEW_TITLE, description=NEW_DESC)


class Migration(migrations.Migration):
    dependencies = [
        ("wallet", "0016_seed_stat_slide_cost"),
    ]

    operations = [
        migrations.RunPython(update, migrations.RunPython.noop),
    ]
