"""مدل‌های موتور تیکت و ارتباطات حبیب‌هاب.

اصول:
- وضعیت، مستقل برای هر گیرنده است (TicketRecipient.state).
- پیام‌های داخلی (internal note) هرگز برای کاربر عادی دیده نمی‌شود (selectors فیلتر می‌کنند).
- شمارهٔ عمومی تیکت HUB-YYYY-NNNNNN است؛ شناسهٔ دیتابیس هرگز عمومی نمی‌شود.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from . import constants as C
from .numbering import TicketYearCounter  # noqa: F401  (ثبت مدل شمارنده برای makemigrations)


def _upload_to(instance, filename):
    import os
    ext = os.path.splitext(filename or "")[1].lower()
    return f"tickets/{instance.message.ticket.number}/{instance.id or 'tmp'}{ext}"


class SensitiveTerm(models.Model):
    """واژه/عبارتِ حساسِ ثبت‌شده توسط ادمین برای پالایش محتوای تیکت‌ها.

    پالایش توسط موتور tickets.filtering اعمال می‌شود؛ هر رکورد با «حالت تطبیق»
    و «دستهٔ تخلف» تعریف می‌شود تا ادمین کنترل دقیق‌تری روی خطاهای مثبت داشته باشد.
    غیرفعال‌کردن (is_active=False) جایگزین امنِ حذف است.
    """

    term = models.CharField("واژه/عبارت یا الگو", max_length=150)
    mode = models.CharField(
        "حالت تطبیق", max_length=20, choices=C.CONTENT_MODES, default="word",
    )
    category = models.CharField(
        "دستهٔ تخلف", max_length=30, choices=C.CONTENT_CATEGORIES, default="insult",
    )
    note = models.CharField("توضیح (برای ادمین)", max_length=255, blank=True)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "واژه/عبارت حساس"
        verbose_name_plural = "واژه‌ها و عبارت‌های حساس"
        ordering = ["category", "mode", "term"]

    def __str__(self):
        return self.term


class TicketCategory(models.Model):
    # نوع تیکت از این پس توسط ادمین در پنل مدیریت تعریف می‌شود؛ بنابراین code
    # دیگر به فهرست ثابت CATEGORIES محدود نیست (فقط یکتا بودن لازم است).
    code = models.CharField("کد", max_length=30, unique=True)
    name_fa = models.CharField("نام فارسی", max_length=100)
    name_en = models.CharField("نام انگلیسی", max_length=100, blank=True)
    name_zh = models.CharField("نام چینی", max_length=100, blank=True)
    icon = models.CharField("آیکون", max_length=40, default="bi-life-preserver")
    order = models.PositiveSmallIntegerField("ترتیب", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "دستهٔ تیکت"
        verbose_name_plural = "دسته‌های تیکت"
        ordering = ["order", "code"]

    def __str__(self):
        return self.name_fa or self.code

    def name(self, lang="fa"):
        return getattr(self, f"name_{lang}") or self.name_fa


class TicketDepartment(models.Model):
    code = models.CharField("کد", max_length=40, unique=True)
    name_fa = models.CharField("نام فارسی", max_length=120)
    name_en = models.CharField("نام انگلیسی", max_length=120, blank=True)
    name_zh = models.CharField("نام چینی", max_length=120, blank=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="children", verbose_name="دپارتمان والد")
    sla_override_hours = models.JSONField("لغو SLA (ساعت)", default=dict, blank=True)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "دپارتمان"
        verbose_name_plural = "دپارتمان‌ها"
        ordering = ["code"]

    def __str__(self):
        return self.name_fa or self.code


class TicketDepartmentMember(models.Model):
    ROLE_CHOICES = ((C.ROLE_AGENT, "کارشناس"), (C.ROLE_SUPERVISOR, "سرپرست"),
                    (C.ROLE_DEPT_MANAGER, "مدیر دپارتمان"))
    department = models.ForeignKey(TicketDepartment, on_delete=models.CASCADE,
                                   related_name="memberships", verbose_name="دپارتمان")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="ticket_memberships", verbose_name="کاربر")
    role = models.CharField("نقش", max_length=20, choices=ROLE_CHOICES, default=C.ROLE_AGENT)

    class Meta:
        verbose_name = "عضو دپارتمان"
        verbose_name_plural = "اعضای دپارتمان"
        constraints = [models.UniqueConstraint(fields=["department", "user"],
                                               name="uniq_dept_member")]

    def __str__(self):
        return f"{self.user} در {self.department} ({self.role})"


class Ticket(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                               related_name="authored_tickets", verbose_name="فرستنده")
    number = models.CharField("شمارهٔ تیکت", max_length=30, unique=True, editable=False)
    category = models.ForeignKey(TicketCategory, null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="tickets",
                                 verbose_name="دسته")
    department = models.ForeignKey(TicketDepartment, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="tickets",
                                   verbose_name="دپارتمان")
    subject = models.CharField("موضوع", max_length=200)
    description = models.TextField("شرح", blank=True)
    priority = models.CharField("اولویت", max_length=20, choices=[(p, p) for p in C.PRIORITIES],
                                default="normal")
    status = models.CharField("وضعیت", max_length=20, choices=[(s, s) for s in C.STATUSES],
                              default=C.STATUS_OPEN, db_index=True)
    sla_response_hours = models.FloatField("زمان پاسخ SLA (ساعت)", default=24)
    sla_resolution_hours = models.FloatField("زمان حل SLA (ساعت)", default=72)
    due_at = models.DateTimeField("مهلت", null=True, blank=True)
    resolved_at = models.DateTimeField("زمان حل", null=True, blank=True)
    closed_at = models.DateTimeField("زمان بسته‌شدن", null=True, blank=True)
    reopened_count = models.PositiveSmallIntegerField("تعداد بازگشایی", default=0)
    metadata = models.JSONField("فراداده", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تیکت"
        verbose_name_plural = "تیکت‌ها"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "priority", "created_at"], name="tkt_status_prio"),
            models.Index(fields=["author", "-created_at"], name="tkt_author_dt"),
        ]

    def __str__(self):
        return self.number

    def current_assignment(self):
        return self.assignments.filter(is_active=True).select_related("agent").first()

    @property
    def assigned_to(self):
        a = self.current_assignment()
        return a.agent if a else None


class TicketRecipient(models.Model):
    """هر گیرنده وضعیت مستقل دارد؛ وضعیت سراسری وجود ندارد."""

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE,
                               related_name="recipients", verbose_name="تیکت")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="ticket_recipients", verbose_name="گیرنده")
    state = models.CharField("وضعیت گیرنده", max_length=20,
                             choices=[(s, s) for s in C.RECIPIENT_STATES],
                             default=C.RECIPIENT_UNREAD, db_index=True)
    is_author = models.BooleanField("فرستندهٔ تیکت", default=False)
    is_staff_participant = models.BooleanField("عضو کارکنان", default=False)
    important = models.BooleanField("مهم", default=False)
    archived = models.BooleanField("بایگانی", default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "گیرندهٔ تیکت"
        verbose_name_plural = "گیرندگان تیکت"
        constraints = [models.UniqueConstraint(fields=["ticket", "user"],
                                               name="uniq_ticket_recipient")]
        indexes = [
            models.Index(fields=["user", "archived", "state", "-updated_at"],
                         name="rcpt_user_inbox"),
            models.Index(fields=["user", "is_author", "-created_at"], name="rcpt_sent"),
        ]

    def __str__(self):
        return f"{self.ticket.number} ← {self.user} [{self.state}]"


class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE,
                               related_name="messages", verbose_name="تیکت")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                               related_name="ticket_messages", verbose_name="نویسنده")
    kind = models.CharField("نوع", max_length=20, choices=[(k, k) for k in C.MSG_KINDS],
                            default=C.MSG_NORMAL)
    body = models.TextField("متن")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    edited_at = models.DateTimeField("آخرین ویرایش", null=True, blank=True)

    class Meta:
        verbose_name = "پیام تیکت"
        verbose_name_plural = "پیام‌های تیکت"
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["ticket", "created_at"], name="msg_ticket_dt")]

    def __str__(self):
        return f"{self.ticket.number} / {self.kind}: {self.body[:40]}"

    @property
    def is_internal(self):
        return self.kind == C.MSG_INTERNAL_NOTE


class TicketAttachment(models.Model):
    message = models.ForeignKey(TicketMessage, on_delete=models.CASCADE,
                                related_name="attachments", verbose_name="پیام")
    file = models.FileField(upload_to=_upload_to, verbose_name="فایل")
    name = models.CharField("نام اصلی", max_length=255)
    size = models.PositiveBigIntegerField("حجم (بایت)", default=0)
    mime = models.CharField("MIME", max_length=120, blank=True)
    sha256 = models.CharField("SHA-256", max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "پیوست"
        verbose_name_plural = "پیوست‌ها"
        ordering = ["id"]

    def __str__(self):
        return self.name or self.file.name


class TicketAssignment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE,
                               related_name="assignments", verbose_name="تیکت")
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="ticket_assignments", verbose_name="کارشناس")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+",
                                    verbose_name="ارجاع‌دهنده")
    kind = models.CharField("نوع ارجاع", max_length=20, default="manual",
                            choices=[("manual", "دستی"), ("round_robin", "چرخشی"),
                                     ("workload", "بر اساس حجم کار"), ("auto", "خودکار")])
    is_active = models.BooleanField("ارجاع فعلی", default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ارجاع تیکت"
        verbose_name_plural = "ارجاعات تیکت"
        ordering = ["-assigned_at"]
        indexes = [models.Index(fields=["agent", "is_active"], name="asg_agent")]

    def __str__(self):
        return f"{self.ticket.number} → {self.agent} ({self.kind})"


class TicketStatusHistory(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE,
                               related_name="status_history", verbose_name="تیکت")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="+")
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تاریخچهٔ وضعیت"
        verbose_name_plural = "تاریخچهٔ وضعیت‌ها"
        ordering = ["created_at"]


class TicketPriorityHistory(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE,
                               related_name="priority_history", verbose_name="تیکت")
    from_priority = models.CharField(max_length=20, blank=True)
    to_priority = models.CharField(max_length=20)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تاریخچهٔ اولویت"
        verbose_name_plural = "تاریخچهٔ اولویت‌ها"
        ordering = ["created_at"]


class TicketAuditLog(models.Model):
    """ثبت رویداد ضمیمه‌ناپذیر — حذف/ویرایش نمی‌شود (فقط append)."""

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="+")
    action = models.CharField("عملیات", max_length=60, db_index=True)
    object_type = models.CharField("نوع شیء", max_length=40)
    object_id = models.PositiveBigIntegerField("شناسهٔ شیء", null=True, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("مرورگر", max_length=500, blank=True)
    meta = models.JSONField("فراداده", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "لاگ حسابرسی"
        verbose_name_plural = "لاگ‌های حسابرسی"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["object_type", "object_id"], name="audit_obj")]


class TicketTarget(models.Model):
    """الگوی هدف‌گیری ذخیره‌شدهٔ کاربر/ادمین."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="ticket_targets", verbose_name="مالک")
    name = models.CharField("نام الگو", max_length=150)
    rules = models.JSONField("قواعد", default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "الگوی هدف‌گیری"
        verbose_name_plural = "الگوهای هدف‌گیری"

    def __str__(self):
        return self.name


class TicketTargetRule(models.Model):
    """ثبت هر ارسال هدفمند + آمار آن (§۴۴)."""

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE,
                               related_name="target_rules", verbose_name="تیکت")
    audience = models.CharField("مخاطب", max_length=30,
                                choices=[(a, a) for a in C.AUD_KINDS])
    label = models.CharField("توضیح هدف", max_length=300, blank=True)
    rules_json = models.JSONField("قواعد", default=dict, blank=True)
    eligible_count = models.PositiveIntegerField("واجد شرایط", default=0)
    recipient_count = models.PositiveIntegerField("گیرندگان واقعی", default=0)
    read_count = models.PositiveIntegerField("خوانده‌شده", default=0)
    reply_count = models.PositiveIntegerField("پاسخ‌ها", default=0)
    resolved_count = models.PositiveIntegerField("حل‌شده", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "قاعدهٔ هدف‌گیری تیکت"
        verbose_name_plural = "قواعد هدف‌گیری تیکت"
        ordering = ["id"]


class TicketAudience(models.Model):
    """جامعهٔ هدفِ تعریف‌شده توسط ادمین در پنل مدیریت.

    هر رکورد یک «الگوی مخاطب» آماده است (مثلاً «کاربران تهران»، «شاغلان حوزهٔ
    ساختمان»، «موبایل‌های شروع‌شونده با 0912» و ...) که کاربر هنگام ارسال انبوهِ
    تیکت آن را انتخاب می‌کند. قواعد با همان ساختار موتور هدف‌گیری (targeting)
    ذخیره می‌شود؛ غیرفعال‌کردن (is_active=False) جایگزین امنِ حذف است.
    """

    name = models.CharField("نام جامعهٔ هدف", max_length=150)
    kind = models.CharField("نوع مخاطب", max_length=30,
                            choices=[(a, C.AUD_LABELS.get(a, a)) for a in C.AUD_KINDS],
                            default=C.AUD_ALL)
    description = models.CharField("توضیح (برای نمایش به کاربر)", max_length=300, blank=True)
    rules = models.JSONField("قواعد هدف‌گیری", default=dict, blank=True)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "جامعهٔ هدف تیکت"
        verbose_name_plural = "جوامع هدف تیکت"
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active"], name="aud_target_act")]

    def __str__(self):
        return self.name

    @property
    def kind_label(self):
        return C.AUD_LABELS.get(self.kind, self.kind)

    @property
    def rules_label(self):
        from .targeting import label_for

        try:
            return label_for(self.rules) if self.rules else "—"
        except Exception:  # noqa: BLE001 - قواعد خراب نباید لیست را بشکند
            return "قواعد نامعتبر"

    def eligible_count(self, exclude_user_id=None):
        """تعداد واجدین شرایط فعلی بر اساس قواعد (برای نمایش در پنل)."""
        try:
            from .targeting import resolve

            return resolve(self.rules, exclude_user_id=exclude_user_id).count()
        except Exception:  # noqa: BLE001
            return None


class TicketSLA(models.Model):
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE,
                                  related_name="sla", verbose_name="تیکت")
    response_deadline = models.DateTimeField("موعد پاسخ", null=True, blank=True)
    resolution_deadline = models.DateTimeField("موعد حل", null=True, blank=True)
    first_response_at = models.DateTimeField("نخستین پاسخ کارشناس", null=True, blank=True)
    response_breached = models.BooleanField("نقض پاسخ", default=False)
    resolution_breached = models.BooleanField("نقض حل", default=False)
    warn_sent = models.BooleanField("هشدار ارسال شد", default=False)
    escalation_level = models.PositiveSmallIntegerField("سطح ارتقا", default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SLA تیکت"
        verbose_name_plural = "SLA تیکت‌ها"

    def __str__(self):
        return f"SLA {self.ticket.number}"


class TicketRating(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE,
                               related_name="ratings", verbose_name="تیکت")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="ticket_ratings", verbose_name="کاربر")
    stars = models.PositiveSmallIntegerField("ستاره", validators=[MinValueValidator(1),
                                                                  MaxValueValidator(5)])
    response_quality = models.PositiveSmallIntegerField(
        "کیفیت پاسخ", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    resolution_quality = models.PositiveSmallIntegerField(
        "کیفیت حل", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField("نظر", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "امتیازدهی تیکت"
        verbose_name_plural = "امتیازدهی تیکت‌ها"
        constraints = [models.UniqueConstraint(fields=["ticket", "user"],
                                               name="uniq_ticket_rating")]

    def __str__(self):
        return f"{self.ticket.number} ★{self.stars}"


class TicketNotification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name="ticket_notifications", verbose_name="گیرنده")
    ticket = models.ForeignKey(Ticket, null=True, blank=True, on_delete=models.CASCADE,
                               related_name="notifications")
    message = models.ForeignKey(TicketMessage, null=True, blank=True,
                                on_delete=models.CASCADE, related_name="+")
    event = models.CharField("رویداد", max_length=40, choices=[(e, e) for e in C.EVENTS])
    channel = models.CharField("کانال", max_length=20,
                               choices=[(c, c) for c in C.CHANNELS], default=C.CH_INAPP)
    title = models.CharField("عنوان", max_length=250)
    body = models.TextField("متن", blank=True)
    is_read = models.BooleanField("خوانده‌شده", default=False)
    status = models.CharField("وضعیت ارسال", max_length=20, default="pending",
                              choices=[("pending", "در صف"), ("sent", "ارسال شد"),
                                       ("failed", "ناموفق")])
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "اعلان تیکت"
        verbose_name_plural = "اعلان‌های تیکت"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read", "event"], name="notif_user")]


class UserNotificationPreferences(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="ticket_notif_prefs", verbose_name="کاربر")
    email = models.BooleanField("ایمیل", default=True)
    push = models.BooleanField("پوش", default=True)
    sms = models.BooleanField("پیامک", default=False)
    in_app = models.BooleanField("داخل برنامه", default=True)
    per_event = models.JSONField("تنظیم رویدادی", default=dict, blank=True)

    class Meta:
        verbose_name = "تنظیمات اعلان کاربر"
        verbose_name_plural = "تنظیمات اعلان کاربران"

    def __str__(self):
        return f"prefs {self.user}"

    def wants(self, event, channel):
        override = self.per_event.get(event, {})
        if channel in override:
            return bool(override[channel])
        return bool(getattr(self, channel, True))
