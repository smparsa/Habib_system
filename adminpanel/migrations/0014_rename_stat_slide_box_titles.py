"""تغییر نام عنوان باکس‌های اسلایدشوی آمار داشبورد به «اسلایدشو A/B/C/D».

به درخواست مالک: عنوان چهار باکس آمار داشبورد در هر جای برنامه (فرم ثبت اسلاید،
پنل مدیریت، صفحهٔ اسلایدشو و داشبورد) با نام‌های جدید نمایش داده شود.
"""

from django.db import migrations


OLD_TO_NEW = {
    "stat_tasks": ("اسلایدشو A", "اسلایدشوی بالای داشبورد — محل باکس «اسلایدشو A»."),
    "stat_revenue": ("اسلایدشو B", "اسلایدشوی بالای داشبورد — محل باکس «اسلایدشو B»."),
    "stat_projects": ("اسلایدشو C", "اسلایدشوی بالای داشبورد — محل باکس «اسلایدشو C»."),
    "stat_users": ("اسلایدشو D", "اسلایدشوی بالای داشبورد — محل باکس «اسلایدشو D»."),
}

NEW_TO_OLD = {code: info for code, info in {
    "stat_users": ("باکس کل کاربران", "اسلایدشوی بالای داشبورد — محل باکس «کل کاربران»."),
    "stat_projects": ("باکس پروژه‌های فعال", "اسلایدشوی بالای داشبورد — محل باکس «پروژه‌های فعال»."),
    "stat_revenue": ("باکس درآمد ماهانه", "اسلایدشوی بالای داشبورد — محل باکس «درآمد ماهانه»."),
    "stat_tasks": ("باکس وظایف در انتظار", "اسلایدشوی بالای داشبورد — محل باکس «وظایف در انتظار»."),
}.items()}


def rename_boxes(apps, schema_editor):
    StatSlideBox = apps.get_model("adminpanel", "StatSlideBox")
    for code, (title, description) in OLD_TO_NEW.items():
        StatSlideBox.objects.filter(code=code).update(title=title, description=description)


def restore_old_titles(apps, schema_editor):
    StatSlideBox = apps.get_model("adminpanel", "StatSlideBox")
    for code, (title, description) in NEW_TO_OLD.items():
        StatSlideBox.objects.filter(code=code).update(title=title, description=description)


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0013_advertisement_expiry_warning_notified_at_and_more"),
    ]

    operations = [
        migrations.RunPython(rename_boxes, restore_old_titles),
    ]
