"""دیسک پایدار Archil — نگه‌داری فایل‌هایی که باید بین اجراها باقی بمانند.

این ماژول فقط سمت سرور است (هرگز از کد سمت مرورگر import نشود):

- پیکربندی از متغیرهای محیطی خوانده می‌شود:
  ``ARCHIL_API_KEY`` (کلید API، با پیشوند ``key-`` — نه توکن مانت/دیسک)،
  ``ARCHIL_REGION`` (پیش‌فرض ``aws-us-east-1``) و ``ARCHIL_DISK_ID``.
- کلید API فقط در فرایند سرور می‌ماند و هیچ‌جا چاپ یا در پاسخ برگردانده نمی‌شود؛
  توکن یک‌بارمصرفِ مانت هم (که ``create_disk`` برمی‌گرداند) عمداً دور ریخته می‌شود
  تا در کد یا لاگ نیفتد.
- هر ``exec`` یک کانتینر تازه است: فایل‌های روی دیسک می‌مانند، وضعیت کانتینر نه.
  دیسک در ``/mnt/data`` مانت است و همان پوشهٔ کاری است.

نمونهٔ استفاده::

    from cloudstorage import archil_storage

    disk = archil_storage.get_disk()
    archil_storage.write_file("health/report.json", "{}")
    print(archil_storage.read_text("health/report.json"))
    res = archil_storage.run_command("ls -la")   # res.stdout / res.exit_code

برای پروژه‌هایی که فایل‌هایشان باید از «یک اجرا» جان سالم به در ببرد (نه فقط از
یک درخواست)، کافی است همین توابع را در جای مناسب صدا بزنید.
"""
from __future__ import annotations

import os
from pathlib import Path

import archil

# ناحیهٔ پیش‌فرض؛ exec فقط در aws-us-east-1، aws-us-west-2 و aws-eu-west-1 اجرا می‌شود.
DEFAULT_REGION = "aws-us-east-1"

# نام دیسکی که وقتی ARCHIL_DISK_ID تنظیم نشده ساخته می‌شود.
APP_DISK_NAME = "habib-system"

# ریشهٔ پروژه (همان BASE_DIR جنگو) — برای یافتن فایل .env محلی.
BASE_DIR = Path(__file__).resolve().parent.parent

_ENV_LOADED = False


class ArchilStorageError(RuntimeError):
    """خطای پیکربندی یا فراخوانی Archil (کلید نامعتبر، دیسک ناموجود و …)."""


# --------------------------------------------------------------------------- #
# فایل .env محلی (بدون وابستگی بیرونی؛ فقط برای پر کردن متغیرهای تنظیم‌نشده)
# --------------------------------------------------------------------------- #
def env_file_path() -> Path:
    """مسیر فایل .env محلی در ریشهٔ پروژه."""
    return BASE_DIR / ".env"


def load_env_file(path=None):
    """خواندن .env محلی و تنظیم متغیرهایی که در محیط تعریف نشده‌اند.

    مقدارها هرگز چاپ نمی‌شوند؛ متغیرهای محیطیِ واقعی همیشه اولویت دارند.
    """
    global _ENV_LOADED
    if _ENV_LOADED and path is None:
        return
    target = Path(path) if path else env_file_path()
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        name, sep, value = line.partition("=")
        if not sep:
            continue
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = value
    if path is None:
        _ENV_LOADED = True


