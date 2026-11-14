"""ویوهای مرکز تیکت — نازک؛ منطق در سرویس/سلکتور است."""

import csv
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied as AccessDenied
from django.db.models import Count, Q as ModelsQ
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from django.utils import timezone

from accounting.jalali import en_to_fa, gregorian_to_jalali

from . import constants as C
from . import selectors, services, targeting, workflows
from .exceptions import PermissionDenied, TicketError
from .forms import CreateTicketForm, RatingForm
from .models import (
    Ticket,
    TicketAudience,
    TicketCategory,
    TicketDepartment,
    TicketMessage,
    TicketRecipient,
)
from .permissions import (
    can_manage, can_reply, can_view, department_ids, is_staff_user, role_of,
)

BOXES = ("inbox", "sent", "assigned", "waiting", "waiting_me", "important",
         "unread", "resolved", "closed", "archived", "all", "magazine")


def _staff_only(view):
    from functools import wraps

    @login_required(login_url="core:index")
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not is_staff_user(request.user):
            messages.error(request, "این بخش مخصوص کارکنان است.")
            return redirect("tickets:center")
        return view(request, *args, **kwargs)

    return wrapper


def _parse_audience(post, role):
    """تبدیل ورودی‌های فرم به (rules|None, error).

    - «saved:<id>»: جامعهٔ هدفِ تعریف‌شده توسط ادمین — ارسال انبوه برای همهٔ کاربران مجاز است
      (ادمین کنترل می‌کند چه جامعه‌هایی ساخته و فعال شود).
    - انتخاب دستی: کاربرِ عادی فقط «کاربر مشخص»؛ سایر هدف‌گذاری‌ها ویژهٔ کارکنان.
    """
    audience = (post.get("audience") or "").strip()
    if not audience:
        # پشتیبانی → بدون مخاطب: گیرندگان کارکنان
        return None, None
    # نام‌های کوتاهِ فرم (level/score) ← ثابت‌های رسمی (user_level/user_score)
    audience = {"level": C.AUD_LEVEL, "score": C.AUD_SCORE}.get(audience, audience)
    if audience.startswith("saved:") and audience.split(":", 1)[1].isdigit():
        aud = TicketAudience.objects.filter(pk=int(audience.split(":", 1)[1]),
                                            is_active=True).first()
        if aud is None:
            return None, "جامعهٔ هدف انتخاب‌شده در دسترس نیست (شاید غیرفعال شده باشد)."
        if not aud.rules:
            return None, "قواعد جامعهٔ هدف انتخاب‌شده خالی است."
        rules = dict(aud.rules)
        rules.setdefault("label", aud.name)
        rules["kind"] = aud.kind
        return rules, None
    allowed_staff = {C.AUD_ALL, C.AUD_JOB, C.AUD_COUNTRY, C.AUD_PROVINCE, C.AUD_CITY,
                     C.AUD_RADIUS, C.AUD_GROUP, C.AUD_LEVEL, C.AUD_SCORE, C.AUD_USERS,
                     C.AUD_MOBILE_PREFIX, C.AUD_AGE}
    allowed_user = {C.AUD_USERS}
    if audience not in (allowed_staff if role != C.ROLE_USER else allowed_user):
        return None, "انتخاب نوع مخاطب مجاز نیست."

    def split(v):
        return [x.strip() for x in (v or "").replace("，", ",").split(",") if x.strip()]

    leaf = {"kind": audience}
    if audience in (C.AUD_JOB, C.AUD_COUNTRY, C.AUD_PROVINCE, C.AUD_CITY,
                    C.AUD_MOBILE_PREFIX):
        leaf["values"] = split(post.get("location") or post.get("jobs") or
                               post.get("geo_values") or post.get("values"))
        if not leaf["values"]:
            return None, "مقدار هدف را وارد کنید."
    elif audience == C.AUD_RADIUS:
        leaf.update(lat=post.get("lat"), lng=post.get("lng"), km=post.get("km") or 1)
    elif audience == C.AUD_LEVEL:
        leaf["value"] = post.get("level") or 0
    elif audience == C.AUD_SCORE:
        leaf["value"] = post.get("score") or 0
    elif audience == C.AUD_GROUP:
        leaf["values"] = post.getlist("groups") or split(post.get("groups"))
    elif audience == C.AUD_USERS:
        nids = [ln.strip() for ln in post.get("nids", "").splitlines() if ln.strip()]
        from accounts.models import Profile

        found = list(Profile.objects.filter(national_id__in=nids).values_list("user_id", flat=True))
        if not found:
            return None, "هیچ عضوی با این کد ملی‌ها یافت نشد."
        leaf["values"] = found
    elif audience == C.AUD_AGE:
        age_min = post.get("age_min")
        age_max = post.get("age_max")
        if not age_min and not age_max:
            return None, "بازهٔ سنی (حداقل یا حداکثر) را وارد کنید."
        leaf["age_min"] = age_min or None
        leaf["age_max"] = age_max or None
    return {"logic": "and", "items": [leaf]}, None


