import os
import sys

from django.apps import AppConfig


class AdminpanelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "adminpanel"
    verbose_name = "پنل مدیریت"

    def ready(self):
        """شروع رشتهٔ پشتیبان‌گیری خودکار (یک‌بار در فرایندِ اصلی سرویس‌دهنده)."""
        # فقط در فرایندِ واقعیِ سرویس‌دهنده، نه در ابزارهای مدیریتی
        argv = [a.lower() for a in (sys.argv or [])]
        if any(a in argv for a in (
            "migrate", "makemigrations", "check", "test", "shell",
            "createsuperuser", "flush", "loaddata", "dumpdata",
            "db_backup", "collectstatic",
        )):
            return
        # runserver با autoreload: فرایندِ والد (ناظر) رشته را اجرا نکند؛ فقط فرزند
        is_runserver = any("runserver" in a for a in argv)
        if is_runserver:
            no_reload = any(a in ("--noreload", "-noreload") for a in argv)
            if os.environ.get("RUN_MAIN") != "true" and not no_reload:
                return
        try:
            from .backup_scheduler import start as _start_backup_scheduler

            _start_backup_scheduler()
        except Exception:  # noqa: BLE001 - آغاز ناقص نباید اجرای برنامه را متوقف کند
            pass