def remember_disk_id(identifier: str) -> None:
    """ثبت شناسهٔ دیسک در .env محلی (و در محیط همین فرایند) برای اجراهای بعدی."""
    identifier = (identifier or "").strip()
    if not identifier:
        return
    os.environ["ARCHIL_DISK_ID"] = identifier
    target = env_file_path()
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = ["# متغیرهای محیطی محلی — در git نادیده گرفته می‌شود."]
    kept, replaced = [], False
    for line in lines:
        if line.strip().startswith("ARCHIL_DISK_ID="):
            kept.append(f"ARCHIL_DISK_ID={identifier}")
            replaced = True
        else:
            kept.append(line)
    if not replaced:
        kept.append(f"ARCHIL_DISK_ID={identifier}")
    target.write_text("\n".join(kept) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# پیکربندی
# --------------------------------------------------------------------------- #
def api_key() -> str:
    """کلید API از محیط؛ اگر تنظیم نشده باشد خطای گویا می‌دهد (بدون چاپ مقدار)."""
    load_env_file()
    key = (os.environ.get("ARCHIL_API_KEY") or "").strip()
    if not key:
        raise ArchilStorageError(
            "متغیر محیطی ARCHIL_API_KEY تنظیم نشده است؛ کلید API (ابتدای key-) را از "
            "https://console.archil.com/api-keys در فایل .env بگذارید."
        )
    return key


def region() -> str:
    """ناحیهٔ Archil از محیط (پیش‌فرض aws-us-east-1)."""
    load_env_file()
    return (os.environ.get("ARCHIL_REGION") or "").strip() or DEFAULT_REGION


def disk_id() -> str:
    """شناسهٔ دیسک (``dsk-…``) از ARCHIL_DISK_ID."""
    load_env_file()
    return (os.environ.get("ARCHIL_DISK_ID") or "").strip()


def configure() -> None:
    """پیکربندی SDK از متغیرهای محیطی — برای هر فرایند یک‌بار کافی است."""
    archil.configure(api_key=api_key(), region=region())


def _guard(exc: archil.ArchilError):
    """تبدیل خطای SDK به خطای این ماژول با راهنمای کوتاه (بدون لو دادن کلید)."""
    if getattr(exc, "status", None) == 401:
        hint = (
            " کلید ارائه‌شده معتبر نیست: مقدار باید کلید API با پیشوند key- از "
            "https://console.archil.com/api-keys باشد (نه توکن دیسک/مانت adt_…) و "
            f"هم‌ناحیه با ARCHIL_REGION={region()} باشد."
        )
    else:
        hint = ""
    return ArchilStorageError(f"خطای Archil: {exc}{hint}")


# --------------------------------------------------------------------------- #
# دیسک
# --------------------------------------------------------------------------- #
def get_disk():
    """دیسک نام‌برده در ARCHIL_DISK_ID — خطا اگر تنظیم نشده باشد."""
    configure()
    identifier = disk_id()
    if not identifier:
        raise ArchilStorageError(
            "متغیر محیطی ARCHIL_DISK_ID تنظیم نشده است؛ یک‌بار "
            "`python check_archil_persistence.py` اجرا کنید تا دیسک ساخته و شناسه‌اش ثبت شود."
        )
    try:
        return archil.get_disk(identifier)
    except archil.ArchilError as exc:
        raise _guard(exc) from exc


def ensure_disk(name: str | None = None):
    """دیسک موجود (ARCHIL_DISK_ID) یا ساخت یک دیسک تازه با نام پیش‌فرض.

    توکن یک‌بارمصرفِ مانت عمداً برگردانده/چاپ نمی‌شود؛ برای exec لازم نیست.
    """
    if disk_id():
        return get_disk()
    configure()
    try:
        created = archil.create_disk(name=name or APP_DISK_NAME)
    except archil.ArchilError as exc:
        raise _guard(exc) from exc
    return created.disk.wait_until_ready()


# --------------------------------------------------------------------------- #
# اجرای فرمان روی دیسک
# --------------------------------------------------------------------------- #
def run_command(command: str):
    """اجرای فرمان روی دیسک (پوشهٔ کاری = /mnt/data) و برگرداندن ExecResult.

    خروجی: ``.stdout``، ``.stderr``، ``.exit_code`` و ``.timing``.
    """
    try:
        return get_disk().exec(command)
    except archil.ArchilError as exc:
        raise _guard(exc) from exc


# --------------------------------------------------------------------------- #
# نوشتن/خواندن فایل روی دیسک (کلید = مسیر نسبی از ریشهٔ دیسک)
# --------------------------------------------------------------------------- #
def write_file(key: str, data) -> None:
    """نوشتن فایل روی دیسک (متن یا بایت) — محتوا بدون نیاز به نقل‌قول شل امن است."""
    body = data.encode("utf-8") if isinstance(data, str) else data
    try:
        get_disk().put_object(key, body)
    except archil.ArchilError as exc:
        raise _guard(exc) from exc


def read_file(key: str) -> bytes:
    """خواندن بایت‌های یک فایل از دیسک."""
    try:
        return get_disk().get_object(key)
    except archil.ArchilError as exc:
        raise _guard(exc) from exc


def read_text(key: str) -> str:
    """خواندن یک فایل متنی از دیسک."""
    return read_file(key).decode("utf-8")
