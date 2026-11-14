"""آزمون‌های سامانهٔ تیکت — احراز هویت، مجوز شیء‌محور، هدف‌گیری، گردش کار، SLA، امتیاز و API."""

from datetime import timedelta

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from tickets import constants as C
from tickets.models import (
    Ticket, TicketAssignment, TicketAuditLog, TicketDepartment,
    TicketDepartmentMember, TicketMessage, TicketNotification, TicketRating,
    TicketRecipient, TicketSLA,
)

STAFF_MOBILE = "09160000001"


def _mk(mobile, nid, staff=False, superuser=False, city="", province="", country="",
        lat=None, lng=None, score=0, level=1, job="", dept=None, role=None):
    """ساخت کاربر + پروفایل با کد ملی و فیلدهای هدف‌گیری."""
    user = User.objects.create_user(mobile_number=mobile)
    user.is_staff = staff
    if superuser:
        user.is_superuser = True
    user.save()
    p = user.profile
    p.national_id = nid
    p.city = city
    p.province = province
    p.country = country
    p.job_title = job
    p.user_score = score
    p.user_level = level
    if lat is not None:
        p.latitude = lat
        p.longitude = lng
    p.save()
    if dept and role:
        TicketDepartmentMember.objects.create(user=user, department=dept, role=role)
    return user


class BaseTicketTest(TestCase):
    def setUp(self):
        self.staff = _mk(STAFF_MOBILE, "1111111111", staff=True)
        self.cs = Client()
        self.cs.force_login(self.staff)

    def make_support_ticket(self, author=None, client=None, subject="موضوع تست",
                            desc="شرح تست", priority="normal", audience=""):
        """تیکت پشتیبانی (بدون مخاطب → گیرنده‌ها کارکنان).

        make_user_ticket: تیکتِ کاربر عادی (نویسنده = کاربر؛ گیرندگان کارکنان).
        """
        author = author or self.staff
        client = client or self.cs
        r = client.post(reverse("tickets:create"), {
            "category": "support", "subject": subject, "description": desc,
            "priority": priority, "audience": audience, "due_date": ""})
        self.assertEqual(r.status_code, 302, r.content[:500])
        ticket = Ticket.objects.get(number=r.url.rstrip("/").split("/")[-1])
        return ticket

    def make_user_ticket(self, member, subject="موضوع تست کاربر",
                         desc="شرح تست کاربر", priority="normal"):
        """تیکتِ ساخته‌شده توسط کاربر عادی (مسیر واقعی پشتیبانی)."""
        cm = Client()
        cm.force_login(member)
        r = cm.post(reverse("tickets:create"), {
            "category": "support", "subject": subject, "description": desc,
            "priority": priority, "audience": "", "due_date": ""})
        self.assertEqual(r.status_code, 302, r.content[:500])
        return Ticket.objects.get(number=r.url.rstrip("/").split("/")[-1])


