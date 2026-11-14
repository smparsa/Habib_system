"""سرویس پشتیبان‌گیری و بازیابی دیتابیس MySQL (ماژول پنل مدیریت).

- پشتیبان: با ابزار mysqldump از همان دیتابیسِ تنظیمات جنگو یک فایل .sql می‌سازد.
- بازیابی: ابتدا همهٔ جدول‌های فعلی حذف و سپس فایل پشتیبان دوباره بارگذاری می‌شود
  (بازگردانی دقیق «همان لحظهٔ پشتیبان»).
- خودکار: تابع auto_backup_if_due توسط یک رشتهٔ پس‌زمینه (apps.py) و دستور
  مدیریت db_backup و نیز صفحهٔ پنل (فرصت‌طلبانه) صدا زده می‌شود.

امنیت: ابزارهای mysql از مسیرهایی که در PATH یا مسیرهای استاندارد ویندوز
پیدا می‌شوند استفاده می‌کنند؛ رمز عبور از طریق متغیر محیطی MYSQL_PWD منتقل
می‌شود (نه آرگومان خط فرمان).
"""

import glob
import os
import shutil
import subprocess
import tempfile
import threading
from datetime import datetime

from django.conf import settings
from django.db import connections
from django.utils import timezone

from .models import (
    BACKUP_KIND_AUTO,
    BACKUP_KIND_MANUAL,
    BACKUP_STATUS_FAILED,
    BACKUP_STATUS_OK,
    BackupFile,
    BackupSetting,
)

# یک نمونه برای کل فرایند: جلوی تداخل دو پشتیبان/بازیابی هم‌زمان را می‌گیرد
_busy_lock = threading.Lock()

_MYSQL_DIR_CANDIDATES = [
    r"C:\Program Files\MySQL\MySQL Server 8.0\bin",
    r"C:\Program Files\MySQL\MySQL Server 8.4\bin",
    r"C:\Program Files\MySQL\MySQL Server 5.7\bin",
    r"C:\xampp\mysql\bin",
    r"C:\laragon\bin\mysql",
    r"C:\wamp64\bin\mysql",
]


class BackupError(Exception):
    """خطای قابل‌نمایش به کاربر در ماژول پشتیبان‌گیری."""


# ---------------------------------------------------------------------------
# تنظیمات و ابزارهای پایه
# ---------------------------------------------------------------------------


def db_config():
    cfg = settings.DATABASES["default"]
    return {
        "name": cfg["NAME"],
        "user": cfg["USER"],
        "password": cfg["PASSWORD"],
        "host": cfg.get("HOST") or "127.0.0.1",
        "port": str(cfg.get("PORT") or "3306"),
    }


def default_backup_dir():
    return os.path.join(settings.BASE_DIR, "db_backups")


def backup_dir():
    """پوشهٔ پشتیبان (از تنظیمات یا پیش‌فرض) — ساخته می‌شود اگر نباشد."""
    setting = BackupSetting.get()
    path = (setting.folder or "").strip() or default_backup_dir()
    path = os.path.abspath(path)
    os.makedirs(path, exist_ok=True)
    return path


def _no_window():
    if os.name == "nt":
        return subprocess.CREATE_NO_WINDOW
    return 0


def _find_tool(name):
    found = shutil.which(name)
    if found:
        return found
    exe = name + (".exe" if os.name == "nt" else "")
    roots = [_MYSQL_DIR_CANDIDATES]
    for pattern in (
        r"C:\Program Files\MySQL\MySQL Server *\bin",
        r"C:\laragon\bin\mysql\*\bin",
        r"C:\wamp64\bin\mysql\*\bin",
    ):
        roots.append(glob.glob(pattern))
    for root_list in roots:
        for root in root_list:
            candidate = os.path.join(root, exe)
            if os.path.isfile(candidate):
                return candidate
    return None


def mysqldump_bin():
    path = _find_tool("mysqldump")
    if not path:
        raise BackupError(
            "ابزار mysqldump پیدا نشد. لطفاً MySQL Server را نصب کنید یا مسیر "
            "پوشهٔ bin آن را در PATH سیستم قرار دهید."
        )
    return path


def mysql_bin():
    path = _find_tool("mysql")
    if not path:
        raise BackupError(
            "ابزار mysql (کلاینت) پیدا نشد. برای بازیابی به آن نیاز است."
        )
    return path


def _run_sql_tool(cmd, input_file=None, timeout=900):
    env = os.environ.copy()
    env["MYSQL_PWD"] = db_config()["password"]
    kwargs = {
        "env": env,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "creationflags": _no_window(),
        "timeout": timeout,
    }
    if input_file is not None:
        kwargs["stdin"] = input_file
    proc = subprocess.run(cmd, **kwargs)
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# پشتیبان‌گیری
# ---------------------------------------------------------------------------


