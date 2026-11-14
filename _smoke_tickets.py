import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "habib_system.settings")
django.setup()

from django.test import Client
from django.urls import reverse
from accounts.models import User
from tickets import constants as C
from tickets.models import (Ticket, TicketMessage, TicketRecipient,
                            TicketAuditLog, TicketNotification)

M_USER = "09150000001"
M_AGENT = "09150000002"

Ticket.objects.filter(author__mobile_number__in=[M_USER, M_AGENT, "09150000003"]).delete()
for m in (M_USER, M_AGENT, "09150000003"):
    User.objects.filter(mobile_number=m).delete()

ok_n = []
def ok(name, cond, extra=""):
    ok_n.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra else ""))

try:
    member = User.objects.create_user(mobile_number=M_USER)
    member.profile.national_id = "9999000001"
    member.profile.save()
    agent = User.objects.create_user(mobile_number=M_AGENT)
    agent.is_staff = True
    agent.save()
    agent.profile.national_id = "9999000002"
    agent.profile.save()

    cu = Client(); cu.force_login(member)
    ca = Client(); ca.force_login(agent)

    # --- create (support flow → staff recipients) ---
    r = cu.post(reverse("tickets:create"), {
        "category": "support", "subject": "نمی‌توانم وارد شوم",
        "description": "پیام ورود خطا می‌دهد", "priority": "high",
        "audience": "", "due_date": ""})
    ok("create redirects to detail", r.status_code == 302 and "/tickets/ticket/" in r.url, r.url)
    number = r.url.rstrip("/").split("/")[-1]
    t = Ticket.objects.get(number=number)
    ok("ticket number format", t.number.startswith("HUB-"), t.number)
    ok("author recipient row", TicketRecipient.objects.filter(ticket=t, user=member, is_author=True).exists())
    ok("staff got recipients", TicketRecipient.objects.filter(ticket=t, user=agent).exists())
    ok("audit created", TicketAuditLog.objects.filter(object_id=t.id, action=C.ACT_CREATED).exists())
    ok("notifications queued", TicketNotification.objects.filter(ticket=t).exists())

    # --- user detail page renders; message visible; reply by user ---
    b = cu.get(reverse("tickets:detail", args=[number])).content.decode("utf-8")
    ok("detail page renders", r.status_code == 302 and "detail" in r.url or b.count("tkt-composer") > 0)
    r = cu.post(reverse("tickets:detail", args=[number]), {"action": "reply", "body": "توضیح بیشتر"})
    ok("user reply ok", r.status_code == 302)
    ok("user reply message", TicketMessage.objects.filter(ticket=t, author=member).count() == 2)

    # --- staff manages: assign, status, priority, internal note ---
    r = ca.post(reverse("tickets:detail", args=[number]),
                {"action": "assign", "agent": str(agent.id)})
    ok("assign ok", r.status_code == 302)
    ok("assignment active", t.assignments.filter(is_active=True, agent=agent).exists())
    r = ca.post(reverse("tickets:detail", args=[number]),
                {"action": "status", "status": C.STATUS_IN_PROGRESS})
    ok("status change ok", r.status_code == 302)
    t.refresh_from_db(); ok("status now in_progress", t.status == C.STATUS_IN_PROGRESS, t.status)
    r = ca.post(reverse("tickets:detail", args=[number]),
                {"action": "priority", "priority": "urgent"})
    t.refresh_from_db(); ok("priority changed", t.priority == "urgent")
    r = ca.post(reverse("tickets:detail", args=[number]),
                {"action": "note", "body": "یادداشت داخلی محرمانه"})
    ok("internal note added", TicketMessage.objects.filter(ticket=t, kind=C.MSG_INTERNAL_NOTE).exists())

    # staff reply -> requester row back to unread; user cannot see internal note
    r = ca.post(reverse("tickets:detail", args=[number]), {"action": "reply", "body": "بررسی شد"})
    rr = TicketRecipient.objects.get(ticket=t, user=member)
    ok("requester state unread after staff reply", rr.state == C.RECIPIENT_UNREAD, rr.state)
    bu = cu.get(reverse("tickets:detail", args=[number])).content.decode("utf-8")
    ok("user does NOT see internal note", "یادداشت داخلی محرمانه" not in bu)
    ba = ca.get(reverse("tickets:detail", args=[number])).content.decode("utf-8")
    ok("staff DOES see internal note", "یادداشت داخلی محرمانه" in ba)

    # --- privacy: other user cannot open ---
    other = User.objects.create_user(mobile_number="09150000003")
    other.profile.national_id = "9999000003"; other.profile.save()
    co = Client(); co.force_login(other)
    ok("stranger blocked (403)", co.get(reverse("tickets:detail", args=[number])).status_code == 403)

    # --- center list, staff dashboard, export ---
    ok("center 200", cu.get(reverse("tickets:center")).status_code == 200)
    ok("staff page 200", ca.get(reverse("tickets:staff")).status_code == 200)
    ok("staff blocked for normal", cu.get(reverse("tickets:staff")).status_code == 302)
    csv_r = ca.get(reverse("tickets:export"))
    ok("export csv", csv_r.status_code == 200 and "HUB-" in csv_r.content.decode("utf-8"))

    # --- estimate endpoint (staff: broadcast kind) ---
    r = ca.get(reverse("tickets:audience_estimate") + f"?audience=all_users")
    ok("estimate all users", r.json().get("status") == "ok", r.json())
    r = cu.get(reverse("tickets:audience_estimate") + "?audience=all_users")
    ok("normal user cannot estimate broadcast", r.json().get("status") == "error")

    # --- resolve → rating + score bridge ---
    r = ca.post(reverse("tickets:detail", args=[number]),
                {"action": "status", "status": C.STATUS_RESOLVED})
    t.refresh_from_db(); ok("resolved", t.status == C.STATUS_RESOLVED)
    member.profile.refresh_from_db()
    ok("score awarded to member", member.profile.user_score >= 5, member.profile.user_score)
    r = cu.post(reverse("tickets:detail", args=[number]),
                {"action": "rate", "stars": "5", "comment": "عالی بود"})
    ok("rating submitted", r.status_code == 302)

    # --- API ---
    r = cu.get("/api/tickets/?box=sent")
    ok("api list 200", r.status_code == 200, getattr(r, "status_code", None))
    r = cu.get(f"/api/tickets/{number}/")
    ok("api detail 200", r.status_code == 200)
    body = r.json()
    ok("api hides internal note for user", all(m["kind"] != "internal_note" for m in body["messages"]))
    r = ca.post(f"/api/tickets/{number}/reply/", {"body": "پاسخ API"}, content_type="application/json")
    ok("api reply ok", r.status_code == 201, r.content[:120])
    r = cu.post(f"/api/tickets/{number}/reply/", {"internal": True, "body": "x"},
                content_type="application/json")
    ok("api blocks internal note by user", r.status_code == 403)

finally:
    Ticket.objects.filter(author__mobile_number__in=[M_USER, M_AGENT, "09150000003"]).delete()
    User.objects.filter(mobile_number__in=[M_USER, M_AGENT, "09150000003"]).delete()

fails = [n for n, p in ok_n if not p]
print(f"\n{len(ok_n) - len(fails)}/{len(ok_n)} checks passed")
if fails:
    print("FAILED:", fails)
    raise SystemExit(1)
