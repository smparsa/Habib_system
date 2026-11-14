"""مجوزهای سامانهٔ تیکت — نقش و کنترل دسترسی شیء‌محور.

اصل امنیتی: نقشِ «admin» برای هر کارمند is_staff به‌صورت ضمنی اعطا نمی‌شود مگر
اینکه سطحِ دسترسیِ او صریحاً درخواست شود؛ اعضای دپارتمان‌ها نقش خود را از
TicketDepartmentMember می‌گیرند. کاربرِ عادی فقط تیکت‌هایی را می‌بیند که
گیرنده/فرستندهٔ آن است.
"""

from . import constants as C
from .models import TicketDepartmentMember, TicketRecipient

ROLE_RANK = {C.ROLE_USER: 0, C.ROLE_AGENT: 1, C.ROLE_SUPERVISOR: 2,
             C.ROLE_DEPT_MANAGER: 3, C.ROLE_ADMIN: 4, C.ROLE_SUPER_ADMIN: 5}


def role_of(user):
    if not user.is_authenticated:
        return C.ROLE_USER
    if user.is_superuser:
        return C.ROLE_SUPER_ADMIN
    member = (
        TicketDepartmentMember.objects.filter(user=user)
        .order_by("-role")
        .values_list("role", flat=True)
        .first()
    )
    if member:
        return member
    if user.is_staff:
        return C.ROLE_ADMIN
    return C.ROLE_USER


def is_staff_user(user):
    return ROLE_RANK[role_of(user)] >= ROLE_RANK[C.ROLE_AGENT]


def department_ids(user):
    return list(
        TicketDepartmentMember.objects.filter(user=user).values_list("department_id", flat=True)
    )


def is_participant(user, ticket):
    return TicketRecipient.objects.filter(ticket=ticket, user=user).exists()


def _ticket_department_ok(user, ticket):
    """کارشناس/سرپرست دپارتمان فقط تیکت همان دپارتمان (یا ارجاع‌شده به خودش)."""
    role = role_of(user)
    if role in (C.ROLE_SUPER_ADMIN, C.ROLE_ADMIN):
        return True
    depts = department_ids(user)
    if ticket.department_id in depts:
        return True
    assigned = ticket.assignments.filter(is_active=True, agent=user).exists()
    if role in (C.ROLE_AGENT, C.ROLE_SUPERVISOR, C.ROLE_DEPT_MANAGER) and assigned:
        return True
    return False


def can_view(user, ticket):
    if not user.is_authenticated:
        return False
    if is_participant(user, ticket):
        return True
    if is_staff_user(user):
        return _ticket_department_ok(user, ticket)
    return False


def can_manage(user, ticket):
    """تغییر وضعیت/ارجاع/بستن: فقط کارکنان دارای مجوزِ صریح."""
    if not user.is_authenticated:
        return False
    return is_staff_user(user) and _ticket_department_ok(user, ticket)


def can_assign(user, ticket=None):
    role = role_of(user)
    if role in (C.ROLE_SUPER_ADMIN, C.ROLE_ADMIN, C.ROLE_SUPERVISOR, C.ROLE_DEPT_MANAGER):
        return True
    if ticket is not None:
        return is_staff_user(user) and _ticket_department_ok(user, ticket)
    return False


def can_reply(user, ticket):
    if not user.is_authenticated:
        return False
    if is_participant(user, ticket):
        return True
    return can_manage(user, ticket)


def can_see_internal(user):
    return is_staff_user(user)


def visible_messages_qs(user, ticket):
    qs = ticket.messages.all()
    if not can_see_internal(user):
        qs = qs.exclude(kind=C.MSG_INTERNAL_NOTE)
    return qs


def visible_recipients_qs(user, ticket):
    """حفظ حریم خصوصی: گیرندگانِ عادی لیست گیرندگان را نمی‌بینند."""
    if is_staff_user(user):
        return ticket.recipients.select_related("user__profile")
    return ticket.recipients.none()


def require_staff(user):
    return is_staff_user(user)


def eligible_agents_for(ticket):
    """کارشناسانِ در دسترس برای ارجاع خودکار/چرخشی یک تیکت."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    dept = ticket.department
    ids = TicketDepartmentMember.objects.filter(department=dept).values_list("user_id", flat=True)
    return User.objects.filter(is_active=True, pk__in=list(ids))
