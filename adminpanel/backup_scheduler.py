"""رشتهٔ پس‌زمینهٔ «پشتیبان خودکار» — هر چند ثانیه وضعیت را می‌سنجد و در صورت
رسیدن زمان (با توجه به BackupSetting)، یک نسخهٔ خودکار می‌گیرد.

تا وقتی سرور برنامه روشن است (runserver یا WSGI) این رشته کار می‌کند؛ برای
سرورهایی که خاموش‌اند، می‌توان پشتیبان را با دستور مدیریت نیز زمان‌بندی کرد:
    python manage.py db_backup
"""

import threading
import time

_POLL_SECONDS = 60


def _loop():
    while True:
        time.sleep(_POLL_SECONDS)
        try:
            from django.db import close_old_connections

            from .backup_service import auto_backup_if_due

            auto_backup_if_due()
        except Exception:  # noqa: BLE001 - خودکار نباید برنامه را از کار بیندازد
            pass
        finally:
            try:
                close_old_connections()
            except Exception:  # noqa: BLE001
                pass


_started = False
_start_lock = threading.Lock()


def start():
    """رشته را فقط یک‌بار در هر فرایند آغاز می‌کند."""
    global _started
    with _start_lock:
        if _started:
            return
        thread = threading.Thread(target=_loop, daemon=True, name="habib-db-auto-backup")
        thread.start()
        _started = True
