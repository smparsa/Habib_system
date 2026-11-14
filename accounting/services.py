"""سرویس‌های حسابداری: دفتر کاربر و سال مالی، ورود، پلان حساب، سند دابل‌انتری، چک و گزارش‌ها.

همهٔ کوئری‌ها از org/fiscal_year عبور می‌کنند (ایزولاسیون row-level) و تغییرات
مالی درون db_transaction.atomic() انجام می‌شود.
"""

from datetime import timedelta
from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models import Sum
from django.db.models.functions import Lower
from django.utils import timezone

from . import jalali
from .models import (
    Account,
    AccountingOrg,
    AccountingSession,
    AccountingUser,
    AuditLog,
    Cheque,
    FiscalYear,
    GROUP_NATURE,
    JournalEntry,
    LoginAttempt,
    TransactionLine,
    build_default_plan,
    next_child_code,
)

ZERO = Decimal("0")


class LineValidationError(ValueError):
    """خطای اعتبارسنجی یک ردیف سند؛ برای فوکوس خودکار فیلد مقصر در فرم.

    row: شمارهٔ ردیف یک‌مبنا (1-based) یا 0- برای خطای کلی سند؛
    field: نام فیلد مقصر در ردیف (acc/debit/credit/amount) برای هایلایت.
    """

    def __init__(self, row=0, field="", message=""):
        super().__init__(message)
        self.row = row
        self.field = field


# ------------------------------------------------------------------ دفتر و سال مالی

def get_or_create_org(user):
    """دفتر حسابداری یگانهٔ کاربر؛ در اولین ورود خودکار ساخته می‌شود."""
    org, created = AccountingOrg.objects.get_or_create(
        owner=user, defaults={"name": f"دفتر حسابداری {user.mobile_number}"},
    )
    if created:
        AuditLog.log(org, None, "account_create", f"ایجاد دفتر برای {user.mobile_number}")
    return org


def create_fiscal_year(org, jalali_year, is_default=False):
    """ساخت سال مالی با مرز فروردین ۱ تا اسفند ۲۹/۳۰ + پلان حساب پیش‌فرض."""
    gy, gm, gd = jalali.jalali_to_gregorian(jalali_year, 1, 1)
    start = __import__("datetime").date(gy, gm, gd)
    end_year = jalali_year + 1
    gy2, gm2, gd2 = jalali.jalali_to_gregorian(end_year, 1, 1)
    from datetime import date as _date
    end = _date(gy2, gm2, gd2) - timedelta(days=1)

    if FiscalYear.objects.filter(org=org, jalali_year=jalali_year).exists():
        raise ValueError("برای این سال شمسی قبلاً سال مالی تعریف شده است.")
    if org.fiscal_years.count() >= FiscalYear.MAX_YEARS:
        raise ValueError(f"حداکثر {FiscalYear.MAX_YEARS} سال مالی قابل تعریف است.")

    with db_transaction.atomic():
        fy = FiscalYear.objects.create(
            org=org, jalali_year=jalali_year, start_date=start, end_date=end,
            is_default=is_default,
        )
        seed_default_plan(fy)
        if is_default:
            FiscalYear.objects.filter(org=org).exclude(pk=fy.pk).update(is_default=False)
    return fy


def seed_default_plan(fy):
    """ایجاد ۹ گروه + حساب‌های کل/معین + صندوق/بانک/تنخواه مطابق تصویر ۴."""
    plan = build_default_plan()
    cache = {}
    for item in plan:
        parent = cache.get(item["parent_code"])
        acc = Account.objects.create(
            fiscal_year=fy,
            code=item["code"],
            name=item["name"],
            level=item["level"],
            parent=parent,
            group=item["group"],
            is_leaf=item.get("leaf", False),
        )
        cache[item["code"]] = acc
    return cache


def close_fiscal_year(fy):
    """بستن سال مالی: انتقال ماندهٔ حساب‌های ترازنامه‌ای به «سود (زیان) انباشته»."""
    if fy.is_closed:
        raise ValueError("این سال مالی قبلاً بسته شده است.")
    if not fy.journal_entries.filter(status=JournalEntry.STATUS_POSTED).exists() and \
       not fy.accounts.filter(level__gte=3, is_active=True).exists():
        raise ValueError("سال مالی خالی است.")

    with db_transaction.atomic():
        cumulative = ZERO
        for acc in fy.accounts.filter(level__gte=2):
            bal = acc.balance()
            if bal == 0:
                continue
            if GROUP_NATURE[acc.group] != "debit":
                cumulative += bal  # بستانکار: سود
            # ماندهٔ حساب‌های ترازنامه‌ای در همین مدل سال بعد منتقل می‌شود (carry forward
            # کامل در همین فاز ساده نگه داشته شده و مانده در حساب خود باقی می‌ماند).
        fy.is_closed = True
        fy.save(update_fields=["is_closed"])
        AuditLog.log(fy.org, None, "fiscal_close", f"بستن {fy.name}")
    return cumulative


