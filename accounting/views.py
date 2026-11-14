"""ویوهای ماژول حسابداری — مستقل از داشبورد کاربر با قالب/کوکی نشست اختصاصی.

جریان ورود (مطابق PRD §۳.۲ و تصاویر نگین پارسا):
  ۱) /accounting/ → اگر نشست فعال: داشبورد؛ وگرنه انتخاب سال مالی (تصویر ۱)
  ۲) /accounting/login/?fy=<id> → نام کاربری/کلمه عبور مجزای حسابداری (تصویر ۲)
  ۳) پس از تأیید → کوکی acc_session_key ست شده و کاربر به داشبورد چک می‌رود (تصویر ۳)
"""

import json
from decimal import Decimal

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.db.models import Sum
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import jalali
from .forms import AccountForm, AccountingLoginForm, FiscalYearForm
from .models import (
    Account,
    AccountingSession,
    AccountingUser,
    AuditLog,
    Cheque,
    FiscalYear,
    JournalEntry,
    TransactionLine,
)
from .services import (
    LineValidationError,
    authenticate_acc_user,
    balance_sheet,
    cancel_journal_entry,
    create_acc_session,
    create_cheque,
    create_cheque_entry,
    create_fiscal_year,
    create_journal_entry,
    cheque_dashboard,
    next_journal_number,
    upcoming_cheques,
    delete_journal_entry,
    destroy_acc_session,
    get_or_create_org,
    income_statement,
    person_ledger,
    persons_queryset,
    post_journal_entry,
    resolve_acc_session,
    statement_of_account,
    transition_cheque,
    trial_balance,
    update_journal_entry,
    validate_lines,
)

ACC_COOKIE = "acc_session_key"


# ------------------------------------------------------------------ helpers

def _acc_context(request):
    """نشست/دفتر/سال مالی فعال — برای همهٔ ویوهای داخلی."""
    sess, org, fy, acc_user = resolve_acc_session(request)
    return sess, org, fy, acc_user


def acc_login_required(view):
    """دکوراتور دسترسی: کاربر اصلی لاگین + نشست حسابداری فعال."""

    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("core:index")
        sess, org, fy, acc_user = _acc_context(request)
        if sess is None:
            return redirect("accounting:index")
        request.acc_session = sess
        request.acc_org = org
        request.acc_fy = fy
        request.acc_user = acc_user
        response = view(request, *args, **kwargs)
        # تمدید کوکی
        response.set_cookie(ACC_COOKIE, sess.session_key, max_age=60 * 60 * 8,
                            httponly=True, samesite="Lax")
        return response

    return wrapper


def _base_ctx(request, fy, acc_user, active):
    return {
        "fy": fy,
        "acc_user": acc_user,
        "active": active,
        "today_fa": jalali.JalaliDate.today().strftime_fa(),
        "can_settings": acc_user.can_write("settings") if acc_user else False,
    }


def _log(request, action, obj=""):
    return AuditLog.log(request.acc_org, request.acc_user, action, obj,
                        ip=request.META.get("REMOTE_ADDR"))


def _pending_cheques(request, leaf_accounts):
    """چک‌های پنل «ثبت چک» فرم سند — مشخصات خام؛ ذخیره در لحظهٔ ثبت/ذخیرهٔ سند.

    قالب، هر «ثبت چک» را هم به جدول ردیف‌ها اضافه می‌کند و هم در JSON
    pending_cheques نگه می‌دارد؛ اینجا فقط اعتبارسنجی/تجزیه انجام می‌شود.
    خروجی: فهرست dict برای create_cheque_entry.
    """
    try:
        specs_raw = json.loads(request.POST.get("pending_cheques") or "[]")
    except (ValueError, TypeError):
        specs_raw = []
    from accounts.models import Profile as _Profile
    specs = []
    for raw in specs_raw:
        if not isinstance(raw, dict):
            continue
        number = str(raw.get("number") or "").strip()
        if not number:
            raise ValueError("شماره چک را وارد کنید.")
        profile = None
        pid = str(raw.get("person_id") or "").strip()
        if pid.isdigit():
            profile = (_Profile.objects.select_related("user")
                       .filter(user_id=int(pid)).exclude(national_id="").first())
        if profile is None:
            raise ValueError("صاحب چک را از فهرست اشخاص انتخاب کنید.")
        due = jalali.parse_jalali_str(str(raw.get("due") or ""))
        if due is None:
            raise ValueError("سررسید چک نامعتبر است. نمونه: ۱۴۰۵/۰۸/۱۵")
        amount = str(raw.get("amount") or "").replace(",", "") or "0"
        bank_field = str(raw.get("bank") or "").strip()
        specs.append({
            "direction": "paid" if str(raw.get("direction") or "") == "paid" else "received",
            "number": number,
            "amount": jalali.fa_to_en(amount),
            "due_date": due,
            "sayad_id": str(raw.get("sayad") or "").strip(),
            "bank_name": bank_field.split("/")[0].strip() if bank_field else "",
            "branch": "/".join(bank_field.split("/")[1:]).strip() if "/" in bank_field else "",
            "party_name": profile.full_name,
            "description": str(raw.get("desc") or "").strip(),
            "person": profile.user,
            "deposit_account": (leaf_accounts.filter(pk=str(raw.get("deposit") or "")).first()
                                if str(raw.get("deposit") or "").strip().isdigit() else None),
        })
    return specs


