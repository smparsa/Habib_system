"""یک اسلایدشو برای همه‌جا: فقط «اسلایدشو A» می‌ماند؛ باکس‌های B/C/D حذف می‌شوند.

- باکس A همان کد ``stat_tasks`` است (در صورت نبودن ساخته می‌شود).
- هر اسلایدی که قبلاً فقط در B/C/D بود (یا هر اسلاید دیگر) به A متصل می‌شود تا
  اسلایدِ پرداخت‌شدهٔ کاربران تا پایان بازهٔ نمایش‌شان در همان یک اسلایدشو بماند.
- سپس باکس‌های ``stat_revenue`` / ``stat_projects`` / ``stat_users`` حذف می‌شوند.
- برگشت (reverse): باکس‌های B/C/D با همان عنوان‌ها دوباره ساخته می‌شوند (اتصال اسلایدها برنمی‌گردد).
"""

from django.db import migrations

BOX_A = "stat_tasks"
REMOVED = {
    "stat_revenue": ("اسلایدشو B", 1),
    "stat_projects": ("اسلایدشو C", 2),
    "stat_users": ("اسلایدشو D", 3),
}


def to_single(apps, schema_editor):
    Box = apps.get_model("adminpanel", "StatSlideBox")
    Slide = apps.get_model("adminpanel", "StatSlide")
    box_a, _ = Box.objects.get_or_create(
        code=BOX_A,
        defaults={"title": "اسلایدشو A", "is_active": True, "sort_order": 0},
    )
    box_a.title = "اسلایدشو A"
    box_a.description = "اسلایدشوی بالای داشبورد."
    box_a.save(update_fields=["title", "description"])
    for slide in Slide.objects.all():
        slide.boxes.add(box_a)
    Box.objects.filter(code__in=list(REMOVED)).delete()


def restore_boxes(apps, schema_editor):
    Box = apps.get_model("adminpanel", "StatSlideBox")
    for code, (title, order) in REMOVED.items():
        Box.objects.get_or_create(
            code=code,
            defaults={"title": title, "is_active": True, "sort_order": order,
                      "description": f"اسلایدشوی بالای داشبورد — محل باکس «{title}»."},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("adminpanel", "0016_approval_refund_fields"),
    ]

    operations = [
        migrations.RunPython(to_single, restore_boxes),
    ]
