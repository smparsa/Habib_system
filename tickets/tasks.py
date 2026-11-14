"""تسک‌های Celery سامانهٔ تیکت — ورودی‌های یکسان قابل فراخوانی از management command.

بدون broker (حالت EAGER) تسک‌ها هم‌زمان اجرا می‌شوند؛ با broker واقعی در صف می‌روند.
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("tickets.tasks")


@shared_task
def sla_sweep_task():
    from . import constants as C
    from . import services
    from .models import Ticket, TicketSLA
    from .sla import check_sla, supervisors_for

    changed = {"warned": 0, "breached": 0}
    open_tickets = Ticket.objects.filter(
        status__in=[C.STATUS_OPEN, C.STATUS_IN_PROGRESS, C.STATUS_WAITING_USER,
                    C.STATUS_USER_REPLIED])
    for ticket in open_tickets.iterator():
        warned, breached, level = check_sla(ticket)
        if warned:
            changed["warned"] += 1
            _notify_sla(ticket, C.EV_SLA_WARN, f"موعد پاسخ {ticket.number} نزدیک است")
            services.audit(None, "sla.warning", "Ticket", ticket.id,
                           meta={"number": ticket.number})
        if breached:
            changed["breached"] += 1
            _notify_sla(ticket, C.EV_SLA_BREACH,
                        f"SLA نقض شد (سطح {level}): {ticket.number}")
            services.audit(None, "sla.breached", "Ticket", ticket.id,
                           meta={"level": level, "number": ticket.number})
    return changed


def _notify_sla(ticket, event, title):
    from .notifications import enqueue
    from .sla import supervisors_for

    enqueue([u for u in supervisors_for(ticket)],
            event, title, body=f"{ticket.subject}", ticket=ticket)


@shared_task
def bulk_recipient_task(ticket_id, user_ids, chunk=500):
    """گیرنده‌سازی در پس‌زمینه برای فهرست‌های بزرگ (همان سرویس اتمیک)."""
    from . import services
    from .models import Ticket

    ticket = Ticket.objects.get(id=ticket_id)
    for start in range(0, len(user_ids), chunk):
        services.add_recipient_batch(ticket, user_ids[start:start + chunk])
    return len(user_ids)