# ------------------------------------------------------------------ احراز هویت مجزا

def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return (xff.split(",")[0].strip() if xff else None) or request.META.get("REMOTE_ADDR")


def _is_locked(org, username):
    since = timezone.now() - timedelta(minutes=AccountingSession.LOCKOUT_MINUTES)
    fails = LoginAttempt.objects.filter(
        org=org, username=username, success=False, created_at__gte=since,
    ).count()
    return fails >= AccountingSession.MAX_FAILED_LOGINS


def authenticate_acc_user(org, username, password, request=None):
    """ورود به حسابداری؛ دو مسیر پشتیبانی می‌شود:

    ۱) اعتبارنامهٔ تعریف‌شده توسط کاربر در «پروفایل من ← اطلاعات امنیتی»
       (accounts.User.acc_username / acc_password) — مسیر اصلی و ترجیحی.
    ۲) کاربران داخلی دفتر (AccountingUser) که مدیر دفتر از تنظیمات می‌سازد
       (حسابدار/مشاهده‌کننده) — برای کارکنانِ دفترِ همان کاربر.

    قفل ورود پس از ۵ خطا در ۱۵ دقیقه روی هر دو مسیر اعمال می‌شود.
    خروجی: (user, error_msg) که user یک AccountingUser تازه/موجود متصل به نشست است.
    """
    ip = _client_ip(request) if request else None
    if _is_locked(org, username):
        return None, "به دلیل تلاش‌های ناموفق، ورود موقتاً قفل شده است. ۱۵ دقیقه بعد تلاش کنید."

    from django.contrib.auth import get_user_model

    User = get_user_model()
    # تطبیق نام کاربری به بزرگی/کوچکی حساس نیست (Lower روی نسخهٔ حروف‌کوچک؛
    # در هر دو دیتابیس MySQL و SQLite رفتار یکسان دارد).
    owner_user = (
        User.objects.annotate(acc_username_lower=Lower("acc_username"))
        .filter(acc_username_lower=(username or "").strip().lower())
        .first()
    )
    if owner_user is not None and owner_user.check_acc_password(password):
        LoginAttempt.objects.create(org=org, username=username, ip=ip, success=True)
        if owner_user == org.owner:
            acc_user = org.acc_users.filter(username=username).first()
            if acc_user is None:
                acc_user = AccountingUser.objects.create(
                    org=org, username=username,
                    full_name=getattr(owner_user.profile, "full_name", "") or username,
                    role="manager",
                )
            else:
                acc_user.role = "manager"
                acc_user.is_active = True
                acc_user.save(update_fields=["role", "is_active"])
            return acc_user, None
        return None, "نام کاربری یا کلمه عبور نادرست است."

    user = AccountingUser.objects.filter(org=org, username=username, is_active=True).first()
    if user and user.check_password(password):
        LoginAttempt.objects.create(org=org, username=username, ip=ip, success=True)
        return user, None

    LoginAttempt.objects.create(org=org, username=username, ip=ip, success=False)
    return None, "نام کاربری یا کلمه عبور نادرست است."


def create_acc_session(user, fiscal_year):
    """ساخت نشست حسابداری مستقل با انقضای ۳۰ دقیقه‌ای."""
    return AccountingSession.objects.create(
        user=user,
        fiscal_year=fiscal_year,
        session_key=AccountingSession.new_key(),
        expires_at=timezone.now() + timedelta(minutes=AccountingSession.SESSION_MINUTES),
    )


def resolve_acc_session(request):
    """بازیابی نشست فعال از کوکی اختصاصی؛ در صورت انقضا None برمی‌گرداند.

    خروجی: (session, org, fiscal_year, acc_user) یا (None, org, None, None)
    """
    org = get_or_create_org(request.user) if request.user.is_authenticated else None
    if org is None:
        return None, None, None, None

    key = request.COOKIES.get("acc_session_key")
    if not key:
        return None, org, None, None
    sess = (AccountingSession.objects
            .select_related("user", "fiscal_year")
            .filter(session_key=key, is_active=True, user__org=org, user__is_active=True)
            .first())
    if sess is None or sess.is_expired():
        if sess:
            sess.is_active = False
            sess.save(update_fields=["is_active"])
        return None, org, None, None
    # تمدید خودکار ۳۰ دقیقه‌ای
    sess.expires_at = timezone.now() + timedelta(minutes=AccountingSession.SESSION_MINUTES)
    sess.save(update_fields=["expires_at"])
    return sess, org, sess.fiscal_year, sess.user


