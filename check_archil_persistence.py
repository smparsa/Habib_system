"""بررسی پایداری دیسک Archil: نوشتن در یک exec و خواندن در exec دوم.

هر exec یک کانتینر تازه است؛ پس اگر خطِ نوشته‌شده در اجرای دوم خوانده شود،
یعنی فایل واقعاً روی دیسک ماندگار شده است.

اجرا::

    python check_archil_persistence.py

پیش‌نیاز: ARCHIL_API_KEY (ابتدای key-) در فایل .env یا در محیط همین شل.
اگر ARCHIL_DISK_ID تنظیم نشده باشد یک دیسک تازه ساخته و شناسه‌اش در .env ثبت
می‌شود؛ توکن یک‌بارمصرفِ مانت هیچ‌جا چاپ نمی‌شود. کد خروج غیرصفر = شکست بررسی.
"""
from __future__ import annotations

import os
import secrets
import sys
from datetime import datetime, timezone

from cloudstorage import archil_storage


def ok(message):
    print("OK  ", message)


def fail(message, code=1):
    print("FAIL", message, file=sys.stderr)
    raise SystemExit(code)


def main():
    archil_storage.load_env_file()

    if not (os.environ.get("ARCHIL_API_KEY") or "").strip():
        fail(
            "ARCHIL_API_KEY تنظیم نشده است.\n"
            "      کلید API (ابتدای key-) را از https://console.archil.com/api-keys\n"
            "      در فایل .env ریشهٔ پروژه بگذارید: ARCHIL_API_KEY=key-…"
        )
    if not (os.environ.get("ARCHIL_API_KEY") or "").strip().startswith("key-"):
        print(
            "WARN  مقدار ARCHIL_API_KEY با key- شروع نمی‌شود؛ احتمالاً توکن دیسک/مانت "
            "(adt_…) است و API پاسخ 401 می‌دهد.",
            file=sys.stderr,
        )

    print(f"REGION {archil_storage.region()}")

    try:
        disk = archil_storage.ensure_disk()
    except archil_storage.ArchilStorageError as exc:
        fail(str(exc))

    archil_storage.remember_disk_id(disk.id)
    ok(f"disk {disk.name} ({disk.id}) در {archil_storage.region()} — شناسه در .env ثبت شد")

    # پوشهٔ تازه برای همین اجرا (در حالت shared، نوشتن در زیرپوشهٔ تازه مجاز است)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    job = f"persist-check-{stamp}-{secrets.token_hex(4)}"
    marker = f"archil-persistence line {job} {secrets.token_hex(8)}"

    write_cmd = (
        f"mkdir -p {job} && cd {job} && printf '%s\\n' '{marker}' > probe.txt && cat probe.txt"
    )
    read_cmd = f"cd {job} && cat probe.txt"

    try:
        first = archil_storage.run_command(write_cmd)
    except archil_storage.ArchilStorageError as exc:
        fail(f"exec اول (نوشتن) شکست خورد: {exc}")
    if first.exit_code != 0:
        fail(f"exec اول (نوشتن) با کد {first.exit_code} تمام شد: {first.stderr.strip()[:500]}")
    if marker not in (first.stdout or ""):
        fail("exec اول خطِ نشانه را در خروجی خودش برنگرداند.")
    ok(f"exec اول: نوشتن در {job}/probe.txt")

    # اجرای دوم — کانتینر تازه، فقط دیسک مشترک است.
    try:
        second = archil_storage.run_command(read_cmd)
    except archil_storage.ArchilStorageError as exc:
        fail(f"exec دوم (خواندن) شکست خورد: {exc}")
    if second.exit_code != 0:
        fail(f"exec دوم (خواندن) با کد {second.exit_code} تمام شد: {second.stderr.strip()[:500]}")

    read_back = (second.stdout or "").strip()
    if marker not in read_back:
        fail(f"خطِ نوشته‌شده در اجرای دوم پیدا نشد. خوانده شد: {read_back[:500]!r}")
    ok(f"exec دوم: بازخوانی «{read_back}»")
    ok("پایداری تایید شد: فایل بین دو exec جداگانه باقی ماند.")


if __name__ == "__main__":
    main()
