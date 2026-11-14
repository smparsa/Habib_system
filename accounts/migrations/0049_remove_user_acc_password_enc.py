# حذف فیلد کمکیِ نسخهٔ رمزنگاری‌شدهٔ کلمهٔ عبور حسابداری (0048 آن را اضافه کرده بود).
# دلیل: ویژگی «ارسال کلمهٔ عبور به خودِ کاربر» حذف و با «ریست کلمهٔ عبور»
# جایگزین شد؛ کلمهٔ عبور دوباره فقط به‌صورت هش (بازیابی‌ناپذیر) ذخیره می‌شود.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0048_user_acc_password_enc'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='acc_password_enc',
        ),
    ]