def destroy_acc_session(request):
    key = request.COOKIES.get("acc_session_key")
    if key:
        AccountingSession.objects.filter(session_key=key).update(is_active=False)


# ------------------------------------------------------------------ اسناد دابل‌انتری

def next_journal_number(fy):
    last = fy.journal_entries.order_by("-number").values_list("number", flat=True).first()
    return (last or 0) + 1


def _to_decimal(value):
    """تبدیل امن مبلغ: '۱۰٬۰۰۰٬۰۰۰'، '10,000,000'، '۱۰۰' و Decimal پذیرفته می‌شود."""
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        return ZERO
    text = jalali.fa_to_en(str(value)).replace("٬", "").replace(",", "").strip()
    try:
        return Decimal(text)
    except Exception:
        raise ValueError(f"مبلغ نامعتبر: {value}")


def validate_lines(lines):
    """اعتبارسنجی ردیف‌ها: حساب تفصیلی، یک‌طرفه بودن هر ردیف، تراز کلی.

    lines: فهرستی از dict با کلیدهای account/debit/credit/description
    خطای هر ردیف با اضافه‌شدن «ردیف i:» همراه است تا فرم بتواند فیلد مقصر را
    (با کلاس اکسپشن LineValidationError) فوکوس کند.
    """
    if not lines:
        raise LineValidationError(-1, "", "سند بدون ردیف قابل ثبت نیست.")
    cleaned = []
    for i, ln in enumerate(lines, start=1):
        acc = ln.get("account")
        try:
            debit = _to_decimal(ln.get("debit"))
            credit = _to_decimal(ln.get("credit"))
        except ValueError as exc:
            raise LineValidationError(i, "debit", f"ردیف {i}: {exc}") from exc
        if debit < 0 or credit < 0:
            raise LineValidationError(i, "debit", f"ردیف {i}: مبلغ منفی مجاز نیست.")
        if debit > 0 and credit > 0:
            raise LineValidationError(i, "debit", f"ردیف {i}: همزمان بدهکار و بستانکار مجاز نیست.")
        if debit == 0 and credit == 0:
            raise LineValidationError(i, "debit", f"ردیف {i}: مبلغ صفر مجاز نیست.")
        if not acc or not isinstance(acc, Account):
            raise LineValidationError(
                i, "acc",
                f"نام حساب ردیف {i} را از فهرست جستجو انتخاب کنید — "
                "کافیست بخشی از نام یا کد حساب را تایپ و از فهرستِ بازشده انتخاب کنید.")
        if not acc.is_leaf:
            raise LineValidationError(i, "acc", f"ردیف {i}: فقط حساب تفصیلی در سند استفاده می‌شود ({acc}).")
        cleaned.append({"account": acc, "debit": debit, "credit": credit,
                        "description": (ln.get("description") or "").strip()[:500],
                        "person": ln.get("person")})
    total_d = sum((l["debit"] for l in cleaned), ZERO)
    total_c = sum((l["credit"] for l in cleaned), ZERO)
    if total_d != total_c:
        raise ValueError(f"سند تراز نیست: بدهکار {total_d:,} ≠ بستانکار {total_c:,}")
    return cleaned


def update_journal_entry(entry, lines, date=None, description="", acc_user=None, post=False):
    """ویرایش سند پیش‌نویس: جایگزینی کامل ردیف‌ها + به‌روزرسانی تاریخ/شرح.

    سند ثبت‌شده/لغوشده قابل ویرایش نیست (طبق PRD، سند اصلاحی جایگزین می‌شود).
    در صورت post=True، پس از ویرایش سند ثبت هم می‌شود.
    """
    if entry.status != JournalEntry.STATUS_DRAFT:
        raise ValueError("فقط سند پیش‌نویس قابل ویرایش است؛ برای اصلاح سند ثبت‌شده، آن را لغو و سند جدید بزنید.")
    if entry.fiscal_year.is_closed:
        raise ValueError("سال مالی بسته‌شده قابل تغییر نیست.")
    cleaned = validate_lines(lines)
    if date is not None:
        from datetime import date as _date
        if isinstance(date, _date) and (date < entry.fiscal_year.start_date or date > entry.fiscal_year.end_date):
            raise ValueError("تاریخ سند خارج از بازهٔ سال مالی است.")
        entry.date = date
    if description is not None:
        entry.description = description
    with db_transaction.atomic():
        entry.lines.all().delete()
        for i, ln in enumerate(cleaned, start=1):
            TransactionLine.objects.create(entry=entry, row_number=i, **ln)
        entry.save(update_fields=["date", "description"])
        if post:
            post_journal_entry(entry, acc_user=acc_user)
        else:
            AuditLog.log(entry.fiscal_year.org, acc_user, "entry_update", f"ویرایش سند {entry.number}")
    return entry


