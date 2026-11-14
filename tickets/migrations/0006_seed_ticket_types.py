"""داده‌های اولیهٔ «نوع تیکت» قابل تعریف توسط ادمین (پنل مدیریت).

این دسته‌ها از این پس در پنل مدیریت قابل افزودن/ویرایش/غیرفعال‌سازی هستند؛
در اینجا فقط نمونه‌های اولیهٔ پرکاربردِ درخواستی seed می‌شوند.
"""

from django.db import migrations

TYPES = [
    ("product", "درخواست کالا/خدمات", "Product/Service Request", "商品/服务请求",
     "bi-box-seam", 1),
    ("advertising", "ارسال متن تبلیغاتی", "Advertising", "广告", "bi-megaphone", 2),
    ("admin", "ارتباط با ادمین", "Contact Admin", "联系管理员", "bi-person-gear", 3),
]


def seed(apps, schema_editor):
    Cat = apps.get_model("tickets", "TicketCategory")
    for code, fa, en, zh, icon, order in TYPES:
        Cat.objects.get_or_create(code=code, defaults={
            "name_fa": fa, "name_en": en, "name_zh": zh, "icon": icon, "order": order,
        })


def unseed(apps, schema_editor):
    Cat = apps.get_model("tickets", "TicketCategory")
    Cat.objects.filter(code__in=[t[0] for t in TYPES]).delete()


class Migration(migrations.Migration):
    dependencies = [("tickets", "0005_alter_tickettargetrule_audience_ticketaudience")]

    operations = [migrations.RunPython(seed, unseed)]