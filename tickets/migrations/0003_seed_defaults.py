from django.db import migrations

CATS = [
    ("support", "پشتیبانی", "Support", "支持", "bi-life-preserver"),
    ("question", "سؤال", "Question", "问题", "bi-question-circle"),
    ("complaint", "اعتراض", "Complaint", "投诉", "bi-flag"),
    ("suggestion", "پیشنهاد", "Suggestion", "建议", "bi-lightbulb"),
    ("bug", "گزارش باگ", "Bug Report", "错误报告", "bi-bug"),
    ("feature", "درخواست قابلیت", "Feature Request", "功能请求", "bi-stars"),
    ("financial", "مالی", "Financial", "财务", "bi-cash-coin"),
    ("account", "حساب کاربری", "Account", "账户", "bi-person-gear"),
    ("general", "عمومی", "General", "通用", "bi-chat-dots"),
    ("other", "سایر", "Other", "其他", "bi-three-dots"),
]

DEPTS = [
    ("tech", "پشتیبانی فنی", "Technical Support", "技术支持"),
    ("accounting", "حسابداری", "Accounting", "会计"),
    ("sales", "فروش", "Sales", "销售"),
    ("management", "مدیریت", "Management", "管理"),
    ("hr", "منابع انسانی", "HR", "人力资源"),
    ("it", "فناوری اطلاعات", "IT", "信息技术"),
    ("support", "خدمات مشتریان", "Customer Support", "客户服务"),
]


def seed(apps, schema_editor):
    Cat = apps.get_model("tickets", "TicketCategory")
    Dept = apps.get_model("tickets", "TicketDepartment")
    for code, fa, en, zh, icon in CATS:
        Cat.objects.get_or_create(code=code, defaults={
            "name_fa": fa, "name_en": en, "name_zh": zh, "icon": icon})
    for code, fa, en, zh in DEPTS:
        Dept.objects.get_or_create(code=code, defaults={
            "name_fa": fa, "name_en": en, "name_zh": zh})


def unseed(apps, schema_editor):
    apps.get_model("tickets", "TicketCategory").objects.all().delete()
    apps.get_model("tickets", "TicketDepartment").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("tickets", "0002_ticketyearcounter")]

    operations = [migrations.RunPython(seed, unseed)]
