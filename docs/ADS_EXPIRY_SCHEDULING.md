# اجرای دوره‌ای تیکت پایان دورهٔ تبلیغ — celery beat / کرون

## خلاصه

`ads_expiry_sweep_task` (تعریف در `ads/tasks.py`) تبلیغ‌های منقضی‌شده را پیدا می‌کند و به تبلیغ‌کننده تیکتِ «مالی» (financial) با اولویت عادی می‌فرستد. تسک **idempotent** است — به ازای هر تبلیغ فقط یک‌بار تیکت می‌دهد (فلگ `expiry_notified_at`)؛ پس اجرای مکرر بی‌ضرر است.

## ۱) Celery Beat (پیشنهادی)

در `habib_system/settings.py` تنظیم شد:

```python
CELERY_BEAT_SCHEDULE = {
    'ads-expiry-sweep': {
        'task': 'ads.tasks.ads_expiry_sweep_task',
        'schedule': crontab(minute='0', hour='*/1'),  # هر ساعت، دقیقهٔ ۰
    },
    'tickets-sla-sweep': {
        'task': 'tickets.tasks.sla_sweep_task',
        'schedule': crontab(minute='*/15'),  # هر ۱۵ دقیقه
    },
}
CELERY_TIMEZONE = 'Asia/Tehran'
```

### اجرا

از ریشهٔ پروژه (`/c/Habib_system`):

```bash
# زمان‌بند:
./venv/Scripts/python.exe -m celery -A habib_system beat --loglevel=INFO

# ورکر (در ترمینال deuxième):
./venv/Scripts/python.exe -m celery -A habib_system worker --pool=solo --loglevel=INFO
```

یا هر دو در یک فرآیند (مناسب دمو/توسعه):

```bash
./venv/Scripts/python.exe -m celery -A habib_system worker --pool=solo -B --loglevel=INFO
```

- پیش‌فرض تنظیمات: `CELERY_EAGER=1` — تسک‌ها هم‌زمان اجرا می‌شوند (تست/توسعه). بدون broker واقعی، `beat` هم هنوز سالم است (chip زمان‌بندی async نیست، اما تنظیمات تا زمان‌بندی load می‌شود).
- برای ثبت در فایل که زمان‌بندیها load می‌شوند:
  ```bash
  PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe -m celery -A habib_system inspect schedule
  # یا celery -A habib_system shell برای چک schedule:
  # from habib_system.celery import app; print(app.conf.beat_schedule)
  ```

## ۲) کرون (بدون celery beat)

اگر سرور کرون دارد (و بدون رصد Redis برای beat):

```cron
# هر ساعت — تیکت پایان دورهٔ تبلیغ
0 * * * * cd /c/Habib_system && PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe manage.py ads_expiry_sweep >> /var/log/ads_sweep.log 2>&1

# هر ۱۵ دقیقه — برسی SLA تیکت‌ها
*/15 * * * * cd /c/Habib_system && PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe manage.py tickets_sla_sweep >> /var/log/sla_sweep.log 2>&1
```

## ۳) بررسی صحت اجرا

```bash
cd /c/Habib_system
PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe manage.py ads_expiry_sweep
# خروجی: اطلاع‌رسانی: N | ناموفق: M
```

اگر `N > 0` باشد، تیکت‌های پایان دوره ارسال شده‌اند. کومند فقط تبلیغ‌هایی را «ネスنت شده» نکنه می‌کند که `expiry_notified_at` ندارند؛ پس اجرا مجدد امن است.