def create_journal_entry(fy, lines, date=None, description="", acc_user=None, post=True, auto_code=""):
    """ساخت سند (و در صورت post=True ثبت آن). خروجی JournalEntry.

    lines: [{'account': Account, 'debit': Decimal, 'credit': Decimal, 'description': str}]
    """
    from datetime import date as _date
    date = date or timezone.localdate()
    if date < fy.start_date or date > fy.end_date:
        raise ValueError("تاریخ سند خارج از بازهٔ سال مالی است.")
    cleaned = validate_lines(lines)

    with db_transaction.atomic():
        entry = JournalEntry.objects.create(
            fiscal_year=fy,
            number=next_journal_number(fy),
            date=date,
            description=description,
            status=JournalEntry.STATUS_DRAFT,
            auto_code=auto_code,
            created_by=acc_user,
        )
        for i, ln in enumerate(cleaned, start=1):
            TransactionLine.objects.create(entry=entry, row_number=i, **ln)
        if post:
            post_journal_entry(entry, acc_user=acc_user)
    return entry


def post_journal_entry(entry, acc_user=None):
    """ثبت نهایی سند (draft → posted) با بررسی مجدد تراز."""
    if entry.status != JournalEntry.STATUS_DRAFT:
        raise ValueError("فقط سند پیش‌نویس قابل ثبت است.")
    if not entry.is_balanced:
        raise ValueError("سند تراز نیست؛ ثبت ممکن نیست.")
    if entry.date < entry.fiscal_year.start_date or entry.date > entry.fiscal_year.end_date:
        raise ValueError("تاریخ سند خارج از بازهٔ سال مالی است.")
    if entry.fiscal_year.is_closed:
        raise ValueError("سال مالی بسته‌شده قابل تغییر نیست.")
    entry.status = JournalEntry.STATUS_POSTED
    entry.posted_at = timezone.now()
    entry.save(update_fields=["status", "posted_at"])
    AuditLog.log(entry.fiscal_year.org, acc_user, "entry_post", f"ثبت سند {entry.number}")
    return entry


def cancel_journal_entry(entry, acc_user=None):
    """لغو سند ثبت‌شده (posted → cancelled). ردیف‌ها حفظ می‌شوند اما در گردش حساب نمی‌آیند."""
    if entry.status != JournalEntry.STATUS_POSTED:
        raise ValueError("فقط سند ثبت‌شده قابل لغو است.")
    entry.status = JournalEntry.STATUS_CANCELLED
    entry.cancelled_at = timezone.now()
    entry.save(update_fields=["status", "cancelled_at"])
    AuditLog.log(entry.fiscal_year.org, acc_user, "entry_cancel", f"لغو سند {entry.number}")
    return entry


def delete_journal_entry(entry, acc_user=None):
    if entry.status != JournalEntry.STATUS_DRAFT:
        raise ValueError("فقط سند پیش‌نویس قابل حذف است.")
    AuditLog.log(entry.fiscal_year.org, acc_user, "entry_delete", f"حذف سند {entry.number}")
    entry.delete()


def account_lines_queryset(account, posted_only=True):
    """ردیف‌های یک حساب (دفتر معین) — فقط اسناد ثبت‌شده به‌صورت پیش‌فرض."""
    qs = account.journal_lines.filter(entry__fiscal_year=account.fiscal_year)
    if posted_only:
        qs = qs.filter(entry__status=JournalEntry.STATUS_POSTED)
    return qs.order_by("entry__date", "entry__number", "row_number")


# ------------------------------------------------------------------ اشخاص (کاربران دارای کد ملی)

def persons_queryset(q=""):
    """فهرست کاربران اصلی سایت که کد ملی ثبت‌شده دارند (منوی «اشخاص» حسابداری).

    خروجی: Profile به‌همراه کاربر؛ فیلد سبک برای نمایش نام/نام خانوادگی/کد ملی.
    """
    from accounts.models import Profile

    qs = (Profile.objects
          .filter(user__is_active=True)
          .exclude(national_id="")
          .exclude(national_id__isnull=True)
          .select_related("user", "first_name", "last_name")
          .order_by("last_name__familyname_fa", "first_name__first_name_fa"))
    if q:
        from django.db.models import Q
        qs = qs.filter(
            Q(national_id__icontains=q)
            | Q(first_name__first_name_fa__icontains=q)
            | Q(last_name__familyname_fa__icontains=q)
        )
    return qs


