"""ثابت‌ها و انتخاب‌های سامانهٔ تیکت — همهٔ «hard-code»ها اینجا متمرکز شده‌اند."""

# ------- دسته‌های تیکت (Step 1) -------
CATEGORIES = (
    "support", "question", "complaint", "suggestion", "bug",
    "feature", "financial", "account", "general", "other",
)
CATEGORY_LABELS = {
    "support": "پشتیبانی",
    "question": "سؤال",
    "complaint": "اعتراض",
    "suggestion": "پیشنهاد",
    "bug": "گزارش باگ",
    "feature": "درخواست قابلیت",
    "financial": "مالی",
    "account": "حساب کاربری",
    "general": "عمومی",
    "other": "سایر",
}

# ------- اولویت -------
PRIORITIES = ("low", "normal", "high", "urgent", "critical")
PRIORITY_LABELS = {
    "low": "کم",
    "normal": "عادی",
    "high": "زیاد",
    "urgent": "فوری",
    "critical": "بحرانی",
}
PRIORITY_ORDER = {p: i for i, p in enumerate(PRIORITIES)}

# ------- وضعیت گردش کار -------
STATUS_OPEN = "open"
STATUS_IN_PROGRESS = "in_progress"
STATUS_WAITING_USER = "waiting_user"
STATUS_USER_REPLIED = "user_replied"
STATUS_RESOLVED = "resolved"
STATUS_CLOSED = "closed"
STATUSES = (
    STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_WAITING_USER,
    STATUS_USER_REPLIED, STATUS_RESOLVED, STATUS_CLOSED,
)
STATUS_LABELS = {
    STATUS_OPEN: "باز",
    STATUS_IN_PROGRESS: "در حال بررسی",
    STATUS_WAITING_USER: "در انتظار کاربر",
    STATUS_USER_REPLIED: "کاربر پاسخ داد",
    STATUS_RESOLVED: "حل‌شده",
    STATUS_CLOSED: "بسته‌شده",
}

# ------- حالت مستقلِ هر گیرنده -------
RECIPIENT_UNREAD = "unread"
RECIPIENT_READ = "read"
RECIPIENT_REPLIED = "replied"
RECIPIENT_RESOLVED = "resolved"
RECIPIENT_CLOSED = "closed"
RECIPIENT_STATES = (
    RECIPIENT_UNREAD, RECIPIENT_READ, RECIPIENT_REPLIED,
    RECIPIENT_RESOLVED, RECIPIENT_CLOSED,
)
RECIPIENT_LABELS = {
    RECIPIENT_UNREAD: "خوانده‌نشده",
    RECIPIENT_READ: "خوانده‌شده",
    RECIPIENT_REPLIED: "پاسخ داده",
    RECIPIENT_RESOLVED: "حل‌شده",
    RECIPIENT_CLOSED: "بسته",
}

# ------- نوع پیام -------
MSG_NORMAL = "normal"
MSG_SYSTEM = "system"
MSG_INTERNAL_NOTE = "internal_note"
MSG_STATUS_UPDATE = "status_update"
MSG_ASSIGNMENT = "assignment"
MSG_AUTO = "auto"
MSG_KINDS = (MSG_NORMAL, MSG_SYSTEM, MSG_INTERNAL_NOTE,
             MSG_STATUS_UPDATE, MSG_ASSIGNMENT, MSG_AUTO)

# ------- نوع مخاطب (Target Audience، مرحلهٔ ۲) -------
AUD_ALL = "all_users"
AUD_JOB = "job"
AUD_COUNTRY = "country"
AUD_PROVINCE = "province"
AUD_CITY = "city"
AUD_RADIUS = "radius"
AUD_USERS = "specific_users"
AUD_GROUP = "user_group"
AUD_LEVEL = "user_level"
AUD_SCORE = "user_score"
# جدید: شروع شماره موبایل، بازهٔ سنی، و رده‌های پنج‌گانهٔ کاتالوگ مشاغل
AUD_MOBILE_PREFIX = "mobile_prefix"
AUD_AGE = "age"
AUD_JOB_SECTOR = "job_sector"
AUD_JOB_INDUSTRY = "job_industry"
AUD_JOB_CATEGORY = "job_category"
AUD_JOB_TITLE = "job_title"
AUD_JOB_SPEC = "job_spec"
AUD_KINDS = (AUD_ALL, AUD_JOB, AUD_COUNTRY, AUD_PROVINCE, AUD_CITY,
             AUD_RADIUS, AUD_USERS, AUD_GROUP, AUD_LEVEL, AUD_SCORE,
             AUD_MOBILE_PREFIX, AUD_AGE,
             AUD_JOB_SECTOR, AUD_JOB_INDUSTRY, AUD_JOB_CATEGORY,
             AUD_JOB_TITLE, AUD_JOB_SPEC)

