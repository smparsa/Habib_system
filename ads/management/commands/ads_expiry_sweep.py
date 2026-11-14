from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "اطلاع‌رسانی پایان دورهٔ نمایش تبلیغ‌ها با تیکت به تبلیغ‌کننده (همان تسک Celery)."

    def handle(self, *args, **options):
        try:
            from ads.tasks import ads_expiry_sweep_task
        except Exception as exc:  # noqa: BLE001
            self.stderr.write(f"خطا در بارگذاری تسک: {exc}")
            return
        result = ads_expiry_sweep_task()
        self.stdout.write(self.style.SUCCESS(
            f"اطلاع‌رسانی: {result['notified']} | ناموفق: {result['failed']}"))