def person_ledger(user, fiscal_year):
    """دفتر بدهکار/بستانکار یک شخص (کاربر سایت) در سال مالی داده‌شده.

    ردیف‌های سندِ ثبت‌شده‌ای که شخصِ آن‌ها این کاربر است؛ مانده = بدهکار − بستانکار
    (مثبت = طلب از شخص، منفی = بدهی به شخص) مطابق دفتر اشخاص.
    """
    lines = (TransactionLine.objects
             .filter(person=user,
                     entry__fiscal_year=fiscal_year,
                     entry__status=JournalEntry.STATUS_POSTED)
             .select_related("entry", "account")
             .order_by("entry__date", "entry__number", "row_number"))
    running = ZERO
    rows = []
    for ln in lines:
        running += ln.debit - ln.credit
        rows.append({
            "date_fa": jalali.format_jalali(ln.entry.date),
            "number": ln.entry.number,
            "description": ln.description or ln.entry.description or "—",
            "account": ln.account,
            "debit": ln.debit,
            "credit": ln.credit,
            "balance": running,
        })
    return rows, running


def statement_of_account(subject, fiscal_year, date_from=None, date_to=None):
    """صورتحساب یک حساب یا یک شخص «از تاریخ تا تاریخ» (مبنای منوی گزارش‌ها).

    subject: یا Account (گردش دفتر معین) یا User سایت (گردش دفتر اشخاص).
    date_from/date_to: تاریخ میلادی (datetime.date) یا None — نقطهٔ شروع پیش‌فرض
    ابتدای سال مالی و نقطهٔ پایان پیش‌فرض امروز است.

    خروجی: dict شامل opening (مانده ابتدای دوره)، rows (ردیف‌های بازه با ماندهٔ
    running)، total_debit/total_credit/period_balance (جمع دوره) و closing
    (ماندهٔ پایان دوره = ماندهٔ ابتدای دوره + جمع دوره).
    """
    is_person = not hasattr(subject, "journal_lines")
    if is_person:
        base = (TransactionLine.objects
                .filter(person=subject,
                        entry__fiscal_year=fiscal_year,
                        entry__status=JournalEntry.STATUS_POSTED)
                .select_related("entry", "account"))
    else:
        base = (TransactionLine.objects
                .filter(account=subject,
                        entry__fiscal_year=fiscal_year,
                        entry__status=JournalEntry.STATUS_POSTED)
                .select_related("entry", "account"))
    if date_from is not None:
        base = base.filter(entry__date__gte=date_from)
    if date_to is not None:
        base = base.filter(entry__date__lte=date_to)

    # مانده ابتدای دوره: کل گردش «قبل از از تاریخ» (شامل اسناد پیش‌درآمد سال).
    before_qs = base.none()
    if date_from is not None:
        before_qs = base.model.objects.filter(
            **({"person": subject} if is_person else {"account": subject}),
            entry__fiscal_year=fiscal_year,
            entry__status=JournalEntry.STATUS_POSTED,
            entry__date__lt=date_from,
        )
        opening = sum((ln.debit - ln.credit for ln in before_qs), ZERO)
    else:
        opening = ZERO

    lines = base.order_by("entry__date", "entry__number", "row_number")
    running = opening
    rows = []
    for ln in lines:
        running += ln.debit - ln.credit
        rows.append({
            "date_fa": jalali.format_jalali(ln.entry.date),
            "number": ln.entry.number,
            "description": ln.description or ln.entry.description or "—",
            "account": ln.account,
            "person": ln.person,
            "debit": ln.debit,
            "credit": ln.credit,
            "balance": running,
        })
    total_d = sum((ln.debit for ln in lines), ZERO)
    total_c = sum((ln.credit for ln in lines), ZERO)
    return {
        "opening": opening,
        "rows": rows,
        "total_debit": total_d,
        "total_credit": total_c,
        "period_balance": total_d - total_c,
        "closing": opening + total_d - total_c,
    }


# ------------------------------------------------------------------ خزانه‌داری: چک