def _entry_error_focus(exc, ch_number=""):
    """از خطای ثبت سند/چک، شناسهٔ فیلد مقصر برای فوکوس خودکار بساز.

    خروجی: dict یا None — قالب با json_script آن را به JS می‌دهد تا فیلد را
    باز کند، اسکرول و فوکوس و هایلایت نماید.
    """
    if isinstance(exc, LineValidationError):
        return {"panel": "lines", "row": exc.row, "field": exc.field or "acc"}
    msg = str(exc)
    if "صاحب چک" in msg:
        return {"panel": "cheque", "field": "ch_person"}
    if "سررسید چک" in msg:
        return {"panel": "cheque", "field": "ch_due"}
    if "مبلغ چک" in msg:
        return {"panel": "cheque", "field": "ch_amount"}
    if "شماره چک" in msg:
        return {"panel": "cheque", "field": "ch_number"}
    if ch_number:
        return {"panel": "cheque", "field": "ch_number"}
    if "تاریخ سند" in msg:
        return {"panel": "entry", "field": "id_date"}
    return None


def _form_repaint(request):
    """مقادیر POST برای بازپرکردن فرم پس از خطا (تا فوکوسِ فیلد مقصر بی‌فایده نباشد)."""
    post = request.POST
    rows = []
    i = 0
    while f"debit_{i}" in post or f"credit_{i}" in post or f"desc_{i}" in post or f"account_{i}" in post:
        rows.append({
            "idx": i,
            "account": (post.get(f"account_{i}") or "").strip(),
            "account_text": (post.get(f"account_text_{i}") or "").strip(),
            "person": (post.get(f"person_{i}") or "").strip(),
            "person_text": (post.get(f"person_text_{i}") or "").strip(),
            "debit": (post.get(f"debit_{i}") or "").strip(),
            "credit": (post.get(f"credit_{i}") or "").strip(),
            "desc": (post.get(f"desc_{i}") or "").strip(),
        })
        i += 1    # چک‌های در انتظارِ ثبت‌شده در جدول سند — بعد از خطا برمی‌گردند تا کاربر چیزی را از دست ندهد
    try:
        pending = json.loads(post.get("pending_cheques") or "[]")
    except (ValueError, TypeError):
        pending = []
    if not isinstance(pending, list):
        pending = []
    return {
        "date": (post.get("date") or "").strip(),
        "description": (post.get("description") or "").strip(),
        "rows": rows,
        "pending_cheques": [p for p in pending if isinstance(p, dict)],
    }


# ------------------------------------------------------------------ ورود دو مرحله‌ای

def index(request):
    """نقطهٔ ورود ماژول حسابداری: هدایت هوشمند بر اساس وضعیت نشست."""
    if not request.user.is_authenticated:
        return redirect("core:index")
    sess, org, fy, acc_user = _acc_context(request)
    if sess is not None:
        return redirect("accounting:dashboard")
    fiscal_years = FiscalYear.objects.filter(org=org).order_by("-jalali_year")
    if not fiscal_years:
        # اولین ورود: ساخت دفتر + سال مالی جاری + پلان حساب پیش‌فرض
        create_fiscal_year(org, jalali.JalaliDate.today().year, is_default=True)
        fiscal_years = FiscalYear.objects.filter(org=org).order_by("-jalali_year")
        messages.success(request, "دفتر حسابداری شما با سال مالی جاری و پلان حساب پیش‌فرض ایجاد شد.")
    return render(request, "accounting/fiscal_year_select.html", {
        "fiscal_years": fiscal_years,
        "org": org,
    })


def select_fiscal_year(request, fy_id):
    """انتخاب سال مالی → فرم ورود مجزای حسابداری."""
    if not request.user.is_authenticated:
        return redirect("core:index")
    org = get_or_create_org(request.user)
    get_object_or_404(FiscalYear, pk=fy_id, org=org)
    return redirect("accounting:login", fy_id=fy_id)


def login_view(request, fy_id):
    """گام دوم ورود: نام کاربری/کلمه عبور حسابداری (تصویر ۲)."""
    if not request.user.is_authenticated:
        return redirect("core:index")
    org = get_or_create_org(request.user)
    fy = get_object_or_404(FiscalYear, pk=fy_id, org=org)

    if request.method == "POST":
        form = AccountingLoginForm(request.POST)
        if form.is_valid():
            user, err = authenticate_acc_user(org, form.cleaned_data["username"],
                                              form.cleaned_data["password"], request=request)
            if err is None:
                # اولین ورود موفق هر سال مالیِ بدون کاربر → ساخت خودکار با رمز اولیه؟
                # خیر: کاربر باید از تنظیمات ساخته شود؛ اینجا فقط نشست می‌سازیم.
                sess = create_acc_session(user, fy)
                AuditLog.log(org, user, "login", f"ورود به {fy.name}",
                             ip=request.META.get("REMOTE_ADDR"))
                response = redirect("accounting:dashboard")
                response.set_cookie(ACC_COOKIE, sess.session_key,
                                    max_age=60 * AccountingSession.SESSION_MINUTES * 2,
                                    httponly=True, samesite="Lax")
                return response
            form.add_error(None, err)
    else:
        form = AccountingLoginForm()
    return render(request, "accounting/login.html", {"form": form, "fy": fy})


def logout_view(request):
    destroy_acc_session(request)
    response = redirect("accounting:index")
    response.delete_cookie(ACC_COOKIE)
    return response


