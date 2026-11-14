"""لایهٔ سرویس‌های تیکت — منطق کسب‌وکار اینجاست، نه در ویوها.

تراکنش‌ها: ساخت تیکت + گیرنده‌سازی یکجا atomic است و idempotent (unique constraint
و تشخیص تکراری). همهٔ عملیات، رویداد حسابرسی ثبت می‌کنند.
"""

import logging

from django.db import transaction
from django.db.models import Count, Q as models_Q
from django.utils import timezone

from . import constants as C
from . import targeting, workflows
from .exceptions import PermissionDenied, StateError, TicketError
from .models import (
    Ticket, TicketAssignment, TicketAttachment, TicketAuditLog, TicketCategory,
    TicketDepartment, TicketMessage, TicketPriorityHistory, TicketRating,
    TicketRecipient, TicketStatusHistory, TicketTargetRule,
)
from .numbering import next_ticket_number
from .permissions import can_manage, can_reply, can_see_internal, is_staff_user

logger = logging.getLogger("tickets.services")


# --------------------------------------------------------------------------- #
# Audit
# --------------------------------------------------------------------------- #
def audit(actor, action, object_type, object_id=None, ip=None, user_agent="",
          meta=None, request=None):
    if request is not None:
        ip = ip or getattr(request, "client_ip", None) or _ip(request)
        user_agent = user_agent or request.META.get("HTTP_USER_AGENT", "")[:500]
    return TicketAuditLog.objects.create(
        actor=None if actor is None or getattr(actor, "is_anonymous", False) else actor,
        action=action, object_type=object_type, object_id=object_id,
        ip=ip, user_agent=user_agent, meta=meta or {},
    )


def _ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


# --------------------------------------------------------------------------- #
# Recipient resolution + creation
# --------------------------------------------------------------------------- #
def recipient_users_from_rules(rules, exclude_user_id=None):
    qs = targeting.resolve(rules, exclude_user_id=exclude_user_id)
    return qs.values_list("user_id", flat=True)


def _add_recipient(ticket, user, is_author=False, staff=False):
    lookup = {"user_id": user} if isinstance(user, int) else {"user": user}
    TicketRecipient.objects.get_or_create(
        ticket=ticket, **lookup,
        defaults={"is_author": is_author, "is_staff_participant": staff},
    )


def add_recipient_batch(ticket, user_ids, chunk_note=""):
    """گیرنده‌سازی دسته‌ای idempotent (برای تسک پس‌زمینهٔ فهرست‌های بزرگ)."""
    added = 0
    for uid in set(user_ids):
        _, created = TicketRecipient.objects.get_or_create(
            ticket=ticket, user_id=uid,
            defaults={"is_staff_participant": True}
        )
        added += 1 if created else 0
    if added:
        audit(None, C.ACT_RECIPIENT_ADDED, "Ticket", ticket.id,
              meta={"count": added, "note": chunk_note})
    return added


def _staff_users():
    from django.contrib.auth import get_user_model

    return get_user_model().objects.filter(is_active=True, is_staff=True)


# --------------------------------------------------------------------------- #
# Content moderation (sensitive words / phrases)
# --------------------------------------------------------------------------- #


def _guard_content(author, text, request=None, object_type="Ticket"):
    """مسدودکردن محتوای حساسِ کاربران عادی (کارکنان معاف‌اند).

    متن ممنوع هرگز ذخیره/لاگ نمی‌شود؛ فقط رویداد «content.blocked» با دسته‌ها
    ثبت و خطای فارسی به کاربر داده می‌شود تا متن را اصلاح کند.
    """
    if is_staff_user(author):
        return
    from .filtering import block_message, find_violations

    hits = find_violations(text)
    if hits:
        audit(
            author, C.ACT_CONTENT_BLOCKED, object_type, None, request=request,
            meta={"categories": sorted({h.category for h in hits})},
        )
        raise TicketError(block_message(hits))


