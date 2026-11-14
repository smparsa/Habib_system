# حذف فیلد کمکیِ «تیکت خصوصی» (0008 آن را اضافه کرده بود).
# دلیل: ویژگی «ارسال کلمهٔ عبور به خودِ کاربر» حذف شد؛ پرچم is_private دیگر
# جایی استفاده نمی‌شود.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0008_ticket_is_private'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ticket',
            name='is_private',
        ),
    ]
