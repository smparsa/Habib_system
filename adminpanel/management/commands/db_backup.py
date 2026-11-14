"""دستور مدیریت: پشتیبان‌گیری از دیتابیس از خط فرمان.

نمونه:
    python manage.py db_backup                            # پشتیبان دستی
    python manage.py db_backup --auto                     # پشتیبان خودکار (برای زمان‌بندی خارجی)
    python manage.py db_backup --title "پیش از به‌روزرسانی" --note "دوره‌ای"  # دستی با نام/توضیح
    python manage.py db_backup --show                      # نمایش تنظیمات و آخرین نسخه‌ها

می‌توان این دستور را با «Task Scheduler ویندوز» یا cron نیز زمان‌بندی کرد تا حتی
وقتی سرور خاموش است پشتیبان خودکار گرفته شود.
"""

from django.core.management.base import BaseCommand

from adminpanel.backup_service import (
    BACKUP_KIND_AUTO,
    BACKUP_KIND_MANUAL,
    BackupError,
    auto_backup_if_due,
    run_backup,
)
from adminpanel.models import BackupFile, BackupSetting


class Command(BaseCommand):
    help = "گرفتن نسخهٔ پشتیبان از دیتابیس (دستی یا خودکار) و نمایش وضعیت."

    def add_arguments(self, parser):
        parser.add_argument(
            "--auto", action="store_true", help="به‌جای نسخهٔ دستی، نسخهٔ خودکار بگیر."
        )
        parser.add_argument(
            "--due", action="store_true",
            help="فقط اگر زمانِ نسخهٔ خودکار رسیده باشد بگیر (همان منطق رشتهٔ پس‌زمینه).",
        )
        parser.add_argument(
            "--title", default="", help="نام/برچسب دلخواه برای نسخهٔ دستی (اختیاری)."
        )
        parser.add_argument(
            "--note", default="", help="توضیح دلخواه برای نسخهٔ دستی (اختیاری)."
        )
        parser.add_argument(
            "--show", action="store_true", help="وضعیت تنظیمات و آخرین نسخه‌ها را نشان بده.",
        )

    def handle(self, *args, **options):
        if options["show"]:
            from datetime import datetime

            from adminpanel.backup_service import days_since_last_success

            setting = BackupSetting.get()
            self.stdout.write(f"پشتیبان خودکار: {'فعال' if setting.auto_enabled else 'غیرفعال'}")
            self.stdout.write(f"بازه (دقیقه): {setting.interval_minutes} | نگه‌داری: {setting.keep_count}")
            self.stdout.write(f"آخرین نسخهٔ خودکار: {setting.last_auto_at or '—'}")
            self.stdout.write(f"کپی به پوشهٔ ابری: {setting.sync_folder or '—'}")
            self.stdout.write(f"هشدار پس از: {setting.stale_after_days} روز بدون پشتیبان موفق")
            days, last = days_since_last_success()
            if last:
                self.stdout.write(
                    f"آخرین پشتیبان موفق: {last.filename} "
                    f"({last.size_bytes} بایت) — {last.created_at:%Y-%m-%d %H:%M} "
                    f"({int(days) if days is not None else 0} روز پیش)"
                )
            else:
                self.stdout.write("آخرین پشتیبان موفق: هیچ نسخه‌ای ثبت نشده!")
            return

        try:
            if options["due"]:
                auto_backup_if_due()
                self.stdout.write(self.style.SUCCESS("بررسی خودکار انجام شد."))
                return
            kind = BACKUP_KIND_AUTO if options["auto"] else BACKUP_KIND_MANUAL
            record = run_backup(
                kind=kind,
                title=options.get("title") or "",
                note=options.get("note") or "",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"پشتیبان {'خودکار' if kind == BACKUP_KIND_AUTO else 'دستی'} گرفته شد: "
                    f"{record.filename} ({record.size_bytes} بایت)"
                )
            )
        except BackupError as exc:
            self.stderr.write(self.style.ERROR(f"خطا: {exc}"))
            raise SystemExit(1)