@acc_login_required
@require_POST
def setup_credentials(request):
    """تعریف/تغییر نام کاربری و کلمه عبور حسابداری از داخل ماژول (نقش مدیر)."""
    if not request.acc_user.can_write("settings"):
        messages.error(request, "فقط مدیر دفتر می‌تواند کاربران حسابداری را مدیریت کند.")
        return redirect("accounting:dashboard")
    username = (request.POST.get("username") or "").strip()
    password = request.POST.get("password") or ""
    full_name = (request.POST.get("full_name") or "").strip()
    role = request.POST.get("role") or "accountant"
    if not username or len(password) < 4:
        messages.error(request, "نام کاربری و کلمه عبور (حداقل ۴ کاراکتر) الزامی است.")
        return redirect("accounting:settings")
    if role not in {"manager", "accountant", "viewer"}:
        role = "accountant"
    user, created = AccountingUser.objects.get_or_create(
        org=request.acc_org, username=username,
        defaults={"full_name": full_name, "role": role},
    )
    user.set_password(password)
    user.full_name = full_name or user.full_name
    user.role = role if not user.role else (role if created else user.role)
    if created:
        user.role = role
    user.save()
    _log(request, "account_update", f"{'ایجاد' if created else 'ویرایش'} کاربر حسابداری {username}")
    messages.success(request, f"کاربر حسابداری «{username}» {'ایجاد' if created else 'به‌روزرسانی'} شد.")
    return redirect("accounting:settings")


# ------------------------------------------------------------------ داشبورد (تصویر ۳)

@acc_login_required
def dashboard(request):
    ctx = _base_ctx(request, request.acc_fy, request.acc_user, "dashboard")
    ctx.update(cheque_dashboard(request.acc_fy))
    ctx["upcoming_cheques"] = upcoming_cheques(request.acc_fy, days=10)
    ctx["posted_count"] = request.acc_fy.journal_entries.filter(status=JournalEntry.STATUS_POSTED).count()
    ctx["draft_count"] = request.acc_fy.journal_entries.filter(status=JournalEntry.STATUS_DRAFT).count()
    return render(request, "accounting/dashboard.html", ctx)


# ------------------------------------------------------------------ پلان حساب‌ها (تصویر ۴)

@acc_login_required
def accounts_list(request):
    ctx = _base_ctx(request, request.acc_fy, request.acc_user, "accounts")
    q = (request.GET.get("q") or "").strip()
    qs = request.acc_fy.accounts.all().order_by("code")
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))
    ctx["accounts"] = qs
    ctx["q"] = q
    ctx["form"] = AccountForm(fiscal_year=request.acc_fy)
    ctx["can_write"] = request.acc_user.can_write("account")
    return render(request, "accounting/accounts.html", ctx)


@acc_login_required
@require_POST
def account_create(request):
    if not request.acc_user.can_write("account"):
        messages.error(request, "دسترسی لازم را ندارید.")
        return redirect("accounting:accounts")
    form = AccountForm(request.POST, fiscal_year=request.acc_fy)
    if form.is_valid():
        parent = form.cleaned_data["parent"]
        name = form.cleaned_data["name"].strip()
        code = next_child_code = _next_child_code(parent)
        Account.objects.create(
            fiscal_year=request.acc_fy, code=code, name=name,
            level=parent.level + 1, parent=parent, group=parent.group,
            is_leaf=parent.level + 1 == Account.LEVEL_DETAIL,
        )
        _log(request, "account_create", f"حساب {code} - {name}")
        messages.success(request, f"حساب «{name}» با کد {code} ایجاد شد.")
    else:
        for errs in form.errors.values():
            for e in errs:
                messages.error(request, e)
    return redirect("accounting:accounts")


def _next_child_code(parent):
    from .models import next_child_code
    return next_child_code(parent)


@acc_login_required
@require_POST
def account_toggle(request, pk):
    if not request.acc_user.can_write("account"):
        messages.error(request, "دسترسی لازم را ندارید.")
        return redirect("accounting:accounts")
    acc = get_object_or_404(Account, pk=pk, fiscal_year=request.acc_fy)
    if acc.has_transactions():
        messages.error(request, "حساب دارای تراکنش است و غیرفعال‌سازی از این مسیر مجاز نیست.")
        return redirect("accounting:accounts")
    acc.is_active = not acc.is_active
    acc.save(update_fields=["is_active"])
    _log(request, "account_update", f"{'فعال‌سازی' if acc.is_active else 'غیرفعال‌سازی'} {acc}")
    return redirect("accounting:accounts")


@acc_login_required
def account_ledger(request, pk):
    """دفتر حساب (گردش + مانده) — دکمهٔ «دفتر حساب» تصویر ۴."""
    acc = get_object_or_404(Account, pk=pk, fiscal_year=request.acc_fy)
    from .services import account_lines_queryset
    lines = account_lines_queryset(acc)
    running = Decimal("0")
    rows = []
    for ln in lines:
        running += ln.debit - ln.credit
        rows.append({
            "date_fa": jalali.format_jalali(ln.entry.date),
            "number": ln.entry.number,
            "description": ln.description or ln.entry.description,
            "debit": ln.debit, "credit": ln.credit, "balance": running,
        })
    ctx = _base_ctx(request, request.acc_fy, request.acc_user, "accounts")
    ctx.update({"account": acc, "rows": rows, "balance": running})
    return render(request, "accounting/account_ledger.html", ctx)


# ------------------------------------------------------------------ اسناد (تصویر ۵)

