"""بازپرّی تبلیغ‌های قدیمی بدون هدر — همهٔ محل‌های موجود به آن‌ها داده می‌شود.

سازگاری با عقب: تبلیغ‌های قبلیِ پیش از مدل AdHeaderPlacement (فقط نوار داشبورد)
که هدر انتخاب‌نشده دارند، به‌طور خودکار به همهٔ محل‌های فعلی (dashboard و ...)
متصل می‌شوند تا از نوارها حذف نشوند. تبلیغ‌های جدید همیشه صریح انتخاب می‌کنند.
"""

from django.db import migrations


def backfill(apps, schema_editor):
    Advertisement = apps.get_model("adminpanel", "Advertisement")
    Placement = apps.get_model("adminpanel", "AdHeaderPlacement")
    placements = list(Placement.objects.order_by("sort_order", "id"))
    if not placements:
        return
    for ad in Advertisement.objects.all():
        if not ad.header_modules.exists():
            ad.header_modules.set(placements)


def unbackfill(apps, schema_editor):
    # بازگشت پذیر نیست (پیوند‌های ناشناخته حذف می‌شوند)؛ بدون کاری می‌مانیم.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0007_seed_ad_header_placements"),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
