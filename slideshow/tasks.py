"""تسک‌های Celery ماژول «اسلایدشوی آمار داشبورد».

- ``slideshow_expiry_warning_task``: در «۲ روز پایانی» هر اسلایدِ کاربرِ تأییدشده
  و فعال، تیکت هشدار انقضا به صاحبش ارسال می‌شود (فقط یک‌بار؛ فلگ
  ``expiry_warning_notified_at``).
- ``slideshow_expired_sweep_task``: پایان دورهٔ نمایش اسلایدهای کاربر → تیکت
  اطلاع‌رسانی به صاحب اسلاید (فقط یک‌بار؛ فلگ ``expiry_notified_at`` — هم‌الگوی
  ``ads.tasks.ads_opacity_sweep_task``).
  اسلایدهای ادمین (``advertiser`` خالی) مخاطب ندارند و رد می‌شوند.
"""

import logging

from celery import shared_task

logger = logging.getLogger("slideshow.tasks")


def _box_titles(slide):
    return "، ".join(b.title for b in slide.boxes.all()) or "—"


@shared_task
def slideshow_expiry_warning_task():
    """اسلایدهای در ۴۸ ساعت پایانی دوره → تیکت هشدار به صاحب اسلاید.

    از لحظه‌ای که تا پایان دوره کمتر از ۴۸ ساعت بماند (و هنوز منقضی نشده)،
    یک‌بار برای هر اسلاید تیکت هشدار «۲ روز پایانی» می‌فرستد. شکستِ ارسالِ
    تیکت هرگز روند sweep را متوقف نمی‌کند.
    """
    from datetime import timedelta

    from django.utils import timezone

    from adminpanel.models import AD_STATUS_APPROVED, StatSlide
    from tickets.services import TicketError, create_ticket

    now = timezone.now()
    near = StatSlide.objects.filter(
        advertiser__isnull=False,
        status=AD_STATUS_APPROVED,
        is_active=True,
        show_until__gte=now,
        show_until__lte=now + timedelta(hours=48),
        expiry_warning_notified_at__isnull=True,
    ).select_related("advertiser").prefetch_related("boxes")

    changed = {"warned": 0, "failed": 0}
    for slide in near:
        boxes = _box_titles(slide)
        subject = f"هشدار: ۲ روز پایانی دورهٔ نمایش اسلاید «{slide.title[:60]}»"
        body = (
            f"دورهٔ نمایش اسلاید «{slide.title}» به‌زودی (کمتر از ۴۸ ساعت) به پایان می‌رسد.\n\n"
            f"• پایان دوره: {slide.show_until:%Y-%m-%d %H:%M}\n"
            f"• باکس‌های پخش: {boxes}\n"
            f"• تعداد نمایش (views): {slide.views}\n\n"
            "برای ادامهٔ نمایش، می‌توانید همین اسلاید را با بازهٔ جدید از ماژول\n"
            "«اسلایدشوی آمار داشبورد» تمدید کنید (دکمهٔ «تمدید» در اسلایدهای من).\n"
            "این پیام به‌صورت خودکار در دو روز پایانیِ دوره برای شما ارسال شده است."
        )
        try:
            create_ticket(
                author=slide.advertiser,
                subject=subject,
                description=body,
                priority="normal",
                category_code="financial",
                specific_user_ids=None,
                duplicate_window=0,
            )
            slide.expiry_warning_notified_at = now
            slide.save(update_fields=["expiry_warning_notified_at"])
            changed["warned"] += 1
        except TicketError as exc:
            changed["failed"] += 1
            logger.warning("slideshow_expiry_warning: TicketError for slide %s: %s", slide.pk, exc)
        except Exception:  # noqa: BLE001 - شکست تیکت هرگز sweep را نمی‌شکند
            changed["failed"] += 1
            logger.exception("slideshow_expiry_warning: failed to warn slide %s", slide.pk)
    return changed


@shared_task
def slideshow_expired_sweep_task():
    """اسلایدهای کاربرِ تأییدشده که دورهٔ نمایششان تمام شد → تیکت به صاحب اسلاید."""
    from django.utils import timezone

    from adminpanel.models import AD_STATUS_APPROVED, StatSlide
    from tickets.services import TicketError, create_ticket

    now = timezone.now()
    expired = StatSlide.objects.filter(
        advertiser__isnull=False,
        status=AD_STATUS_APPROVED,
        is_active=True,
        show_until__lt=now,
        expiry_notified_at__isnull=True,
    ).select_related("advertiser").prefetch_related("boxes")

    changed = {"notified": 0, "failed": 0}
    for slide in expired:
        boxes = _box_titles(slide)
        subject = f"پایان دورهٔ نمایش اسلاید «{slide.title[:60]}»"
        body = (
            f"دورهٔ نمایش اسلاید «{slide.title}» به پایان رسید.\n\n"
            f"• دورهٔ نمایش: {slide.show_from:%Y-%m-%d %H:%M} تا {slide.show_until:%Y-%m-%d %H:%M}\n"
            f"• باکس‌های پخش: {boxes}\n"
            f"• تعداد نمایش (views): {slide.views}\n\n"
            "برای ادامهٔ نمایش، می‌توانید همین اسلاید را با بازهٔ جدید از ماژول\n"
            "«اسلایدشوی آمار داشبورد» تمدید کنید (دکمهٔ «تمدید» در اسلایدهای من).\n"
            "این پیام به‌صورت خودکار پس از پایان دورهٔ نمایش برای شما ارسال شده است."
        )
        try:
            create_ticket(
                author=slide.advertiser,
                subject=subject,
                description=body,
                priority="normal",
                category_code="financial",
                specific_user_ids=None,
                duplicate_window=0,
            )
            slide.expiry_notified_at = now
            slide.save(update_fields=["expiry_notified_at"])
            changed["notified"] += 1
        except TicketError as exc:
            changed["failed"] += 1
            logger.warning("slideshow_expired_sweep: TicketError for slide %s: %s", slide.pk, exc)
        except Exception:  # noqa: BLE001 - شکست تیکت هرگز sweep را نمی‌شکند
            changed["failed"] += 1
            logger.exception("slideshow_expired_sweep: failed to notify slide %s", slide.pk)
    return changed