# --------------------------------------------------------------------------- #
# Ticket creation
# --------------------------------------------------------------------------- #
def create_ticket(*, author, subject, description="", priority="normal",
                  category_code=None, department_id=None,
                  rules=None, specific_user_ids=None, due_at=None,
                  request=None, duplicate_window=120):
    """ساخت تیکت + (گیرنده‌سازی یا ارجاع به کارکنان) + SLA + پیام اول + اعلان.

    - rules (درخت AND/OR) → ارسال هدفمند به واجدها
    - بدون rules → تیکت پشتیبانی: گیرندگان، کارکنانِ فعالِ همان دپارتمان (یا همهٔ staff)
    """
    from .notifications import enqueue
    from .sla import create_sla

    subject = (subject or "").strip()
    if not subject:
        raise TicketError("موضوع تیکت الزامی است.")
    description = (description or "").strip()

    # پالایش محتوای حساس پیش از هر ساخت (موضوع + شرح)
    _guard_content(author, subject + "\n" + description, request=request)

    now = timezone.now()
    # ضداسپم: تیکت تکراریِ همان نویسنده در پنجرهٔ کوتاه
    if duplicate_window and Ticket.objects.filter(
        author=author, subject=subject, description=description,
        created_at__gte=now - timezone.timedelta(seconds=duplicate_window),
    ).exists():
        raise TicketError("تیکتی با همین موضوع در لحظات اخیر ثبت شده است؛ چند لحظه صبر کنید.")

    category = None
    if category_code:
        category = TicketCategory.objects.filter(code=category_code, is_active=True).first()
    department = TicketDepartment.objects.filter(id=department_id, is_active=True).first() \
        if department_id else None

    with transaction.atomic():
        ticket = Ticket.objects.create(
            author=author, number=next_ticket_number(), subject=subject,
            description=description, priority=priority, category=category,
            department=department, due_at=due_at,
        )
        # وضعیت SLA در لحظهٔ ساخت snapshot می‌شود
        create_sla(ticket)

        target_row = None
        eligible = None
        label = ""
        audience = "custom"
        if rules:
            rule_ids = recipient_users_from_rules(rules, exclude_user_id=author.id)
            eligible = len(set(rule_ids))
            label = targeting.label_for(rules)
            audience = rules.get("kind") or "custom"
        if specific_user_ids is not None:
            target_users = list(specific_user_ids)
            if rules is None:
                audience = C.AUD_USERS
                label = f"{len(target_users)} کاربر مشخص"
        elif rules:
            target_users = list(rule_ids)
        else:
            staff = list(_staff_users().values_list("id", flat=True))
            target_users = [u for u in staff if u != author.id]
            audience = C.AUD_ALL
            label = "کارکنان / دپارتمان"
        target_row = TicketTargetRule.objects.create(
            ticket=ticket, audience=audience, label=label,
            rules_json=rules or {}, eligible_count=eligible or len(target_users),
        )

        recipients_added = 0
        for uid in set(target_users):
            _add_recipient(ticket, uid)
            recipients_added += 1
        # فرستنده نیز یک گیرنده با وضعیت مستقل است
        TicketRecipient.objects.get_or_create(
            ticket=ticket, user=author, defaults={"is_author": True}
        )
        if target_row:
            target_row.recipient_count = recipients_added
            target_row.save(update_fields=["recipient_count"])

        # پیام نخست (متن شرح)
        msg = TicketMessage.objects.create(
            ticket=ticket, author=author, kind=C.MSG_NORMAL, body=description or subject,
        )

        # اعلان NEW_TICKET برای گیرندگانِ غیرنویسنده (in_app/email طبق ترجیح)
        enqueue(
            users=[r.user for r in ticket.recipients.exclude(user=author)],
            event=C.EV_NEW_TICKET,
            title=f"تیکت جدید: {ticket.number} — {subject}",
            body=description[:500], ticket=ticket, message=msg, actor=author,
        )

    audit(author, C.ACT_CREATED, "Ticket", ticket.id, request=request,
          meta={"number": ticket.number, "subject": subject})
    if recipients_added:
        audit(author, C.ACT_RECIPIENT_ADDED, "Ticket", ticket.id, request=request,
              meta={"count": recipients_added})
    return ticket, recipients_added


# --------------------------------------------------------------------------- #
# Conversation
# --------------------------------------------------------------------------- #
def _update_states_on_reply(ticket, author, is_internal):
    """به‌روزرسانی وضعیت مستقل گیرندگان هنگام پیام جدید."""
    rows = ticket.recipients.filter(user=author).first()
    if is_internal:
        return
    if is_staff_user(author):
        # پاسخ کارشناس → برای همهٔ متقاضیان (غیرکارکنان)، محتوای جدیدِ خوانده‌نشده
        ticket.recipients.filter(is_staff_participant=False).update(
            state=C.RECIPIENT_UNREAD, read_at=None)
    else:
        if rows:
            rows.state = C.RECIPIENT_REPLIED
            rows.replied_at = timezone.now()
            rows.save(update_fields=["state", "replied_at"])
        # بقیهٔ گیرنده‌ها همچنان مستقل‌اند؛ فقط نویسنده علامت می‌خورد


