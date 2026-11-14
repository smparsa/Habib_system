from django.db import migrations, models


def _fields(model_name):
    return [
        migrations.AddField(
            model_name=model_name, name="approval_ticket_id",
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name="شناسهٔ تیکت درخواست تأیید",
                help_text="تیکتی که پس از ثبت و کسر هزینه برای تأیید مدیر ساخته شد."),
        ),
        migrations.AddField(
            model_name=model_name, name="refunded_coins",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=14, verbose_name="سکهٔ بازگشتی به کاربر",
                help_text="در صورت رد توسط مدیر: مبلغ بازگردانده‌شده به کیف پول (پس از کسر کارمزد)."),
        ),
        migrations.AddField(
            model_name=model_name, name="refund_fee_coins",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=14, verbose_name="کارمزد کسرشده هنگام رد (سکه)",
                help_text="سهم کسرشده (پیش‌فرض ۱۰٪) از هزینهٔ پرداختی هنگام رد."),
        ),
        migrations.AddField(
            model_name=model_name, name="refunded_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="زمان بازگشت وجه",
                help_text="خالی = وجهی بازگردانده نشده؛ برای جلوگیری از بازگشت مضاعف استفاده می‌شود."),
        ),
    ]


class Migration(migrations.Migration):
    dependencies = [
        ("adminpanel", "0015_alter_statslidebox_title"),
    ]

    operations = _fields("advertisement") + _fields("statslide")
