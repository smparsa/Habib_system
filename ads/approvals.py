"""گردش کار مشترک «تأیید مدیر» برای تبلیغ و اسلایدشوی آمار.

۱. پس از ثبت و کسر هزینه، یک «تیکت درخواست تأیید» برای مدیران ساخته می‌شود
   (``open_approval_request``).
۲. تأیید مدیر → وضعیت «تأییدشده» (ورود به صف نمایش طبق ترتیب/بازهٔ زمانی)،
   اطلاع به کاربر و بستن تیکت (``approve_item``).
۳. رد مدیر → اگر مورد هنوز «در انتظار تأیید» بوده، ``AD_REJECT_FEE_PERCENT``
   (پیش‌فرض ۱۰٪) از هزینهٔ پرداختی نگه داشته و مابقی به کیف پول کاربر بازمی‌گردد.
   بازگشت وجه فقط یک‌بار انجام می‌شود (``refunded_at``) و هر حرکت مالی با تیکت
   به کاربر و مدیران اعلام می‌گردد (``reject_item``).

شکست ساخت/بستن تیکت هرگز گردش مالی یا تغییر وضعیت را متوقف نمی‌کند.
"""

from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from adminpanel.models import (
    AD_STATUS_APPROVED,
    AD_STATUS_PENDING,
    AD_STATUS_REJECTED,
    Advertisement,
)
from wallet.services import WalletError, _movement_ticket, refund_module_charge


def reject_fee_percent():
    """درصد کارمزد هنگام رد (تنظیم‌پذیر با ``settings.AD_REJECT_FEE_PERCENT``)."""
    return Decimal(str(getattr(settings, "AD_REJECT_FEE_PERCENT", 10)))


def _meta(item):
    """برچسب‌های متنی بر اساس نوع رکورد (تبلیغ / اسلایدشو)."""
    if isinstance(item, Advertisement):
        return {
            "noun": "تبلیغ", "prefix": "AD", "ref_code": "ad_submission",
            "places_label": "هدرها",
            "places": ", ".join(item.header_modules.values_list("title", flat=True)),
            "panel": "پنل مدیریت ← تبلیغات",
        }
    return {
        "noun": "اسلایدشوی آمار", "prefix": "SL", "ref_code": "stat_slide_submission",
        "places_label": "محل نمایش",
        "places": "اسلایدشو A",
        "panel": "پنل مدیریت ← اسلایدشوی آمار",
    }


def item_ref(item):
    return f"{_meta(item)['prefix']}-{item.pk}"


def _jdt(value):
    try:
        from core.templatetags.core_extras import jdatetime
        return str(jdatetime(value))
    except Exception:  # noqa: BLE001 - قالب‌بندی تاریخ نباید گردش را بشکند
        return str(value)


def _owner(item):
    return item.advertiser


def _close_approval_ticket(item, admin, note, request=None):
    """تیکت درخواست تأیید را (در صورت باز بودن) با پیام نتیجه «حل‌شده» می‌کند."""
    if not item.approval_ticket_id:
        return
    try:
        from tickets import constants as tkt_c
        from tickets.models import Ticket
        from tickets.services import add_message, change_status

        ticket = Ticket.objects.filter(pk=item.approval_ticket_id).first()
        if ticket is None or ticket.status in (tkt_c.STATUS_RESOLVED, tkt_c.STATUS_CLOSED):
            return
        if note:
            add_message(ticket, admin, note, request=request)
        change_status(ticket, admin, tkt_c.STATUS_RESOLVED,
                      note=f"{item_ref(item)} بررسی شد", request=request)
    except Exception:  # noqa: BLE001
        return


def open_approval_request(item, request=None):
    """ساخت «تیکت درخواست تأیید» برای مدیران پس از ثبت و کسر هزینه.

    تیکت از طرف کاربر به همهٔ مدیران فعال ارسال می‌شود (کاربر هم آن را می‌بیند).
    شناسهٔ تیکت در ``approval_ticket_id`` ذخیره می‌شود تا هنگام تأیید/رد بسته شود.
    """
    owner = _owner(item)
    if owner is None:
        return None
    m = _meta(item)
    body = (
        f"درخواست تأیید {m['noun']} — کد {item_ref(item)}\n"
        f"عنوان: {item.title}\n"
        f"{m['places_label']}: {m['places'] or '—'}\n"
        f"بازهٔ نمایش: {_jdt(item.show_from)} تا {_jdt(item.show_until)}\n"
        f"هزینهٔ کسرشده از کیف پول: {item.coins_paid} سکه\n"
        f"برای بررسی: {m['panel']}. در صورت رد، {reject_fee_percent().normalize():f}٪ هزینه کسر و "
        f"مابقی به کیف پول کاربر بازمی‌گردد."
    )
    ticket = _movement_ticket(
        request, owner, f"درخواست تأیید {m['noun']} — {item_ref(item)}", body,
        include_staff=True, priority="high",
    )
    if ticket is not None:
        item.approval_ticket_id = ticket.pk
        item.save(update_fields=["approval_ticket_id"])
    return ticket


