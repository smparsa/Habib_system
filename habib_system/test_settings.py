"""تنظیمات مخصوص اجرای تست‌ها روی محیطی که کاربر MySQL اجازهٔ ساخت
دیتابیس تست (test_*) را ندارد — دیتاستس SQLite در حافظه.

اجرا:
    python manage.py test --settings=habib_system.test_settings
"""
from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "OPTIONS": {
            "init_command": "PRAGMA foreign_keys=ON;",
        },
    }
}
