"""
Add StudyGroup model and convert StudyField.education_group text → study_group FK.

Steps inside this migration file:
1. Create tables for StudyGroup (new model).
2. Add nullable study_group FK to StudyField.
3. Populate 4 exam groups + map old text groups → group FK via RunPython.
4. Set FK NOT NULL (since all existing fields are now mapped).
5. Remove old education_group text column.
"""

from django.db import migrations, models


def _normalize(text):
    return (text or "").strip().replace("\u200c", "").replace("\u200e", "").replace("\u200f", "").strip()


GROUP_DEFS = [
    ("EG-TM", "فنی و مهندسی", "Technical & Engineering",
     "رشته‌های فنی و مهندسی: مهندسی، فناوری، معماری، صنایع و ..."),
    ("EG-SC", "علوم پایه", "Basic Sciences",
     "رشته‌های علوم پایه: ریاضی، فیزیک، شیمی، زیست‌شناسی، آمار و ..."),
    ("EG-HU", "علوم انسانی و هنر", "Human Sciences & Arts",
     "رشته‌های علوم انسانی، هنر، علوم اجتماعی و ..."),
    ("EG-FL", "زبان‌های خارجی", "Foreign Languages",
     "زبان‌های خارجی و ادبیاتشان: انگلیسی، فرانسوی، آلمانی، اسپانیایی و ..."),
]

# متن‌های ممکن در education_group قدیمی → کد_group جدید
GROUP_TEXT_ALIASES = {
    "فنی و مهندسی": "EG-TM",
    "علوم پایه": "EG-SC",
    "علوم انسانی": "EG-HU",
    "علوم انسانی و هنر": "EG-HU",
    "هنر": "EG-HU",
    "زبان‌های خارجی": "EG-FL",
}


def create_groups_and_migrate(apps, schema_editor):
    StudyGroup = apps.get_model("accounts", "StudyGroup")
    StudyField = apps.get_model("accounts", "StudyField")

    # ۱. ایجاد ۴ گروه امتحانی
    groups_by_code = {}
    for code, name, name_en, description in GROUP_DEFS:
        obj, _ = StudyGroup.objects.update_or_create(
            code=code,
            defaults={"name": name, "name_en": name_en, "description": description, "is_active": True},
        )
        groups_by_code[code] = obj

    default_group = groups_by_code.get("EG-TM")

    # ۲. انتقال رشته‌های دارای گروه → گروه جدید
    mapped = 0
    for field in StudyField.objects.exclude(education_group=""):
        group_code = GROUP_TEXT_ALIASES.get(_normalize(field.education_group))
        group = groups_by_code.get(group_code) if group_code else None
        if group:
            field.study_group = group
            field.save(update_fields=["study_group_id"])
            mapped += 1

    # ۳. رشته‌های بدون گروه ← پیش‌فرض فنی و مهندسی
    if default_group:
        updated = StudyField.objects.filter(education_group="", study_group__isnull=True).update(
            study_group=default_group
        )
        mapped += updated

    # 이미 سابقه 전이된 رکوردها را هم مطمئن می‌کنیم (مثلاً اگر Group.objects.create قبل از این اجرا شده باشد)
    if default_group:
        StudyField.objects.filter(study_group__isnull=True).update(study_group=default_group)



def reverse_migrate(apps, schema_editor):
    StudyField = apps.get_model("accounts", "StudyField")
    # FK را NULL می‌کنیم؛ دادهٔ متنِ قدیمی از migration 0032 موجود است
    StudyField.objects.update(study_group=None)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0032_seed_education_catalog"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudyGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, verbose_name="نام گروه")),
                ("name_en", models.CharField(blank=True, max_length=150, verbose_name="نام گروه (انگلیسی)")),
                ("code", models.CharField(max_length=20, unique=True, verbose_name="کد")),
                ("description", models.TextField(blank=True, verbose_name="توضیحات")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "گروه امتحانی",
                "verbose_name_plural": "گروه‌های امتحانی",
                "ordering": ["code"],
            },
        ),
        migrations.AddField(
            model_name="studyfield",
            name="study_group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.PROTECT,
                related_name="fields",
                to="accounts.studygroup",
                verbose_name="گروه امتحانی",
            ),
        ),
        migrations.RunPython(create_groups_and_migrate, reverse_migrate),
        migrations.RemoveField(
            model_name="studyfield",
            name="education_group",
        ),
        migrations.AlterField(
            model_name="studyfield",
            name="study_group",
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name="fields",
                to="accounts.studygroup",
                verbose_name="گروه امتحانی",
            ),
        ),
    ]
