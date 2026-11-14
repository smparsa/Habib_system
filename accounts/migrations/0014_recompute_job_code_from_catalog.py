"""
اصلاح «کد اختصاصی شغل» برای ردیف‌های موجود: کدهایی که پیش از این به‌صورت شمارهٔ
ترتیبیِ شغل (مثل JOB-001) یا به هر شکلِ دیگری ذخیره شده‌اند، حالا از روی شناسهٔ
رکوردهای دیتابیسِ پنج لایهٔ کاتالوگ (حوزه→صنعت→دسته→عنوان→تخصص) بازسازی می‌شوند؛
مثل ۳|۷|۱۱|۲۰|۲۶ = «37112026». شغل‌های «ورود دستی» (بدون زنجیره) بدون کد می‌مانند.
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


def recompute_job_codes(apps, schema_editor):
    Job = apps.get_model("accounts", "Job")
    chain_q = Q()
    for field in _LEVELS:
        chain_q |= Q(**{f"{field}__isnull": False})
    chain_pks = list(Job.objects.filter(chain_q).values_list("pk", flat=True))
    for job in Job.objects.filter(pk__in=chain_pks):
        code = _code_for(job)
        if not code:
            continue
        job.job_code = code
        try:
            job.save(update_fields=["job_code"])
        except IntegrityError:
            # ردیف‌های تکراریِ قدیمی (که پیش از constraint ثبت شده‌اند) بدون کد می‌مانند
            job.job_code = None
    # شغل‌های بدون زنجیرهٔ کاتالوگ هیچ کد اختصاصی ندارند
    Job.objects.exclude(pk__in=chain_pks).update(job_code=None)


def noop_reverse(apps, schema_editor):
    """برگرداندن این اصلاح معنا ندارد؛ مهاجرت برگشتی هیچ کاری نمی‌کند."""


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_backfill_job_codes"),
    ]

    operations = [
        migrations.RunPython(recompute_job_codes, noop_reverse),
    ]
