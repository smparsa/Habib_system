"""شماره‌دهی سفارش/انتقال سکه: WAL-{year}-{seq:06d} و TRF-{year}-{seq:06d}.

مثل شمارندهٔ تیکت، از SELECT ... FOR UPDATE استفاده می‌کند تا در تراکنش‌های
هم‌زمان کد تکراری ساخته نشود.
"""

from django.db import transaction
from django.utils import timezone

from .models import WalletCounter


def next_code(kind, prefix):
    """تولید کد یکتای سالانه برای نوعِ مشخص (order / transfer)."""
    now = timezone.now()
    with transaction.atomic():
        row, _ = WalletCounter.objects.select_for_update().get_or_create(
            kind=kind, year=now.year, defaults={"seq": 0}
        )
        row.seq += 1
        row.save(update_fields=["seq"])
        return f"{prefix}-{now.year}-{row.seq:06d}"