def add_message(ticket, author, body, kind=C.MSG_NORMAL, attachments=(),
                request=None, notify=True):
    from .notifications import enqueue
    from .sla import register_first_response

    if kind == C.MSG_INTERNAL_NOTE and not can_see_internal(author):
        raise PermissionDenied("فقط کارکنان می‌توانند یادداشت داخلی ثبت کنند.")
    if not can_reply(author, ticket):
        raise PermissionDenied("شما به این تیکت دسترسی ندارید.")
    body = (body or "").strip()
    if not body and not attachments:
        raise TicketError("پیام خالی است.")
    # پالایش محتوای حساس (فقط متن؛ پیوست جداگانه بررسی می‌شود)
    _guard_content(author, body, request=request, object_type="TicketMessage")

    with transaction.atomic():
        msg = TicketMessage.objects.create(
            ticket=ticket, author=author, kind=kind, body=body or "📎 پیوست"
        )
        if kind == C.MSG_NORMAL and is_staff_user(author):
            register_first_response(ticket)
            if ticket.status in (C.STATUS_OPEN, C.STATUS_WAITING_USER, C.STATUS_USER_REPLIED):
                _auto_transition(ticket, C.STATUS_IN_PROGRESS, author)
        elif kind == C.MSG_NORMAL and not is_staff_user(author):
            if ticket.status == C.STATUS_WAITING_USER:
                _auto_transition(ticket, C.STATUS_USER_REPLIED, author)

        _update_states_on_reply(ticket, author, kind == C.MSG_INTERNAL_NOTE)

        saved = []
        for af in attachments or []:
            saved.append(save_attachment(msg, af))

        if notify and kind != C.MSG_INTERNAL_NOTE:
            qs = ticket.recipients.exclude(user=author)
            if is_staff_user(author):
                qs = qs.filter(is_staff_participant=False)
            enqueue(
                users=[r.user for r in qs],
                event=C.EV_NEW_REPLY, title=f"پاسخ جدید در {ticket.number}",
                body=body[:500], ticket=ticket, message=msg, actor=author,
            )

    audit(author, C.ACT_MESSAGE, "TicketMessage", msg.id, request=request,
          meta={"ticket": ticket.id, "kind": kind})
    return msg


def save_attachment(message, upload):
    import hashlib

    from .validators import validate_upload

    validate_upload(upload)
    content = upload.read()
    sha = hashlib.sha256(content).hexdigest()
    upload.seek(0)
    att = TicketAttachment(
        message=message, file=upload, name=upload.name,
        size=len(content), mime=upload.content_type or "", sha256=sha,
    )
    att.save()
    audit(message.author if hasattr(message, "author") else None,
          C.ACT_ATTACHMENT, "TicketAttachment", att.id,
          meta={"ticket": message.ticket_id})
    return att


def edit_message(message, editor, new_body):
    from .permissions import can_manage

    if message.author_id != editor.id and not can_manage(editor, message.ticket):
        raise PermissionDenied("فقط نویسنده یا کارشناس مجاز می‌تواند پیام را ویرایش کند.")
    message.body = new_body
    message.edited_at = timezone.now()
    message.save(update_fields=["body", "edited_at"])
    audit(editor, C.ACT_MESSAGE_EDIT, "TicketMessage", message.id,
          meta={"ticket": message.ticket_id})
    return message


def _auto_transition(ticket, to_status, actor):
    """انتقال وضعیت خودکار هنگام پاسخ‌ها (بدون خطای کاربر)."""
    if ticket.status == to_status:
        return
    from .workflows import transition

    try:
        transition(ticket, to_status, actor)
        ticket.save(update_fields=["status", "resolved_at", "closed_at",
                                   "reopened_count", "updated_at"])
    except StateError:
        pass


# --------------------------------------------------------------------------- #
# Workflow actions
# --------------------------------------------------------------------------- #
def change_status(ticket, actor, to_status, note="", request=None):
    from .notifications import notify_participants

    if not can_manage(actor, ticket):
        raise PermissionDenied("شما مجاز به تغییر وضعیت این تیکت نیستید.")
    with transaction.atomic():
        ticket, changed = workflows.transition(ticket, to_status, actor,
                                               note=note, request=request)
        if changed:
            ticket.save()
            _score_on_resolution(ticket, to_status)
    if changed:
        audit(actor, C.ACT_STATUS, "Ticket", ticket.id, request=request,
              meta={"to": to_status, "note": note})
        notify_participants(
            ticket, C.EV_STATUS if to_status != C.STATUS_RESOLVED else C.EV_RESOLVED,
            f"{ticket.number}: وضعیت به «{C.STATUS_LABELS[to_status]}» تغییر کرد",
            exclude=[actor])
    return ticket