@acc_login_required
def entries_list(request):
    ctx = _base_ctx(request, request.acc_fy, request.acc_user, "entries")
    status = request.GET.get("status") or ""
    qs = request.acc_fy.journal_entries.all()
    if status in {"draft", "posted", "cancelled"}:
        qs = qs.filter(status=status)
    ctx["entries"] = qs[:200]
    ctx["status"] = status
    return render(request, "accounting/entries.html", ctx)


@acc_login_required
def entry_create(request):
    """سند جدید (و ویرایش سند پیش‌نویس از همین صفحه با ?edit=<id>).

    ستون «حساب / شخص» ادغام‌شده: حساب تفصیلی + شخص (کاربر دارای کد ملی) در یک
    فیلد واحد با جستجو. سندهای قبلی قابل بارگذاری و ویرایش‌اند.
    """
    ctx = _base_ctx(request, request.acc_fy, request.acc_user, "entries")
    # حساب‌های تفصیلی به‌همراه نام گروه والد برای جستجو (مثلاً تایپ «بانک»
    # همهٔ حساب‌های زیرمجموعهٔ بانک را می‌آورد)
    leaf_accounts = (request.acc_fy.accounts
                     .filter(is_leaf=True, is_active=True)
                     .select_related("parent").order_by("code"))

    # حالت ویرایش: بارگذاری سند پیش‌نویس موجود (?edit=<id> در گام نمایش،
    # و فیلد مخفی edit_pk در گام ذخیرهٔ فرم)
    editing_entry = None
    edit_param = (request.GET.get("edit") or request.POST.get("edit_pk") or "").strip()
    if edit_param.isdigit():
        candidate = JournalEntry.objects.filter(
            pk=int(edit_param), fiscal_year=request.acc_fy,
        ).first()
        if candidate is not None and candidate.status == JournalEntry.STATUS_DRAFT:
            editing_entry = candidate
        elif candidate is not None and request.method == "GET":
            messages.error(request, "فقط سند پیش‌نویس قابل ویرایش است؛ سند ثبت‌شده باید لغو و مجدداً ثبت شود.")
            return redirect("accounting:entry_create")

    if request.method == "POST":
        ch_number = ""  # سازگاری با خطایابی قدیمی
        date = jalali.parse_jalali_str(request.POST.get("date") or "")
        description = (request.POST.get("description") or "").strip()
        rows = []
        i = 0
        # ردیف‌ها: حساب/شخص از hidden inputs کامبوباکس جستجوی تایپی می‌آیند؛
        # حلقه تا آخرین ردیف موجود ادامه دارد (اگر حسابی انتخاب شده یا مبلغی هست).
        max_idx = -1
        for key in request.POST:
            if key.startswith("account_") or key.startswith("debit_") or key.startswith("credit_"):
                try:
                    max_idx = max(max_idx, int(key.rsplit("_", 1)[1]))
                except (ValueError, IndexError):
                    pass
        for i in range(max_idx + 1):
            acc_id = (request.POST.get(f"account_{i}") or "").strip()
            # سازگاری با مرورگرهای قدیمی/فیلدهای hidden: اگر فقط کد حساب (مثل 110102)
            # ارسال شده باشد، به شناسهٔ حساب ترجمه شود. اگر به‌جای شناسه، برچسب
            # («110102 - بانک») یا نامِ تنها آمده باشد، همان متن برای resolve
            # پایین نگه داشته می‌شود تا خطای «حساب نامعتبر» رخ ندهد.
            raw_acc = acc_id
            if acc_id and not acc_id.isdigit():
                acc_id = ""
            elif acc_id:
                exists = leaf_accounts.filter(pk=int(acc_id)).exists()
                if not exists:
                    by_code = leaf_accounts.filter(code=acc_id).first()
                    acc_id = str(by_code.pk) if by_code else ""
            # متن کامل برچسب/کد/نام — از account_i (برچسبِ رهاشده) یا کادر تایپ
            # (account_text_i) — پیش از خطا resolve می‌شود.
            raw = (request.POST.get(f"account_text_{i}") or raw_acc or "").strip()
            if not acc_id and raw:
                raw_en = jalali.fa_to_en(raw).strip()
                q_code = " ".join(raw_en.replace("-", " ").split())
                q_nospace = "".join(raw_en.split())
                cand = None
                for a in leaf_accounts:
                    lab = f"{a.code} - {a.name}"
                    lab_nospace = "".join(lab.split())
                    if (raw_en == lab or raw_en == a.name or raw_en == str(a.code)
                            or q_code == str(a.code)
                            or q_nospace == lab_nospace):
                        cand = a
                        break
                if cand is not None:
                    acc_id = str(cand.pk)
            # «اشخاص»: فیلد شخصِ ردیف (hidden کامبوباکس شخص)
            person = None
            person_raw = (request.POST.get(f"person_{i}")
                          or request.POST.get(f"person_text_{i}") or "").strip()
            if person_raw:
                from accounts.models import User as _SiteUser
                raw_en = jalali.fa_to_en(person_raw).strip()
                persons = list(persons_queryset())
                matched = None
                if raw_en.isdigit():
                    # اولویت با کد ملی (تا شناسهٔ عددی جای کد ملی را نگیرد)
                    for p in persons:
                        if str(p.national_id) == raw_en:
                            matched = p
                            break
                    if matched is None and len(raw_en) <= 8:
                        matched = next(
                            (p for p in persons if p.user_id == int(raw_en)), None)
                if matched is None:
                    # نام کامل یا برچسب کامل («نام (کد ملی)»)
                    matched = next(
                        (p for p in persons
                         if raw_en == (p.full_name or "").strip()
                         or raw_en == f"{p.full_name} ({p.national_id})"), None)
                if matched is not None:
                    person = matched.user
            # اگر ردیف شخص دارد اما حساب ندارد، حساب پیش‌فرض (اولین صندوق، سپس اولین بانک) جایگزین می‌شود
            # تا «انتخاب شخص» خودش یک ردیف سند کامل بسازد و کاربر با خطای «حساب نامعتبر» مواجه نشود.
            if person is not None and not acc_id:
                default_acc = leaf_accounts.filter(code__startswith="11").order_by("code").first() \
                    or leaf_accounts.order_by("code").first()
                if default_acc:
                    acc_id = str(default_acc.pk)
            debit = (request.POST.get(f"debit_{i}") or "").replace(",", "") or "0"
            credit = (request.POST.get(f"credit_{i}") or "").replace(",", "") or "0"
            desc = request.POST.get(f"desc_{i}") or ""
            # ردیف‌های ناشی از «ثبت چک» فلگ دارند؛ سرویس چک خودش ردیف‌ها را
            # می‌سازد — اینجا حذف می‌شوند تا دوباره‌شماری نشوند.
            if (request.POST.get(f"cheque_row_{i}") or "").strip():
                continue
            if acc_id or Decimal(debit) > 0 or Decimal(credit) > 0:
                acc = leaf_accounts.filter(pk=acc_id).first() if acc_id else None
                rows.append({
                    "account": acc,
                    "debit": jalali.fa_to_en(debit),
                    "credit": jalali.fa_to_en(credit),
                    "description": desc,
                    "person": person,
                })
        try:
            if date is None:
                raise ValueError("تاریخ سند نامعتبر است. نمونه: ۱۴۰۵/۰۷/۰۲")
            is_post = request.POST.get("action") == "post"
            # پنل «ثبت چک» فرم سند: چک‌های افزوده‌شده به جدول، همراه بقیهٔ ردیف‌ها
            # در همان سند ذخیره می‌شوند (در لحظهٔ ثبت/ذخیرهٔ سند — نه قبل از آن).
            cheque_specs = _pending_cheques(request, leaf_accounts)
            if editing_entry is not None:
                entry = update_journal_entry(
                    editing_entry, rows, date=date, description=description,
                    acc_user=request.acc_user, post=is_post,
                )
                _log(request, "entry_post", f"{'ثبت' if is_post else 'ویرایش'} سند {entry.number}")
                messages.success(
                    request,
                    f"سند شماره {entry.number} {'ثبت' if is_post else 'به‌روزرسانی'} شد.")
            else:
                if cheque_specs:
                    # چک(ها) + ردیف‌های دستی در «یک» سند با auto_code=cheq
                    entry, cheques = create_cheque_entry(
                        request.acc_fy, cheque_specs, rows=rows, date=date,
                        description=description, acc_user=request.acc_user,
                        post=is_post,
                    )
                    _log(request, "entry_post", f"ثبت سند {entry.number} با {len(cheques)} چک")
                    who = "، ".join(c.party_name for c in cheques)
                    if is_post:
                        messages.success(
                            request,
                            f"چک {cheques[0].number} برای {who} به سند شماره {entry.number} اضافه و سند ثبت شد.")
                    else:
                        messages.success(
                            request,
                            f"چک {cheques[0].number} برای {who} به سند پیش‌نویس شماره {entry.number} اضافه شد.")
                else:
                    entry = create_journal_entry(
                        request.acc_fy, rows, date=date, description=description,
                        acc_user=request.acc_user, post=is_post,
                    )
                    _log(request, "entry_post", f"ثبت سند {entry.number}")
                    messages.success(request, f"سند شماره {entry.number} با موفقیت ذخیره شد.")
            return redirect("accounting:entries")
        except ValueError as exc:
            messages.error(request, str(exc))
            # فیلد مقصر برای فوکوس خودکار + بازپرکردن فرم با مقادیر تایپ‌شده
            ctx["error_focus"] = _entry_error_focus(exc, ch_number)
            ctx["form_data"] = _form_repaint(request)
    ctx["leaf_accounts"] = [
        {
            "id": a.id,
            "code": a.code,
            "name": a.name,
            "parent_name": a.parent.name if a.parent else "",
        }
        for a in leaf_accounts
    ]
    # فهرست اشخاص (کاربران دارای کد ملی) برای انتخاب در ردیف‌های سند —
    # نام، فامیل و کد ملی جداگانه برای جفتِ هماهنگ و جستجوی نام فامیل
    ctx["persons"] = [
        {
            "id": p.user_id,
            "label": f"{p.full_name} ({p.national_id})",
            "name": p.full_name,
            "family": (p.last_name.familyname_fa if p.last_name else ""),
            "nid": p.national_id,
        }
        for p in persons_queryset()
    ]
    # سندهای قبلی برای ناوبری: سند قبل/بعد، انتخاب سریع و ویرایش پیش‌نویس‌ها
    # در حالت ویرایش، همان سند (هر وضعیتی) در فهرست دیده شود.
    all_qs = request.acc_fy.journal_entries.order_by("number")
    ctx["recent_entries"] = [
        e for e in all_qs
        if e.status == JournalEntry.STATUS_DRAFT or (editing_entry and e.pk == editing_entry.pk)
    ][-30:]
    ctx["prev_entry"] = (all_qs.filter(number__lt=(editing_entry.number if editing_entry
                                                else next_journal_number(request.acc_fy)))
                         .order_by("-number").first())
    ctx["next_entry"] = (all_qs.filter(number__gt=(editing_entry.number if editing_entry else 0))
                         .order_by("number").first())
    ctx["total_entries"] = all_qs.count()
    ctx["latest_entry"] = all_qs.order_by("-number").first()
    # حساب‌های وصول برای پنل چک: بانک‌ها و صندوق‌های شرکت (گروه ۱) تفصیلی
    ctx["deposit_accounts"] = (request.acc_fy.accounts
                               .filter(is_leaf=True, is_active=True, group=1)
                               .order_by("code"))
    ctx["editing_entry"] = editing_entry
    if editing_entry is not None:
        ctx["edit_date_fa"] = jalali.format_jalali(editing_entry.date)
        ctx["next_number"] = editing_entry.number
        ctx["edit_lines"] = []
        for ln in editing_entry.lines.select_related("account", "person__profile").all():
            prof = getattr(ln.person, "profile", None) if ln.person_id else None
            ctx["edit_lines"].append({
                "account_id": ln.account_id,
                "person_id": ln.person_id or "",
                "person_name": (getattr(prof, "full_name", "") or "") if prof else "",
                "person_nid": (getattr(prof, "national_id", "") or "") if prof else "",
                "debit": f"{ln.debit:,}" if ln.debit else "",
                "credit": f"{ln.credit:,}" if ln.credit else "",
                "description": ln.description,
            })
    else:
        ctx["today_fa"] = jalali.jalali_today_str()
        ctx["next_number"] = next_journal_number(request.acc_fy)
    # دادهٔ تقویم شمسی برای انتخابگر تاریخ (سال مالی جاری ± یک سال)
    ctx["calendar_year"] = request.acc_fy.jalali_year
    ctx["calendar_months"] = [
        {"n": m, "days": jalali.jalali_month_length(request.acc_fy.jalali_year, m)}
        for m in range(1, 13)
    ]
    return render(request, "accounting/entry_form.html", ctx)