def approve_item(item, admin, request=None):
    """تأیید: ورود به صف نمایش + اطلاع به کاربر. خروجی: (ok, code)."""
    if item.refunded_at is not None:
        return False, "refunded"
    if item.status == AD_STATUS_APPROVED:
        return False, "already"
    item.status = AD_STATUS_APPROVED
    item.save(update_fields=["status", "updated_at"])
    m = _meta(item)
    owner = _owner(item)
    if owner is not None:
        _movement_ticket(
            request, admin, f"تأیید {m['noun']} — {item_ref(item)}",
            f"{m['noun']} «{item.title}» توسط مدیر تأیید شد و طبق بازهٔ نمایش "
            f"({_jdt(item.show_from)} تا {_jdt(item.show_until)}) در صف نمایش قرار گرفت.",
            recipient_user_ids=[owner.id], priority="normal",
        )
    _close_approval_ticket(item, admin, f"{m['noun']} تأیید و در صف نمایش قرار گرفت.", request)
    return True, "approved"


def reject_item(item, admin, request=None, reason=""):
    """رد: اگر «در انتظار» بود، کسر کارمزد و بازگشت مابقی به کیف پول (یک‌بار).

    خروجی: dict با کلیدهای ok, code ('rejected' | 'already'), refunded, refund, fee.
    رد موردِ تأییدشده/در حال پخش، فقط وضعیت را عوض می‌کند و وجهی بازنمی‌گرداند.
    """
    result = {"ok": False, "code": "already", "refunded": False,
              "refund": Decimal("0"), "fee": Decimal("0")}
    m = _meta(item)
    owner = _owner(item)
    with transaction.atomic():
        locked = type(item).objects.select_for_update().get(pk=item.pk)
        if locked.status == AD_STATUS_REJECTED:
            return result
        was_pending = locked.status == AD_STATUS_PENDING
        locked.status = AD_STATUS_REJECTED
        update_fields = ["status", "updated_at"]
        paid = Decimal(str(locked.coins_paid or 0))
        if was_pending and owner is not None and paid > 0 and locked.refunded_at is None:
            refund, fee = refund_module_charge(
                owner, paid, fee_percent=reject_fee_percent(),
                ref_code=m["ref_code"], admin=admin, request=request, notify=False,
                note=f"بازگشت هزینهٔ {m['noun']} ردشده «{locked.title}» ({item_ref(locked)})",
            )
            locked.refunded_coins = refund
            locked.refund_fee_coins = fee
            locked.refunded_at = timezone.now()
            update_fields += ["refunded_coins", "refund_fee_coins", "refunded_at"]
            result.update(refunded=True, refund=refund, fee=fee)
        locked.save(update_fields=update_fields)
    # همگام‌سازی نمونهٔ فراخوان با رکورد ذخیره‌شده
    for f in ("status", "refunded_coins", "refund_fee_coins", "refunded_at"):
        setattr(item, f, getattr(locked, f))
    result.update(ok=True, code="rejected")

    why = f"\nدلیل: {reason}" if reason else ""
    if owner is not None:
        if result["refunded"]:
            text = (
                f"{m['noun']} «{item.title}» ({item_ref(item)}) توسط مدیر تأیید نشد.{why}\n"
                f"از {paid} سکهٔ پرداختی، {reject_fee_percent().normalize():f}٪ "
                f"({result['fee']} سکه) به‌عنوان کارمزد کسر و {result['refund']} سکه "
                f"به کیف پول شما بازگشت."
            )
        else:
            text = f"{m['noun']} «{item.title}» ({item_ref(item)}) توسط مدیر رد شد.{why}"
        _movement_ticket(
            request, admin, f"رد {m['noun']} — {item_ref(item)}", text,
            recipient_user_ids=[owner.id],
        )
    _close_approval_ticket(
        item, admin,
        f"{m['noun']} رد شد." + (f" بازگشت وجه: {result['refund']} سکه (کارمزد {result['fee']})."
                                  if result["refunded"] else ""),
        request,
    )
    return result


__all__ = ["open_approval_request", "approve_item", "reject_item", "item_ref",
           "reject_fee_percent", "WalletError"]