@login_required(login_url="core:index")
def center_view(request):
    box = request.GET.get("box", "inbox")
    if box not in BOXES:
        box = "inbox"
    q = request.GET.get("q", "")
    status = request.GET.get("status", "")
    priority = request.GET.get("priority", "")
    page = max(1, int(request.GET.get("page", 1)))
    per_page = 15

    rows = selectors.center_entries(request.user, box=box, q=q, status=status,
                                    priority=priority)
    total = len(rows)
    pages = max(1, -(-total // per_page))
    page = min(page, pages)
    start = (page - 1) * per_page
    entries = rows[start:start + per_page]
    for e in entries:
        if e.get("mag"):
            continue
        e["status_label"] = C.STATUS_LABELS.get(e["ticket"].status, e["ticket"].status)
        e["prio_label"] = C.PRIORITY_LABELS.get(e["ticket"].priority, e["ticket"].priority)
        e["category_label"] = e["ticket"].category.name_fa if e["ticket"].category else ""
    # صندوق «فرستاده»: آمار وضعیت ارسال (ارسال ✓ / دیده‌شده ✓✓) برای هر تیکت انبوه
    if box == "sent":
        tids = [e["ticket"].id for e in entries]
        agg = {
            r["ticket_id"]: (r["cnt"], r["read"])
            for r in TicketRecipient.objects.filter(ticket_id__in=tids, is_author=False)
            .values("ticket_id")
            .annotate(cnt=Count("id"), read=Count("id", filter=ModelsQ(
                state__in=[C.RECIPIENT_READ, C.RECIPIENT_REPLIED,
                           C.RECIPIENT_RESOLVED, C.RECIPIENT_CLOSED])))
        }
        for e in entries:
            e["recipient_count"], e["read_count"] = agg.get(e["ticket"].id, (0, 0))
    counts = selectors.user_stats(request.user)
    # افزودن آمار تیکت‌های مجله
    mag_tickets = selectors.magazine_tickets(request.user)
    counts["mag_total"] = mag_tickets.count()
    counts["mag_unread"] = mag_tickets.filter(is_read=False).count()

    return render(request, "tickets/center.html", {
        "box": box, "boxes": BOXES, "q": q, "status": status, "priority": priority,
        "entries": entries, "counts": counts, "page": page, "pages": pages,
        "is_staff": is_staff_user(request.user),
        "status_choices": [(s, C.STATUS_LABELS[s]) for s in C.STATUSES],
        "priority_choices": [(p, C.PRIORITY_LABELS[p]) for p in C.PRIORITIES],
    })


@login_required(login_url="core:index")
def create_view(request):
    form = CreateTicketForm()
    is_staff = is_staff_user(request.user)
    if request.method == "POST":
        form = CreateTicketForm(request.POST)
        rules = None
        error = None
        if form.is_valid():
            data = form.cleaned_data
            rules, error = _parse_audience(request.POST, role_of(request.user))
            if error:
                messages.error(request, error)
            else:
                try:
                    ticket, count = services.create_ticket(
                        author=request.user, subject=data["subject"],
                        description=data["description"], priority=data["priority"],
                        category_code=data["category"] or None,
                        rules=rules, request=request,
                    )
                    messages.success(
                        request,
                        f"تیکت {ticket.number} ایجاد شد." +
                        (f" برای {count} گیرنده ارسال شد." if count else ""))
                    return redirect("tickets:detail", number=ticket.number)
                except TicketError as exc:
                    messages.error(request, str(exc))
        else:
            messages.error(request, "لطفاً فرم را به‌درستی تکمیل کنید.")

    return render(request, "tickets/create.html", {
        "form": form, "is_staff": is_staff,
        "categories": TicketCategory.objects.filter(is_active=True),
        "priority_choices": [(p, C.PRIORITY_LABELS[p]) for p in C.PRIORITIES],
        "radius_choices": [(round(m / 1000.0, 4), f"{m} متر") for m in targeting.RADIUS_METERS],
        "groups": __import__("accounts.models", fromlist=["UserGroup"]).UserGroup.objects
        .filter(is_active=True),
        "saved_audiences": TicketAudience.objects.filter(is_active=True),
    })


@login_required(login_url="core:index")
def detail_view(request, number):
    ticket = get_object_or_404(Ticket, number=number)
    if not can_view(request.user, ticket):
        raise AccessDenied("شما به این تیکت دسترسی ندارید.")
    can_see_note = is_staff_user(request.user)

    draft_reply = ""
    if request.method == "POST":
        action = request.POST.get("action", "")
        try:
            _handle_action(request, ticket, action)
            return redirect("tickets:detail", number=ticket.number)
        except (TicketError, PermissionDenied) as exc:
            messages.error(request, str(exc))
            # پاسخ/یادداشتِ مسدودشده (مثلاً شامل واژهٔ حساس): متن کاربر حفظ می‌شود
            # تا بتواند همان‌جا اصلاحش کند و چیزی از دست نرود.
            if action not in ("reply", "note"):
                return redirect("tickets:detail", number=ticket.number)
            draft_reply = request.POST.get("body", "")

    # نشانه‌گذاری خوانده برای گیرنده
    services.mark_read(ticket, request.user)
    conversation = _visible(ticket, request.user)
    my_rec = selectors.my_recipient(request.user, ticket)
    assignment = ticket.current_assignment()

    # تیکت‌های درخواست خرید/فروش سکه: سفارش مرتبط (با کد WAL-... در موضوع) برای
    # میان‌برِ «بررسی در پنل مدیریت» — فقط برای کارکنان.
    wallet_order = None
    if is_staff_user(request.user):
        from wallet.models import CoinOrder

        m = re.search(r"WAL-\d{4}-\d+", ticket.subject or "")
        if m:
            wallet_order = CoinOrder.objects.filter(code=m.group(0)).first()

    # تیکتِ «درخواست تأیید تبلیغ/اسلایدشو»: دکمه‌های تأیید/رد مستقیم در تیکت (فقط کارکنان)
    approval_item, approval_kind, approval_fee = None, "", ""
    if is_staff_user(request.user):
        approval_item, approval_kind = _approval_item_for(ticket)
        if approval_item is not None:
            from ads.approvals import reject_fee_percent

            approval_fee = f"{reject_fee_percent().normalize():f}"

    rating_form = None
    can_rate = (ticket.status in (C.STATUS_RESOLVED, C.STATUS_CLOSED)
                and selectors.my_recipient(request.user, ticket) is not None
                and not ticket.ratings.filter(user=request.user).exists()
                and not is_staff_user(request.user))
    if can_rate:
        rating_form = RatingForm()

    transitions = [
        (s, C.STATUS_LABELS[s]) for s in workflows.allowed_to_status(ticket.status)
        if workflows.can_transition_to(request.user, ticket, s)
    ]
    # وضعیت ارسال/مشاهدهٔ هر گیرنده (✓ ارسال‌شده / ✓✓ دیده‌شده):
    # برای کارکنان همیشه؛ برای فرستندهٔ تیکتِ انبوه (بیش از یک گیرنده) نیز نمایش داده می‌شود
    show_recipients = is_staff_user(request.user) \
        or (request.user == ticket.author and ticket.recipients.count() > 1)
    recipients_data = []
    seen_count = 0
    if show_recipients:
        for r in ticket.recipients.select_related("user__profile")[:100]:
            seen = r.state in (C.RECIPIENT_READ, C.RECIPIENT_REPLIED,
                               C.RECIPIENT_RESOLVED, C.RECIPIENT_CLOSED)
            seen_count += 1 if seen else 0
            recipients_data.append({
                "user": r.user, "state": r.state,
                "state_label": C.RECIPIENT_LABELS.get(r.state, r.state),
                "name": (r.user.profile.full_name
                         if r.user_id and hasattr(r.user, "profile")
                         else r.user.mobile_number),
                "is_author": r.is_author,
                "ticks": "seen" if seen else "sent",
                "sent_at": r.created_at,
                "read_at": r.read_at,
            })
    return render(request, "tickets/detail.html", {
        "ticket": ticket, "conversation": conversation,
        "status_label": C.STATUS_LABELS.get(ticket.status, ticket.status),
        "priority_label": C.PRIORITY_LABELS.get(ticket.priority, ticket.priority),
        "category_label": ticket.category.name_fa if ticket.category else "",
        "department_label": ticket.department.name_fa if ticket.department else "",
        "can_reply": can_reply(request.user, ticket),
        "draft_reply": draft_reply,
        "can_manage": can_manage(request.user, ticket),
        "can_see_note": can_see_note,
        "can_assign": can_manage(request.user, ticket),
        "my_state": my_rec.state if my_rec else "",
        "my_rec": my_rec,
        "assignment": assignment,
        "agents": _agents_for(ticket, request.user),
        "departments": TicketDepartment.objects.filter(is_active=True),
        "transitions": transitions,
        "status_choices": [(s, C.STATUS_LABELS[s]) for s in C.STATUSES],
        "priority_choices": [(p, C.PRIORITY_LABELS[p]) for p in C.PRIORITIES],
        "rating_form": rating_form, "can_rate": can_rate,
        "history": list(ticket.status_history.select_related("actor")[:10]),
        "recipients_count": ticket.recipients.count(),
        "show_recipients": show_recipients,
        "recipients": recipients_data,
        "seen_count": seen_count,
        "approval_item": approval_item, "approval_kind": approval_kind,
        "approval_fee": approval_fee,
        # سفارش سکهٔ مرتبط (تیکت‌های درخواست خرید/فروش) برای میان‌بر ادمین
        "wallet_order": wallet_order,
    })


def _visible(ticket, user):
    from .permissions import visible_messages_qs

    qs = visible_messages_qs(user, ticket).select_related("author__profile")
    qs = qs.prefetch_related("attachments")
    return list(qs)


def _agents_for(ticket, user):
    if not can_manage(user, ticket):
        return []
    from .permissions import eligible_agents_for

    return eligible_agents_for(ticket) if ticket.department_id else list(
        __import__("django.contrib.auth", fromlist=["get_user_model"]).get_user_model()
        .objects.filter(is_staff=True, is_active=True)[:200])


def _approval_item_for(ticket):
    """رکوردِ تبلیغ/اسلایدی که این تیکت «درخواست تأیید»ِ آن است (یا (None, ""))."""
    from adminpanel.models import Advertisement, StatSlide

    item = Advertisement.objects.filter(approval_ticket_id=ticket.pk).first()
    if item is not None:
        return item, "ad"
    item = StatSlide.objects.filter(approval_ticket_id=ticket.pk).first()
    return (item, "slide") if item is not None else (None, "")


def _handle_approval(request, ticket, action):
    """تأیید/رد درخواست تبلیغ یا اسلایدشو از داخل تیکت (فقط کارکنان)."""
    from ads.approvals import approve_item, reject_item

    if not is_staff_user(request.user):
        raise PermissionDenied("فقط کارکنان می‌توانند درخواست را تأیید یا رد کنند.")
    item, kind = _approval_item_for(ticket)
    if item is None:
        raise TicketError("این تیکت به درخواست تبلیغ/اسلایدشوی مرتبطی وصل نیست.")
    noun = "تبلیغ" if kind == "ad" else "اسلاید"
    if action == "approval_approve":
        ok, code = approve_item(item, request.user, request=request)
        if ok:
            messages.success(request, f"{noun} «{item.title}» تأیید شد و در صف نمایش قرار گرفت.")
        elif code == "refunded":
            raise TicketError(f"این {noun} قبلاً رد و وجهش بازگردانده شده؛ کاربر باید دوباره ثبت کند.")
        else:
            messages.info(request, f"این {noun} قبلاً تأیید شده است.")
    else:
        res = reject_item(item, request.user, request=request,
                          reason=(request.POST.get("reason") or "").strip())
        if res["code"] == "already":
            messages.info(request, f"این {noun} قبلاً رد شده است.")
        elif res["refunded"]:
            messages.success(
                request,
                f"{noun} «{item.title}» رد شد؛ {res['refund']} سکه به کیف پول کاربر بازگشت "
                f"(کارمزد {res['fee']} سکه).")
        else:
            messages.success(request, f"{noun} «{item.title}» رد شد (وجهی بازگردانده نشد).")


def _handle_action(request, ticket, action):
    user = request.user
    files = request.FILES.getlist("attachments")
    if action in ("approval_approve", "approval_reject"):
        return _handle_approval(request, ticket, action)
    if action == "reply":
        body = request.POST.get("body", "")
        if not body.strip() and not files:
            raise TicketError("متن پیام خالی است.")
        services.add_message(ticket, user, body, attachments=files, request=request)
    elif action == "note":
        if not is_staff_user(user):
            raise PermissionDenied("فقط کارکنان می‌توانند یادداشت داخلی بنویسند.")
        body = request.POST.get("body", "")
        if not body.strip():
            raise TicketError("متن یادداشت خالی است.")
        services.add_message(ticket, user, body, kind=C.MSG_INTERNAL_NOTE,
                             attachments=files, request=request)
    elif action == "status":
        to_status = request.POST.get("status", "")
        if to_status not in C.STATUSES:
            raise TicketError("وضعیت نامعتبر است.")
        services.change_status(ticket, user, to_status,
                               note=request.POST.get("note", ""), request=request)
    elif action == "priority":
        services.change_priority(ticket, user, request.POST.get("priority"), request=request)
    elif action == "assign":
        agent_id = request.POST.get("agent")
        from django.contrib.auth import get_user_model

        agent = get_user_model().objects.filter(id=agent_id).first() if agent_id else None
        services.assign(ticket, user, agent=agent, request=request)
    elif action == "unassign":
        services.unassign(ticket, user, request=request)
    elif action == "reopen":
        services.reopen(ticket, user, note=request.POST.get("note", ""), request=request)
    elif action in ("important", "unimportant", "archive", "unarchive"):
        services.set_flag(ticket, user,
                          important=(action == "important") if action.startswith("important")
                          else None,
                          archived=(action == "archive") if action.startswith("archive")
                          else None)
    elif action == "rate":
        form = RatingForm(request.POST)
        if not form.is_valid():
            raise TicketError("امتیاز معتبر نیست.")
        services.rate_ticket(ticket, user,
                             stars=form.cleaned_data["stars"],
                             response_quality=form.cleaned_data["response_quality"],
                             resolution_quality=form.cleaned_data["resolution_quality"],
                             comment=form.cleaned_data["comment"], request=request)
        messages.success(request, "امتیاز شما ثبت شد.")
    else:
        raise TicketError("عملیات ناشناخته است.")


@require_GET
@login_required(login_url="core:index")
def audience_estimate(request):
    """برآورد تعداد گیرنده برای بازبینی مرحلهٔ ۴ (بدون افشای نام‌ها)."""
    rules, error = _parse_audience(request.GET, role_of(request.user))
    if error:
        return JsonResponse({"status": "error", "message": error})
    if rules is None:
        return JsonResponse({"status": "ok", "count": "کارکنان/دپارتمان"})
    try:
        count = targeting.resolve(rules, exclude_user_id=request.user.id).count()
        return JsonResponse({"status": "ok", "count": count,
                             "label": targeting.label_for(rules)})
    except TicketError as exc:
        return JsonResponse({"status": "error", "message": str(exc)})


@_staff_only
def staff_dashboard(request):
    from django.contrib.auth import get_user_model as _gum

    # عملیات گروهی (bulk) با تأیید کاربر
    if request.method == "POST":
        ids = [int(i) for i in request.POST.getlist("ids") if i.isdigit()]
        action = request.POST.get("bulk_action", "")
        if ids and action:
            kwargs = {}
            if action == "assign" and request.POST.get("agent"):
                kwargs["agent_id"] = request.POST.get("agent")
            if action in ("status", "close") and request.POST.get("status"):
                kwargs["status"] = request.POST.get("status")
            if action == "priority" and request.POST.get("priority"):
                kwargs["priority"] = request.POST.get("priority")
            res = services.bulk_apply(request.user, ids, action, **kwargs)
            messages.success(request, f"{res['ok']} تیکت به‌روزرسانی شد.")
            for e in res["errors"][:5]:
                messages.error(request, e)
            return redirect("tickets:staff")
        messages.error(request, "تیکتی انتخاب نشده است.")
        return redirect("tickets:staff")

    status = request.GET.get("status", "")
    q = request.GET.get("q", "")
    stats = selectors.admin_stats()
    base = Ticket.objects.select_related("category", "author__profile",
                                         "department").prefetch_related("recipients")
    if status:
        base = base.filter(status=status)
    if q:
        from django.db.models import Q

        base = base.filter(Q(number__icontains=q) | Q(subject__icontains=q))
    tickets = list(base.order_by("-created_at")[:200])
    rows = []
    for t in tickets:
        rows.append({
            "id": t.id, "number": t.number, "subject": t.subject,
            "status": t.status, "status_label": C.STATUS_LABELS.get(t.status, t.status),
            "priority": t.priority,
            "priority_label": C.PRIORITY_LABELS.get(t.priority, t.priority),
            "category_label": t.category.name_fa if t.category else "",
            "dept_label": t.department.name_fa if t.department else "",
            "author_label": t.author.profile.full_name
            if hasattr(t.author, "profile") else t.author.mobile_number,
            "created": t.created_at, "url": reverse("tickets:detail", args=[t.number]),
        })
    agents = _gum().objects.filter(is_staff=True, is_active=True)
    return render(request, "tickets/staff.html", {
        "stats": stats, "rows": rows, "q": q, "status": status,
        "status_choices": [(s, C.STATUS_LABELS[s]) for s in C.STATUSES],
        "priority_choices": [(p, C.PRIORITY_LABELS[p]) for p in C.PRIORITIES],
        "agents": agents,
    })


@_staff_only
def export_csv(request):
    box = request.GET.get("box", "")
    if request.method == "POST" and request.POST.get("ids"):
        ids = request.POST.getlist("ids")
        tickets = Ticket.objects.filter(id__in=[int(i) for i in ids])
    else:
        tickets = Ticket.objects.all()
    tickets = list(tickets.select_related("author__profile", "category").order_by("-created_at"))

    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="tickets-export.csv"'
    resp.write("\ufeff")  # BOM برای اکسل
    writer = csv.writer(resp)
    writer.writerow(["Number", "Subject", "Author", "Category", "Priority",
                     "Status", "Created", "Resolved", "Closed"])

    def _jdt(dt):
        """datetime → '1405/07/05 14:30' شمسی (به وقت تهران) برای خروجی CSV."""
        if not dt:
            return ""
        local = timezone.localtime(dt) if timezone.is_aware(dt) else dt
        jy, jm, jd = gregorian_to_jalali(local.year, local.month, local.day)
        return en_to_fa(f"{jy:04d}/{jm:02d}/{jd:02d} {local.hour:02d}:{local.minute:02d}")

    for t in tickets:
        writer.writerow([
            t.number, t.subject, t.author.profile.full_name if hasattr(t.author, "profile")
            else t.author.mobile_number, t.category.name_fa if t.category else "",
            C.PRIORITY_LABELS.get(t.priority, t.priority),
            C.STATUS_LABELS.get(t.status, t.status),
            _jdt(t.created_at),
            _jdt(t.resolved_at),
            _jdt(t.closed_at),
        ])
    return resp