def _cheque_record(fy, direction, number, amount, due_date, *, sayad_id="", bank_name="",
                   branch="", account_number="", party_name="", description="",
                   issue_date=None):
    """ساخت رکورد چک (بدون سند)؛ ذخیرهٔ نهایی در تراکنش سند انجام می‌شود."""
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("مبلغ چک باید مثبت باشد.")
    return Cheque.objects.create(
        fiscal_year=fy, direction=direction, number=number, sayad_id=sayad_id,
        amount=amount, due_date=due_date, issue_date=issue_date,
        bank_name=bank_name, branch=branch, account_number=account_number,
        party_name=party_name, description=description,
        status=Cheque.STATUS_DRAFT,
    )


def _cheque_direction_lines(fy, ch, person=None):
    """ردیف‌های سندِ یک چک: دریافتی → بدهکار «اسناد دریافتنی» / بستانکار حساب صاحب چک.

    ردیف طرف حساب، «شخصِ صاحب چک» را دارد تا گردش در دفتر شخص هم ثبت شود.
    """
    recv = _leaf_account(fy, "140101", "اسناد دریافتنی", parent_code="14", group=1)
    pay = _leaf_account(fy, "230101", "اسناد پرداختنی", parent_code="23", group=2)
    party_acc = _party_account(fy, ch.party_name)
    doc_acc = recv if ch.direction == Cheque.DIR_RECEIVED else pay
    if ch.direction == Cheque.DIR_RECEIVED:
        return [
            {"account": doc_acc, "debit": ch.amount, "credit": ZERO,
             "description": f"دریافت چک {ch.number} از {ch.party_name}"},
            {"account": party_acc, "debit": ZERO, "credit": ch.amount,
             "description": f"دریافت چک {ch.number}", "person": person},
        ]
    return [
        {"account": party_acc, "debit": ch.amount, "credit": ZERO,
         "description": f"پرداخت چک {ch.number} به {ch.party_name}", "person": person},
        {"account": doc_acc, "debit": ZERO, "credit": ch.amount,
         "description": f"صدور چک {ch.number}"},
    ]


def create_cheque(fy, direction, number, amount, due_date, *, sayad_id="", bank_name="",
                  branch="", account_number="", party_name="", description="",
                  issue_date=None, acc_user=None, auto_entry=True, person=None,
                  deposit_account=None):
    """ثبت چک دریافتی/پرداختی + سند خودکار (auto_code=cheq) — مسیر قدیمی/سرویس‌ها.

    دریافت چک: بدهکار «اسناد دریافتنی» / بستانکار «حساب طرف»
    صدور (پرداخت) چک: بدهکار «حساب طرف» / بستانکار «اسناد پرداختنی»
    person: صاحب چک (کاربر سایت)؛ روی ردیفِ طرف حساب ثبت می‌شود (دفتر شخص).
    """
    with db_transaction.atomic():
        ch = _cheque_record(
            fy, direction, number, amount, due_date, sayad_id=sayad_id,
            bank_name=bank_name, branch=branch, account_number=account_number,
            party_name=party_name, description=description, issue_date=issue_date)
        if getattr(deposit_account, "is_leaf", False):
            ch.deposit_account = deposit_account
            ch.save(update_fields=["deposit_account"])
        if auto_entry:
            entry = create_journal_entry(
                fy, _cheque_direction_lines(fy, ch, person), date=due_date,
                description=("دریافت چک " if ch.direction == Cheque.DIR_RECEIVED else "صدور چک ") + number,
                acc_user=acc_user, post=True, auto_code="cheq",
            )
            ch.entry = entry
            ch.save(update_fields=["entry"])
    return ch


def create_cheque_entry(fy, cheque_specs, rows=(), date=None, description="",
                        acc_user=None, post=True):
    """چک‌های پنل «ثبت چک» فرم سند جدید → همراه بقیهٔ ردیف‌ها در «یک» سند (auto_code=cheq).

    تا زمان ثبت/ذخیرهٔ سند، چیزی ذخیره نمی‌شود؛ همهٔ چک‌ها و ردیف‌های دستی کاربر
    با یک تراکنش در یک سند ذخیره می‌شوند (در صورت post=True، ثبت هم می‌شود).
    هر spec: dict با کلیدهای direction/number/amount/due_date/sayad_id/bank_name/
    branch/party_name/description/person(User)/deposit_account(Account)/issue_date.
    خروجی: (JournalEntry, [Cheque])
    """
    specs = list(cheque_specs)
    if not specs:
        raise ValueError("مشخصات چک برای افزودن به سند کامل نیست.")
    with db_transaction.atomic():
        cheques = []
        for spec in specs:
            cheques.append(_cheque_record(
                fy, spec.get("direction", Cheque.DIR_RECEIVED), spec.get("number"),
                spec.get("amount"), spec.get("due_date"),
                sayad_id=spec.get("sayad_id", ""), bank_name=spec.get("bank_name", ""),
                branch=spec.get("branch", ""), party_name=spec.get("party_name", ""),
                description=spec.get("description", ""), issue_date=spec.get("issue_date"),
            ))
        for ch, spec in zip(cheques, specs):
            if getattr(spec.get("deposit_account"), "is_leaf", False):
                ch.deposit_account = spec["deposit_account"]
                ch.save(update_fields=["deposit_account"])
        lines = []
        for ch, spec in zip(cheques, specs):
            lines.extend(_cheque_direction_lines(fy, ch, spec.get("person")))
        lines.extend(rows)
        entry = create_journal_entry(
            fy, lines, date=date, description=description,
            acc_user=acc_user, post=post, auto_code="cheq",
        )
        for ch in cheques:
            ch.entry = entry
            ch.save(update_fields=["entry"])
    return entry, cheques