class CreationWorkflowTests(BaseTicketTest):
    def test_numbering_and_recipients(self):
        member = _mk("09160000002", "1111111112")
        # تیکت پشتیبانی (نویسنده: کارکنان) → فقط کارکنان گیرنده‌اند (حریم خصوصی)
        t = self.make_support_ticket()
        # قالب شماره: HUB-سال-شماره
        self.assertRegex(t.number, r"^HUB-\d{4}-\d{6}$")
        # نویسنده (کارکنان) گیرندهٔ تیکت است؛ کاربرِ عادی گیرنده نیست
        self.assertTrue(TicketRecipient.objects.filter(
            ticket=t, user=self.staff, is_author=True).exists())
        self.assertFalse(TicketRecipient.objects.filter(
            ticket=t, user=member).exists())
        # تیکتِ کاربر عادی → نویسنده = کاربر؛ گیرندگان = کارکنان (member عضو نیست)
        t2 = self.make_user_ticket(member)
        self.assertTrue(TicketRecipient.objects.filter(
            ticket=t2, user=member, is_author=True).exists())
        self.assertTrue(TicketRecipient.objects.filter(
            ticket=t2, user=self.staff, is_author=False,
            is_staff_participant=False).exists())
        self.assertTrue(TicketAuditLog.objects.filter(
            object_id=t.id, action=C.ACT_CREATED).exists())
        # اعلانِ تیکت کاربر برای گیرندگان (کارکنان) ساخته می‌شود
        self.assertTrue(TicketNotification.objects.filter(ticket=t2).exists())

    def test_internal_notes_private_and_recipient_state(self):
        member = _mk("09160000002", "1111111112")
        # تیکتِ کاربر عادی: کاربر نویسنده/عضو است و یادداشت داخلی را نبیند
        t = self.make_user_ticket(member)
        cu = Client()
        cu.force_login(member)

        self.cs.post(reverse("tickets:detail", args=[t.number]),
                     {"action": "note", "body": "یادداشت محرمانهٔ داخلی"})
        # یادداشت داخلی فقط برای کارکنان
        self.assertNotContains(cu.get(reverse("tickets:detail", args=[t.number])),
                               "یادداشت محرمانهٔ داخلی")
        self.assertContains(self.cs.get(reverse("tickets:detail", args=[t.number])),
                            "یادداشت محرمانهٔ داخلی")

        # پاسخ کارشناس، گیرندهٔ نویسنده (کاربر) را به «خوانده‌نشده» برمی‌گرداند
        self.cs.post(reverse("tickets:detail", args=[t.number]),
                     {"action": "reply", "body": "بررسی شد"})
        rec = TicketRecipient.objects.get(ticket=t, user=member)
        self.assertEqual(rec.state, C.RECIPIENT_UNREAD)

    def test_workflow_and_assignment(self):
        member = _mk("09160000002", "1111111112")
        t = self.make_support_ticket()
        self.assertEqual(t.status, C.STATUS_OPEN)
        self.cs.post(reverse("tickets:detail", args=[t.number]),
                     {"action": "assign", "agent": str(self.staff.id)})
        self.assertTrue(t.assignments.filter(is_active=True, agent=self.staff).exists())
        self.cs.post(reverse("tickets:detail", args=[t.number]),
                     {"action": "status", "status": C.STATUS_IN_PROGRESS})
        t.refresh_from_db()
        self.assertEqual(t.status, C.STATUS_IN_PROGRESS)

    def test_rating_after_resolve(self):
        member = _mk("09160000002", "1111111112")
        # تیکتِ کاربر عادی؛ پس از حل، امتیازِ حل به نویسنده (کاربر) می‌رسد.
        # پل امتیاز با transaction.on_commit اجرا می‌شود؛ captureOnCommitCallbacks
        # منتظر اجرای آن می‌ماند (رفتار واقعی پس از commit).
        t = self.make_user_ticket(member)
        cu = Client()
        cu.force_login(member)
        with self.captureOnCommitCallbacks(execute=True):
            self.cs.post(reverse("tickets:detail", args=[t.number]),
                         {"action": "status", "status": C.STATUS_RESOLVED})
        t.refresh_from_db()
        self.assertEqual(t.status, C.STATUS_RESOLVED)
        # امتیاز (scoring bridge) به نویسنده اعطا شد
        member.profile.refresh_from_db()
        self.assertGreaterEqual(member.profile.user_score, 5)
        r = cu.post(reverse("tickets:detail", args=[t.number]),
                    {"action": "rate", "stars": "5", "comment": "عالی"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(TicketRating.objects.filter(
            ticket=t, user=member, stars=5).exists())
        # فقط یک بار می‌توان امتیاز داد
        b = cu.get(reverse("tickets:detail", args=[t.number])).content.decode("utf-8")
        self.assertNotIn("tkt-rate-form", b)


class AuthorizationTests(BaseTicketTest):
    def test_stranger_blocked(self):
        member = _mk("09160000002", "1111111112")
        other = _mk("09160000003", "1111111113")
        t = self.make_support_ticket()
        co = Client()
        co.force_login(other)
        self.assertEqual(co.get(reverse("tickets:detail", args=[t.number])).status_code, 403)

    def test_department_isolation(self):
        """کارشناسِ دپارتمان B نباید تیکت دپارتمان A را ببیند مگر ارجاع شده باشد."""
        member = _mk("09160000002", "1111111112")
        dept_a = TicketDepartment.objects.create(code="dept-a", name_fa="دپارتمان الف")
        dept_b = TicketDepartment.objects.create(code="dept-b", name_fa="دپارتمان ب")
        agent_a = _mk("09160000004", "1111111114", dept=dept_a, role=C.ROLE_AGENT)
        agent_b = _mk("09160000005", "1111111115", dept=dept_b, role=C.ROLE_AGENT)
        t = self.make_support_ticket()
        t.department = dept_a
        t.save(update_fields=["department"])

        ca = Client()
        ca.force_login(agent_a)
        cb = Client()
        cb.force_login(agent_b)
        self.assertEqual(ca.get(reverse("tickets:detail", args=[t.number])).status_code, 200)
        self.assertEqual(cb.get(reverse("tickets:detail", args=[t.number])).status_code, 403)

    def test_normal_user_cannot_reach_staff_pages(self):
        member = _mk("09160000002", "1111111112")
        cu = Client()
        cu.force_login(member)
        self.assertEqual(cu.get(reverse("tickets:staff")).status_code, 302)
        # برآورد انبوه نیز ممنوع
        r = cu.get(reverse("tickets:audience_estimate") + "?audience=all_users")
        self.assertEqual(r.json()["status"], "error")


class TargetingTests(BaseTicketTest):
    def test_city_and_score_and_or_rules(self):
        _mk("09160000002", "1111111112", city="یزد", score=90, level=5)
        _mk("09160000003", "1111111113", city="یزد", score=10, level=1)
        _mk("09160000004", "1111111114", city="تهران", score=95, level=6)
        base = {"logic": "and", "items": [{"kind": "city", "values": ["یزد"]}]}
        self.assertEqual(set(self.ids(base)), {"1111111112", "1111111113"})
        # AND: شهر=یزد و امتیاز>=50
        rules = {"logic": "and", "items": [
            {"kind": "city", "values": ["یزد"]},
            {"kind": "score", "value": 50}]}
        self.assertEqual(set(self.ids(rules)), {"1111111112"})
        # OR: شهر=یزد یا سطح>=6
        rules = {"logic": "or", "items": [
            {"kind": "city", "values": ["یزد"]},
            {"kind": "level", "value": 6}]}
        self.assertEqual(set(self.ids(rules)), {"1111111112", "1111111113", "1111111114"})

    def ids(self, rules):
        from tickets.targeting import resolve
        return list(resolve(rules).values_list("national_id", flat=True))

    def test_geo_radius(self):
        # یزد مرکز 31.9, 54.4 — حدود ۱ کیلومتر دورتر
        _mk("09160000002", "1111111112", lat=31.8974, lng=54.35)
        _mk("09160000003", "1111111113", lat=31.90, lng=54.40)
        _mk("09160000004", "1111111114", lat=35.68, lng=51.39)  # تهران (دور)
        rules = {"logic": "and", "items": [
            {"kind": "radius", "lat": 31.9, "lng": 54.35, "km": 10}]}
        self.assertEqual(set(self.ids(rules)), {"1111111112", "1111111113"})

    def test_broadcast_creation_and_count(self):
        _mk("09160000002", "1111111112", city="یزد")
        _mk("09160000003", "1111111113", city="یزد")
        _mk("09160000004", "1111111114", city="تهران")
        # برآورد
        r = self.cs.get(reverse("tickets:audience_estimate"),
                        {"audience": "city", "location": "یزد"})
        self.assertEqual(r.json()["status"], "ok")
        self.assertEqual(r.json()["count"], 2)
        # ارسال دسته‌ای واقعی
        r = self.cs.post(reverse("tickets:create"), {
            "category": "general", "subject": "اعلامیهٔ شهری",
            "description": "به کاربران یزد", "priority": "normal",
            "audience": "city", "location": "یزد", "due_date": ""})
        self.assertEqual(r.status_code, 302)
        t = Ticket.objects.get(number=r.url.rstrip("/").split("/")[-1])
        got = set(TicketRecipient.objects.filter(
            ticket=t, is_author=False).values_list("user__profile__national_id", flat=True))
        self.assertEqual(got, {"1111111112", "1111111113"})

    def test_estimate_per_recipient_state(self):
        member = _mk("09160000002", "1111111112")
        # تیکتِ کاربر عادی: کاربر نویسنده/عضو است و حالت گیرندهٔ مستقل دارد
        t = self.make_user_ticket(member)
        cu = Client()
        cu.force_login(member)
        rec_member = TicketRecipient.objects.get(ticket=t, user=member)
        rec_staff = TicketRecipient.objects.get(ticket=t, user=self.staff)
        self.assertEqual(rec_member.state, C.RECIPIENT_UNREAD)
        # خواندن توسط یک گیرنده، حالتِ او را جداگانه عوض می‌کند
        cu.get(reverse("tickets:detail", args=[t.number]))
        rec_member.refresh_from_db()
        rec_staff.refresh_from_db()
        self.assertEqual(rec_member.state, C.RECIPIENT_READ)
        self.assertEqual(rec_staff.state, C.RECIPIENT_UNREAD)


class SLASweepTests(BaseTicketTest):
    def test_breach_detected(self):
        member = _mk("09160000002", "1111111112")
        t = self.make_support_ticket(priority="critical")
        TicketSLA.objects.filter(ticket=t).update(
            response_deadline=timezone.now() - timedelta(minutes=5),
            resolution_deadline=timezone.now() + timedelta(hours=1))
        out = call_command("tickets_sla_sweep")
        sla = TicketSLA.objects.get(ticket=t)
        self.assertTrue(sla.response_breached)
        self.assertEqual(sla.escalation_level, 1)
        self.assertTrue(TicketAuditLog.objects.filter(
            action="sla.breached", object_id=t.id).exists())


class APITests(BaseTicketTest):
    def test_api_privacy_and_reply(self):
        member = _mk("09160000002", "1111111112")
        # تیکتِ کاربر عادی: نویسنده = کاربر؛ دسترسی API و حریم یادداشت بررسی می‌شود
        t = self.make_user_ticket(member)
        cu = Client()
        cu.force_login(member)
        # لیست و جزئیات
        self.assertEqual(cu.get(f"/api/tickets/{t.number}/").status_code, 200)
        body = cu.get(f"/api/tickets/{t.number}/").json()
        self.assertTrue(all(m["kind"] != C.MSG_INTERNAL_NOTE for m in body["messages"]))
        # پاسخ API (کارکنان؛ 201 = پیام ساخته شد)
        r = self.cs.post(f"/api/tickets/{t.number}/reply/",
                         {"body": "پاسخ از API"}, content_type="application/json")
        self.assertEqual(r.status_code, 201)
        # پیام داخلی از سمت کاربر عادی ممنوع
        r = cu.post(f"/api/tickets/{t.number}/reply/",
                    {"body": "یادداشت", "kind": "internal_note"},
                    content_type="application/json")
        self.assertNotEqual(r.status_code, 200)

    def test_api_permission_denied(self):
        other = _mk("09160000003", "1111111113")
        t = self.make_support_ticket()
        co = Client()
        co.force_login(other)
        self.assertEqual(co.get(f"/api/tickets/{t.number}/").status_code, 403)
