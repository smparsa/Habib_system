"""شماره‌دهی تیکت: HUB-{year}-{seq:06d}.

از یک جدول شمارنده با SELECT ... FOR UPDATE استفاده می‌کند تا در تراکنش‌های
همزمان شماره تکراری نسازد. شمارهٔ عمومی جایگزین شناسهٔ دیتابیس است.
"""

import logging
from datetime import datetime

from django.db import models, transaction
from django.utils import timezone

from .constants import TICKET_NUMBER_FORMAT

logger = logging.getLogger("tickets.numbering")


class TicketYearCounter(models.Model):
    """شمارندهٔ داخلی سالانه — در admin نمایش داده نمی‌شود."""

    year = models.PositiveSmallIntegerField("سال", unique=True)
    seq = models.PositiveBigIntegerField("آخرین شماره", default=0)

    class Meta:
        app_label = "tickets"
        verbose_name = "شمارنده تیکت"
        verbose_name_plural = "شمارنده‌های تیکت"


def next_ticket_number(now=None):
    now = now or timezone.now()
    year = now.year
    with transaction.atomic():
        row, _ = TicketYearCounter.objects.select_for_update().get_or_create(
            year=year, defaults={"seq": 0}
        )
        row.seq += 1
        row.save(update_fields=["seq"])
        return TICKET_NUMBER_FORMAT.format(year=year, seq=row.seq)


def current_year_sequence(now=None):
    now = now or timezone.now()
    row = TicketYearCounter.objects.filter(year=now.year).first()
    return row.seq if row else 0
