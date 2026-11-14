"""Seed ۴ محل نوار تبلیغات (dashboard/wallet/accounting/tickets) — یک‌بار.

ادمین بعداً در پنل می‌تواند «پذیرش تبلیغ» هر محل را فعال/غیرفعال کند.
"""

from django.db import migrations

SEED = [
    ("dashboard", "نوار پایین داشبورد", "پخش تبلیغ در نوار متحرک پایین داشبورد اصلی همهٔ کاربران.", 0),
    ("wallet", "نوار هدر کیف پول و سکه", "پخش تبلیغ در نوار متحرک هدر ماژول «کیف پول و سکه».", 1),
    ("accounting", "نوار هدر حسابداری", "پخش تبلیغ در نوار متحرک هدر ماژول «حسابداری».", 2),
    ("tickets", "نوار هدر مرکز تیکت", "پخش تبلیغ در نوار متحرک هدر ماژول «مرکز تیکت».", 3),
]


def seed_placements(apps, schema_editor):
    placement = apps.get_model("adminpanel", "AdHeaderPlacement")
    for code, title, desc, order in SEED:
        placement.objects.get_or_create(
            code=code,
            defaults={"title": title, "description": desc, "sort_order": order},
        )


def unseed(apps, schema_editor):
    placement = apps.get_model("adminpanel", "AdHeaderPlacement")
    placement.objects.filter(code__in=[s[0] for s in SEED]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0006_adheaderplacement_advertisement_expiry_notified_at_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_placements, unseed),
    ]
