"""
بازپردازی «کد اختصاصی شغل» برای مشاغلِ ثبت‌شدهٔ پیشین که پیش از افزودنِ فیلد
job_code ذخیره شده‌اند؛ کد از شناسهٔ رکوردهای دیتابیسِ پنج لایهٔ کاتالوگ
(حوزه→صنعت→دسته→عنوان→تخصص) ساخته و روی همان ردیف نوشته می‌شود.
"""

from django.db import migrations
from django.db.models import Q
from django.db.utils import IntegrityError

_LEVELS = ("sector", "industry", "category", "occupation_title", "specialization")


def _code_for(job):
    parts = []
    for field in _LEVELS:
        pk = getattr(job, f"{field}_id")
        if pk is not None:
            parts.append(str(pk))
    return "".join(parts)


def backfill_job_codes(apps, schema_editor):
    Job = apps.get_model("accounts", "Job")
    chain_q = Q()
    for field in _LEVELS:
        chain_q |= Q(**{f"{field}__isnull": False})
    jobs = list(
        Job.objects.filter(chain_q).filter(Q(job_code__isnull=True) | Q(job_code=""))
    )
    for job in jobs:
        code = _code_for(job)
        if not code:
            continue
        job.job_code = code
        try:
            job.save(update_fields=["job_code"])
        except IntegrityError:
            # ردیف‌های تکراریِ قدیمی (که پیش از constraint ثبت شده‌اند) بدون کد می‌مانند
            job.job_code = None


def unbackfill_job_codes(apps, schema_editor):
    Job = apps.get_model("accounts", "Job")
    Job.objects.exclude(job_code__isnull=True).update(job_code=None)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_job_job_code_job_uniq_profile_job_code"),
    ]

    operations = [
        migrations.RunPython(backfill_job_codes, unbackfill_job_codes),
    ]
