from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "بررسی SLA تیکت‌های باز: هشدار/نقض + ارتقا + اعلان (همان تسک Celery)."

    def handle(self, *args, **options):
        try:
            from tickets.tasks import sla_sweep_task
        except Exception as exc:  # noqa: BLE001
            self.stderr.write(f"خطا در بارگذاری تسک: {exc}")
            return
        result = sla_sweep_task()
        self.stdout.write(self.style.SUCCESS(
            f"هشدار: {result['warned']} | نقض SLA: {result['breached']}"))
