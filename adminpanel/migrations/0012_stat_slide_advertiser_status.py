"""افزودن گردش تأیید کاربر به «اسلاید اسلایدشوی آمار».

- `advertiser`: صاحب اسلاید (کاربر ثبت‌کننده از ماژول اسلایدشو؛ ادمین = خالی).
- `status`: pending / approved / rejected — فقط «approved» در باکس‌ها پخش شود.
- اسلایدهای قبلی (ثبت‌شده از پنل مدیریت) «تأییدشده» منظور می‌شوند.
- ظرفیت هر باکس = حداکثر ۱۰ اسلاید (اعتبارسنجی در فرم/نمای ثبت).
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def approve_existing(apps, schema_editor):
    Slide = apps.get_model("adminpanel", "StatSlide")
    Slide.objects.all().update(status="approved")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("adminpanel", "0011_seed_stat_slide_boxes"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="statslide",
            name="advertiser",
            field=models.ForeignKey(
                blank=True,
                help_text="ادمین = خالی؛ اسلایدِ ثبت‌شده توسط کاربر از ماژول اسلایدشو، صاحبش می‌گیرد.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="stat_slides",
                to=settings.AUTH_USER_MODEL,
                verbose_name="صاحب اسلاید (کاربر)",
            ),
        ),
        migrations.AddField(
            model_name="statslide",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "در انتظار تأیید (پرداخت نشده)"),
                    ("approved", "تأییدشده — در حال/آمادهٔ پخش"),
                    ("rejected", "ردشده"),
                ],
                default="pending",
                help_text="در انتظار تأیید / تأییدشده / ردشده — فقط اسلایدهای «تأییدشده» در باکس‌ها پخش می‌شوند.",
                max_length=20,
                verbose_name="وضعیت تأیید",
            ),
        ),
        migrations.RunPython(approve_existing, noop),
    ]