def reopen(ticket, actor, note="", request=None):
    from .notifications import notify_participants

    with transaction.atomic():
        ticket, changed = workflows.transition(ticket, C.STATUS_OPEN, actor, note=note,
                                               request=request)
        if changed:
            ticket.save()
    if changed:
        notify_participants(ticket, C.EV_REOPENED, f"{ticket.number} بازگشایی شد",
                            exclude=[actor])
    return ticket


def change_priority(ticket, actor, priority, request=None):
    from .sla import create_sla

    if not can_manage(actor, ticket):
        raise PermissionDenied("مجوز تغییر اولویت ندارید.")
    old = ticket.priority
    if old == priority:
        return ticket
    with transaction.atomic():
        TicketPriorityHistory.objects.create(
            ticket=ticket, from_priority=old, to_priority=priority, actor=actor)
        ticket.priority = priority
        ticket.save(update_fields=["priority", "updated_at"])
        create_sla(ticket)  # snapshot تازه بر اساس اولویت جدید
    audit(actor, C.ACT_PRIORITY, "Ticket", ticket.id, request=request,
          meta={"from": old, "to": priority})
    return ticket


def _score_on_resolution(ticket, to_status):
    """پل امتیازدهی: بدون تغییر منطق مالیِ سکه/کیف پول."""
    try:
        from accounts.scoring import award

        if to_status == C.STATUS_RESOLVED:
            for r in ticket.recipients.filter(is_author=True, is_staff_participant=False):
                award(r.user.profile, C.SCORE_RESOLVED_USER, reason=f"ticket {ticket.number}")
            agent = ticket.assigned_to
            if agent:
                award(agent.profile, C.SCORE_RESOLVED_AGENT, reason=f"ticket {ticket.number}")
    except Exception:  # noqa: BLE001 - امتیاز نباید گردش کار را بشکند
        logger.exception("scoring bridge failed")


# --------------------------------------------------------------------------- #
# Assignment
# --------------------------------------------------------------------------- #
def choose_agent(ticket, kind):
    from .permissions import eligible_agents_for

    agents = eligible_agents_for(ticket)
    if not agents.exists():
        from django.contrib.auth import get_user_model

        agents = get_user_model().objects.filter(is_staff=True, is_active=True)
    if not agents.exists():
        return None
    if kind == "round_robin":
        last = (TicketAssignment.objects.filter(ticket__department=ticket.department,
                                                kind=kind, is_active=True)
                .order_by("-assigned_at").first())
        qs = agents.order_by("id")
        if last:
            qs = agents.filter(id__gt=last.agent_id).order_by("id")
            if not qs.exists():
                qs = agents.order_by("id")
        return qs.first()
    # workload: کمترین ارجاع فعال
    return (agents.annotate(active_count=Count(
        "ticket_assignments", filter=models_Q(ticket_assignments__is_active=True)))
        .order_by("active_count", "id").first())


def assign(ticket, actor, agent=None, kind="manual", request=None):
    from .notifications import enqueue

    if not agent:
        if not can_manage(actor, ticket):
            raise PermissionDenied("مجوز ارجاع ندارید.")
        agent = choose_agent(ticket, kind)
        if agent is None:
            raise TicketError("کارشناس در دسترس نیست.")
    else:
        from .permissions import can_assign

        if not can_assign(actor, ticket):
            raise PermissionDenied("مجوز ارجاع ندارید.")

    with transaction.atomic():
        TicketAssignment.objects.filter(ticket=ticket, is_active=True).update(is_active=False)
        TicketAssignment.objects.create(
            ticket=ticket, agent=agent, assigned_by=actor, kind=kind)
        TicketRecipient.objects.get_or_create(
            ticket=ticket, user=agent, defaults={"is_staff_participant": True})
        TicketMessage.objects.create(
            ticket=ticket, author=actor, kind=C.MSG_ASSIGNMENT,
            body=f"ارجاع به {agent}",
        )
        ticket.department = ticket.department or _dept_of(actor, ticket)
        ticket.save(update_fields=["department", "updated_at"])
    audit(actor, C.ACT_ASSIGNMENT, "Ticket", ticket.id, request=request,
          meta={"agent": agent.id, "kind": kind})
    enqueue([agent], C.EV_ASSIGNED, f"تیکت {ticket.number} به شما ارجاع شد",
            ticket=ticket, actor=actor)
    return agent


