"""سمتِ خواندن: کوئری‌های ایندکس‌شده برای صندوق ورودی/فرستاده/ارجاع‌شده و آمار.

تمام کوئری‌ها select_related/prefetch دارند تا N+1 نباشد؛ pagination در ویو انجام
می‌شود (آیتم‌های سمت کاربر مرتب‌شده و برش خورده).
"""

from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from . import constants as C
from .models import Ticket, TicketAssignment, TicketRecipient


def _user_rows(user, box):
    """QuerySet گیرنده برای باکس‌های سمت کاربر (regular)."""
    rq = TicketRecipient.objects.filter(user=user, archived=False)
    mapping = {
        "inbox": rq.filter(is_author=False, is_staff_participant=False),
        "sent": rq.filter(is_author=True),
        "all": rq,
        "important": rq.filter(important=True),
        "unread": rq.filter(state=C.RECIPIENT_UNREAD),
        "resolved": rq.filter(ticket__status=C.STATUS_RESOLVED),
        "closed": rq.filter(ticket__status=C.STATUS_CLOSED),
        "archived": TicketRecipient.objects.filter(user=user, archived=True),
        "waiting": rq.filter(ticket__status__in=[
            C.STATUS_WAITING_USER, C.STATUS_USER_REPLIED, C.STATUS_IN_PROGRESS]),
    }
    return mapping.get(box, mapping["inbox"])


def center_entries(user, box="inbox", q="", status="", priority="", department=None,
                   order="-updated_at"):
    """آیتم‌های فیلترشده/جستجو/مرتب برای یک تب؛ خروجی لیست dict (برای صفحه‌بندی)."""
    from .permissions import is_staff_user

    is_staff = is_staff_user(user)
    if box == "magazine":
        rows = list(magazine_tickets(user))
        if q:
            q_low = q.lower()
            rows = [r for r in rows
                    if q_low in r.sender.mobile_number.lower()
                    or q_low in (r.sender.profile.full_name or "").lower()
                    or q_low in (r.post.text or "").lower()]
        return [{
            "mag": True,
            "mag_id": r.id,
            "ticket": r,
            "recipient": None,
            "my_state": "unread" if not r.is_read else "read",
            "sender_name": r.sender.profile.full_name
            if r.sender.profile else r.sender.mobile_number,
            "snippet": (r.post.text or "").strip()[:90],
            "kind_label": r.post.display_kind,
            "created_at": r.created_at,
        } for r in rows]

    if box in ("assigned", "waiting_me"):
        base = TicketAssignment.objects.filter(agent=user, is_active=True)
        if box == "waiting_me":
            base = base.filter(ticket__status__in=[
                C.STATUS_WAITING_USER, C.STATUS_USER_REPLIED, C.STATUS_IN_PROGRESS])
        if q:
            base = base.filter(Q(ticket__number__icontains=q) | Q(ticket__subject__icontains=q))
        if status:
            base = base.filter(ticket__status=status)
        if priority:
            base = base.filter(ticket__priority=priority)
        rows = list(base.select_related("ticket__category", "ticket__author__profile")
                    .order_by("-ticket__updated_at")[:200])
        return [{"ticket": r.ticket, "recipient": None, "my_state": None} for r in rows]

    rows_qs = _user_rows(user, box).select_related(
        "ticket__category", "ticket__author__profile"
    )
    if q:
        rows_qs = rows_qs.filter(
            Q(ticket__number__icontains=q) | Q(ticket__subject__icontains=q))
    if status:
        rows_qs = rows_qs.filter(ticket__status=status)
    if priority:
        rows_qs = rows_qs.filter(ticket__priority=priority)
    if department:
        rows_qs = rows_qs.filter(ticket__department_id=department)
    field = "updated_at" if order.startswith("-") else order
    sign = "-" if order.startswith("-") else ""
    rows_qs = rows_qs.order_by(sign + field)
    out = []
    for r in rows_qs:
        out.append({
            "ticket": r.ticket,
            "recipient": r,
            "my_state": r.state,
        })
    return out


def magazine_tickets(user):
    """فوروارد‌های مجله که برای کاربر ارسال شده‌اند."""
    from magazine.models import MagazineTicket
    return MagazineTicket.objects.filter(recipient=user).select_related(
        "sender__profile", "post", "post__author__profile"
    )


def my_recipient(user, ticket):
    return TicketRecipient.objects.filter(user=user, ticket=ticket).first()


def user_stats(user):
    """آمار کاربر برای هدر مرکز تیکت (شمردن سمت دیتابیس)."""
    rq = TicketRecipient.objects.filter(user=user, archived=False)
    return {
        "total": rq.count(),
        "unread": rq.filter(state=C.RECIPIENT_UNREAD, is_author=False).count(),
        "important": rq.filter(important=True).count(),
        "waiting": rq.filter(ticket__status__in=[
            C.STATUS_WAITING_USER, C.STATUS_USER_REPLIED, C.STATUS_IN_PROGRESS]).count(),
        "resolved": rq.filter(ticket__status=C.STATUS_RESOLVED).count(),
        "closed": rq.filter(ticket__status=C.STATUS_CLOSED).count(),
    }


def admin_stats():
    """KPI داشبورد مدیریتی."""
    base = Ticket.objects.all()
    open_ = base.filter(status=C.STATUS_OPEN)
    in_flow = base.filter(status__in=[C.STATUS_OPEN, C.STATUS_IN_PROGRESS])
    return {
        "total": base.count(),
        "open": open_.count(),
        "urgent": open_.filter(priority__in=["urgent", "critical"]).count(),
        "unassigned": in_flow.exclude(assignments__is_active=True).count(),
        "sla_breached": _sla_breached_count(),
        "waiting_user": base.filter(status=C.STATUS_WAITING_USER).count(),
        "resolved": base.filter(status=C.STATUS_RESOLVED).count(),
        "closed": base.filter(status=C.STATUS_CLOSED).count(),
        "statuses": list(
            base.values("status").annotate(c=Count("id")).order_by("status")),
        "priorities": list(
            base.values("priority").annotate(c=Count("id")).order_by("priority")),
        "by_day": list(
            base.filter(created_at__gte=timezone.now() - timedelta(days=14))
            .annotate(day=TruncDate("created_at")).values("day")
            .annotate(c=Count("id")).order_by("day")),
        "by_category": list(
            base.values("category__name_fa").annotate(c=Count("id"))
            .exclude(category__isnull=True).order_by("-c")[:10]),
        "by_city": list(
            base.values("author__profile__city").annotate(c=Count("id"))
            .exclude(author__profile__city="").order_by("-c")[:10]),
        "by_job": list(
            base.values("author__profile__job_title").annotate(c=Count("id"))
            .exclude(author__profile__job_title="").order_by("-c")[:10]),
        "by_dept": list(
            base.values("department__name_fa").annotate(c=Count("id"))
            .exclude(department__isnull=True).order_by("-c")[:10]),
    }


def _sla_breached_count():
    from .models import TicketSLA

    return TicketSLA.objects.filter(response_breached=True).count()
