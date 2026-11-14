"""سرویس SLA — موعدها، اولین پاسخ، نقض و ارتقا.

جدول پیش‌فرض ساعت‌ها در constants.SLA_HOURS است و دپارتمان می‌تواند لغو کند
(TicketDepartment.sla_override_hours). همهٔ مقادیر در زمان ساخت تیکت snapshot می‌شوند.
"""

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from . import constants as C
from .models import TicketSLA

logger = logging.getLogger("tickets.sla")


def hours_for(ticket):
    hours = dict(C.SLA_HOURS)
    if ticket.department_id:
        override = ticket.department.sla_override_hours or {}
        hours.update({k: float(v) for k, v in override.items() if v})
    return {
        "response": hours.get(ticket.priority, hours["normal"]),
        "resolution": max(hours.get(ticket.priority, hours["normal"]) * 2, hours["normal"]),
    }


def create_sla(ticket):
    h = hours_for(ticket)
    now = timezone.now()
    sla, _ = TicketSLA.objects.get_or_create(
        ticket=ticket,
        defaults={
            "response_deadline": now + timedelta(hours=h["response"]),
            "resolution_deadline": now + timedelta(hours=h["resolution"]),
        },
    )
    return sla


def register_first_response(ticket, at=None):
    """نخستین پاسخ کارشناس (غیرسیستمی) را ثبت می‌کند."""
    sla = TicketSLA.objects.filter(ticket=ticket).first() or create_sla(ticket)
    if sla.first_response_at is None:
        sla.first_response_at = at or timezone.now()
        sla.save(update_fields=["first_response_at"])
    return sla


def check_sla(ticket, now=None):
    """
    بررسی نقض/هشدار؛ برمی‌گرداند (warned, breached, escalation_level)
    تا caller اعلان/audit را صادر کند. خودش فقط flags را به‌روز می‌کند.
    """
    sla = TicketSLA.objects.filter(ticket=ticket).first()
    if sla is None:
        return (False, False, 0)
    now = now or timezone.now()
    changed_warn = changed_breach = False
    if not sla.warn_sent and sla.response_deadline and sla.response_deadline > now:
        if (sla.response_deadline - now).total_seconds() <= C.SLA_WARN_BEFORE_MIN * 60:
            sla.warn_sent = True
            changed_warn = True
    if sla.response_deadline and now >= sla.response_deadline and not sla.response_breached:
        sla.response_breached = True
        sla.escalation_level += 1
        changed_breach = True
    if sla.resolution_deadline and now >= sla.resolution_deadline and not sla.resolution_breached:
        sla.resolution_breached = True
        sla.escalation_level += 1
        changed_breach = True
    if changed_warn or changed_breach:
        sla.save(update_fields=["warn_sent", "response_breached",
                                "resolution_breached", "escalation_level"])
    return changed_warn, changed_breach, sla.escalation_level


def supervisors_for(ticket):
    """گیرندگان اطلاع‌رسانی ارتقا: مدیر/سرپرست دپارتمان + ادمین‌ها."""
    User = get_user_model()
    ids = set()
    if ticket.department_id:
        ids.update(
            ticket.department.memberships.filter(
                role__in=(C.ROLE_SUPERVISOR, C.ROLE_DEPT_MANAGER)
            ).values_list("user_id", flat=True)
        )
    if not ids:
        ids.update(User.objects.filter(is_staff=True, is_active=True).values_list("id", flat=True))
    return User.objects.filter(id__in=ids, is_active=True)
