from django.db import migrations


EDUCATION_COMPLETION_RULE = {
    "code": "education_completion",
    "title": "تکمیل اطلاعات تحصیلی",
    "unit_label": "یک‌بار برای هر کاربر پس از ذخیرهٔ اطلاعات تحصیلی",
    "description": (
        "پس از نخستین ذخیرهٔ موفق فرم اطلاعات تحصیلی، سکه و امتیاز به کاربر "
        "اختصاص می‌یابد؛ میزان سکه از همین قانون در پنل مدیریت قابل تغییر است."
    ),
    "coins": 1,
}


def seed_education_completion(apps, schema_editor):
    RewardRule = apps.get_model("wallet", "RewardRule")
    RewardRule.objects.update_or_create(
        code=EDUCATION_COMPLETION_RULE["code"],
        defaults={
            "title": EDUCATION_COMPLETION_RULE["title"],
            "unit_label": EDUCATION_COMPLETION_RULE["unit_label"],
            "description": EDUCATION_COMPLETION_RULE["description"],
            "coins": EDUCATION_COMPLETION_RULE["coins"],
            "is_active": True,
        },
    )


def unseed_education_completion(apps, schema_editor):
    RewardRule = apps.get_model("wallet", "RewardRule")
    RewardRule.objects.filter(code=EDUCATION_COMPLETION_RULE["code"]).delete()


class Migration(migrations.Migration):
    dependencies = [("wallet", "0007_seed_profile_completion_rule")]
    operations = [migrations.RunPython(seed_education_completion, unseed_education_completion)]