def run_backup(kind=BACKUP_KIND_MANUAL, user=None, title="", note=""):
    """یک فایل پشتیبان می‌سازد و رکوردش را ثبت می‌کند؛ رکورد/فایل را برمی‌گرداند.

    title/note: نام و توضیح دلخواه ادمین (برای نسخه‌های دستی). پس از موفقیت، اگر
    «کپی خودکار به پوشهٔ درایو» در تنظیمات تعیین شده باشد، فایل به آنجا نیز کپی
    می‌شود (شکست کپی مانع موفقیت پشتیبان نمی‌شود).
    """
    acquired = _busy_lock.acquire(blocking=False)
    if not acquired:
        raise BackupError("هم‌اکنون عملیات پشتیبان‌گیری یا بازیابی دیگری در جریان است؛ کمی بعد دوباره تلاش کنید.")
    try:
        cfg = db_config()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"habib_db_{stamp}_{kind}.sql"
        path = os.path.join(backup_dir(), filename)

        cmd = [
            mysqldump_bin(),
            "--no-tablespaces",
            "--single-transaction",
            "--routines",
            "--triggers",
            "--default-character-set=utf8mb4",
            "--column-statistics=0",
            f"--host={cfg['host']}",
            f"--port={cfg['port']}",
            f"--user={cfg['user']}",
            cfg["name"],
        ]
        try:
            with open(path, "wb") as out:
                env = os.environ.copy()
                env["MYSQL_PWD"] = cfg["password"]
                proc = subprocess.Popen(
                    cmd,
                    stdout=out,
                    stderr=subprocess.PIPE,
                    env=env,
                    creationflags=_no_window(),
                )
                try:
                    _, stderr = proc.communicate(timeout=900)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    _, stderr = proc.communicate()
                    raise BackupError("پشتیبان‌گیری بیش از حد انتظار طول کشید و متوقف شد.")
        except BackupError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise BackupError(f"خطا هنگام اجرای mysqldump: {exc}") from exc

        if proc.returncode != 0:
            tail = (stderr or b"").decode("utf-8", "replace").strip()[-600:]
            try:
                os.remove(path)
            except OSError:
                pass
            raise BackupError(f"پشتیبان‌گیری ناموفق بود. {tail}")

        size = os.path.getsize(path)
        record = BackupFile.objects.create(
            filename=filename,
            kind=kind,
            status=BACKUP_STATUS_OK,
            size_bytes=size,
            title=title.strip() if kind == BACKUP_KIND_MANUAL else "",
            note=note.strip() if kind == BACKUP_KIND_MANUAL else "",
            created_by=user if kind == BACKUP_KIND_MANUAL else None,
        )
        if kind == BACKUP_KIND_AUTO:
            setting = BackupSetting.get()
            setting.last_auto_at = datetime.now()
            setting.save(update_fields=["last_auto_at", "updated_at"])
            _cleanup_auto(setting.keep_count)
        _sync_to_folder(record)
        return record
    finally:
        _busy_lock.release()


def _sync_to_folder(record):
    """کپی خودکار فایل پشتیبان به پوشهٔ درایو/ابر (در صورت تعیین‌شدن در تنظیمات).

    غیرمخرب است: اگر پوشه در دسترس نباشد یا کپی شکست بخورد، پشتیبان همچنان موفق
    محسوب می‌شود (فقط از این کپی صرف‌نظر می‌شود).
    """
    try:
        setting = BackupSetting.get()
        target = (setting.sync_folder or "").strip()
        if not target:
            return
        src = safe_path_for(record)
        if not src:
            return
        target = os.path.abspath(target)
        os.makedirs(target, exist_ok=True)
        shutil.copy2(src, os.path.join(target, os.path.basename(src)))
    except Exception:  # noqa: BLE001 - کپی ابری اختیاری است
        pass


def days_since_last_success():
    """تعداد روزهای سپری‌شده از آخرین پشتیبان موفق (None اگر هرگز موفق نبوده)."""
    last = (
        BackupFile.objects.filter(status=BACKUP_STATUS_OK)
        .order_by("-created_at")
        .first()
    )
    if not last:
        return None, None
    days = (timezone.now() - last.created_at).total_seconds() / 86400.0
    return days, last


def delete_backup(record):
    """حذف فایل و رکورد یک پشتیبان."""
    path = safe_path_for(record)
    if path and os.path.isfile(path):
        os.remove(path)
    record.delete()


def safe_path_for(record):
    """مسیر امن فایل (فقط داخل پوشهٔ پشتیبان) یا None اگر فایل وجود نداشته باشد."""
    folder = os.path.abspath(backup_dir())
    candidate = os.path.abspath(os.path.join(folder, os.path.basename(record.filename)))
    if not candidate.startswith(folder + os.sep) and candidate != folder:
        return None
    return candidate if os.path.isfile(candidate) else None