def _leaf_account(fy, code, name, *, parent_code, group):
    acc = fy.accounts.filter(code=code).first()
    if acc:
        return acc
    parent = fy.accounts.filter(code=parent_code).first()
    return Account.objects.create(
        fiscal_year=fy, code=code, name=name,
        level=(parent.level + 1) if parent else 3,
        parent=parent, group=group, is_leaf=True,
    )


def _party_account(fy, party_name):
    """حساب تفصیلی اشخاص (گروه ۶) به نام طرف حساب؛ در صورت نبود ساخته می‌شود."""
    name = (party_name or "متفرقه").strip()
    acc = fy.accounts.filter(name=name, group=6).first()
    if acc:
        return acc
    parent = fy.accounts.filter(code="6101").first()
    if parent is None:
        parent = _leaf_account(fy, "6101", "اشخاص حقیقی", parent_code="61", group=6)
    code = next_child_code(parent)
    return Account.objects.create(
        fiscal_year=fy, code=code, name=name, level=parent.level + 1,
        parent=parent, group=6, is_leaf=True,
    )


def transition_cheque(cheque, new_status, acc_user=None, *, bank_name=None, post_entry=True):
    """تغییر وضعیت چک طبق ماشین وضعیت + سند خودکار وصول/برگشت."""
    if not cheque.can_transition(new_status):
        raise ValueError(f"گذار وضعیت از «{cheque.get_status_display()}» به «{new_status}» مجاز نیست.")
    if cheque.fiscal_year.is_closed:
        raise ValueError("سال مالی بسته‌شده قابل تغییر نیست.")

    with db_transaction.atomic():
        old = cheque.status
        cheque.status = new_status
        cheque.save(update_fields=["status", "updated_at"])
        AuditLog.log(cheque.fiscal_year.org, acc_user, "cheque_status",
                     f"چک {cheque.number}: {old} → {new_status}")

        if post_entry and cheque.entry and new_status == Cheque.STATUS_COLLECTED and cheque.direction == Cheque.DIR_RECEIVED:
            fy = cheque.fiscal_year
            # وصول در حساب بانکی انتخاب‌شدهٔ چک؛ در نبود آن، حساب پیش‌فرض «بانک» (110102)
            bank_acc = (cheque.deposit_account
                        if cheque.deposit_account_id and cheque.deposit_account.is_leaf
                        else _leaf_account(fy, "110102", "بانک", parent_code="1101", group=1))
            recv_acc = _leaf_account(fy, "140101", "اسناد دریافتنی", parent_code="14", group=1)
            lines = [
                {"account": bank_acc, "debit": cheque.amount, "credit": ZERO, "description": f"وصول چک {cheque.number}"},
                {"account": recv_acc, "debit": ZERO, "credit": cheque.amount, "description": f"وصول چک {cheque.number}"},
            ]
            entry = create_journal_entry(fy, lines, date=cheque.due_date,
                                         description=f"وصول چک {cheque.number}", acc_user=acc_user, post=True)
            cheque.entry = entry
            cheque.save(update_fields=["entry"])
    return cheque


# ------------------------------------------------------------------ گزارش‌ها

def trial_balance(fy, level=3):
    """تراز آزمایشی: کد/نام/بدهکار/بستانکار/مانده به تفکیک حساب‌های سطح داده‌شده."""
    accounts = fy.accounts.filter(level=level, is_active=True).order_by("code")
    rows = []
    totals = {"debit": ZERO, "credit": ZERO, "balance": ZERO}
    for acc in accounts:
        agg = acc.journal_lines.filter(entry__status=JournalEntry.STATUS_POSTED).aggregate(
            d=Sum("debit"), c=Sum("credit"))
        d, c = agg["d"] or ZERO, agg["c"] or ZERO
        if d == 0 and c == 0:
            continue
        bal = d - c
        rows.append({"account": acc, "debit": d, "credit": c, "balance": bal})
        totals["debit"] += d
        totals["credit"] += c
        totals["balance"] += bal
    return rows, totals