def unassign(ticket, actor, request=None):
    if not can_manage(actor, ticket):
        raise PermissionDenied("مجوز برداشتن ارجاع ندارید.")
    with transaction.atomic():
        TicketAssignment.objects.filter(ticket=ticket, is_active=True).update(is_active=False)
        TicketMessage.objects.create(ticket=ticket, author=actor, kind=C.MSG_ASSIGNMENT,
                                     body="ارجاع برداشته شد")
    audit(actor, C.ACT_ASSIGNMENT, "Ticket", ticket.id, request=request, meta={"agent": None})


def _dept_of(user, ticket):
    from .permissions import department_ids

    d = department_ids(user)
    if d:
        return TicketDepartment.objects.filter(id__in=d).first()
    return None


# --------------------------------------------------------------------------- #
# Recipient actions (user side)
# --------------------------------------------------------------------------- #
def mark_read(ticket, user):
    row = TicketRecipient.objects.filter(ticket=ticket, user=user).first()
    if row and row.state != C.RECIPIENT_REPLIED:
        changed = row.state != C.RECIPIENT_READ
        row.state = C.RECIPIENT_READ
        row.read_at = timezone.now()
        row.save(update_fields=["state", "read_at"])
        return changed
    return False


def set_flag(ticket, user, important=None, archived=None):
    row = TicketRecipient.objects.filter(ticket=ticket, user=user).first()
    if row is None:
        raise PermissionDenied("این تیکت برای شما نیست.")
    if important is not None:
        row.important = important
    if archived is not None:
        row.archived = archived
    row.save(update_fields=["important", "archived", "updated_at"])
    return row


def rate_ticket(ticket, user, stars, response_quality=None, resolution_quality=None,
                comment="", request=None):
    if not TicketRecipient.objects.filter(ticket=ticket, user=user).exists():
        raise PermissionDenied("فقط شرکت‌کننده می‌تواند امتیاز دهد.")
    if ticket.status not in (C.STATUS_RESOLVED, C.STATUS_CLOSED):
        raise TicketError("امتیازدهی فقط پس از حل/بستن تیکت ممکن است.")
    rating, created = TicketRating.objects.get_or_create(
        ticket=ticket, user=user,
        defaults={"stars": stars, "response_quality": response_quality,
                  "resolution_quality": resolution_quality, "comment": comment},
    )
    if not created:
        rating.stars = stars
        rating.response_quality = response_quality
        rating.resolution_quality = resolution_quality
        rating.comment = comment
        rating.save()
    audit(user, "ticket.rated", "Ticket", ticket.id, request=request,
          meta={"stars": stars})
    return rating


# --------------------------------------------------------------------------- #
# Stats refresh for target rules (analytics §44)
# --------------------------------------------------------------------------- #
def refresh_target_stats(ticket):
    TicketTargetRule.objects.filter(ticket=ticket).update(
        read_count=ticket.recipients.filter(state=C.RECIPIENT_READ).count()
        + ticket.recipients.filter(state=C.RECIPIENT_REPLIED).count(),
        reply_count=ticket.recipients.filter(state=C.RECIPIENT_REPLIED).count(),
        resolved_count=ticket.recipients.filter(state=C.RECIPIENT_RESOLVED).count(),
    )


# --------------------------------------------------------------------------- #
# Bulk operations (staff)
# --------------------------------------------------------------------------- #
def bulk_apply(actor, ticket_ids, action, **kwargs):
    """عملیات گروهی با تأیید: status/priority/assign/close/archive."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    results = {"ok": 0, "errors": []}
    for tid in ticket_ids:
        ticket = Ticket.objects.filter(id=tid).first()
        if ticket is None or not can_manage(actor, ticket):
            results["errors"].append(f"#{tid}: بدون مجوز")
            continue
        try:
            if action == "status":
                change_status(ticket, actor, kwargs.get("status"))
            elif action == "priority":
                change_priority(ticket, actor, kwargs.get("priority"))
            elif action == "assign":
                agent = User.objects.filter(id=kwargs.get("agent_id")).first()
                assign(ticket, actor, agent=agent)
            elif action == "close":
                change_status(ticket, actor, C.STATUS_CLOSED)
            elif action == "unassign":
                unassign(ticket, actor)
            results["ok"] += 1
        except TicketError as exc:
            results["errors"].append(f"{ticket.number}: {exc}")
    return results