@acc_login_required
def entry_detail(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, fiscal_year=request.acc_fy)
    ctx = _base_ctx(request, request.acc_fy, request.acc_user, "entries")
    ctx["entry"] = entry
    return render(request, "accounting/entry_detail.html", ctx)


@acc_login_required
@require_POST
def entry_post(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, fiscal_year=request.acc_fy)
    try:
        post_journal_entry(entry, acc_user=request.acc_user)
        messages.success(request, f"سند {entry.number} ثبت شد.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("accounting:entry_detail", pk=pk)


@acc_login_required
@require_POST
def entry_cancel(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, fiscal_year=request.acc_fy)
    try:
        cancel_journal_entry(entry, acc_user=request.acc_user)
        messages.success(request, f"سند {entry.number} لغو شد.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("accounting:entry_detail", pk=pk)


@acc_login_required
@require_POST
def entry_delete(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, fiscal_year=request.acc_fy)
    number = entry.number
    try:
        delete_journal_entry(entry, acc_user=request.acc_user)
        messages.success(request, f"سند {number} حذف شد.")
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("accounting:entry_detail", pk=pk)
    return redirect("accounting:entries")


# ------------------------------------------------------------------ چک‌ها

@acc_login_required
def cheques_list(request):
    ctx = _base_ctx(request, request.acc_fy, request.acc_user, "cheques")
    direction = request.GET.get("direction") or ""
    qs = request.acc_fy.cheques.all()
    if direction in {Cheque.DIR_RECEIVED, Cheque.DIR_PAID}:
        qs = qs.filter(direction=direction)
    cheques = list(qs[:200])
    for ch in cheques:
        ch.next_statuses = ch.VALID_TRANSITIONS.get(ch.status, [])
        # صاحب چک: شخصِ ردیفِ طرف حساب در سند خودکار چک (برای لینک «دفتر شخص»)
        ch.owner = None
        if ch.entry_id:
            if ch.direction == Cheque.DIR_RECEIVED:
                owner_line = (ch.entry.lines.filter(person__isnull=False)
                              .exclude(account__code="140101").first())
            else:
                owner_line = (ch.entry.lines.filter(person__isnull=False)
                              .exclude(account__code="230101").first())
            if owner_line is not None:
                prof = getattr(owner_line.person, "profile", None)
                ch.owner = {
                    "user_id": owner_line.person_id,
                    "name": (prof.full_name if prof else "") or str(owner_line.person),
                    "nid": (prof.national_id if prof else "") or "",
                }
    ctx["cheques"] = cheques
    ctx["direction"] = direction
    ctx["can_write"] = request.acc_user.can_write("cheque")
    return render(request, "accounting/cheques.html", ctx)


@acc_login_required
@require_POST
def cheque_create(request):
    """(منسوخ) ثبت چک از صفحهٔ گزارش چک‌ها — ثبت چک حالا از فرم سند جدید انجام می‌شود."""
    messages.info(
        request,
        "ثبت چک از فرم سند جدید (پنل «ثبت چک») انجام می‌شود؛ صاحب چک همان‌جا انتخاب و در سند ثبت می‌گردد.")
    return redirect("accounting:entry_create")


@acc_login_required
@require_POST
def cheque_transition(request, pk):
    if not request.acc_user.can_write("cheque"):
        messages.error(request, "دسترسی لازم را ندارید.")
        return redirect("accounting:cheques")
    cheque = get_object_or_404(Cheque, pk=pk, fiscal_year=request.acc_fy)
    new_status = request.POST.get("status") or ""
    try:
        transition_cheque(cheque, new_status, acc_user=request.acc_user)
        messages.success(request, f"وضعیت چک {cheque.number} به «{cheque.get_status_display()}» تغییر کرد.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("accounting:cheques")


# ------------------------------------------------------------------ اشخاص (کاربران دارای کد ملی)

@acc_login_required
def persons_list(request):
    """منوی «اشخاص»: دیتابیس کاربران اصلی سایت که کد ملی ثبت‌شده دارند.

    فیلدها: نام، نام خانوادگی، کد ملی؛ با جستجو. از این فهرست در اسناد
    (بدهکار/بستانکار ردیف‌ها) استفاده می‌شود.
    """
    ctx = _base_ctx(request, request.acc_fy, request.acc_user, "persons")
    q = (request.GET.get("q") or "").strip()
    profiles = persons_queryset(q)
    persons = []
    for p in profiles[:500]:
        persons.append({
            "user_id": p.user_id,
            "full_name": p.full_name,
            "first_name": p.first_name.first_name_fa if p.first_name else "",
            "last_name": p.last_name.familyname_fa if p.last_name else "",
            "national_id": p.national_id,
        })
    ctx["persons"] = persons
    ctx["total_count"] = profiles.count()
    ctx["q"] = q
    return render(request, "accounting/persons.html", ctx)


@acc_login_required
def person_ledger_view(request, user_id):
    """دفتر بدهکار/بستانکار یک شخص (کاربر سایت) در سال مالی فعال."""
    from accounts.models import User as _SiteUser
    person = get_object_or_404(
        _SiteUser.objects.select_related("profile"), pk=user_id,
        profile__national_id__gt="",
    )
    ctx = _base_ctx(request, request.acc_fy, request.acc_user, "persons")
    rows, balance = person_ledger(person, request.acc_fy)
    profile = person.profile
    ctx.update({
        "person": person,
        "full_name": profile.full_name,
        "national_id": profile.national_id,
        "rows": rows,
        "balance": balance,
    })
    return render(request, "accounting/person_ledger.html", ctx)


# ------------------------------------------------------------------ راهنما

@acc_login_required
def guide(request):
    """راهنمای جامع استفاده از ماژول حسابداری برای همهٔ بخش‌ها."""
    ctx = _base_ctx(request, request.acc_fy, request.acc_user, "guide")
    return render(request, "accounting/guide.html", ctx)


# ------------------------------------------------------------------ گزارش‌ها

@acc_login_required
def reports_trial_balance(request):
    ctx = _base_ctx(request, request.acc_fy, request.acc_user, "reports")
    level = int(request.GET.get("level") or 3)
    if level not in (2, 3, 4):
        level = 3
    rows, totals = trial_balance(request.acc_fy, level=level)
    ctx.update({"rows": rows, "totals": totals, "level": level})
    return render(request, "accounting/report_trial_balance.html", ctx)


@acc_login_required
def reports_income_statement(request):
    ctx = _base_ctx(request, request.acc_fy, request.acc_user, "reports")
    ctx.update(income_statement(request.acc_fy))
    return render(request, "accounting/report_income.html", ctx)


@acc_login_required
def reports_balance_sheet(request):
    ctx = _base_ctx(request, request.acc_fy, request.acc_user, "reports")
    ctx.update(balance_sheet(request.acc_fy))
    return render(request, "accounting/report_balance.html", ctx)


@acc_login_required
def reports_statement(request):
    """صورتحساب «از تاریخ تا تاریخ» برای یک حساب یا یک شخص.

    پارامترها: account=<pk> یا person=<pk> + date_from/date_to به شکل شمسی (۱۴۰۵/۰۷/۰۲).
    پیش‌فرض: از ابتدای سال مالی تا امروز.
    """
    ctx = _base_ctx(request, request.acc_fy, request.acc_user, "reports")
    fy = request.acc_fy
    leaf_accounts = (fy.accounts
                     .filter(is_leaf=True, is_active=True)
                     .select_related("parent").order_by("code"))
    subject = None
    subject_kind = ""
    account_pk = request.GET.get("account") or ""
    person_pk = request.GET.get("person") or ""
    if account_pk.isdigit():
        subject = get_object_or_404(Account, pk=int(account_pk), fiscal_year=fy)
        subject_kind = "account"
    elif person_pk.isdigit():
        from accounts.models import User as _SiteUser
        subject = get_object_or_404(
            _SiteUser.objects.select_related("profile"), pk=int(person_pk),
            profile__national_id__gt="",
        )
        subject_kind = "person"

    date_from = jalali.parse_jalali_str(request.GET.get("date_from") or "")
    date_to = jalali.parse_jalali_str(request.GET.get("date_to") or "")
    # تاریخ پیش‌فرض: ابتدای سال مالی تا امروز
    default_from_fa = jalali.format_jalali(fy.start_date)
    default_to_fa = jalali.format_jalali(timezone.localdate())

    # درخت آبشاری حساب‌ها به‌صورت فهرستِ مرتب با عمق و زنجیرهٔ پدران (برای آکاردئون قالب):
    # گروه (عمق ۰) → کل (۱) → معین (۲) → تفصیلی (۳) — بخش «نام حساب» صفحه صورتحساب.
    # فقط حساب‌هایی نمایش داده می‌شوند که ماندهٔ غیرصفر دارند (تا تاریخ انتخابی).
    zero = Decimal("0")

    def build_tree():
        lines_agg = (TransactionLine.objects
                     .filter(entry__fiscal_year=fy,
                             entry__status=JournalEntry.STATUS_POSTED))
        if date_to is not None:
            lines_agg = lines_agg.filter(entry__date__lte=date_to)
        agg = {row["account_id"]: row["bal"]
               for row in lines_agg
               .values("account_id")
               .annotate(bal=Sum("debit") - Sum("credit"))}
        all_accs = list(fy.accounts.filter(is_active=True).order_by("code"))
        by_parent = {}
        for a in all_accs:
            by_parent.setdefault(a.parent_id, []).append(a)

        memo_total = {}

        def subtree_total(pk):
            if pk in memo_total:
                return memo_total[pk]
            total = agg.get(pk, zero)
            for k in by_parent.get(pk, []):
                total += subtree_total(k.pk)
            memo_total[pk] = total
            return total

        memo_active = {}

        def has_active(pk):
            """آیا این گره یا یکی از نوادگانش ماندهٔ غیرصفر دارد؟"""
            if pk in memo_active:
                return memo_active[pk]
            res = subtree_total(pk) != zero
            if not res:
                for k in by_parent.get(pk, []):
                    if has_active(k.pk):
                        res = True
                        break
            memo_active[pk] = res
            return res

        parent_pks = {a.parent_id for a in all_accs if a.parent_id}
        rows = []

        def walk(parent_id, depth, ancestors):
            for a in by_parent.get(parent_id, []):
                if not has_active(a.pk):
                    continue
                rows.append({
                    "acc": a,
                    "depth": depth,
                    "has_children": a.pk in parent_pks,
                    "ancestors": ",".join(str(x) for x in ancestors),
                    "balance": subtree_total(a.pk),
                })
                walk(a.pk, depth + 1, ancestors + [a.pk])

        walk(None, 0, [])
        return rows

    ctx["account_tree"] = build_tree()
    # فهرست اشخاص (بخش «اشخاص» صفحه صورتحساب) — فقط اشخاصی که ماندهٔ غیرصفر دارند
    p_lines = (TransactionLine.objects
               .filter(entry__fiscal_year=fy,
                       entry__status=JournalEntry.STATUS_POSTED,
                       person__isnull=False))
    if date_to is not None:
        p_lines = p_lines.filter(entry__date__lte=date_to)
    p_agg = {row["person_id"]: row["bal"]
             for row in p_lines
             .values("person_id")
             .annotate(bal=Sum("debit") - Sum("credit"))}
    ctx["persons_list"] = [
        {"id": p.user_id, "name": p.full_name, "nid": p.national_id,
         "family": p.last_name.familyname_fa if p.last_name_id else "",
         "balance": p_agg.get(p.user_id, zero)}
        for p in persons_queryset() if p_agg.get(p.user_id, zero) != zero
    ]

    data = None
    if subject is not None:
        data = statement_of_account(subject, fy, date_from=date_from, date_to=date_to)
        if subject_kind == "account":
            ctx["subject_name"] = f"{subject.code} - {subject.name}"
            ctx["subject_code"] = subject.code
        else:
            prof = subject.profile
            ctx["subject_name"] = f"{prof.full_name} ({prof.national_id})"
            ctx["subject_code"] = prof.national_id
        ctx["subject_kind"] = subject_kind
        ctx["subject_pk"] = subject.pk
        ctx.update(data)
    ctx.update({
        "date_from_fa": jalali.format_jalali(date_from) if date_from else default_from_fa,
        "date_to_fa": jalali.format_jalali(date_to) if date_to else default_to_fa,
        "in_subject": subject is not None,
    })
    return render(request, "accounting/report_statement.html", ctx)


# ------------------------------------------------------------------ تنظیمات و سیستم

@acc_login_required
def settings_view(request):
    ctx = _base_ctx(request, request.acc_fy, request.acc_user, "settings")
    ctx["acc_users"] = request.acc_org.acc_users.all().order_by("username")
    ctx["fiscal_years"] = request.acc_org.fiscal_years.all().order_by("-jalali_year")
    ctx["audit_logs"] = request.acc_org.audit_logs.all()[:50]
    ctx["can_settings"] = request.acc_user.can_write("settings")
    ctx["fyform"] = FiscalYearForm()
    return render(request, "accounting/settings.html", ctx)


@acc_login_required
@require_POST
def fiscal_year_create(request):
    if not request.acc_user.can_write("settings"):
        messages.error(request, "فقط مدیر دفتر می‌تواند سال مالی تعریف کند.")
        return redirect("accounting:settings")
    form = FiscalYearForm(request.POST)
    if form.is_valid():
        try:
            fy = create_fiscal_year(request.acc_org, form.cleaned_data["jalali_year"],
                                    is_default=form.cleaned_data.get("is_default"))
            messages.success(request, f"سال مالی «{fy.name}» با پلان حساب پیش‌فرض ایجاد شد.")
        except ValueError as exc:
            messages.error(request, str(exc))
    return redirect("accounting:settings")


@acc_login_required
@require_POST
def fiscal_year_close(request, fy_id):
    if not request.acc_user.can_write("settings"):
        messages.error(request, "فقط مدیر دفتر می‌تواند سال مالی را ببندد.")
        return redirect("accounting:settings")
    fy = get_object_or_404(FiscalYear, pk=fy_id, org=request.acc_org)
    from .services import close_fiscal_year
    try:
        close_fiscal_year(fy)
        messages.success(request, f"سال مالی «{fy.name}» بسته شد و فقط خواندنی است.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("accounting:settings")