def income_statement(fy):
    """صورت سود و زیان ساده بر اساس گروه‌های ۴، ۵، ۸ و ۹."""
    qs = fy.accounts.filter(level__gte=2, is_active=True)
    revenue = expense = cogs = ZERO
    for acc in qs:
        agg = acc.journal_lines.filter(entry__status=JournalEntry.STATUS_POSTED).aggregate(
            d=Sum("debit"), c=Sum("credit"))
        d, c = agg["d"] or ZERO, agg["c"] or ZERO
        bal = d - c  # بدهکار مثبت
        if acc.group == 4:
            revenue += -bal
        elif acc.group == 5:
            expense += bal
        elif acc.group == 8:
            revenue += -bal
        elif acc.group == 9:
            cogs += bal
    gross_profit = revenue - cogs
    net_profit = gross_profit - expense
    return {
        "revenue": revenue, "cogs": cogs, "gross_profit": gross_profit,
        "expense": expense, "net_profit": net_profit,
    }


def balance_sheet(fy):
    """ترازنامه ساده: ماندهٔ گروه‌های ۱، ۲، ۳ (+ سود دوره در سمت سرمایه)."""
    pl = income_statement(fy)
    assets = liabilities = equity = ZERO
    qs = fy.accounts.filter(level__gte=2, is_active=True)
    for acc in qs:
        agg = acc.journal_lines.filter(entry__status=JournalEntry.STATUS_POSTED).aggregate(
            d=Sum("debit"), c=Sum("credit"))
        d, c = agg["d"] or ZERO, agg["c"] or ZERO
        bal = d - c
        if acc.group == 1:
            assets += bal
        elif acc.group == 2:
            liabilities += -bal
        elif acc.group == 3:
            equity += -bal
    equity += pl["net_profit"]
    return {
        "assets": assets, "liabilities": liabilities, "equity": equity,
        "net_profit": pl["net_profit"],
        "difference": assets - (liabilities + equity),
    }


def cheque_dashboard(fy, delay_days=3):
    """داشبورد خلاصه چک‌ها مطابق تصویر ۳ (PRD §۳.۳)."""
    today = timezone.localdate()
    from django.db.models import Count

    def agg(qs):
        return qs.aggregate(n=Count("id"), s=Sum("amount"))

    received_today = agg(fy.cheques.filter(direction=Cheque.DIR_RECEIVED, due_date=today))
    paid_today = agg(fy.cheques.filter(direction=Cheque.DIR_PAID, due_date=today))
    received_total = agg(fy.cheques.filter(direction=Cheque.DIR_RECEIVED))
    paid_total = agg(fy.cheques.filter(direction=Cheque.DIR_PAID))

    def pack(a):
        return {"count": a["n"] or 0, "amount": a["s"] or ZERO}

    jtoday = jalali.JalaliDate.fromgregorian(date=today)
    return {
        "received_today": pack(received_today),
        "paid_today": pack(paid_today),
        "received_total": pack(received_total),
        "paid_total": pack(paid_total),
        "today_jalali": jtoday.strftime_fa(),
        "delay_days": delay_days,
    }


def upcoming_cheques(fy, days=10):
    """چک‌های نزدیک سررسید برای هشدار داشبورد.

    دریافتی‌ها/پرداختی‌هایی که هنوز وصول یا باطل نشده‌اند و سررسیدشان
    در بازهٔ [امروز − تأخیر پذیرفته، امروز + days] است؛ مرتب بر اساس سررسید.
    """
    from datetime import timedelta
    today = timezone.localdate()
    qs = (fy.cheques
          .exclude(status=Cheque.STATUS_COLLECTED)
          .exclude(status=Cheque.STATUS_CANCELLED)
          .filter(due_date__gte=today - timedelta(days=3),
                  due_date__lte=today + timedelta(days=days))
          .order_by("due_date"))
    items = []
    for ch in qs:
        delta = (ch.due_date - today).days
        if delta < 0:
            urgency = "overdue"
        elif delta <= 3:
            urgency = "soon"
        else:
            urgency = "upcoming"
        items.append({
            "cheque": ch,
            "days_left": delta,
            "urgency": urgency,
            "due_fa": jalali.format_jalali(ch.due_date),
        })
    return items
