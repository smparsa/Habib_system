"""مدل‌های ماژول حسابداری — ایزولاسیون کامل به ازای هر کاربر (Shared schema، Row-level isolation).

هر کاربرِ اصلی سایت یک دفتر حسابداری مستقل دارد؛ تمایز بین «کاربر مالک»
(accounts.User) و «نام کاربری حسابداری» (AccountingUser) طبق PRD ACC.docx است.
مبالغ همه‌جا به ریال و با DecimalField(max_digits=20, decimal_places=0) ذخیره می‌شوند.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from .jalali import en_to_fa

# ------------------------------------------------------------------ گروه‌های حساب

GROUP_CHOICES = [
    (1, "دارایی"),
    (2, "بدهی"),
    (3, "سرمایه"),
    (4, "درآمد"),
    (5, "هزینه"),
    (6, "اشخاص"),
    (7, "موجودی کالا"),
    (8, "فروش کالا"),
    (9, "قیمت تمام‌شده کالای فروش‌رفته"),
]

GROUP_NAMES = dict(GROUP_CHOICES)

GROUP_NATURE = {
    1: "debit", 2: "credit", 3: "credit", 4: "credit",
    5: "debit", 6: "mixed", 7: "debit", 8: "credit", 9: "debit",
}

GROUP_STATEMENT = {1: "BS", 2: "BS", 3: "BS", 7: "BS", 4: "PL", 5: "PL", 8: "PL", 9: "PL"}

GROUP_DEFAULTS = {
    1: [
        ("11", "دارایی‌های ثابت"),
        ("12", "دارایی‌های نامشهود"),
        ("14", "اسناد دریافتنی"),
        ("15", "حساب‌های دریافتنی"),
        ("16", "سایر دریافتنی‌ها"),
        ("17", "موجودی نقد و بانک"),
    ],
    2: [
        ("23", "اسناد پرداختنی"),
        ("24", "حساب‌های پرداختنی"),
        ("25", "سایر پرداختنی‌ها"),
    ],
    3: [
        ("3101", "سرمایه"),
        ("3103", "سود (زیان) انباشته"),
    ],
    4: [
        ("4101", "درآمد عملیاتی"),
        ("4102", "سایر درآمدها"),
    ],
    5: [
        ("5101", "بهای تمام‌شده"),
        ("5201", "هزینه‌های فروش، اداری و عمومی"),
    ],
    6: [
        ("6101", "اشخاص حقیقی"),
        ("6201", "اشخاص حقوقی"),
    ],
    7: [
        ("7101", "موجودی کالا"),
    ],
    8: [
        ("8101", "فروش کالا"),
    ],
    9: [
        ("9101", "قیمت تمام‌شده کالای فروش‌رفته"),
    ],
}

DEFAULT_LEDGER_ACCOUNTS = {
    "110101": "صندوق",
    "110102": "بانک",
    "110103": "تنخواه",
}


def build_default_plan():
    """پلان حساب پیش‌فرض مطابق تصویر ۴ نگین پارسا (۹ گروه، ساختار ۴ سطحی).

    خروجی: فهرستی از dict با کلیدهای code/name/level/parent_code/group.
    """
    plan = []
    for group, subs in GROUP_DEFAULTS.items():
        gcode = str(group)
        plan.append({"code": gcode, "name": GROUP_NAMES[group], "level": 1,
                     "parent_code": None, "group": group})
        for kcode, kname in subs:
            parent_code = kcode[:2] if len(kcode) > 2 else gcode
            if parent_code != gcode and not any(p["code"] == parent_code for p in plan):
                plan.append({"code": parent_code, "name": kname, "level": 2,
                             "parent_code": gcode, "group": group})
            plan.append({"code": kcode, "name": kname, "level": 3 if len(kcode) > 2 else 2,
                         "parent_code": parent_code, "group": group, "leaf": len(kcode) > 2})
    for code, name in DEFAULT_LEDGER_ACCOUNTS.items():
        plan.append({"code": code, "name": name, "level": 3,
                     "parent_code": "1101" if code.startswith("1101") else "110102" if code == "110103" else "17",
                     "group": 1, "leaf": True})
    return plan


def next_child_code(parent: "Account"):
    """کد بعدی برای فرزندِ حساب داده‌شده (کد والد + شمارهٔ بعدی)."""
    used = set()
    for child in parent.children.all():
        suffix = child.code[len(parent.code):]
        if suffix.isdigit():
            used.add(int(suffix))
    i = 1
    while i in used:
        i += 1
    return parent.code + str(i)


class AccountingOrg(models.Model):
    """دفتر حسابداری مستقل متعلق به یک کاربر اصلی سایت (یگانه به ازای هر کاربر)."""

    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="accounting_org", verbose_name="کاربر مالک")
    name = models.CharField("نام دفتر", max_length=200, default="دفتر حسابداری من")
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)

    class Meta:
        verbose_name = "دفتر حسابداری"
        verbose_name_plural = "دفترهای حسابداری"

    def __str__(self):
        return f"{self.name} ({self.owner})"

    def get_or_create_user(self, username, password=None, full_name="", role="manager"):
        """ساخت (یا بازیابی) کاربر حسابداری برای این دفتر؛ کد ملی/موبایل مالک پیش‌فرض است."""
        user, created = AccountingUser.objects.get_or_create(
            org=self,
            username=username,
            defaults={"full_name": full_name, "role": role},
        )
        if created and password:
            user.set_password(password)
            user.save(update_fields=["password_hash"])
        return user, created


class FiscalYear(models.Model):
    """سال مالی — معادل «بانک اطلاعاتی» در نگین پارسا (حداکثر ۸ سال فعال)."""

    MAX_YEARS = 8

    org = models.ForeignKey(AccountingOrg, on_delete=models.CASCADE, related_name="fiscal_years")
    name = models.CharField("عنوان", max_length=120, blank=True)
    jalali_year = models.PositiveSmallIntegerField("سال شمسی")
    start_date = models.DateField("تاریخ شروع")
    end_date = models.DateField("تاریخ پایان")
    is_closed = models.BooleanField("بسته‌شده", default=False)
    is_default = models.BooleanField("پیش‌فرض ورود", default=False)
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)

    class Meta:
        verbose_name = "سال مالی"
        verbose_name_plural = "سال‌های مالی"
        ordering = ["-jalali_year"]
        constraints = [
            models.UniqueConstraint(fields=["org", "jalali_year"], name="uniq_accounting_fiscal_year"),
        ]

    def __str__(self):
        return self.name or en_to_fa(self.jalali_year)

    def clean_name(self):
        if not self.name:
            self.name = f"سال مالی {en_to_fa(self.jalali_year)}"

    def save(self, *args, **kwargs):
        self.clean_name()
        super().save(*args, **kwargs)


class AccountingUser(models.Model):
    """نام کاربری/کلمه عبور مجزا برای ورود به بخش حسابداری (غیر از اکانت اصلی سایت)."""

    ROLE_CHOICES = [
        ("manager", "مدیر"),
        ("accountant", "حسابدار"),
        ("viewer", "مشاهده‌کننده"),
    ]

    org = models.ForeignKey(AccountingOrg, on_delete=models.CASCADE, related_name="acc_users")
    username = models.CharField("نام کاربری", max_length=100)
    password_hash = models.CharField("کلمه عبور (هش)", max_length=255, blank=True)
    full_name = models.CharField("نام کامل", max_length=200, blank=True)
    role = models.CharField("نقش", max_length=20, choices=ROLE_CHOICES, default="manager")
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)

    class Meta:
        verbose_name = "کاربر حسابداری"
        verbose_name_plural = "کاربران حسابداری"
        constraints = [
            models.UniqueConstraint(fields=["org", "username"], name="uniq_accounting_username"),
        ]

    def __str__(self):
        return f"{self.username} ({self.org_id})"

    # ---------- رمز عبور (PBKDF2 جنگو، بدون وابستگی جدید) ----------
    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password) -> bool:
        from django.contrib.auth.hashers import check_password
        if not self.password_hash:
            return False
        return check_password(raw_password, self.password_hash)

    # ---------- مجوزها ----------
    ROLE_PERMS = {
        "manager": {"entry": "crud", "account": "crud", "cheque": "crud", "report": True, "settings": True},
        "accountant": {"entry": "crud", "account": "read", "cheque": "crud", "report": True, "settings": False},
        "viewer": {"entry": "read", "account": "read", "cheque": "read", "report": True, "settings": False},
    }

    def perm(self, key):
        return self.ROLE_PERMS.get(self.role, self.ROLE_PERMS["viewer"]).get(key)

    def can_write(self, key):
        perm = self.perm(key)
        return perm is True or perm == "crud"


class AccountingSession(models.Model):
    """نشست مجزای حسابداری — مستقل از نشست اصلی جنگو؛ انقضا پس از ۳۰ دقیقه بی‌فعالیتی."""

    SESSION_MINUTES = 30
    MAX_FAILED_LOGINS = 5
    LOCKOUT_MINUTES = 15

    user = models.ForeignKey(AccountingUser, on_delete=models.CASCADE, related_name="sessions")
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name="sessions")
    session_key = models.CharField("کلید نشست", max_length=64, unique=True)
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    last_activity = models.DateTimeField("آخرین فعالیت", auto_now=True)
    expires_at = models.DateTimeField("انقضا")
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "نشست حسابداری"
        verbose_name_plural = "نشست‌های حسابداری"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}@{self.fiscal_year.name}"

    @classmethod
    def new_key(cls):
        import secrets
        return secrets.token_urlsafe(48)

    def is_expired(self):
        from django.utils import timezone
        return self.is_active and timezone.now() > self.expires_at


class LoginAttempt(models.Model):
    """ثبت تلاش‌های ناموفق ورود برای قفل ۱۵ دقیقه‌ای پس از ۵ خطا (PRD §۹)."""

    org = models.ForeignKey(AccountingOrg, on_delete=models.CASCADE, related_name="login_attempts")
    username = models.CharField("نام کاربری", max_length=100)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    success = models.BooleanField("موفق", default=False)
    created_at = models.DateTimeField("زمان", auto_now_add=True)

    class Meta:
        verbose_name = "تلاش ورود"
        verbose_name_plural = "تلاش‌های ورود"
        ordering = ["-created_at"]


# ------------------------------------------------------------------ پلان حساب‌ها

class Account(models.Model):
    """حساب پلان — ۴ سطحی (گروه / کل / معین / تفصیلی) مطابق تصویر ۴."""

    LEVEL_GROUP = 1
    LEVEL_LEDGER = 2
    LEVEL_SUBSIDIARY = 3
    LEVEL_DETAIL = 4

    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name="accounts")
    code = models.CharField("کد", max_length=20)
    name = models.CharField("نام", max_length=200)
    level = models.PositiveSmallIntegerField("سطح", choices=[
        (1, "گروه"), (2, "حساب کل"), (3, "حساب معین"), (4, "حساب تفصیلی"),
    ])
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE,
                               related_name="children", verbose_name="حساب والد")
    group = models.PositiveSmallIntegerField("گروه", choices=GROUP_CHOICES)
    is_leaf = models.BooleanField("قابل استفاده در سند", default=False)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "حساب"
        verbose_name_plural = "پلان حساب‌ها"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["fiscal_year", "code"], name="uniq_account_code"),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    # ---------- ماهیت و گردش ----------
    @property
    def nature(self):
        return GROUP_NATURE[self.group]

    def balance(self):
        """ماندهٔ حساب از دید ماهیت گروه: بدهکار مثبت، بستانکار منفی (مگر اشخاص: بدهکار مثبت)."""
        agg = self.journal_lines.aggregate(
            d=models.Sum("debit"), c=models.Sum("credit"),
        )
        d = agg["d"] or Decimal("0")
        c = agg["c"] or Decimal("0")
        return d - c

    def has_transactions(self) -> bool:
        return self.journal_lines.exists()


class JournalEntry(models.Model):
    """سند حسابداری."""

    STATUS_DRAFT = "draft"
    STATUS_POSTED = "posted"
    STATUS_CANCELLED = "cancelled"
    STATUSES = [
        (STATUS_DRAFT, "پیش‌نویس"),
        (STATUS_POSTED, "ثبت‌شده"),
        (STATUS_CANCELLED, "لغو‌شده"),
    ]

    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT, related_name="journal_entries")
    number = models.PositiveIntegerField("شماره سند")
    date = models.DateField("تاریخ سند")
    description = models.CharField("شرح سند", max_length=500, blank=True)
    status = models.CharField("وضعیت", max_length=12, choices=STATUSES, default=STATUS_DRAFT)
    auto_code = models.CharField("کد سند خودکار", max_length=30, blank=True,
                                 help_text="برای اسناد خودکار چک/پرداخت (مثل RCPT-CHEQUE-1)")
    created_by = models.ForeignKey(AccountingUser, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="journal_entries",
                                   verbose_name="ایجادکننده")
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    posted_at = models.DateTimeField("زمان ثبت", null=True, blank=True)
    cancelled_at = models.DateTimeField("زمان لغو", null=True, blank=True)

    class Meta:
        verbose_name = "سند حسابداری"
        verbose_name_plural = "اسناد حسابداری"
        ordering = ["-date", "-number"]
        constraints = [
            models.UniqueConstraint(fields=["fiscal_year", "number"], name="uniq_journal_number"),
        ]

    def __str__(self):
        return f"سند {self.number} ({self.get_status_display()})"

    @property
    def total_debit(self):
        return self.lines.aggregate(s=models.Sum("debit"))["s"] or Decimal("0")

    @property
    def total_credit(self):
        return self.lines.aggregate(s=models.Sum("credit"))["s"] or Decimal("0")

    @property
    def is_balanced(self) -> bool:
        return self.total_debit == self.total_credit and self.total_debit > 0

    def can_edit(self) -> bool:
        """سند ثبت‌شده قابل ویرایش/حذف نیست — فقط لغو و سند اصلاحی (PRD §۹)."""
        return self.status == self.STATUS_DRAFT


class TransactionLine(models.Model):
    """ردیف سند حسابداری (آرتیکل)."""

    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    row_number = models.PositiveSmallIntegerField("ردیف")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="journal_lines")
    debit = models.DecimalField("بدهکار (ریال)", max_digits=20, decimal_places=0, default=Decimal("0"))
    credit = models.DecimalField("بستانکار (ریال)", max_digits=20, decimal_places=0, default=Decimal("0"))
    description = models.CharField("توضیحات", max_length=500, blank=True)
    # «اشخاص»: اتصال ردیف سند به کاربرِ اصلی سایت که کد ملی‌اش ثبت شده؛
    # مبنای دفتر بدهکار/بستانکار هر شخص در منوی «اشخاص» ماژول حسابداری است.
    person = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.PROTECT, related_name="accounting_transaction_lines",
        verbose_name="شخص (کاربر سایت)",
    )

    class Meta:
        verbose_name = "ردیف سند"
        verbose_name_plural = "ردیف‌های سند"
        ordering = ["row_number"]

    @property
    def person_display(self):
        """نمایش شخص متصل به ردیف: نام و نام خانوادگی + کد ملی (در صورت وجود)."""
        if not self.person_id:
            return ""
        profile = getattr(self.person, "profile", None)
        if profile is None:
            return str(self.person)
        return f"{profile.full_name} ({profile.national_id})"


# ------------------------------------------------------------------ خزانه‌داری: چک

class Cheque(models.Model):
    """چک دریافتی/پرداختی با ماشین وضعیت مطابق PRD §۳.۷ (سامانه صیاد)."""

    DIR_RECEIVED = "received"
    DIR_PAID = "paid"
    DIRECTIONS = [(DIR_RECEIVED, "دریافتی"), (DIR_PAID, "پرداختی")]

    STATUS_UNUSED = "unused"        # چک برگه‌ای صادرنشده از دفترچه
    STATUS_DRAFT = "draft"          # صادرشده/در جریان وصول
    STATUS_REGISTERED = "registered"  # ثبت‌شده در صیاد / تحویل‌شده
    STATUS_DEPOSITED = "deposited"  # واگذارشده به بانک
    STATUS_COLLECTED = "collected"  # وصول‌شده
    STATUS_BOUNCED = "bounced"      # برگشتی
    STATUS_CANCELLED = "cancelled"  # باطل‌شده

    STATUSES = [
        (STATUS_UNUSED, "صادرنشده"),
        (STATUS_DRAFT, "در جریان"),
        (STATUS_REGISTERED, "ثبت‌شده (صیاد)"),
        (STATUS_DEPOSITED, "واگذارشده به بانک"),
        (STATUS_COLLECTED, "وصول‌شده"),
        (STATUS_BOUNCED, "برگشتی"),
        (STATUS_CANCELLED, "باطل‌شده"),
    ]

    VALID_TRANSITIONS = {
        STATUS_UNUSED: [STATUS_DRAFT, STATUS_CANCELLED],
        STATUS_DRAFT: [STATUS_REGISTERED, STATUS_CANCELLED],
        STATUS_REGISTERED: [STATUS_DEPOSITED, STATUS_CANCELLED],
        STATUS_DEPOSITED: [STATUS_COLLECTED, STATUS_BOUNCED],
        STATUS_COLLECTED: [],
        STATUS_BOUNCED: [STATUS_DRAFT],  # پیگیری مجدد
        STATUS_CANCELLED: [],
    }

    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT, related_name="cheques")
    direction = models.CharField("نوع", max_length=10, choices=DIRECTIONS)
    number = models.CharField("شماره چک", max_length=30)
    sayad_id = models.CharField("شناسه صیاد", max_length=20, blank=True)
    amount = models.DecimalField("مبلغ (ریال)", max_digits=20, decimal_places=0)
    due_date = models.DateField("سررسید")
    issue_date = models.DateField("تاریخ صدور", null=True, blank=True)
    bank_name = models.CharField("بانک", max_length=100, blank=True)
    branch = models.CharField("شعبه", max_length=100, blank=True)
    account_number = models.CharField("شماره حساب", max_length=30, blank=True)
    party_name = models.CharField("طرف حساب", max_length=200, blank=True)
    description = models.CharField("شرح", max_length=500, blank=True)
    status = models.CharField("وضعیت", max_length=12, choices=STATUSES, default=STATUS_DRAFT)
    # حساب بانکی شرکت برای وصول چک دریافتی؛ خالی = حساب پیش‌فرض «بانک» (110102)
    deposit_account = models.ForeignKey(
        "Account", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="cheques_deposited", verbose_name="حساب وصول",
    )
    entry = models.ForeignKey(JournalEntry, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="cheques", verbose_name="سند مرتبط")
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "چک"
        verbose_name_plural = "چک‌ها"
        ordering = ["due_date", "-id"]

    def __str__(self):
        return f"چک {self.number} ({self.get_direction_display()} - {self.get_status_display()})"

    def can_transition(self, new_status) -> bool:
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])


class AuditLog(models.Model):
    """ردگیری تغییرات حساس: سند/چک/حساب/ورود (PRD §۹)."""

    ACTION_CHOICES = [
        ("login", "ورود"),
        ("logout", "خروج"),
        ("entry_post", "ثبت سند"),
        ("entry_cancel", "لغو سند"),
        ("entry_delete", "حذف سند"),
        ("account_create", "ایجاد حساب"),
        ("account_update", "ویرایش حساب"),
        ("account_delete", "حذف حساب"),
        ("cheque_status", "تغییر وضعیت چک"),
        ("fiscal_close", "بستن سال مالی"),
    ]

    org = models.ForeignKey(AccountingOrg, on_delete=models.CASCADE, related_name="audit_logs")
    user = models.ForeignKey(AccountingUser, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField("عملیات", max_length=20, choices=ACTION_CHOICES)
    object_repr = models.CharField("موضوع", max_length=300, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    created_at = models.DateTimeField("زمان", auto_now_add=True)

    class Meta:
        verbose_name = "رخداد حسابرسی"
        verbose_name_plural = "رخدادهای حسابرسی"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_action_display()} - {self.object_repr}"

    @classmethod
    def log(cls, org, user, action, object_repr="", ip=None):
        return cls.objects.create(org=org, user=user, action=action,
                                  object_repr=object_repr[:300], ip=ip)
