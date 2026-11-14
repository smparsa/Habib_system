# حذف ستونِ بی‌استفادهٔ «description» از جدول accounts_job.
#
# این ستون در مدل Job وجود ندارد و در برخی دیتابیس‌ها (مثل MySQL این محیط)
# به‌صورت بازماندهٔ قدیمی جدول/بکاپ باقی مانده است. چون Django هنگام INSERT
# آن را نمی‌فرستد و ستون NOT NULL بدون مقدار پیش‌فرض است، MySQL در حالت strict
# خطای «1364: Field 'description' doesn't have a default value» می‌داد و ثبت
# شغل ممکن نمی‌شد.
#
# نکته: ستون در همهٔ دیتابیس‌ها وجود ندارد (دیتابیس‌های تازه فقط از روی
# migrationها ساخته می‌شوند)؛ بنابراین حذف/افزودن به‌صورت شرطی انجام می‌شود تا
# این migration هم روی MySQL دارای ستون، هم روی دیتابیس‌های تازه کار کند
# (idempotent). ستون در دیتابیس دارایِ آن کاملاً خالی است؛ حذفش هیچ داده‌ای
# از دست نمی‌دهد. عملیات معکوس، ستون را فقط اگر نبود با شکل قبلی (LONGTEXT
# NOT NULL) بازمی‌گرداند.
from django.db import migrations

TABLE = "accounts_job"
COLUMN = "description"


def _columns(schema_editor, table):
    with schema_editor.connection.cursor() as cursor:
        return {
            d.name
            for d in schema_editor.connection.introspection.get_table_description(
                cursor, table
            )
        }


def drop_column_if_exists(apps, schema_editor):
    if COLUMN in _columns(schema_editor, TABLE):
        schema_editor.execute(
            "ALTER TABLE `%s` DROP COLUMN `%s`;" % (TABLE, COLUMN)
        )


def add_column_if_missing(apps, schema_editor):
    if COLUMN not in _columns(schema_editor, TABLE):
        schema_editor.execute(
            "ALTER TABLE `%s` ADD COLUMN `%s` LONGTEXT NOT NULL;"
            % (TABLE, COLUMN)
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0052_alter_user_managers_alter_job_job_code_and_more"),
    ]

    # DDL در MySQL خودش COMMIT می‌کند؛ بنابراین atomic=False
    atomic = False

    operations = [
        migrations.RunPython(drop_column_if_exists, add_column_if_missing),
    ]