def _cleanup_auto(keep):

    """قدیمی‌ترین نسخه‌های خودکارِ فراتر از keep_count را حذف می‌کند."""
    if not keep:
        return
    rows = list(
        BackupFile.objects.filter(kind=BACKUP_KIND_AUTO, status=BACKUP_STATUS_OK)
        .order_by("-created_at")
        .values_list("pk", "filename")[keep:]
    )
    for pk, _filename in rows:
        try:
            rec = BackupFile.objects.get(pk=pk)
            delete_backup(rec)
        except BackupFile.DoesNotExist:
            pass


def auto_backup_if_due():
    """اگر زمانِ پشتیبان خودکار رسیده باشد، آن را اجرا می‌کند (امن برای رشتهٔ پس‌زمینه)."""
    setting = BackupSetting.get()
    if not setting.auto_enabled:
        return
    interval = max(setting.interval_minutes or 0, 1) * 60
    now = datetime.now()
    if setting.last_auto_at and (now - setting.last_auto_at).total_seconds() < interval:
        return
    if not _busy_lock.acquire(blocking=False):
        return
    _busy_lock.release()
    try:
        run_backup(kind=BACKUP_KIND_AUTO)
    except Exception:  # noqa: BLE001 - خودکار نباید برنامه را بشکند
        try:
            _mark_auto_failed()
        except Exception:  # noqa: BLE001
            pass


def _mark_auto_failed():
    """برای بینایی خطاهای خودکار یک رکورد failed ثبت می‌کند (بدون فایل)."""
    BackupFile.objects.create(
        filename=f"auto_failed_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log",
        kind=BACKUP_KIND_AUTO,
        status=BACKUP_STATUS_FAILED,
        error="پشتیبان‌گیری خودکار ناموفق بود؛ فایل ساخته نشد.",
        size_bytes=0,
    )


# ---------------------------------------------------------------------------
# بازیابی
# ---------------------------------------------------------------------------


def run_restore(record):
    """دیتابیس را به وضعیتِ همان فایل پشتیبان برمی‌گرداند.

    هشدار: همهٔ جدول‌های فعلی حذف و از روی فایل پشتیبان دوباره ساخته/پر می‌شوند؛
    هر داده‌ای که پس از زمان پشتیبان ثبت شده باشد از بین می‌رود. فراخواننده باید
    تأیید صریح کاربر را گرفته باشد.
    """
    path = safe_path_for(record)
    if not path:
        raise BackupError("فایل پشتیبان روی دیسک یافت نشد (شاید جابه‌جا یا حذف شده است).")

    acquired = _busy_lock.acquire(blocking=False)
    if not acquired:
        raise BackupError("هم‌اکنون عملیات دیگری (پشتیبان یا بازیابی) در جریان است.")

    tmp_path = None
    try:
        cfg = db_config()
        bin_path = mysql_bin()

        # ۱) بستن اتصال‌های فعلی تا قفل‌سازی نشوند
        connections.close_all()

        # ۲) ساخت یک فایل ترکیبی: حذف همهٔ جدول‌های فعلی + محتوای پشتیبان
        tmp_path = os.path.join(backup_dir(), f"_restore_{record.pk}_{os.getpid()}.sql")
        with open(tmp_path, "w", encoding="utf-8") as out:
            out.write("SET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\n")
            with connections["default"].cursor() as cur:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
                    [cfg["name"]],
                )
                for (tbl,) in cur.fetchall():
                    out.write(f"DROP TABLE IF EXISTS `{tbl}`;\n")
            out.write("SET FOREIGN_KEY_CHECKS=1;\n")
        # بستن اتصالِ فهرست‌خوان قبل از عملیات مخرب
        connections.close_all()
        with open(tmp_path, "ab") as out:
            with open(path, "rb") as src:
                shutil.copyfileobj(src, out, length=1024 * 1024)

        cmd = [
            bin_path,
            "--default-character-set=utf8mb4",
            f"--host={cfg['host']}",
            f"--port={cfg['port']}",
            f"--user={cfg['user']}",
            cfg["name"],
        ]
        with open(tmp_path, "rb") as inp:
            code, _stdout, stderr = _run_sql_tool(cmd, input_file=inp, timeout=1800)
        if code != 0:
            tail = (stderr or b"").decode("utf-8", "replace").strip()[-700:]
            raise BackupError(f"بازیابی ناموفق بود. {tail}")

        # ۳) پس از بارگذاری، اتصال‌ها را تازه کن تا همه از دیتابیس جدید بخوانند
        connections.close_all()
        return True
    finally:
        if tmp_path and os.path.isfile(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        _busy_lock.release()
