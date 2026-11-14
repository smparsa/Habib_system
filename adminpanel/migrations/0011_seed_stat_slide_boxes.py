"""Seed ماژول «اسلایدشوی آمار داشبورد»: ۴ باکس آمار بالای «ماژول‌های کسب‌وکار»."""

from django.db import migrations

BOXES = [
    ("stat_users", "باکس کل کاربران", "اسلایدشوی بالای داشبورد — محل باکس «کل کاربران».", 0),
    ("stat_projects", "باکس پروژه‌های فعال", "اسلایدشوی بالای داشبورد — محل باکس «پروژه‌های فعال».", 1),
    ("stat_revenue", "باکس درآمد ماهانه", "اسلایدشوی بالای داشبورد — محل باکس «درآمد ماهانه».", 2),
    ("stat_tasks", "باکس وظایف در انتظار", "اسلایدشوی بالای داشبورد — محل باکس «وظایف در انتظار».", 3),
]


def seed(apps, schema_editor):
    Box = apps.get_model("adminpanel", "StatSlideBox")
    Setting = apps.get_model("adminpanel", "StatSlideSetting")
    for code, title, description, sort_order in BOXES:
        Box.objects.get_or_create(
            code=code,
            defaults={
                "title": title,
                "description": description,
                "is_active": True,
                "switch_seconds": 0,
                "sort_order": sort_order,
            },
        )
    Setting.objects.get_or_create(pk=1, defaults={"switch_seconds": 6})


def unseed(apps, schema_editor):
    Box = apps.get_model("adminpanel", "StatSlideBox")
    Box.objects.filter(code__in=[b[0] for b in BOXES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("adminpanel", "0010_statslidebox_statslidesetting_statslide"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
