"""تسک‌های Celery ماژول «تبلیغات».

- ``ads_expiry_sweep_task``: پایان دورهٔ نمایش تبلیغ‌ها → تیکت اطلاع‌رسانی
  به تبلیغ‌کننده (دستهٔ «مالی»/financial؛ مشابه الگوی ``sla_sweep_task``).
- ``ads_expiry_warning_task``: در «۲ روز پایانی» هر تبلیغ تأییدشده و فعال،
  تیکت هشدار انقضا به تبلیغ‌کننده (فقط یک‌بار؛ فلگ ``expiry_warning_notified_at``).
  از Command ``ads_expiry_sweep`` هم قابل اجراست.
"""

import logging

from celery import shared_task

logger = logging.getLogger("ads.tasks")


@shared_task
def ads_expiry_warning_task():
    """تبلیغ‌های در ۴۸ ساعت پایانی دوره → تیکت هشدار به تبلیغ‌کننده.

    از لحظه‌ای که تا پایان دوره کمتر از ۴۸ ساعت بماند (و هنوز منقضی نشده)،
    یک‌بار برای هر تبلیغ تیکت هشدار «۲ روز پایانی» می‌فرستد (فلگ
    ``expiry_warning_notified_at``). شکستِ ارسالِ تیکت هرگز sweep را نمی‌شکند.
    """
    from datetime import timedelta

    from django.utils import timezone

    from adminpanel.models import AD_STATUS_APPROVED, Advertisement
    from tickets.services import TicketError, create_ticket

    now = timezone.now()
    near = Advertisement.objects.filter(
        status=AD_STATUS_APPROVED,
        is_active=True,
        show_until__gte=now,
        show_until__lte=now + timedelta(hours=48),
        expiry_warning_notified_at__isnull=True,
    ).select_related("advertiser").prefetch_related("header_modules")

    changed = {"warned": 0, "failed": 0}
    for ad in near:
        headers = "، ".join(p.title for p in ad.header_modules.all()) or "—"
        subject = f"هشدار: ۲ روز پایانی دورهٔ نمایش تبلیغ «{ad.title[:60]}»"
        body = (
            f"دورهٔ نمایش تبلیغ «{ad.title}» به‌زودی (کمتر از ۴۸ ساعت) به پایان می‌رسد.\n\n"
            f"• پایان دوره: {ad.show_until:%Y-%m-%d %H:%M}\n"
            f"• هدرهای پخش: {headers}\n"
            f"• تعداد نمایش (views): {ad.views}\n\n"
            "برای ادامهٔ نمایش، می‌توانید همین تبلیغ را با بازهٔ جدید از ماژول "
            "«تبلیغات» تمدید کنید (دکمهٔ «تمدید» در تبلیغ‌های من).\n"
            "این پیام به‌صورت خودکار در دو روز پایانیِ دوره برای شما ارسال شده است."
        )
        try:
            create_ticket(
                author=ad.advertiser,
                subject=subject,
                description=body,
                priority="normal",
                category_code="financial",
                specific_user_ids=None,
                duplicate_window=0,
            )
            ad.expiry_warning_notified_at = now
            ad.save(update_fields=["expiry_warning_notified_at"])
            changed["warned"] += 1
        except TicketError as exc:
            changed["failed"] += 1
            logger.warning("ads_expiry_warning: TicketError for ad %s: %s", ad.pk, exc)
        except Exception:  # noqa: BLE001 - شکست تیکت هرگز sweep را نمی‌شکند
            changed["failed"] += 1
            logger.exception("ads_expiry_warning: failed to warn ad %s", ad.pk)
    return changed


@shared_task
def ads_expiry_sweep_task():
    """تبلیغ‌های تأییدشده‌ای که دورهٔ نمایششان تمام شده → تیکت به تبلیغ‌کننده.

    فقط «یک‌بار» برای هر تبلیغ (فلگ ``expiry_notified_at``)؛ متن تیکت شامل
    عنوان، بازهٔ نمایش، هدرهای انتخابی و شمارندهٔ نمایش است. شکستِ ارسالِ
    تیکت هرگز روند sweep را متوقف نمی‌کند.
    """
    from django.utils import timezone

    from adminpanel.models import Advertisement
    from tickets.services import TicketError, create_ticket

    now = timezone.now()
    from adminpanel.models import AD_STATUS_APPROVED

    expired = Advertisement.objects.filter(
        status=AD_STATUS_APPROVED,
        is_active=True,
        show_until__lt=now,
        expiry_notified_at__isnull=True,
    ).select_related("advertiser").prefetch_related("header_modules")

    changed = {"notified": 0, "failed": 0}
    for ad in expired:
        headers = "، ".join(p.title for p in ad.header_modules.all()) or "—"
        subject = f"پایان دورهٔ نمایش تبلیغ «{ad.title[:60]}»"
        body = (
            f"دورهٔ نمایش تبلیغ «{ad.title}» به پایان رسید.\n\n"
            f"• دورهٔ نمایش: {ad.show_from:%Y-%m-%d %H:%M} تا {ad.show_until:%Y-%m-%d %H:%M}\n"
            f"• هدرهای پخش: {headers}\n"
            f"• تعداد نمایش (views): {ad.views}\n\n"
            "برای ادامهٔ نمایش، می‌توانید از ماژول «تبلیغات» یک دورهٔ جدید ثبت کنید.\n"
            "این پیام به‌صورت خودکار پس از پایان دورهٔ نمایش برای شما ارسال شده است."
        )
        try:
            create_ticket(
                author=ad.advertiser,
                subject=subject,
                description=body,
                priority="normal",
                category_code="financial",
                specific_user_ids=None,
                duplicate_window=0,
            )
            ad.expiry_notified_at = now
            ad.save(update_fields=["expiry_notified_at"])
            changed["notified"] += 1
        except TicketError as exc:
            changed["failed"] += 1
            logger.warning("ads_expiry_sweep: TicketError for ad %s: %s", ad.pk, exc)
        except Exception:  # noqa: BLE001 - شکست تیکت هرگز sweep را نمی‌شکند
            changed["failed"] += 1
            logger.exception("ads_expiry_sweep: failed to notify ad %s", ad.pk)
    return changed