# برچسب فارسی هر نوع مخاطب (برای پنل مدیریت و گزارش‌ها)
AUD_LABELS = {
    AUD_ALL: "همهٔ کاربران",
    AUD_JOB: "بر اساس شغل (عنوان متن)",
    AUD_COUNTRY: "کشور",
    AUD_PROVINCE: "استان",
    AUD_CITY: "شهر",
    AUD_RADIUS: "شعاع جغرافیایی (GPS)",
    AUD_USERS: "کاربران مشخص (کد ملی)",
    AUD_GROUP: "گروه کاربری",
    AUD_LEVEL: "سطح کاربر",
    AUD_SCORE: "امتیاز کاربر",
    AUD_MOBILE_PREFIX: "شروع شماره موبایل",
    AUD_AGE: "بازهٔ سنی",
    AUD_JOB_SECTOR: "شغل: حوزه (لایهٔ ۱)",
    AUD_JOB_INDUSTRY: "شغل: صنعت (لایهٔ ۲)",
    AUD_JOB_CATEGORY: "شغل: دسته (لایهٔ ۳)",
    AUD_JOB_TITLE: "شغل: عنوان (لایهٔ ۴)",
    AUD_JOB_SPEC: "شغل: تخصص‌های مرتبط (لایهٔ ۵)",
}

# لایه‌های پنج‌گانهٔ کاتالوگ مشاغل برای هدف‌گیری (کد ↔ فیلد در accounts.Job)
JOB_LAYER_FIELDS = {
    AUD_JOB_SECTOR: "sector",
    AUD_JOB_INDUSTRY: "industry",
    AUD_JOB_CATEGORY: "category",
    AUD_JOB_TITLE: "occupation_title",
    AUD_JOB_SPEC: "specialization",
}

# ------- رویدادهای اعلان -------
EV_NEW_TICKET = "NEW_TICKET"
EV_NEW_REPLY = "NEW_REPLY"
EV_STATUS = "STATUS_CHANGED"
EV_ASSIGNED = "ASSIGNED"
EV_UNASSIGNED = "UNASSIGNED"
EV_SLA_WARN = "SLA_WARNING"
EV_SLA_BREACH = "SLA_BREACHED"
EV_RESOLVED = "TICKET_RESOLVED"
EV_REOPENED = "TICKET_REOPENED"
EVENTS = (EV_NEW_TICKET, EV_NEW_REPLY, EV_STATUS, EV_ASSIGNED, EV_UNASSIGNED,
          EV_SLA_WARN, EV_SLA_BREACH, EV_RESOLVED, EV_REOPENED)

# ------- کانال‌ها -------
CH_INAPP = "in_app"
CH_EMAIL = "email"
CH_SMS = "sms"
CH_PUSH = "push"
CHANNELS = (CH_INAPP, CH_EMAIL, CH_SMS, CH_PUSH)

# ------- نقش‌ها -------
ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN = "admin"
ROLE_SUPERVISOR = "supervisor"
ROLE_AGENT = "agent"
ROLE_DEPT_MANAGER = "dept_manager"
ROLE_USER = "user"
ROLES = (ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_SUPERVISOR,
         ROLE_AGENT, ROLE_DEPT_MANAGER, ROLE_USER)

# ------- دسته‌ها و حالت‌های واژه/عبارتِ حساس (فیلتر محتوای تیکت) -------
CONTENT_CATEGORIES = (
    ("insult", "فحش و ناسزا"),
    ("political", "عبارات سیاسی حساس"),
    ("religious", "عبارات مذهبی حساس"),
    ("dignity", "توهین به اشخاص / شخصیت‌ها / کشورها"),
    ("other", "سایر"),
)
CONTENT_MODES = (
    ("word", "واژه / عبارت کامل"),
    ("prefix", "ابتدای واژه"),
    ("contains", "هر جای متن"),
    ("regex", "الگوی منظم (regex)"),
)

# ------- اقدامات حسابرسی -------
ACT_CONTENT_BLOCKED = "content.blocked"
ACT_CREATED = "ticket.created"
ACT_RECIPIENT_ADDED = "recipient.added"
ACT_RECIPIENT_REMOVED = "recipient.removed"
ACT_MESSAGE = "message.sent"
ACT_MESSAGE_EDIT = "message.edited"
ACT_ATTACHMENT = "attachment.added"
ACT_STATUS = "status.changed"
ACT_PRIORITY = "priority.changed"
ACT_ASSIGNMENT = "assignment.changed"
ACT_REOPENED = "ticket.reopened"
ACT_CLOSED = "ticket.closed"
ACT_ADMIN = "admin.action"

# ------- SLA پیش‌فرض (ساعت) -------
SLA_HOURS = {
    "low": 48,
    "normal": 24,
    "high": 8,
    "urgent": 2,
    "critical": 0.5,
}
SLA_WARN_BEFORE_MIN = 60  # هشدار یک ساعت مانده به موعد

# ------- شمارندهٔ تیکت -------
TICKET_NUMBER_FORMAT = "HUB-{year}-{seq:06d}"

# ------- گیمیفیکیشن: امتیاز رویدادها -------
SCORE_RESOLVED_USER = 5
SCORE_RESOLVED_AGENT = 10
