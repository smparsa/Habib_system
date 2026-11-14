"""سرویس گردش کار تیکت — پیکربندی‌مبنا، نه hard-code در ویوها.

جریان پیش‌فرض:
open → in_progress → waiting_user → user_replied → in_progress → resolved → closed
reopen از resolved/closed به open (با کنترل مجوز).
"""

from django.db import transaction
from django.utils import timezone

from . import constants as C
from .exceptions import StateError

TRANSITIONS = {
    # از هر وضعیت، به کدام وضعیت‌ها می‌توان رفت (و چه کسی می‌تواند)
    C.STATUS_OPEN: {
        C.STATUS_IN_PROGRESS: "staff",
        C.STATUS_WAITING_USER: "staff",
        C.STATUS_RESOLVED: "staff",
        C.STATUS_CLOSED: "staff",
    },
    C.STATUS_IN_PROGRESS: {
        C.STATUS_WAITING_USER: "staff",
        C.STATUS_RESOLVED: "staff",
        C.STATUS_CLOSED: "staff",
    },
    C.STATUS_WAITING_USER: {
        C.STATUS_IN_PROGRESS: "staff",
        C.STATUS_RESOLVED: "staff",
        C.STATUS_CLOSED: "staff",
    },
    C.STATUS_USER_REPLIED: {
        C.STATUS_IN_PROGRESS: "staff",
        C.STATUS_RESOLVED: "staff",
        C.STATUS_CLOSED: "staff",
    },
    C.STATUS_RESOLVED: {
        C.STATUS_CLOSED: "staff",
        C.STATUS_OPEN: "any_participant",  # reopen
    },
    C.STATUS_CLOSED: {
        C.STATUS_OPEN: "any_participant",  # reopen
    },
}

# نشان‌های زمانی خودکار هنگام ثبت وضعیت
AUTO_TIMESTAMPS = {
    C.STATUS_RESOLVED: "resolved_at",
    C.STATUS_CLOSED: "closed_at",
}


def allowed_to_status(current):
    return list(TRANSITIONS.get(current, {}).keys())


def can_transition_to(user, ticket, to_status):
    current = ticket.status
    allowed = TRANSITIONS.get(current, {}).get(to_status)
    if not allowed:
        return False
    if allowed == "any_participant":
        from .permissions import can_view

        return can_view(user, ticket)
    from .permissions import can_manage

    return can_manage(user, ticket)


def transition(ticket, to_status, actor, note="", ip=None, user_agent="", request=None):
    """اجرای انتقال وضعیت با ثبت تاریخچه و بازکردن مجدد؛ در تراکنش صدا زده شود."""
    from .models import TicketStatusHistory

    if request is not None:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = ip or (xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", ""))
        user_agent = user_agent or request.META.get("HTTP_USER_AGENT", "")[:500]

    if ticket.status == to_status:
        return ticket, False
    if not can_transition_to(actor, ticket, to_status):
        raise StateError("این انتقال وضعیت برای شما مجاز نیست.")

    old = ticket.status
    from_status = old
    ticket.status = to_status

    ts_field = AUTO_TIMESTAMPS.get(to_status)
    if ts_field == "resolved_at":
        ticket.resolved_at = ticket.resolved_at or timezone.now()
    elif ts_field == "closed_at":
        ticket.closed_at = timezone.now()
    # بازگشایی
    if to_status == C.STATUS_OPEN and old in (C.STATUS_RESOLVED, C.STATUS_CLOSED):
        ticket.reopened_count = (ticket.reopened_count or 0) + 1
        ticket.resolved_at = None
        ticket.closed_at = None
        from .services import audit  # ایمپورت محلی برای اجتناب از سیکل

        audit(actor, C.ACT_REOPENED, "Ticket", ticket.id, ip=ip,
              user_agent=user_agent, meta={"note": note, "ticket": ticket.number})

    TicketStatusHistory.objects.create(
        ticket=ticket, from_status=from_status, to_status=to_status,
        actor=None if actor.is_anonymous else actor, note=note,
    )
    return ticket, True


def apply_on_message(services_ref, ticket, user, kind):
    """در هنگام پیام‌ها، وضعیتِ تیکت را طبق نقش نویسنده به‌روز می‌کند."""
    from . import constants as C
    from .permissions import is_staff_user

    if is_staff_user(user) and kind == C.MSG_NORMAL:
        target = C.STATUS_IN_PROGRESS if ticket.status != C.STATUS_IN_PROGRESS else None
        if target and ticket.status in (C.STATUS_OPEN, C.STATUS_WAITING_USER, C.STATUS_USER_REPLIED):
            return target
    elif not is_staff_user(user) and kind == C.MSG_NORMAL:
        if ticket.status == C.STATUS_WAITING_USER:
            return C.STATUS_USER_REPLIED
        if ticket.status in (C.STATUS_OPEN,):
            return C.STATUS_IN_PROGRESS
    return None
