"""
پنل مدیریت برنامه (فقط کاربر ادمین / is_staff).

ماژول‌های فعال:
- «کاتالوگ سلسله‌مراتبی مشاغل» (حوزه ← صنعت ← دسته ← عنوان ← کلید واژه شغل):
  افزودن/ویرایش/حذف/فعال‌سازی — با پیکربندی LAYERS.
- «کاربران و پروفایل‌ها»: فهرست/جستجو، فعال/غیرفعال‌کردن و ویرایش کاربر و پروفایل.
- «پالایش محتوا»: ثبت واژه‌ها و عبارت‌های حساس (فحش، سیاسی، مذهبی و ...) که موتور
  تیکت هنگام ارسالِ محتوای کاربران عادی به آن‌ها حساسیت نشان داده و با تذکر رد می‌کند.

این ساختار برای افزودن ماژول‌های مدیریتی دیگر (تیکت‌ها، مجله و ...) در آینده آماده
است؛ کافی است در «داشبورد پنل» یک کارت ماژول جدید اضافه شود.
"""

import os
import time
from decimal import Decimal
from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, ProtectedError, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import (
    CityTbl,
    CountryTbl,
    EducationInstitution,
    FameNameTbl,
    StudyField,
    StudyGroup,
    StudySpecialization,
    FamilynameTbl,
    FirstnameTbl,
    Job,
    LocationSetting,
    Profile,
    ProvinceTbl,
    ReservedNationalCode,
    User,
)
from adminpanel.models import (
    AD_STATUS_APPROVED,
    AD_STATUS_PENDING,
    AD_STATUS_REJECTED,
    AdTickerSetting,
    Advertisement,
    AdHeaderPlacement,
    BACKUP_KIND_AUTO,
    BACKUP_KIND_MANUAL,
    BACKUP_STATUS_OK,
    BackupFile,
    BackupSetting,
    BreakingNews,
    StatSlide,
    StatSlideBox,
    StatSlideSetting,
)
from jobs.models import (
    Industry,
    JobCategory,
    JobSpecialization,
    JobTitle,
    Sector,
)
from tickets import constants as TICKET_C
from tickets.models import (
    SensitiveTerm,
    TicketAudience,
    TicketAuditLog,
    TicketCategory,
)
from wallet.models import (
    CoinLedger,
    CoinOrder,
    CoinPriceHistory,
    CoinTransfer,
    FeatureCost,
    RewardRule,
    Wallet,
    WalletSetting,
)
from wallet.services import WalletError as WalletServiceError
from wallet.services import (
    adjust_balance,
    approve_order,
    current_rate,
    find_user_by_national_id,
    reject_order,
    set_coin_value,
    total_coins_in_circulation,
    transfer_coins,
)

from .backup_service import BackupError as BackupServiceError
from .backup_service import (
    auto_backup_if_due,
    backup_dir,
    db_config,
    days_since_last_success,
    delete_backup,
    default_backup_dir,
    run_backup,
    run_restore,
    safe_path_for,
)
from .forms import (
    ADMIN_PROFILE_SECTIONS,
    AdminProfileForm,
    AdminUserForm,
    BackupSettingsForm,
    BreakingNewsForm,
    AdHeaderPlacementForm,
    AdvertisementForm,
    StatSlideForm,
    EducationInstitutionForm,
    StudyFieldForm,
    StudyGroupForm,
    StudySpecializationForm,
    CityForm,
    CountryForm,
    FamilyNameForm,
    FameNameForm,
    FeatureCostForm,
    FirstNameForm,
    RewardRuleForm,
    ProvinceForm,
    IndustryForm,
    JobCategoryForm,
    JobSpecializationForm,
    JobTitleForm,
    LocationSettingsForm,
    ReservedNationalCodeForm,
    SectorForm,
    SensitiveTermForm,
    TicketAudienceForm,
    TicketCategoryForm,
    WalletSettingsForm,
)


# ---------------------------------------------------------------------------
# دسترسی: فقط ادمین (is_staff)
# ---------------------------------------------------------------------------


def staff_required(view_func):
    """هر ویوی پنل را به کاربران ادمین محدود می‌کند."""

    @wraps(view_func)
    @login_required(login_url="core:index")
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(
                request,
                "دسترسی به پنل مدیریت فقط برای کاربران ادمین ممکن است.",
            )
            return redirect("core:dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# کاربران و پروفایل‌ها — ابزارهای کمکی
# ---------------------------------------------------------------------------


def _users_list_url(request, page=None):
    """آدرس فهرست کاربران با حفظ فیلترهای جاری (q / state / role / page)."""
    params = {k: v for k, v in request.GET.items() if k != "page"}
    if page:
        params["page"] = str(page)
    url = reverse("adminpanel:users_list")
    if params:
        url += "?" + urlencode(params)
    return url


def _safe_next(request, default_url):
    """بازگشت امن به فهرست کاربران؛ فقط مسیرهای داخلیِ همین ماژول پذیرفته می‌شود."""
    value = (request.POST.get("next") or request.GET.get("next") or "").strip()
    list_prefix = reverse("adminpanel:users_list")
    if value.startswith(list_prefix) and "://" not in value:
        return value
    return default_url


def _user_label(user):
    """نام نمایشی کاربر: نام کامل پروفایل یا شماره موبایل."""
    try:
        full = user.profile.full_name
    except Profile.DoesNotExist:
        full = ""
    return full or user.mobile_number


# ---------------------------------------------------------------------------
# تعریف پنج لایهٔ کاتالوگ (پیکربندی یکتا؛ ماژول‌های بعدی همین‌جا اضافه می‌شوند)
# ---------------------------------------------------------------------------

def _desc_cell(desc):
    """مقدار «توضیحات» برای نمایش در فهرست؛ متن کامل می‌ماند و کوتاه‌سازی/بازشدن
    چندخطی در قالب (خط‌برش CSS + دکمهٔ نمایش کامل) انجام می‌شود."""
    desc = (desc or "").strip()
    return desc or "—"


LAYERS = {
    "sector": {
        "model": Sector,
        "form": SectorForm,
        "label": "حوزه",
        "plural": "حوزه‌ها",
        "icon": "bi-layers",
        "parent_model": None,
        "parent_field": None,
        "parent_label": None,
        "child": "industry",
        "child_label": "صنایع",
        "select_related": [],
        "cells": lambda obj: [("توضیحات", _desc_cell(obj.description))],
    },
    "industry": {
        "model": Industry,
        "form": IndustryForm,
        "label": "صنعت",
        "plural": "صنایع",
        "icon": "bi-building-gear",
        "parent_model": Sector,
        "parent_field": "sector",
        "parent_label": "حوزه",
        "child": "category",
        "child_label": "دسته‌ها",
        "select_related": ["sector", "parent"],
        "cells": lambda obj: [
            ("حوزه", obj.sector.name if obj.sector_id else "—"),
            ("توضیحات", _desc_cell(obj.description)),
        ],
    },
    "category": {
        "model": JobCategory,
        "form": JobCategoryForm,
        "label": "دسته",
        "plural": "دسته‌ها",
        "icon": "bi-collection",
        "parent_model": Industry,
        "parent_field": "industry",
        "parent_label": "صنعت",
        "child": "title",
        "child_label": "عناوین",
        "select_related": ["industry"],
        "cells": lambda obj: [
            ("صنعت", obj.industry.name if obj.industry_id else "—"),
            ("توضیحات", _desc_cell(obj.description)),
        ],
    },
    "title": {
        "model": JobTitle,
        "form": JobTitleForm,
        "label": "عنوان",
        "plural": "عناوین",
        "icon": "bi-card-heading",
        "parent_model": JobCategory,
        "parent_field": "category",
        "parent_label": "دسته",
        "child": "specialization",
        "child_label": "کلید واژه‌های شغل",
        "select_related": ["category"],
        "cells": lambda obj: [
            ("دسته", obj.category.name if obj.category_id else "—"),
            ("توضیحات", _desc_cell(obj.description)),
        ],
    },
    "specialization": {
        "model": JobSpecialization,
        "form": JobSpecializationForm,
        "label": "کلید واژه شغل",
        "plural": "کلید واژه‌های شغل",
        "icon": "bi-person-badge",
        "parent_model": JobTitle,
        "parent_field": "title",
        "parent_label": "عنوان",
        "child": None,
        "child_label": None,
        "select_related": ["title"],
        "cells": lambda obj: [
            ("عنوان", obj.title.name if obj.title_id else "—"),
            ("توضیحات", _desc_cell(obj.description)),
        ],
    },
}


def _get_layer(layer):
    cfg = LAYERS.get(layer)
    if cfg is None:
        raise Http404("لایهٔ موردنظر در پنل مدیریت تعریف نشده است.")
    return cfg


def _list_url(layer, parent=None):
    """آدرس فهرست یک لایه؛ در صورت وجود والد، به‌همان بافت برمی‌گردد."""
    url = reverse("adminpanel:layer_list", args=[layer])
    if parent is not None:
        url += f"?parent={parent.pk}"
    return url


def _parent_context(cfg, request):
    """والدِ فیلتر (مثلاً حوزه برای صنایع) و فیلتر مربوطه را برمی‌گرداند."""
    parent = None
    filt = {}
    if cfg["parent_model"]:
        parent_id = request.GET.get("parent")
        if parent_id:
            parent = get_object_or_404(cfg["parent_model"], pk=parent_id)
            filt[cfg["parent_field"]] = parent
    return parent, filt


# ---------------------------------------------------------------------------
# داشبورد پنل مدیریت + خانهٔ کاتالوگ
# ---------------------------------------------------------------------------


@staff_required
def dashboard(request):
    """صفحهٔ اصلی پنل مدیریت: آمار و ماژول‌های مدیریتی (آینده: کامل‌تر می‌شود)."""
    counts = {key: cfg["model"].objects.count() for key, cfg in LAYERS.items()}
    return render(
        request,
        "adminpanel/dashboard.html",
        {
            "counts": counts,
            "job_count": Job.objects.count(),
            "user_count": User.objects.count(),
            "first_name_count": FirstnameTbl.objects.count(),
            "family_name_count": FamilynameTbl.objects.count(),
            "country_count": CountryTbl.objects.count(),
            "province_count": ProvinceTbl.objects.count(),
            "city_count": CityTbl.objects.count(),
            "national_code_reserved_count": ReservedNationalCode.objects.count(),
            "national_code_reserved_active": ReservedNationalCode.objects.filter(is_active=True).count(),
            "inactive_user_count": User.objects.filter(is_active=False).count(),
            "admin_count": User.objects.filter(is_staff=True).count(),
            "layers": LAYERS,
            "word_count": SensitiveTerm.objects.count(),
            "word_active_count": SensitiveTerm.objects.filter(is_active=True).count(),
            "blocked_count": TicketAuditLog.objects.filter(
                action=TICKET_C.ACT_CONTENT_BLOCKED
            ).count(),
            "audience_count": TicketAudience.objects.count(),
            "audience_active_count": TicketAudience.objects.filter(is_active=True).count(),
            "ticket_type_count": TicketCategory.objects.count(),
            "ticket_type_active_count": TicketCategory.objects.filter(is_active=True).count(),
            # سکه و کیف پول
            "coin_rate": current_rate(),
            "total_coins": total_coins_in_circulation(),
            "wallet_count": Wallet.objects.count(),
            "pending_order_count": CoinOrder.objects.filter(
                status=CoinOrder.STATUS_PENDING
            ).count(),
            "feature_cost_count": FeatureCost.objects.filter(is_active=True).count(),
            "reward_rule_count": RewardRule.objects.filter(is_active=True).count(),
            "reward_rule_total": RewardRule.objects.count(),
            # پشتیبان‌گیری
            "last_backup": _backup_dashboard_stats(),
        },
    )


def _backup_dashboard_stats():
    """اطلاعات کارت «آخرین پشتیبان موفق» برای داشبورد (بدون تماس با دیسک)."""
    from adminpanel.models import BackupSetting

    days, last = days_since_last_success()
    setting = BackupSetting.get()
    warn_days = setting.stale_after_days or 3
    return {
        "exists": last is not None,
        "created_at": last.created_at if last else None,
        "filename": last.filename if last else "",
        "kind": last.kind if last else "",
        "days": days,
        "days_int": int(days) if days is not None else None,
        "stale": days is None or days >= warn_days,
        "warn_days": warn_days,
    }


@staff_required
def catalog_home(request):
    """خانهٔ ماژول کاتالوگ مشاغل: جستجو در هر پنج لایه + دسترسی سریع."""
    q = (request.GET.get("q") or "").strip()
    results = {}
    if q:
        for key, cfg in LAYERS.items():
            results[key] = list(
                cfg["model"].objects.filter(
                    Q(name__icontains=q) | Q(code__icontains=q) | Q(description__icontains=q)
                )[:15]
            )
    counts = {key: cfg["model"].objects.count() for key, cfg in LAYERS.items()}
    found_any = q and any(results.values())
    return render(
        request,
        "adminpanel/catalog_home.html",
        {
            "q": q,
            "results": results,
            "found_any": found_any,
            "counts": counts,
            "layers": LAYERS,
            "job_count": Job.objects.count(),
        },
    )


# ---------------------------------------------------------------------------
# فهرست / افزودن / ویرایش / حذف / فعال‌سازی — عمومی برای هر پنج لایه
# ---------------------------------------------------------------------------


@staff_required
def layer_list(request, layer):
    cfg = _get_layer(layer)
    parent, filt = _parent_context(cfg, request)
    q = (request.GET.get("q") or "").strip()
    active = request.GET.get("active")

    qs = cfg["model"].objects.filter(**filt).select_related(*cfg["select_related"])
    if active == "1":
        qs = qs.filter(is_active=True)
    elif active == "0":
        qs = qs.filter(is_active=False)
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(code__icontains=q) | Q(description__icontains=q)
        )

    rows = []
    for obj in qs:
        rows.append(
            {
                "pk": obj.pk,
                "name": obj.name,
                "code": obj.code,
                "is_active": obj.is_active,
                "cells": cfg["cells"](obj),
            }
        )

    return render(
        request,
        "adminpanel/layer_list.html",
        {
            "layer": layer,
            "cfg": cfg,
            "parent": parent,
            "q": q,
            "active": active,
            "rows": rows,
            "total": cfg["model"].objects.filter(**filt).count(),
        },
    )


@staff_required
def layer_add(request, layer):
    cfg = _get_layer(layer)
    parent, _ = _parent_context(cfg, request)

    initial = {}
    if parent is not None:
        initial[cfg["parent_field"]] = parent.pk

    form = cfg["form"](request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"{cfg['label']} «{obj.name}» با موفقیت افزوده شد.")
        return redirect(_list_url(layer, parent))

    return render(
        request,
        "adminpanel/layer_form.html",
        {"layer": layer, "cfg": cfg, "form": form, "mode": "add", "parent": parent},
    )


@staff_required
def layer_edit(request, layer, pk):
    cfg = _get_layer(layer)
    obj = get_object_or_404(cfg["model"], pk=pk)

    form = cfg["form"](request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{cfg['label']} «{obj.name}» به‌روزرسانی شد.")
        parent = getattr(obj, cfg["parent_field"], None) if cfg["parent_field"] else None
        return redirect(_list_url(layer, parent))

    return render(
        request,
        "adminpanel/layer_form.html",
        {"layer": layer, "cfg": cfg, "form": form, "mode": "edit", "parent": None},
    )


# ---------------------------------------------------------------------------
# ماژول «پالایش محتوا»: واژه‌ها و عبارت‌های حساس تیکت‌ها
# ---------------------------------------------------------------------------


def _words_list_url(request):
    """آدرس فهرست واژه‌های حساس با حفظ فیلترهای جاری (q / category / active / page)."""
    params = {k: v for k, v in request.GET.items() if k != "page"}
    url = reverse("adminpanel:words_list")
    if params:
        url += "?" + urlencode(params)
    return url


def _category_label(code):
    for value, label in TICKET_C.CONTENT_CATEGORIES:
        if value == code:
            return label
    return code


def _mode_label(code):
    for value, label in TICKET_C.CONTENT_MODES:
        if value == code:
            return label
    return code


@staff_required
def words_list(request):
    """فهرست واژه‌های حساس + جستجو/فیلتر + «آزمون متن» برای ادمین."""
    q = (request.GET.get("q") or "").strip()
    category = request.GET.get("category") or ""
    active = request.GET.get("active") or ""

    # «آزمون متن»: بررسی نمونه‌متن ادمین با موتور پالایش (بدون ذخیره)
    test_result = None
    if request.method == "POST" and request.POST.get("test_text") is not None:
        from tickets.filtering import block_message, find_violations

        sample = request.POST.get("test_text", "")
        if sample.strip():
            hits = find_violations(sample)
            test_result = {
                "text": sample,
                "hits": hits,
                "blocked": bool(hits),
                "message": block_message(hits) if hits else (
                    "نتیجه‌ای یافت نشد؛ متن موردنظر از فیلتر عبور می‌کند."
                ),
            }

    qs = SensitiveTerm.objects.all()
    if category:
        qs = qs.filter(category=category)
    if active == "1":
        qs = qs.filter(is_active=True)
    elif active == "0":
        qs = qs.filter(is_active=False)
    if q:
        qs = qs.filter(term__icontains=q)

    total = qs.count()
    page_obj = Paginator(qs, 25).get_page(request.GET.get("page"))
    rows = []
    for item in page_obj.object_list:
        rows.append({
            "pk": item.pk,
            "term": item.term,
            "mode": item.mode,
            "mode_label": _mode_label(item.mode),
            "category": item.category,
            "category_label": _category_label(item.category),
            "note": item.note,
            "is_active": item.is_active,
            "updated_at": item.updated_at,
        })

    base_params = {k: v for k, v in request.GET.items() if k != "page"}
    return render(
        request,
        "adminpanel/words_list.html",
        {
            "q": q,
            "category": category,
            "active": active,
            "rows": rows,
            "total": total,
            "page_obj": page_obj,
            "base_query": urlencode(base_params),
            "next_url": _words_list_url(request),
            "test_result": test_result,
            "categories": TICKET_C.CONTENT_CATEGORIES,
            "active_count": SensitiveTerm.objects.filter(is_active=True).count(),
        },
    )


@staff_required
def word_add(request):
    """افزودن واژه/عبارت حساس جدید."""
    form = SensitiveTermForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(
            request, f"واژهٔ «{item.term}» ثبت شد و از این پس پالایش می‌شود."
        )
        return redirect(_words_list_url(request))
    return render(
        request,
        "adminpanel/word_form.html",
        {"form": form, "mode": "add", "next_url": _words_list_url(request)},
    )


@staff_required
def word_edit(request, pk):
    """ویرایش واژه/عبارت حساس."""
    item = get_object_or_404(SensitiveTerm, pk=pk)
    form = SensitiveTermForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"واژهٔ «{item.term}» به‌روزرسانی شد.")
        return redirect(_words_list_url(request))
    return render(
        request,
        "adminpanel/word_form.html",
        {"form": form, "mode": "edit", "next_url": _words_list_url(request)},
    )


@staff_required
@require_POST
def word_toggle(request, pk):
    """فعال/غیرفعال‌کردن واژهٔ حساس (جایگزین امنِ حذف)."""
    item = get_object_or_404(SensitiveTerm, pk=pk)
    item.is_active = not item.is_active
    item.save(update_fields=["is_active"])
    messages.success(
        request,
        f"واژهٔ «{item.term}» {'فعال' if item.is_active else 'غیرفعال'} شد.",
    )
    return redirect(_words_list_url(request))


@staff_required
@require_POST
def word_delete(request, pk):
    """حذف کامل واژهٔ حساس."""
    item = get_object_or_404(SensitiveTerm, pk=pk)
    term = item.term
    item.delete()
    messages.success(request, f"واژهٔ «{term}» حذف شد.")
    return redirect(_words_list_url(request))


@staff_required
@require_POST
def layer_delete(request, layer, pk):
    cfg = _get_layer(layer)
    obj = get_object_or_404(cfg["model"], pk=pk)
    parent = getattr(obj, cfg["parent_field"], None) if cfg["parent_field"] else None
    try:
        obj.delete()
        messages.success(request, f"«{obj.name}» حذف شد.")
    except ProtectedError:
        messages.error(
            request,
            f"«{obj.name}» زیرمجموعه دارد یا توسط مشاغلِ کاربران استفاده می‌شود؛ "
            "ابتدا زیرمجموعه‌ها را حذف/انتقال دهید یا رکورد را «غیرفعال» کنید.",
        )
    return redirect(_list_url(layer, parent))


@staff_required
@require_POST
def layer_toggle(request, layer, pk):
    cfg = _get_layer(layer)
    obj = get_object_or_404(cfg["model"], pk=pk)
    parent = getattr(obj, cfg["parent_field"], None) if cfg["parent_field"] else None
    obj.is_active = not obj.is_active
    obj.save(update_fields=["is_active"])
    messages.success(
        request,
        f"«{obj.name}» {'فعال' if obj.is_active else 'غیرفعال'} شد.",
    )
    return redirect(_list_url(layer, parent))


# ---------------------------------------------------------------------------
# ماژول «کاربران و پروفایل‌ها»: فهرست/جستجو، فعال‌سازی و ویرایش
# ---------------------------------------------------------------------------


@staff_required
def users_list(request):
    """فهرست کاربران با جستجو (موبایل/نام/کد ملی) و فیلتر وضعیت حساب و نقش."""
    q = (request.GET.get("q") or "").strip()
    state = request.GET.get("state") or ""
    role = request.GET.get("role") or ""

    qs = (
        User.objects.select_related("profile")
        .annotate(job_count=Count("profile__jobs", distinct=True))
        .order_by("-date_joined")
    )
    if state == "active":
        qs = qs.filter(is_active=True)
    elif state == "inactive":
        qs = qs.filter(is_active=False)
    if role == "admin":
        qs = qs.filter(is_staff=True)
    elif role == "member":
        qs = qs.filter(is_staff=False)
    if q:
        qs = qs.filter(
            Q(mobile_number__icontains=q)
            | Q(profile__first_name__first_name_fa__icontains=q)
            | Q(profile__last_name__familyname_fa__icontains=q)
            | Q(profile__national_id__icontains=q)
        )

    total = qs.count()
    page_obj = Paginator(qs, 25).get_page(request.GET.get("page"))
    rows = [
        {
            "pk": u.pk,
            "mobile": u.mobile_number,
            "full_name": _user_label(u),
            "is_active": u.is_active,
            "is_staff": u.is_staff,
            "is_superuser": u.is_superuser,
            "job_count": u.job_count,
            "date_joined": u.date_joined,
        }
        for u in page_obj.object_list
    ]

    base_params = {k: v for k, v in request.GET.items() if k != "page"}
    return render(
        request,
        "adminpanel/users_list.html",
        {
            "q": q,
            "state": state,
            "role": role,
            "rows": rows,
            "total": total,
            "page_obj": page_obj,
            "base_query": urlencode(base_params),
            "next_url": _users_list_url(request),
        },
    )


@staff_required
@require_POST
def user_toggle(request, pk):
    """فعال/غیرفعال‌کردن حساب کاربر (خودِ ادمین قابل تغییر نیست)."""
    user = get_object_or_404(User.objects.select_related("profile"), pk=pk)
    if user.pk == request.user.pk:
        messages.error(request, "امکان غیرفعال‌کردن حساب خودتان وجود ندارد.")
        return redirect(_safe_next(request, _users_list_url(request)))
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    messages.success(
        request,
        f"حساب «{_user_label(user)}» {'فعال' if user.is_active else 'غیرفعال'} شد.",
    )
    return redirect(_safe_next(request, _users_list_url(request)))


@staff_required
def user_edit(request, pk):
    """ویرایش کاربر: حساب کاربری (فعال/ادمین/سوپریوزر/موبایل) + پروفایل (بخش‌ها)."""
    user = get_object_or_404(User.objects.select_related("profile"), pk=pk)
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        # پروفایل به‌صورت عادی با سیگنال ساخته می‌شود؛ برای امنیت بیشتر:
        profile = Profile.objects.create(user=user)
    is_self = user.pk == request.user.pk
    label = _user_label(user)
    default_back = _users_list_url(request)

    uform = AdminUserForm(instance=user, for_self=is_self)
    pform = AdminProfileForm(instance=profile)

    if request.method == "POST":
        action = request.POST.get("submit")
        back = _safe_next(request, default_back)

        if action == "account":
            # تغییر دسترسی‌های حسابِ خودِ ادمینِ واردشده مجاز نیست
            if is_self:
                messages.error(
                    request, "تغییر دسترسی حساب خودتان در پنل ممکن نیست."
                )
            else:
                uform = AdminUserForm(
                    request.POST, instance=user, for_self=False
                )
                if uform.is_valid():
                    uform.save()
                    messages.success(
                        request, f"حساب کاربری «{label}» به‌روزرسانی شد."
                    )
                    return redirect(back)
        elif action == "profile":
            pform = AdminProfileForm(request.POST, instance=profile)
            if pform.is_valid():
                pform.save()
                messages.success(
                    request, f"پروفایل «{label}» به‌روزرسانی شد."
                )
                return redirect(back)

    return render(
        request,
        "adminpanel/user_edit.html",
        {
            "user": user,
            "profile": profile,
            "label": label,
            "is_self": is_self,
            "uform": uform,
            "pform": pform,
            "sections": ADMIN_PROFILE_SECTIONS,
            "next_url": _safe_next(request, default_back),
        },
    )


# ---------------------------------------------------------------------------
# ماژول «تحصیلات»: مراکز دانشگاهی، رشته‌ها و گرایش‌های مرجع
# ---------------------------------------------------------------------------


def _education_list(request, model, template, title, query_fields, extra_context=None):
    q = (request.GET.get("q") or "").strip()
    qs = model.objects.all()
    if model is EducationInstitution:
        qs = qs.order_by("institution_type", "name")
    elif model is StudySpecialization:
        qs = qs.select_related("field").order_by("field__name", "name")
    elif model is StudyField:
        qs = qs.select_related("study_group").order_by("study_group__code", "name")
    else:
        qs = qs.order_by("name")
    if q:
        query = Q()
        for field in query_fields:
            query |= Q(**{f"{field}__icontains": q})
        qs = qs.filter(query)
    page_obj = Paginator(qs, 50).get_page(request.GET.get("page"))
    return render(request, template, {
        "rows": page_obj.object_list,
        "page_obj": page_obj,
        "q": q,
        "total": qs.count(),
        "title": title,
        **(extra_context or {}),
    })


@staff_required
def education_home(request):
    """خانهٔ ماژول «اطلاعات تحصیلی»: مراکز دانشگاهی، گروه‌های امتحانی، رشته‌ها و گرایش‌ها."""
    return render(
        request,
        "adminpanel/education_home.html",
        {
            "field_count": StudyField.objects.count(),
            "group_count": StudyGroup.objects.count(),
            "spec_count": StudySpecialization.objects.count(),
        },
    )


@staff_required
def education_institutions_list(request):
    return _education_list(
        request, EducationInstitution, "adminpanel/education_institutions_list.html",
        "مراکز دانشگاهی و آموزش عالی", ["name", "name_en", "code", "province", "city"],
        {"type_choices": EducationInstitution.TYPE_CHOICES},
    )


@staff_required
def education_institution_add(request):
    form = EducationInstitutionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "مرکز دانشگاهی ثبت شد و در انتخاب‌گر پروفایل در دسترس قرار گرفت.")
        return redirect("adminpanel:education_institutions_list")
    return render(request, "adminpanel/education_form.html", {"form": form, "title": "افزودن مرکز دانشگاهی", "back_url": reverse("adminpanel:education_institutions_list")})


@staff_required
def education_institution_edit(request, pk):
    obj = get_object_or_404(EducationInstitution, pk=pk)
    form = EducationInstitutionForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "مرکز دانشگاهی به‌روزرسانی شد.")
        return redirect("adminpanel:education_institutions_list")
    return render(request, "adminpanel/education_form.html", {"form": form, "title": "ویرایش مرکز دانشگاهی", "back_url": reverse("adminpanel:education_institutions_list")})


@staff_required
@require_POST
def education_institution_toggle(request, pk):
    obj = get_object_or_404(EducationInstitution, pk=pk)
    obj.is_active = not obj.is_active
    obj.save(update_fields=["is_active"])
    return redirect("adminpanel:education_institutions_list")


@staff_required
@require_POST
def education_institution_delete(request, pk):
    obj = get_object_or_404(EducationInstitution, pk=pk)
    try:
        obj.delete()
        messages.success(request, "مرکز دانشگاهی حذف شد.")
    except ProtectedError:
        messages.error(request, "این مرکز در پروفایل کاربران استفاده شده و قابل حذف نیست؛ آن را غیرفعال کنید.")
    return redirect("adminpanel:education_institutions_list")


@staff_required
def education_groups_list(request):
    return _education_list(
        request, StudyGroup, "adminpanel/education_groups_list.html", "گروه‌های امتحانی",
        ["name", "name_en", "code", "description"],
    )


@staff_required
def education_group_add(request):
    form = StudyGroupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "گروه امتحانی ثبت شد.")
        return redirect("adminpanel:education_groups_list")
    return render(request, "adminpanel/education_form.html", {"form": form, "title": "افزودن گروه امتحانی", "back_url": reverse("adminpanel:education_groups_list")})


@staff_required
def education_group_edit(request, pk):
    obj = get_object_or_404(StudyGroup, pk=pk)
    form = StudyGroupForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "گروه امتحانی به‌روزرسانی شد.")
        return redirect("adminpanel:education_groups_list")
    return render(request, "adminpanel/education_form.html", {"form": form, "title": "ویرایش گروه امتحانی", "back_url": reverse("adminpanel:education_groups_list")})


@staff_required
@require_POST
def education_group_toggle(request, pk):
    obj = get_object_or_404(StudyGroup, pk=pk)
    obj.is_active = not obj.is_active
    obj.save(update_fields=["is_active"])
    return redirect("adminpanel:education_groups_list")


@staff_required
@require_POST
def education_group_delete(request, pk):
    obj = get_object_or_404(StudyGroup, pk=pk)
    try:
        obj.delete()
        messages.success(request, "گروه امتحانی حذف شد.")
    except ProtectedError:
        messages.error(request, "این گروه دارای رشتهٔ تحصیلی است و قابل حذف نیست؛ آن را غیرفعال کنید.")
    return redirect("adminpanel:education_groups_list")


@staff_required
def education_fields_list(request):
    return _education_list(
        request, StudyField, "adminpanel/education_fields_list.html", "رشته‌های تحصیلی",
        ["name", "name_en", "code", "study_group__name"],
    )


@staff_required
def education_field_add(request):
    form = StudyFieldForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "رشتهٔ تحصیلی ثبت شد.")
        return redirect("adminpanel:education_fields_list")
    return render(request, "adminpanel/education_form.html", {"form": form, "title": "افزودن رشتهٔ تحصیلی", "back_url": reverse("adminpanel:education_fields_list")})


@staff_required
def education_field_edit(request, pk):
    obj = get_object_or_404(StudyField, pk=pk)
    form = StudyFieldForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "رشتهٔ تحصیلی به‌روزرسانی شد.")
        return redirect("adminpanel:education_fields_list")
    return render(request, "adminpanel/education_form.html", {"form": form, "title": "ویرایش رشتهٔ تحصیلی", "back_url": reverse("adminpanel:education_fields_list")})


@staff_required
@require_POST
def education_field_toggle(request, pk):
    obj = get_object_or_404(StudyField, pk=pk)
    obj.is_active = not obj.is_active
    obj.save(update_fields=["is_active"])
    return redirect("adminpanel:education_fields_list")


@staff_required
@require_POST
def education_field_delete(request, pk):
    obj = get_object_or_404(StudyField, pk=pk)
    try:
        obj.delete()
        messages.success(request, "رشتهٔ تحصیلی حذف شد.")
    except ProtectedError:
        messages.error(request, "این رشته دارای گرایش یا استفاده در پروفایل است و قابل حذف نیست؛ آن را غیرفعال کنید.")
    return redirect("adminpanel:education_fields_list")


@staff_required
def education_specializations_list(request):
    return _education_list(
        request, StudySpecialization, "adminpanel/education_specializations_list.html", "گرایش‌های تحصیلی",
        ["name", "name_en", "code", "field__name"],
    )


@staff_required
def education_specialization_add(request):
    form = StudySpecializationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "گرایش تحصیلی ثبت شد.")
        return redirect("adminpanel:education_specializations_list")
    return render(request, "adminpanel/education_form.html", {"form": form, "title": "افزودن گرایش تحصیلی", "back_url": reverse("adminpanel:education_specializations_list")})


@staff_required
def education_specialization_edit(request, pk):
    obj = get_object_or_404(StudySpecialization, pk=pk)
    form = StudySpecializationForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "گرایش تحصیلی به‌روزرسانی شد.")
        return redirect("adminpanel:education_specializations_list")
    return render(request, "adminpanel/education_form.html", {"form": form, "title": "ویرایش گرایش تحصیلی", "back_url": reverse("adminpanel:education_specializations_list")})


@staff_required
@require_POST
def education_specialization_toggle(request, pk):
    obj = get_object_or_404(StudySpecialization, pk=pk)
    obj.is_active = not obj.is_active
    obj.save(update_fields=["is_active"])
    return redirect("adminpanel:education_specializations_list")


@staff_required
@require_POST
def education_specialization_delete(request, pk):
    obj = get_object_or_404(StudySpecialization, pk=pk)
    try:
        obj.delete()
        messages.success(request, "گرایش تحصیلی حذف شد.")
    except ProtectedError:
        messages.error(request, "این گرایش در پروفایل کاربران استفاده شده و قابل حذف نیست؛ آن را غیرفعال کنید.")
    return redirect("adminpanel:education_specializations_list")


# ---------------------------------------------------------------------------
# ماژول «اسامی»: تکمیل جدول نام‌ها و نام خانوادگی که پروفایل کاربران از آن‌ها
# می‌خواند (نام/نام پدر/نام مادر از FirstnameTbl و نام خانوادگی از FamilynameTbl)
# ---------------------------------------------------------------------------

# نقش‌های فیلدهای نام در پروفایل برای شمارش «تعداد استفادهٔ هر رکورد»
FIRST_NAME_ROLES = (
    ("profiles_first_name", "نام"),
    ("profiles_father_name", "نام پدر"),
    ("profiles_mother_name", "نام مادر"),
)

_NAME_GENDER_LABELS = {"male": "مردانه", "female": "زنانه"}

NAME_TABLES = {
    "first": {
        "model": FirstnameTbl,
        "form": FirstNameForm,
        "label": "نام",
        "plural": "نام‌ها",
        "icon": "bi-person-vcard",
        "fa_field": "first_name_fa",
        "en_field": "first_name_en",
        "usage": "در پروفایل کاربر برای «نام»، «نام پدر» و «نام مادر» استفاده می‌شود",
    },
    "family": {
        "model": FamilynameTbl,
        "form": FamilyNameForm,
        "label": "نام خانوادگی",
        "plural": "نام‌های خانوادگی",
        "icon": "bi-people",
        "fa_field": "familyname_fa",
        "en_field": "familyname_en",
        "usage": "در پروفایل کاربر برای «نام خانوادگی» استفاده می‌شود",
    },
    "fame": {
        # «شهرت»: نام و عنوانی که نام‌برده در جامعه با آن شناخته می‌شود؛
        # فهرست انتخابیِ فیلد اختیاریِ «شهرت» بخش اطلاعات شخصی پروفایل.
        "model": FameNameTbl,
        "form": FameNameForm,
        "label": "شهرت",
        "plural": "شهرت‌ها",
        "icon": "bi-star",
        "fa_field": "fame_name_fa",
        "en_field": "fame_name_en",
        "usage": "در پروفایل کاربر برای فیلد اختیاریِ «شهرت» استفاده می‌شود",
    },
}


def _get_name_table(kind):
    cfg = NAME_TABLES.get(kind)
    if cfg is None:
        raise Http404("جدول موردنظر در پنل مدیریت تعریف نشده است.")
    return cfg


def _name_usage(obj, kind):
    """تعداد پروفایل‌هایی که از این رکورد استفاده می‌کنند + تفکیک نقش‌های فیلد."""
    if kind == "first":
        roles = FIRST_NAME_ROLES
    elif kind == "fame":
        roles = (("profiles_fame_name", "شهرت"),)
    else:
        roles = (("profiles_last_name", "نام خانوادگی"),)
    total = 0
    parts = []
    for related_name, label in roles:
        count = getattr(obj, related_name).count()
        if count:
            parts.append(f"{label}: {count}")
        total += count
    return total, parts


def _names_list_url(request, kind):
    """آدرس فهرست اسامیِ همان جدول با حفظ فیلترهای جاری (kind / q / page)."""
    params = {k: v for k, v in request.GET.items() if k != "page"}
    params["kind"] = kind
    url = reverse("adminpanel:names_list")
    if params:
        url += "?" + urlencode(params)
    return url


@staff_required
def names_list(request):
    """فهرست نام‌ها / نام‌های خانوادگی با جستجو و تعداد استفاده در پروفایل‌ها."""
    kind = request.GET.get("kind", "first")
    cfg = _get_name_table(kind)
    q = (request.GET.get("q") or "").strip()

    qs = cfg["model"].objects.all()
    if q:
        qs = qs.filter(
            Q(**{f"{cfg['fa_field']}__icontains": q})
            | Q(**{f"{cfg['en_field']}__icontains": q})
        )

    total = qs.count()
    page_obj = Paginator(qs, 50).get_page(request.GET.get("page"))
    rows = []
    for obj in page_obj.object_list:
        used, usage_parts = _name_usage(obj, kind)
        gender = getattr(obj, "gender", "") if kind == "first" else ""
        rows.append({
            "pk": obj.pk,
            "fa": getattr(obj, cfg["fa_field"]),
            "en": getattr(obj, cfg["en_field"]),
            "gender": gender,
            "gender_label": _NAME_GENDER_LABELS.get(gender, ""),
            "used": used,
            "usage_parts": usage_parts,
            # «توضیحات» فقط در تب شهرت‌ها استفاده می‌شود
            "description": getattr(obj, "description", "") if kind == "fame" else "",
        })

    counts = {key: val["model"].objects.count() for key, val in NAME_TABLES.items()}
    base_params = {k: v for k, v in request.GET.items() if k != "page"}
    return render(
        request,
        "adminpanel/names_list.html",
        {
            "kind": kind,
            "cfg": cfg,
            "q": q,
            "rows": rows,
            "total": total,
            "counts": counts,
            "page_obj": page_obj,
            "base_query": urlencode(base_params),
            "next_url": _names_list_url(request, kind),
        },
    )


@staff_required
def name_add(request, kind):
    """افزودن نام/نام خانوادگی جدید به جدول."""
    cfg = _get_name_table(kind)
    form = cfg["form"](request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(
            request,
            f"{cfg['label']} «{getattr(obj, cfg['fa_field'])}» ثبت شد و از این پس "
            "در فهرست انتخاب پروفایل کاربران در دسترس است.",
        )
        return redirect(_names_list_url(request, kind))
    return render(
        request,
        "adminpanel/name_form.html",
        {"kind": kind, "cfg": cfg, "form": form, "mode": "add", "fa_value": ""},
    )


@staff_required
def name_edit(request, kind, pk):
    """ویرایش نام/نام خانوادگی (اصلاح املایی، افزودن معادل انگلیسی و ...)."""
    cfg = _get_name_table(kind)
    obj = get_object_or_404(cfg["model"], pk=pk)
    form = cfg["form"](request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            f"{cfg['label']} «{getattr(obj, cfg['fa_field'])}» به‌روزرسانی شد.",
        )
        return redirect(_names_list_url(request, kind))
    return render(
        request,
        "adminpanel/name_form.html",
        {
            "kind": kind, "cfg": cfg, "form": form, "mode": "edit",
            "fa_value": getattr(obj, cfg["fa_field"]),
        },
    )


@staff_required
@require_POST
def name_delete(request, kind, pk):
    """حذف نام/نام خانوادگی؛ اگر پروفایلی از آن استفاده کرده باشد، حذف نمی‌شود."""
    cfg = _get_name_table(kind)
    obj = get_object_or_404(cfg["model"], pk=pk)
    fa = getattr(obj, cfg["fa_field"])
    used, usage_parts = _name_usage(obj, kind)
    if used:
        messages.error(
            request,
            f"{cfg['label']} «{fa}» توسط {used} پروفایل استفاده شده است "
            f"({"، ".join(usage_parts)}) و قابل حذف نیست؛ برای اصلاح، همین رکورد را ویرایش کنید.",
        )
        return redirect(_names_list_url(request, kind))
    obj.delete()
    messages.success(request, f"{cfg['label']} «{fa}» حذف شد.")
    return redirect(_names_list_url(request, kind))


# ---------------------------------------------------------------------------
# ماژول «اطلاعات مکانی»: جدول‌های مرجع کشور/استان/شهرستان که فیلدهای مکانِ
# پروفایل کاربران (محل سکونت) از آن‌ها خوانده می‌شود؛ ادمین دیتابیس را تکمیل/اصلاح
# می‌کند و کاربر در بخش «اطلاعات مکانی» پروفایل از همین فهرست‌ها انتخاب می‌کند.
# ---------------------------------------------------------------------------

LOC_TABLES = {
    "country": {
        "model": CountryTbl,
        "form": CountryForm,
        "label": "کشور",
        "plural": "کشورها",
        "icon": "bi-globe2",
        "fa_field": "country_fa",
        "en_field": "country_en",
        "usage": "در پروفایل کاربر برای فیلد «کشور» (محل سکونت) استفاده می‌شود",
    },
    "province": {
        "model": ProvinceTbl,
        "form": ProvinceForm,
        "label": "استان",
        "plural": "استان‌ها",
        "icon": "bi-map",
        "fa_field": "province_fa",
        "en_field": "province_en",
        "usage": "در پروفایل کاربر برای فیلد «استان» (محل سکونت) استفاده می‌شود",
    },
    "city": {
        "model": CityTbl,
        "form": CityForm,
        "label": "شهرستان",
        "plural": "شهرستان‌ها",
        "icon": "bi-buildings",
        "fa_field": "city_fa",
        "en_field": "city_en",
        "usage": "در پروفایل کاربر برای فیلد «شهر» (محل سکونت) استفاده می‌شود",
    },
}


def _get_loc_table(kind):
    cfg = LOC_TABLES.get(kind)
    if cfg is None:
        raise Http404("جدول مکان موردنظر در پنل مدیریت تعریف نشده است.")
    return cfg


def _locations_list_url(request, kind):
    """آدرس فهرست اطلاعات مکانی با حفظ فیلترهای جاری (kind / q / page)."""
    params = {k: v for k, v in request.GET.items() if k != "page"}
    params["kind"] = kind
    url = reverse("adminpanel:locations_list")
    if params:
        url += "?" + urlencode(params)
    return url


def _loc_usage_map():
    """تعداد پروفایل‌هایی که با متنِ کشور/استان/شهرِ هر رکورد مطابقت دارند.

    فیلدهای مکان پروفایل متن‌اند (نه FK)؛ بنابراین استفاده بر اساسِ برابریِ نام
    فارسی (یا انگلیسیِ ثبت‌شدهٔ قدیمی) با مقدارِ پروفایل شمارش می‌شود.
    """
    return {
        "country": dict(
            Profile.objects.exclude(country="")
            .values_list("country").annotate(c=Count("id")).order_by()
        ),
        "province": dict(
            Profile.objects.exclude(province="")
            .values_list("province").annotate(c=Count("id")).order_by()
        ),
        "city": dict(
            Profile.objects.exclude(city="")
            .values_list("city").annotate(c=Count("id")).order_by()
        ),
    }


def _loc_row_usage(row_fa, row_en, usage_map):
    """جمع استفاده از یک نام (فارسی یا انگلیسی) در پروفایل‌ها."""
    return usage_map.get(row_fa, 0) + (usage_map.get(row_en, 0) if row_en else 0)


@staff_required
def locations_list(request):
    """فهرست کشورها/استان‌ها/شهرستان‌ها با جستجو و آمار استفاده در پروفایل‌ها."""
    kind = request.GET.get("kind", "country")
    cfg = _get_loc_table(kind)
    q = (request.GET.get("q") or "").strip()

    qs = cfg["model"].objects.all()
    if kind == "province":
        qs = qs.select_related("country")
    elif kind == "city":
        qs = qs.select_related("province__country")
    if q:
        qs = qs.filter(
            Q(**{f"{cfg['fa_field']}__icontains": q})
            | Q(**{f"{cfg['en_field']}__icontains": q})
        )

    total = qs.count()
    page_obj = Paginator(qs, 50).get_page(request.GET.get("page"))
    usage = _loc_usage_map()

    # شمارش فرزندان (استانِ هر کشور و شهرستانِ هر استان) برای نمایش در فهرست
    province_of = dict(
        ProvinceTbl.objects.values_list("country_id")
        .annotate(c=Count("id")).order_by()
    )
    city_of = dict(
        CityTbl.objects.values_list("province_id")
        .annotate(c=Count("id")).order_by()
    )

    rows = []
    for obj in page_obj.object_list:
        fa = getattr(obj, cfg["fa_field"])
        en = getattr(obj, cfg["en_field"]) or ""
        row = {
            "pk": obj.pk,
            "fa": fa,
            "en": en,
            "parent": "",
            "children": 0,
            "children_label": "",
            "used": _loc_row_usage(fa, en, usage[kind]),
        }
        if kind == "country":
            row["children"] = province_of.get(obj.pk, 0)
            row["children_label"] = "استان"
        elif kind == "province":
            row["parent"] = obj.country.country_fa if obj.country_id else ""
            row["children"] = city_of.get(obj.pk, 0)
            row["children_label"] = "شهرستان"
        else:
            row["parent"] = (
                f"{obj.province.country.country_fa} › {obj.province.province_fa}"
                if obj.province_id else ""
            )
        rows.append(row)

    counts = {key: val["model"].objects.count() for key, val in LOC_TABLES.items()}
    base_params = {k: v for k, v in request.GET.items() if k != "page"}
    return render(
        request,
        "adminpanel/locations_list.html",
        {
            "kind": kind,
            "cfg": cfg,
            "q": q,
            "rows": rows,
            "total": total,
            "counts": counts,
            "page_obj": page_obj,
            "base_query": urlencode(base_params),
            "next_url": _locations_list_url(request, kind),
        },
    )


@staff_required
def location_add(request, kind):
    """افزودن کشور/استان/شهرستان جدید به جدول مرجع."""
    cfg = _get_loc_table(kind)
    form = cfg["form"](request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(
            request,
            f"{cfg['label']} «{getattr(obj, cfg['fa_field'])}» ثبت شد و از این پس "
            "در فهرست انتخابِ «اطلاعات مکانی» پروفایل کاربران در دسترس است.",
        )
        return redirect(_locations_list_url(request, kind))
    return render(
        request,
        "adminpanel/location_form.html",
        {"kind": kind, "cfg": cfg, "form": form, "mode": "add", "fa_value": ""},
    )


@staff_required
def location_edit(request, kind, pk):
    """ویرایش کشور/استان/شهرستان (اصلاح املایی، تغییر والد و ...)."""
    cfg = _get_loc_table(kind)
    obj = get_object_or_404(cfg["model"], pk=pk)
    form = cfg["form"](request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            f"{cfg['label']} «{getattr(obj, cfg['fa_field'])}» به‌روزرسانی شد.",
        )
        return redirect(_locations_list_url(request, kind))
    return render(
        request,
        "adminpanel/location_form.html",
        {
            "kind": kind, "cfg": cfg, "form": form, "mode": "edit",
            "fa_value": getattr(obj, cfg["fa_field"]),
        },
    )


@staff_required
@require_POST
def location_delete(request, kind, pk):
    """حذف کشور/استان/شهرستان با محافظت: اگر فرزند یا استفاده در پروفایل دارد، حذف نمی‌شود."""
    cfg = _get_loc_table(kind)
    obj = get_object_or_404(cfg["model"], pk=pk)
    fa = getattr(obj, cfg["fa_field"])
    en = getattr(obj, cfg["en_field"]) or ""

    # کشور دارای استان / استان دارای شهرستان → حذفِ آبشاری زیرمجموعه‌ها ممنوع
    child_related = {"country": "provinces", "province": "cities"}.get(kind)
    if child_related:
        child_count = getattr(obj, child_related).count()
        if child_count:
            child_name = "استان" if kind == "country" else "شهرستان"
            messages.error(
                request,
                f"{cfg['label']} «{fa}» دارای {child_count} {child_name} است و قابل حذف نیست؛ "
                "برای حذف ابتدا زیرمجموعه‌های آن را جابه‌جا یا حذف کنید.",
            )
            return redirect(_locations_list_url(request, kind))

    usage = _loc_usage_map()
    used = _loc_row_usage(fa, en, usage[kind])
    if used:
        messages.error(
            request,
            f"{cfg['label']} «{fa}» توسط {used} پروفایل به‌عنوان محل سکونت استفاده شده "
            "و قابل حذف نیست؛ برای اصلاح املایی همین رکورد را ویرایش کنید.",
        )
        return redirect(_locations_list_url(request, kind))
    obj.delete()
    messages.success(request, f"{cfg['label']} «{fa}» حذف شد.")
    return redirect(_locations_list_url(request, kind))


# ---------------------------------------------------------------------------
# ماژول «کنترل کد ملی»: کدهای ملیِ رزروشده/اختصاصی که کاربران عادی نمی‌توانند
# در پروفایل خود ثبت کنند (مثلاً کد اختصاصی ادمین). اعمال می‌شود در فرم
# «اطلاعات شخصی» پروفایل و Profile.clean (accounts).
# ---------------------------------------------------------------------------


def _national_codes_list_url(request):
    """آدرس فهرست کدهای رزروشده با حفظ فیلترهای جاری (q / active / page)."""
    params = {k: v for k, v in request.GET.items() if k != "page"}
    url = reverse("adminpanel:national_codes_list")
    if params:
        url += "?" + urlencode(params)
    return url


@staff_required
def national_codes_list(request):
    """فهرست کدهای ملیِ رزروشده با جستجو + فیلتر سطح دسترسی/وضعیت."""
    q = (request.GET.get("q") or "").strip()
    access = request.GET.get("access") or ""
    active = request.GET.get("active") or ""

    qs = ReservedNationalCode.objects.all().order_by("national_id")
    if access:
        qs = qs.filter(access_level=access)
    if active == "1":
        qs = qs.filter(is_active=True)
    elif active == "0":
        qs = qs.filter(is_active=False)
    if q:
        qs = qs.filter(Q(national_id__icontains=q) | Q(title__icontains=q))

    total = qs.count()
    page_obj = Paginator(qs, 25).get_page(request.GET.get("page"))
    rows = []
    for item in page_obj.object_list:
        # دارندگانِ فعلیِ همین کد (نام/موبایل آن‌ها برای آگاهی ادمین؛ فقط شمارش نیست).
        # کدهایی که پیش از رزروشدن به کاربری تعلق داشته‌اند دست‌نخورده می‌مانند،
        # پس چنین کاربرانی ممکن است همچنان صاحبِ همین کد باشند.
        holders = list(
            Profile.objects.filter(national_id=item.national_id).select_related("user")
        )
        rows.append({
            "pk": item.pk,
            "national_id": item.national_id,
            "access_level": item.access_level,
            "access_label": item.get_access_level_display(),
            "title": item.title,
            "is_active": item.is_active,
            "holder_count": len(holders),
            "holders": [
                {
                    "name": h.full_name,
                    "mobile": h.user.mobile_number,
                    "is_staff": h.user.is_staff,
                }
                for h in holders
            ],
            "updated_at": item.updated_at,
        })

    base_params = {k: v for k, v in request.GET.items() if k != "page"}
    return render(
        request,
        "adminpanel/national_codes_list.html",
        {
            "q": q,
            "access": access,
            "active": active,
            "rows": rows,
            "total": total,
            "page_obj": page_obj,
            "base_query": urlencode(base_params),
            "next_url": _national_codes_list_url(request),
            "active_count": ReservedNationalCode.objects.filter(is_active=True).count(),
            "access_choices": ReservedNationalCode.ACCESS_CHOICES,
        },
    )


@staff_required
def national_code_add(request):
    """افزودن کد ملی رزروشدهٔ جدید."""
    form = ReservedNationalCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(
            request,
            f"کد ملی «{item.national_id}» رزرو شد؛ از این پس کاربران عادی نمی‌توانند آن را ثبت کنند.",
        )
        return redirect(_national_codes_list_url(request))
    return render(
        request,
        "adminpanel/national_code_form.html",
        {"form": form, "mode": "add", "next_url": _national_codes_list_url(request)},
    )


@staff_required
def national_code_edit(request, pk):
    """ویرایش کد ملی رزروشده (تغییر سطح دسترسی، عنوان و ...)."""
    item = get_object_or_404(ReservedNationalCode, pk=pk)
    form = ReservedNationalCodeForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request, f"کد ملی «{item.national_id}» به‌روزرسانی شد."
        )
        return redirect(_national_codes_list_url(request))
    return render(
        request,
        "adminpanel/national_code_form.html",
        {"form": form, "mode": "edit", "next_url": _national_codes_list_url(request)},
    )


@staff_required
@require_POST
def national_code_toggle(request, pk):
    """فعال/غیرفعال‌کردن محدودیت یک کد رزروشده (جایگزین امنِ حذف)."""
    item = get_object_or_404(ReservedNationalCode, pk=pk)
    item.is_active = not item.is_active
    item.save(update_fields=["is_active"])
    messages.success(
        request,
        f"محدودیت کد ملی «{item.national_id}» {'فعال' if item.is_active else 'غیرفعال'} شد.",
    )
    return redirect(_national_codes_list_url(request))


@staff_required
@require_POST
def national_code_delete(request, pk):
    """حذف کامل رکورد کد رزروشده؛ فقط محدودیت برداشته می‌شود (دادهٔ کاربران دست نمی‌خورد)."""
    item = get_object_or_404(ReservedNationalCode, pk=pk)
    nid = item.national_id
    item.delete()
    messages.success(request, f"رکورد «{nid}» حذف شد؛ از این پس محدودیتی برای این کد وجود ندارد.")
    return redirect(_national_codes_list_url(request))


# ---------------------------------------------------------------------------
# ماژول «مخاطبین هدف تیکت»: جوامع هدف تعریف‌شده توسط ادمین برای ارسال انبوه
# ---------------------------------------------------------------------------


def _audiences_list_url(request):
    params = {k: v for k, v in request.GET.items() if k != "page"}
    url = reverse("adminpanel:audiences_list")
    if params:
        url += "?" + urlencode(params)
    return url


@staff_required
def audiences_list(request):
    """فهرست جوامع هدف با جستجو + فیلتر فعال/غیرفعال + تعداد واجدین شرایط فعلی."""
    q = (request.GET.get("q") or "").strip()
    active = request.GET.get("active") or ""

    qs = TicketAudience.objects.all().order_by("-updated_at")
    if active == "1":
        qs = qs.filter(is_active=True)
    elif active == "0":
        qs = qs.filter(is_active=False)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))

    total = qs.count()
    page_obj = Paginator(qs, 25).get_page(request.GET.get("page"))
    rows = []
    for item in page_obj.object_list:
        rows.append({
            "pk": item.pk,
            "name": item.name,
            "kind": item.kind,
            "kind_label": item.kind_label,
            "description": item.description,
            "rules_label": item.rules_label,
            "eligible": item.eligible_count(),
            "is_active": item.is_active,
            "updated_at": item.updated_at,
        })

    base_params = {k: v for k, v in request.GET.items() if k != "page"}
    return render(
        request,
        "adminpanel/audiences_list.html",
        {
            "q": q,
            "active": active,
            "rows": rows,
            "total": total,
            "page_obj": page_obj,
            "base_query": urlencode(base_params),
            "next_url": _audiences_list_url(request),
            "active_count": TicketAudience.objects.filter(is_active=True).count(),
        },
    )


@staff_required
def audience_add(request):
    """افزودن جامعهٔ هدف جدید."""
    form = TicketAudienceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(request, f"جامعهٔ هدف «{item.name}» ثبت شد و در فهرست ارسال تیکت ظاهر می‌شود.")
        return redirect(_audiences_list_url(request))
    return render(
        request,
        "adminpanel/audience_form.html",
        {"form": form, "mode": "add", "next_url": _audiences_list_url(request)},
    )


@staff_required
def audience_edit(request, pk):
    """ویرایش جامعهٔ هدف."""
    item = get_object_or_404(TicketAudience, pk=pk)
    form = TicketAudienceForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"جامعهٔ هدف «{item.name}» به‌روزرسانی شد.")
        return redirect(_audiences_list_url(request))
    return render(
        request,
        "adminpanel/audience_form.html",
        {"form": form, "mode": "edit", "next_url": _audiences_list_url(request)},
    )


@staff_required
@require_POST
def audience_toggle(request, pk):
    """فعال/غیرفعال‌کردن جامعهٔ هدف (جایگزین امنِ حذف)."""
    item = get_object_or_404(TicketAudience, pk=pk)
    item.is_active = not item.is_active
    item.save(update_fields=["is_active"])
    messages.success(
        request,
        f"جامعهٔ هدف «{item.name}» {'فعال' if item.is_active else 'غیرفعال'} شد.",
    )
    return redirect(_audiences_list_url(request))


@staff_required
@require_POST
def audience_delete(request, pk):
    """حذف کامل جامعهٔ هدف."""
    item = get_object_or_404(TicketAudience, pk=pk)
    name = item.name
    item.delete()
    messages.success(request, f"جامعهٔ هدف «{name}» حذف شد.")
    return redirect(_audiences_list_url(request))


# ---------------------------------------------------------------------------
# ماژول «انواع تیکت»: دسته‌های قابل تعریف توسط ادمین
# ---------------------------------------------------------------------------


def _ticket_types_list_url(request):
    params = {k: v for k, v in request.GET.items() if k != "page"}
    url = reverse("adminpanel:ticket_types_list")
    if params:
        url += "?" + urlencode(params)
    return url


@staff_required
def ticket_types_list(request):
    """فهرست انواع تیکت با جستجو + فیلتر فعال/غیرفعال."""
    q = (request.GET.get("q") or "").strip()
    active = request.GET.get("active") or ""

    qs = TicketCategory.objects.all().order_by("order", "code")
    if active == "1":
        qs = qs.filter(is_active=True)
    elif active == "0":
        qs = qs.filter(is_active=False)
    if q:
        qs = qs.filter(Q(name_fa__icontains=q) | Q(code__icontains=q))

    total = qs.count()
    rows = [
        {
            "pk": item.pk,
            "code": item.code,
            "name_fa": item.name_fa,
            "icon": item.icon,
            "order": item.order,
            "is_active": item.is_active,
            "ticket_count": item.tickets.count(),
        }
        for item in qs
    ]

    base_params = {k: v for k, v in request.GET.items() if k != "page"}
    return render(
        request,
        "adminpanel/ticket_types_list.html",
        {
            "q": q,
            "active": active,
            "rows": rows,
            "total": total,
            "base_query": urlencode(base_params),
            "next_url": _ticket_types_list_url(request),
            "active_count": TicketCategory.objects.filter(is_active=True).count(),
        },
    )


@staff_required
def ticket_type_add(request):
    """افزودن نوع تیکت جدید."""
    form = TicketCategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(request, f"نوع تیکت «{item.name_fa}» ثبت شد و در فرم ارسال تیکت در دسترس است.")
        return redirect(_ticket_types_list_url(request))
    return render(
        request,
        "adminpanel/ticket_type_form.html",
        {"form": form, "mode": "add", "next_url": _ticket_types_list_url(request)},
    )


@staff_required
def ticket_type_edit(request, pk):
    """ویرایش نوع تیکت."""
    item = get_object_or_404(TicketCategory, pk=pk)
    form = TicketCategoryForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"نوع تیکت «{item.name_fa}» به‌روزرسانی شد.")
        return redirect(_ticket_types_list_url(request))
    return render(
        request,
        "adminpanel/ticket_type_form.html",
        {"form": form, "mode": "edit", "next_url": _ticket_types_list_url(request)},
    )


@staff_required
@require_POST
def ticket_type_toggle(request, pk):
    """فعال/غیرفعال‌کردن نوع تیکت (جایگزین امنِ حذف)."""
    item = get_object_or_404(TicketCategory, pk=pk)
    item.is_active = not item.is_active
    item.save(update_fields=["is_active"])
    messages.success(
        request,
        f"نوع تیکت «{item.name_fa}» {'فعال' if item.is_active else 'غیرفعال'} شد.",
    )
    return redirect(_ticket_types_list_url(request))


@staff_required
@require_POST
def ticket_type_delete(request, pk):
    """حذف کامل نوع تیکت (در صورت استفادهٔ زیاد، غیرفعال‌کردن پیشنهاد می‌شود)."""
    item = get_object_or_404(TicketCategory, pk=pk)
    name = item.name_fa
    try:
        item.delete()
        messages.success(request, f"نوع تیکت «{name}» حذف شد.")
    except ProtectedError:
        messages.error(
            request,
            f"نوع تیکت «{name}» توسط تیکت‌های ثبت‌شده استفاده می‌شود؛ آن را «غیرفعال» کنید.",
        )
    return redirect(_ticket_types_list_url(request))


# ---------------------------------------------------------------------------
# ماژول «سکه و کیف پول»: تنظیمات، هزینهٔ ماژول‌ها، سفارش‌ها، انتقال‌ها، موجودی‌ها
# ---------------------------------------------------------------------------


def _user_label_safe(user):
    """نام نمایشی امن برای کاربر (با fallback شماره موبایل)."""
    try:
        return user.profile.full_name
    except Exception:  # noqa: BLE001 - پروفایلِ ناقص نباید لیست را بشکند
        return user.mobile_number


def _orders_list_url(request):
    params = {k: v for k, v in request.GET.items() if k != "page"}
    url = reverse("adminpanel:wallet_orders")
    if params:
        url += "?" + urlencode(params)
    return url


@staff_required
def wallet_settings(request):
    """تنظیمات سراسری کیف پول: نرخ سکه، حداقل/حداکثر، بانک و شبا + تاریخچهٔ نرخ."""
    setting = WalletSetting.get()
    history = CoinPriceHistory.objects.select_related("changed_by")[:20]

    if request.method == "POST":
        action = request.POST.get("submit")
        if action == "rate":
            try:
                new_setting, changed = set_coin_value(
                    request.user, request.POST.get("coin_value_rial"),
                    note=request.POST.get("rate_note", "")[:300],
                    request=request,
                )
                if changed:
                    messages.success(
                        request,
                        f"نرخ هر سکه به {new_setting.coin_value_rial} ریال تغییر کرد "
                        "و تاریخچهٔ آن ثبت شد.",
                    )
                else:
                    messages.info(request, "نرخ تغییری نکرد.")
            except WalletServiceError as exc:
                messages.error(request, str(exc))
            return redirect("adminpanel:wallet_settings")

        if action == "settings":
            form = WalletSettingsForm(request.POST, request.FILES, instance=setting)
            if form.is_valid():
                form.save()
                messages.success(request, "تنظیمات کیف پول ذخیره شد.")
                return redirect("adminpanel:wallet_settings")
            messages.error(request, "لطفاً خطاهای فرم را برطرف کنید.")
        else:
            messages.error(request, "عملیات ناشناخته است.")

    form = WalletSettingsForm(instance=setting)
    return render(
        request,
        "adminpanel/wallet_settings.html",
        {
            "setting": setting,
            "form": form,
            "history": history,
            "rate_note": request.POST.get("rate_note", "") if request.method == "POST" else "",
        },
    )


@staff_required
def location_settings(request):
    """تنظیمات سراسری «سرویس موقعیت»: نقشهٔ نمایشی کاربران و منبع موقعیت (GPS)."""
    setting = LocationSetting.get()

    if request.method == "POST":
        form = LocationSettingsForm(request.POST, instance=setting)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "تنظیمات سرویس موقعیت ذخیره شد؛ نقشهٔ نمایشی و منبع GPS از این پس "
                "بر اساس انتخاب شما عمل می‌کنند.",
            )
            return redirect("adminpanel:location_settings")
        messages.error(request, "لطفاً انتخاب‌ها را بررسی کنید.")
    else:
        form = LocationSettingsForm(instance=setting)

    from accounts.location_settings import location_service_context

    ctx = location_service_context(setting)
    labels = dict(LocationSetting.MAP_PROVIDER_CHOICES)
    return render(
        request,
        "adminpanel/location_settings.html",
        {
            "setting": setting,
            "form": form,
            **ctx,
            "map_provider_label": labels.get(
                ctx["map_provider_active"], ctx["map_provider_active"]
            ),
            "chosen_map_provider_label": labels.get(
                setting.map_provider, setting.map_provider
            ),
        },
    )


# --- هزینهٔ سکهٔ ماژول‌ها ---


def _feature_costs_list_url(request):
    params = {k: v for k, v in request.GET.items() if k != "page"}
    url = reverse("adminpanel:feature_costs_list")
    if params:
        url += "?" + urlencode(params)
    return url


@staff_required
def feature_costs_list(request):
    """فهرست هزینه‌های سکهٔ ماژول‌ها (بخش‌های برنامه)."""
    q = (request.GET.get("q") or "").strip()
    active = request.GET.get("active") or ""

    qs = FeatureCost.objects.all().order_by("title")
    if active == "1":
        qs = qs.filter(is_active=True)
    elif active == "0":
        qs = qs.filter(is_active=False)
    if q:
        qs = qs.filter(Q(code__icontains=q) | Q(title__icontains=q))

    rows = [
        {
            "pk": item.pk,
            "code": item.code,
            "title": item.title,
            "description": item.description,
            "coins": item.coins,
            "is_active": item.is_active,
            "updated_at": item.updated_at,
        }
        for item in qs
    ]
    total = len(rows)
    return render(
        request,
        "adminpanel/feature_costs_list.html",
        {
            "q": q,
            "active": active,
            "rows": rows,
            "total": total,
            "next_url": _feature_costs_list_url(request),
            "active_count": FeatureCost.objects.filter(is_active=True).count(),
        },
    )


@staff_required
def feature_cost_add(request):
    form = FeatureCostForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(
            request,
            f"هزینهٔ سکهٔ «{item.title}» ({item.coins} سکه) ثبت شد.",
        )
        return redirect(_feature_costs_list_url(request))
    return render(
        request,
        "adminpanel/feature_cost_form.html",
        {"form": form, "mode": "add", "next_url": _feature_costs_list_url(request)},
    )


@staff_required
def feature_cost_edit(request, pk):
    item = get_object_or_404(FeatureCost, pk=pk)
    form = FeatureCostForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"هزینهٔ سکهٔ «{item.title}» به‌روزرسانی شد.")
        return redirect(_feature_costs_list_url(request))
    return render(
        request,
        "adminpanel/feature_cost_form.html",
        {"form": form, "mode": "edit", "next_url": _feature_costs_list_url(request)},
    )


@staff_required
@require_POST
def feature_cost_toggle(request, pk):
    item = get_object_or_404(FeatureCost, pk=pk)
    item.is_active = not item.is_active
    item.save(update_fields=["is_active"])
    messages.success(
        request,
        f"هزینهٔ «{item.title}» {'فعال' if item.is_active else 'غیرفعال'} شد.",
    )
    return redirect(_feature_costs_list_url(request))


@staff_required
@require_POST
def feature_cost_delete(request, pk):
    item = get_object_or_404(FeatureCost, pk=pk)
    title = item.title
    item.delete()
    messages.success(request, f"هزینهٔ «{title}» حذف شد.")
    return redirect(_feature_costs_list_url(request))


# --- پاداش‌های سکه (عنوان و میزان را ادمین تعیین می‌کند) ---


def _reward_rules_list_url(request):
    params = {k: v for k, v in request.GET.items() if k != "page"}
    url = reverse("adminpanel:reward_rules_list")
    if params:
        url += "?" + urlencode(params)
    return url


@staff_required
def reward_rules_list(request):
    """فهرست قوانین پاداش سکه (معرف، مطالعه در مجله و ...) با جستجو + فیلتر وضعیت."""
    q = (request.GET.get("q") or "").strip()
    active = request.GET.get("active") or ""

    qs = RewardRule.objects.all().order_by("code")
    if active == "1":
        qs = qs.filter(is_active=True)
    elif active == "0":
        qs = qs.filter(is_active=False)
    if q:
        qs = qs.filter(Q(code__icontains=q) | Q(title__icontains=q))

    rows = [
        {
            "pk": item.pk,
            "code": item.code,
            "title": item.title,
            "unit_label": item.unit_label,
            "description": item.description,
            "coins": item.coins,
            "max_per_user": item.max_per_user,
            "is_active": item.is_active,
            "updated_at": item.updated_at,
        }
        for item in qs
    ]
    total = len(rows)
    return render(
        request,
        "adminpanel/reward_rules_list.html",
        {
            "q": q,
            "active": active,
            "rows": rows,
            "total": total,
            "next_url": _reward_rules_list_url(request),
            "active_count": RewardRule.objects.filter(is_active=True).count(),
        },
    )


@staff_required
def reward_rule_add(request):
    form = RewardRuleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(
            request,
            f"سرفصل تعرفه «{item.title}» ثبت شد (به‌ازای هر واحد {item.coins} امتیاز).",
        )
        return redirect(_reward_rules_list_url(request))
    return render(
        request,
        "adminpanel/reward_rule_form.html",
        {"form": form, "mode": "add", "next_url": _reward_rules_list_url(request)},
    )


@staff_required
def reward_rule_edit(request, pk):
    item = get_object_or_404(RewardRule, pk=pk)
    form = RewardRuleForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"سرفصل تعرفه «{item.title}» به‌روزرسانی شد.")
        return redirect(_reward_rules_list_url(request))
    return render(
        request,
        "adminpanel/reward_rule_form.html",
        {"form": form, "mode": "edit", "next_url": _reward_rules_list_url(request)},
    )


@staff_required
@require_POST
def reward_rule_toggle(request, pk):
    item = get_object_or_404(RewardRule, pk=pk)
    item.is_active = not item.is_active
    item.save(update_fields=["is_active"])
    messages.success(
        request,
        f"سرفصل تعرفه «{item.title}» {'فعال' if item.is_active else 'غیرفعال'} شد.",
    )
    return redirect(_reward_rules_list_url(request))


@staff_required
@require_POST
def reward_rule_delete(request, pk):
    item = get_object_or_404(RewardRule, pk=pk)
    title = item.title
    item.delete()
    messages.success(request, f"سرفصل تعرفه «{title}» حذف شد.")
    return redirect(_reward_rules_list_url(request))


# --- سفارش‌های خرید/فروش ---


@staff_required
def wallet_orders(request):
    """فهرست سفارش‌های خرید/فروش با فیلتر وضعیت و نوع + جستجو."""
    q = (request.GET.get("q") or "").strip()
    status = request.GET.get("status") or ""
    kind = request.GET.get("kind") or ""

    qs = CoinOrder.objects.select_related("user__profile").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    if kind:
        qs = qs.filter(kind=kind)
    if q:
        qs = qs.filter(
            Q(code__icontains=q)
            | Q(user__mobile_number__icontains=q)
            | Q(payout_iban__icontains=q)
        )

    total = qs.count()
    page_obj = Paginator(qs, 25).get_page(request.GET.get("page"))
    rows = [
        {
            "pk": o.pk,
            "code": o.code,
            "user_pk": o.user_id,
            "user_label": _user_label_safe(o.user),
            "mobile": o.user.mobile_number,
            "kind": o.kind,
            "kind_label": o.get_kind_display(),
            "coins": o.coins,
            "unit_price_rial": o.unit_price_rial,
            "total_rial": o.total_rial,
            "payout_iban": o.payout_iban,
            "status": o.status,
            "status_label": o.get_status_display(),
            "admin_note": o.admin_note,
            "created_at": o.created_at,
        }
        for o in page_obj.object_list
    ]

    base_params = {k: v for k, v in request.GET.items() if k != "page"}
    return render(
        request,
        "adminpanel/wallet_orders.html",
        {
            "q": q,
            "status": status,
            "kind": kind,
            "rows": rows,
            "total": total,
            "page_obj": page_obj,
            "base_query": urlencode(base_params),
            "next_url": _orders_list_url(request),
            "pending_count": CoinOrder.objects.filter(
                status=CoinOrder.STATUS_PENDING
            ).count(),
        },
    )


@staff_required
@require_POST
def wallet_order_action(request, pk):
    """تأیید یا ابطال سفارش خرید/فروش توسط ادمین (با تیکت به کاربر)."""
    order = get_object_or_404(CoinOrder, pk=pk)
    action = request.POST.get("action")
    try:
        if action == "approve":
            approve_order(order, request.user, request=request)
            messages.success(request, f"سفارش {order.code} تأیید شد و تیکت نتیجه برای کاربر ارسال گردید.")
        elif action == "reject":
            reject_order(order, request.user, note=request.POST.get("admin_note", ""),
                         request=request)
            messages.success(request, f"سفارش {order.code} ابطال شد و تیکت نتیجه برای کاربر ارسال گردید.")
        else:
            messages.error(request, "عملیات ناشناخته است.")
    except WalletServiceError as exc:
        messages.error(request, str(exc))
    return redirect(_orders_list_url(request))


# --- انتقال‌ها ---


def _transfers_list_url(request):
    params = {k: v for k, v in request.GET.items() if k != "page"}
    url = reverse("adminpanel:wallet_transfers")
    if params:
        url += "?" + urlencode(params)
    return url


def _profile_nid(user):
    """کد ملی کاربر یا «—» (پروفایل/کد ملی ثبت‌نشده نباید لیست را بشکند)."""
    try:
        return user.profile.national_id or "—"
    except Exception:  # noqa: BLE001 - پروفایلِ ناقص نباید لیست را بشکند
        return "—"


@staff_required
@require_http_methods(["GET", "POST"])
def wallet_transfers(request):
    """انتقال‌های سکه: ثبت انتقال «بین دو کاربر» فقط با کد ملی + فهرست/جستجو."""

    # ثبت انتقال توسط ادمین: فقط با کد ملی معتبر فرستنده و گیرنده
    if request.method == "POST" and request.POST.get("action") == "create_transfer":
        try:
            sender = find_user_by_national_id(
                request.POST.get("sender_national_id", "")
            )
            receiver = find_user_by_national_id(
                request.POST.get("receiver_national_id", "")
            )
            transfer = transfer_coins(
                sender, receiver, request.POST.get("coins"),
                note=request.POST.get("note", ""), request=request,
                author=request.user,
            )
            messages.success(
                request,
                f"{transfer.coins} سکه با کد «{transfer.code}» از "
                f"«{_user_label_safe(sender)}» به «{_user_label_safe(receiver)}» "
                "منتقل شد و تیکت اطلاع‌رسانی برای هر دو طرف ارسال گردید.",
            )
        except WalletServiceError as exc:
            messages.error(request, str(exc))
        return redirect(_transfers_list_url(request))

    q = (request.GET.get("q") or "").strip()
    qs = CoinTransfer.objects.select_related("sender__profile", "receiver__profile")
    if q:
        qs = qs.filter(
            Q(code__icontains=q)
            | Q(sender__mobile_number__icontains=q)
            | Q(receiver__mobile_number__icontains=q)
            | Q(sender__profile__national_id__icontains=q)
            | Q(receiver__profile__national_id__icontains=q)
        )
    total = qs.count()
    page_obj = Paginator(qs, 25).get_page(request.GET.get("page"))
    rows = [
        {
            "pk": t.pk,
            "code": t.code,
            "sender_label": _user_label_safe(t.sender),
            "sender_mobile": t.sender.mobile_number,
            "sender_nid": _profile_nid(t.sender),
            "receiver_label": _user_label_safe(t.receiver),
            "receiver_mobile": t.receiver.mobile_number,
            "receiver_nid": _profile_nid(t.receiver),
            "coins": t.coins,
            "note": t.note,
            "created_at": t.created_at,
        }
        for t in page_obj.object_list
    ]
    base_params = {k: v for k, v in request.GET.items() if k != "page"}
    return render(
        request,
        "adminpanel/wallet_transfers.html",
        {
            "q": q,
            "rows": rows,
            "total": total,
            "page_obj": page_obj,
            "base_query": urlencode(base_params),
        },
    )


# --- موجودی کیف پول کاربران ---


@staff_required
def wallet_wallets(request):
    """فهرست کیف پول کاربران + تنظیم دستی موجودی توسط ادمین."""

    def _safe_next():
        params = {k: v for k, v in request.GET.items() if k != "page"}
        url = reverse("adminpanel:wallet_wallets")
        return url + (("?" + urlencode(params)) if params else "")

    # تنظیم دستی موجودی
    if request.method == "POST" and request.POST.get("action") == "adjust":
        try:
            user = get_object_or_404(User, pk=request.POST.get("user_id"))
        except (ValueError, TypeError):
            user = None
        if user:
            try:
                wallet = adjust_balance(
                    request.user, user,
                    request.POST.get("amount"),
                    note=request.POST.get("note", ""),
                    request=request,
                )
                messages.success(
                    request,
                    f"موجودی «{_user_label_safe(user)}» تغییر کرد؛ ماندهٔ فعلی: "
                    f"{wallet.balance} سکه.",
                )
            except WalletServiceError as exc:
                messages.error(request, str(exc))
        return redirect(_safe_next())

    q = (request.GET.get("q") or "").strip()
    qs = Wallet.objects.select_related("user__profile").order_by("-balance")
    if q:
        qs = qs.filter(
            Q(user__mobile_number__icontains=q)
            | Q(user__profile__first_name__first_name_fa__icontains=q)
            | Q(user__profile__last_name__familyname_fa__icontains=q)
        )
    total = qs.count()
    page_obj = Paginator(qs, 25).get_page(request.GET.get("page"))
    rows = [
        {
            "pk": w.pk,
            "user_pk": w.user_id,
            "user_label": _user_label_safe(w.user),
            "mobile": w.user.mobile_number,
            "balance": w.balance,
            "value_rial": (w.balance * current_rate()).quantize(Decimal("0.01")),
            "updated_at": w.updated_at,
        }
        for w in page_obj.object_list
    ]
    base_params = {k: v for k, v in request.GET.items() if k != "page"}
    return render(
        request,
        "adminpanel/wallet_wallets.html",
        {
            "q": q,
            "rows": rows,
            "total": total,
            "page_obj": page_obj,
            "base_query": urlencode(base_params),
        },
    )


# ---------------------------------------------------------------------------
# ماژول «پشتیبان‌گیری و بازیابی دیتابیس» (فقط ادمین)
# ---------------------------------------------------------------------------


@staff_required
def backup_home(request):
    """صفحهٔ ماژول: پشتیبان دستی + تنظیمات خودکار + فهرست نسخه‌ها."""
    # بررسی فرصت‌طلبانه: اگر زمانِ پشتیبان خودکار رسیده باشد همین‌جا انجام می‌شود
    try:
        auto_backup_if_due()
    except Exception:  # noqa: BLE001
        pass

    setting = BackupSetting.get()
    if request.method == "POST" and request.POST.get("submit") == "settings":
        form = BackupSettingsForm(request.POST, instance=setting)
        if form.is_valid():
            form.save()
            messages.success(request, "تنظیمات پشتیبان‌گیری ذخیره شد.")
            return redirect("adminpanel:backup_home")
        messages.error(request, "لطفاً مقادیر فرم تنظیمات را بررسی کنید.")
    else:
        form = BackupSettingsForm(instance=setting)

    files = list(BackupFile.objects.select_related("created_by").all()[:80])
    rows = []
    for f in files:
        path = safe_path_for(f)
        rows.append({
            "pk": f.pk,
            "filename": f.filename,
            "kind": f.kind,
            "kind_label": "خودکار" if f.kind == BACKUP_KIND_AUTO else "دستی",
            "status": f.status,
            "failed": f.status != "ok",
            "error": f.error,
            "size": f.size_bytes,
            "size_label": _human_size(f.size_bytes),
            "exists": path is not None,
            "by": f.created_by.profile.full_name if (f.created_by_id and hasattr(f.created_by, "profile")) else "",
            "title": f.title,
            "note": f.note,
            "created_at": f.created_at,
        })
    return render(
        request,
        "adminpanel/backup_home.html",
        {
            "form": form,
            "setting": setting,
            "rows": rows,
            "backup_dir": backup_dir(),
            "default_dir": default_backup_dir(),        "total_size": sum(f.size_bytes for f in files if f.status == "ok"),
        "db_name": db_config()["name"],
        "backup_stats": _backup_dashboard_stats(),
        },
    )


def _human_size(size):
    if size is None:
        return "—"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024.0
    return f"{value:.1f} GB"


@staff_required
@require_POST
def backup_now(request):
    """گرفتن یک پشتیبان دستی فوری (با نام/توضیح دلخواه ادمین)."""
    title = (request.POST.get("title") or "").strip()[:200]
    note = (request.POST.get("note") or "").strip()[:1000]
    try:
        record = run_backup(
            kind=BACKUP_KIND_MANUAL,
            user=request.user,
            title=title,
            note=note,
        )
        messages.success(
            request,
            f"پشتیبان دستی با موفقیت گرفته شد: «{record.filename}» "
            f"({_human_size(record.size_bytes)})",
        )
    except BackupServiceError as exc:
        messages.error(request, str(exc))
    return redirect("adminpanel:backup_home")


@staff_required
def backup_download_all(request):
    """دانلود همهٔ فایل‌های پشتیبان موجود در یک فایل فشرده (.zip)."""
    import io
    import zipfile

    records = BackupFile.objects.filter(status=BACKUP_STATUS_OK).order_by("-created_at")[:200]
    buffer = io.BytesIO()
    added = 0
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for rec in records:
            path = safe_path_for(rec)
            if not path:
                continue
            zf.write(path, arcname=os.path.basename(path))
            added += 1
    if not added:
        messages.error(request, "هیچ فایل پشتیبان موجودی روی دیسک پیدا نشد.")
        return redirect("adminpanel:backup_home")
    buffer.seek(0)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f"habib_db_backups_{stamp}.zip",
        content_type="application/zip",
    )


@staff_required
def backup_download(request, pk):
    """دانلود فایل پشتیبان (فقط خود فایلِ داخل پوشهٔ پشتیبان)."""
    record = get_object_or_404(BackupFile, pk=pk)
    path = safe_path_for(record)
    if not path:
        messages.error(request, "فایل پشتیبان روی دیسک یافت نشد.")
        return redirect("adminpanel:backup_home")
    return FileResponse(
        open(path, "rb"),
        as_attachment=True,
        filename=record.filename,
        content_type="application/sql",
    )


@staff_required
@require_POST
def backup_delete(request, pk):
    """حذف یک نسخهٔ پشتیبان (فایل + رکورد)."""
    record = get_object_or_404(BackupFile, pk=pk)
    name = record.filename
    try:
        delete_backup(record)
        messages.success(request, f"پشتیبان «{name}» حذف شد.")
    except OSError as exc:
        messages.error(request, f"حذف فایل ناموفق بود: {exc}")
    return redirect("adminpanel:backup_home")


@staff_required
@require_POST
def backup_restore(request, pk):
    """بازیابی دیتابیس از یک نسخهٔ پشتیبان (با تأیید صریح: تایپ نام فایل)."""
    record = get_object_or_404(BackupFile, pk=pk)
    confirm = (request.POST.get("confirm_text") or "").strip()
    if confirm != record.filename:
        messages.error(
            request,
            "عبارت تأیید با نام فایل یکسان نبود؛ بازیابی انجام نشد. نام فایل را دقیقاً همان‌طور که در فهرست است تایپ کنید.",
        )
        return redirect("adminpanel:backup_home")
    try:
        run_restore(record)
        messages.success(
            request,
            f"دیتابیس با موفقیت از «{record.filename}» بازیابی شد. صفحه را تازه‌سازی کنید.",
        )
        # پس از تعویض دیتابیس، نشستِ جاریِ ادمین دوباره ذخیره می‌شود تا لاگ‌اوت نشود
        try:
            request.session.save()
        except Exception:  # noqa: BLE001
            pass
    except BackupServiceError as exc:
        messages.error(request, str(exc))
    return redirect("adminpanel:backup_home")


# ---------------------------------------------------------------------------
# ماژول «اخبار فوری» هدر برنامه
# ---------------------------------------------------------------------------


def _breaking_state(news):
    """وضعیت نمایش خبر فوری برای بِج‌های فهرست."""
    from django.utils import timezone

    now = timezone.now()
    if not news.is_active:
        return "paused"
    if now < news.show_from:
        return "scheduled"
    if now > news.show_until:
        return "ended"
    return "live"


_BREAKING_STATE_LABELS = {
    "live": "در حال پخش",
    "scheduled": "زمان‌بندی‌شده",
    "paused": "متوقف‌شده",
    "ended": "پایان‌یافته",
}


@staff_required
def breaking_news_list(request):
    """فهرست اخبار فوری هدر + شمارندهٔ خبرهای در حال پخش."""
    items = [
        {
            "obj": news,
            "state": _breaking_state(news),
            "state_label": _BREAKING_STATE_LABELS[_breaking_state(news)],
        }
        for news in BreakingNews.objects.all().order_by("sort_order", "id")
    ]
    from django.utils import timezone

    now = timezone.now()
    return render(
        request,
        "adminpanel/breaking_news_list.html",
        {
            "items": items,
            "live_count": BreakingNews.objects.filter(
                is_active=True, show_from__lte=now, show_until__gte=now
            ).count(),
        },
    )


@staff_required
def breaking_news_add(request):
    """افزودن خبر فوری (تاریخ/ساعت با تقویم شمسی در قالب)."""
    form = BreakingNewsForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        news = form.save(commit=False)
        news.created_by = request.user
        news.save()
        messages.success(request, "خبر فوری ثبت شد و در بازهٔ تعیین‌شده پخش می‌شود.")
        return redirect("adminpanel:breaking_news_list")
    return render(
        request,
        "adminpanel/breaking_news_form.html",
        {"form": form, "is_edit": False},
    )


@staff_required
def breaking_news_edit(request, pk):
    """ویرایش خبر فوری."""
    news = get_object_or_404(BreakingNews, pk=pk)
    form = BreakingNewsForm(request.POST or None, instance=news)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "خبر فوری به‌روزرسانی شد.")
        return redirect("adminpanel:breaking_news_list")
    return render(
        request,
        "adminpanel/breaking_news_form.html",
        {"form": form, "is_edit": True},
    )


@staff_required
@require_POST
def breaking_news_toggle(request, pk):
    """توقف/ادامهٔ پخش خبر فوری."""
    news = get_object_or_404(BreakingNews, pk=pk)
    news.is_active = not news.is_active
    news.save(update_fields=["is_active"])
    messages.success(
        request,
        f"خبر «{news.text[:40]}» {'ادامهٔ پخش' if news.is_active else 'متوقف'} شد.",
    )
    return redirect("adminpanel:breaking_news_list")


@staff_required
@require_POST
def breaking_news_delete(request, pk):
    """حذف کامل خبر فوری."""
    news = get_object_or_404(BreakingNews, pk=pk)
    text = news.text[:40]
    news.delete()
    messages.success(request, f"خبر «{text}» حذف شد.")
    return redirect("adminpanel:breaking_news_list")


# ---------------------------------------------------------------------------
# ماژول «تبلیغات»: لوگوی تبلیغاتی کاربران — پخش در نوار متحرک پایین داشبورد
# ---------------------------------------------------------------------------


def _ad_state(ad):
    """وضعیت «نمایش» تبلیغ برای بِج‌های فهرست."""
    from django.utils import timezone

    now = timezone.now()
    if ad.status == AD_STATUS_PENDING:
        return "pending"
    if ad.status == AD_STATUS_REJECTED:
        return "rejected"
    if not ad.is_active:
        return "paused"
    if now < ad.show_from:
        return "scheduled"
    if now > ad.show_until:
        return "ended"
    return "live"


_AD_STATE_LABELS = {
    "live": "در حال پخش",
    "scheduled": "زمان‌بندی‌شده",
    "paused": "متوقف‌شده",
    "ended": "پایان‌یافته",
    "pending": "در انتظار تأیید",
    "rejected": "ردشده",
}


@staff_required
def ads_list(request):
    """فهرست تبلیغ‌های کاربران + تنظیمات ردیف نمایش نوار."""
    ads = Advertisement.objects.select_related("advertiser__profile").order_by(
        "sort_order", "updated_at", "id"
    )
    items = [
        {
            "obj": ad,
            "state": _ad_state(ad),
            "state_label": _AD_STATE_LABELS[_ad_state(ad)],
        }
        for ad in ads
    ]
    # سرعت مؤثرِ فعلی نوار = کمترین سرعت معتبر (۵ تا ۱۲۰) بین تبلیغ‌های
    # «در حال پخش»؛ برای راهنمای ادمین نمایش داده می‌شود (پیش‌فرض: ۳۰).
    live_speeds = [
        it["obj"].speed
        for it in items
        if it["state"] == "live" and 5 <= (it["obj"].speed or 0) <= 120
    ]
    effective_speed = min(live_speeds) if live_speeds else 30
    return render(
        request,
        "adminpanel/ads_list.html",
        {
            "items": items,
            "ticker_setting": AdTickerSetting.get(),
            "effective_speed": effective_speed,
        },
    )


@staff_required
def ads_edit(request, pk):
    """ویرایش تبلیغ: بازهٔ نمایش (تقویم شمسی) + سرعت/ترتیب + هدرهای پخش."""
    ad = get_object_or_404(Advertisement, pk=pk)
    form = AdvertisementForm(request.POST or None, request.FILES or None, instance=ad)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"تبلیغ «{ad.title}» به‌روزرسانی شد.")
        return redirect("adminpanel:ads_list")
    return render(
        request,
        "adminpanel/ad_form.html",
        {"form": form, "item": ad},
    )


@staff_required
@require_POST
def ads_toggle(request, pk):
    """توقف/ادامهٔ پخش تبلیغ."""
    ad = get_object_or_404(Advertisement, pk=pk)
    ad.is_active = not ad.is_active
    ad.save(update_fields=["is_active"])
    messages.success(
        request,
        f"تبلیغ «{ad.title}» {'ادامهٔ پخش' if ad.is_active else 'متوقف'} شد.",
    )
    return redirect("adminpanel:ads_list")


@staff_required
@require_POST
def ads_approve(request, pk):
    """تأیید تبلیغِ در انتظار (پرداخت انجام شده؛ شروع پخش طبق بازهٔ ثبت‌شده).

    کاربر با تیکت مطلع می‌شود و تیکت درخواست تأیید بسته می‌شود.
    """
    from ads.approvals import approve_item

    ad = get_object_or_404(Advertisement, pk=pk)
    ok, code = approve_item(ad, request.user, request=request)
    if ok:
        messages.success(request, f"تبلیغ «{ad.title}» تأیید شد و در صف پخش قرار گرفت.")
    elif code == "refunded":
        messages.error(
            request,
            f"تبلیغ «{ad.title}» قبلاً رد و وجه آن بازگردانده شده؛ برای نمایش، کاربر باید دوباره ثبت کند.",
        )
    else:
        messages.info(request, f"تبلیغ «{ad.title}» قبلاً تأیید شده است.")
    return redirect("adminpanel:ads_list")


@staff_required
@require_POST
def ads_reject(request, pk):
    """رد تبلیغ: برای مورد «در انتظار»، ۱۰٪ کارمزد کسر و مابقی به کیف پول کاربر بازمی‌گردد.

    بازگشت وجه فقط یک‌بار انجام می‌شود و با تیکت به کاربر و مدیران اعلام می‌گردد.
    """
    from ads.approvals import reject_item

    ad = get_object_or_404(Advertisement, pk=pk)
    res = reject_item(ad, request.user, request=request,
                      reason=(request.POST.get("reason") or "").strip())
    if res["code"] == "already":
        messages.info(request, f"تبلیغ «{ad.title}» قبلاً رد شده است.")
    elif res["refunded"]:
        messages.success(
            request,
            f"تبلیغ «{ad.title}» رد شد؛ {res['refund']} سکه به کیف پول کاربر بازگشت "
            f"(کارمزد {res['fee']} سکه).",
        )
    else:
        messages.success(request, f"تبلیغ «{ad.title}» رد شد (وجهی بازگردانده نشد).")
    return redirect("adminpanel:ads_list")


@staff_required
@require_POST
def ads_delete(request, pk):
    """حذف کامل تبلیغ (لوگو هم از دیسک پاک می‌شود)."""
    ad = get_object_or_404(Advertisement, pk=pk)
    title = ad.title
    if ad.logo:
        ad.logo.delete(save=False)
    ad.delete()
    messages.success(request, f"تبلیغ «{title}» حذف شد.")
    return redirect("adminpanel:ads_list")


@staff_required
@require_POST
def ads_move(request, pk, direction):
    """جابه‌جایی ترتیب پخش تبلیغ (up = اولویت بیشتر)."""
    ad = get_object_or_404(Advertisement, pk=pk)
    if direction == "up":
        ad.sort_order = max(0, ad.sort_order - 1)
    elif direction == "down":
        ad.sort_order = ad.sort_order + 1
    else:
        messages.error(request, "جهت جابه‌جایی نامعتبر است.")
        return redirect("adminpanel:ads_list")
    ad.save(update_fields=["sort_order"])
    messages.success(request, f"ترتیب تبلیغ «{ad.title}» تغییر کرد.")
    return redirect("adminpanel:ads_list")


@staff_required
@require_POST
def ads_settings(request):
    """ذخیرهٔ «حداکثر تبلیغ در ردیف نمایش» نوار متحرک."""
    setting = AdTickerSetting.get()
    raw = (request.POST.get("max_visible") or "").strip()
    try:
        setting.max_visible = max(0, int(raw))
        setting.save(update_fields=["max_visible", "updated_at"])
        messages.success(
            request,
            f"سقف ردیف نمایش = {setting.max_visible} تبلیغ ذخیره شد"
            + (" (بدون سقف)." if setting.max_visible == 0 else "."),
        )
    except (TypeError, ValueError):
        messages.error(request, "عدد معتبری برای «حداکثر تبلیغ در ردیف نمایش» وارد کنید.")
    return redirect("adminpanel:ads_list")


# ---------------------------------------------------------------------------
# مدیریت «محل‌های تبلیغ هدر»: هر هدر که نوار تبلیغات در آن پخش شود؛
# فعال/غیرفعال + ترتیب چک‌باکس‌های کاربر
# ---------------------------------------------------------------------------


def _header_placements_list_url(request):
    params = {k: v for k, v in request.GET.items() if k != "page"}
    url = reverse("adminpanel:header_placements_list")
    if params:
        url += "?" + urlencode(params)
    return url


@staff_required
def header_placements_list(request):
    """فهرست محل‌های تبلیغ هدر با جستجو + فیلتر فعال/غیرفعال."""
    q = (request.GET.get("q") or "").strip()
    active = request.GET.get("active") or ""

    qs = AdHeaderPlacement.objects.all().order_by("sort_order", "id")
    if active == "1":
        qs = qs.filter(is_active=True)
    elif active == "0":
        qs = qs.filter(is_active=False)
    if q:
        qs = qs.filter(
            Q(code__icontains=q) | Q(title__icontains=q) | Q(description__icontains=q)
        )

    total = qs.count()
    rows = [
        {
            "pk": item.pk,
            "code": item.code,
            "title": item.title,
            "description": item.description,
            "sort_order": item.sort_order,
            "is_active": item.is_active,
            "ad_count": item.advertisements.count(),
            "updated_at": item.updated_at,
        }
        for item in qs
    ]

    base_params = {k: v for k, v in request.GET.items() if k != "page"}
    return render(
        request,
        "adminpanel/header_placements_list.html",
        {
            "q": q,
            "active": active,
            "rows": rows,
            "total": total,
            "base_query": urlencode(base_params),
            "next_url": _header_placements_list_url(request),
            "active_count": AdHeaderPlacement.objects.filter(is_active=True).count(),
        },
    )


@staff_required
def header_placement_add(request):
    """افزودن محل تبلیغ هدر جدید."""
    form = AdHeaderPlacementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(request, f"محل تبلیغ هدر «{item.title}» ثبت شد.")
        return redirect(_header_placements_list_url(request))
    return render(
        request,
        "adminpanel/header_placement_form.html",
        {"form": form, "mode": "add", "is_edit": False,
         "next_url": _header_placements_list_url(request)},
    )


@staff_required
def header_placement_edit(request, pk):
    """ویرایش محل تبلیغ هدر."""
    item = get_object_or_404(AdHeaderPlacement, pk=pk)
    form = AdHeaderPlacementForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"محل تبلیغ هدر «{item.title}» به‌روزرسانی شد.")
        return redirect(_header_placements_list_url(request))
    return render(
        request,
        "adminpanel/header_placement_form.html",
        {"form": form, "mode": "edit", "is_edit": True,
         "next_url": _header_placements_list_url(request)},
    )


@staff_required
@require_POST
def header_placement_toggle(request, pk):
    """فعال/غیرفعال‌کردن محل تبلیغ هدر (جایگزین امنِ حذف)."""
    item = get_object_or_404(AdHeaderPlacement, pk=pk)
    item.is_active = not item.is_active
    item.save(update_fields=["is_active"])
    messages.success(
        request,
        f"محل تبلیغ هدر «{item.title}» {'فعال' if item.is_active else 'غیرفعال'} شد.",
    )
    return redirect(_header_placements_list_url(request))


@staff_required
@require_POST
def header_placement_delete(request, pk):
    """حذف کامل محل تبلیغ هدر (در صورت استفادهٔ زیاد، غیرفعال‌کردن پیشنهاد می‌شود)."""
    item = get_object_or_404(AdHeaderPlacement, pk=pk)
    title = item.title
    try:
        item.delete()
        messages.success(request, f"محل تبلیغ هدر «{title}» حذف شد.")
    except ProtectedError:
        messages.error(
            request,
            f"محل تبلیغ هدر «{title}» توسط تبلیغ‌های ثبت‌شده استفاده می‌شود؛ آن را «غیرفعال» کنید.",
        )
    return redirect(_header_placements_list_url(request))


# ---------------------------------------------------------------------------
# ماژول «اسلایدشوی آمار داشبورد»: ۴ باکس آمارِ بالای «ماژول‌های کسب‌وکار»
# (اسلایدشو A / اسلایدشو B / اسلایدشو C / اسلایدشو D)؛ مدیریت
# اسلایدها + هزینهٔ دریافتی + تنظیم زمان تغییر اسلاید — مشابه ماژول تبلیغات.
# ---------------------------------------------------------------------------


def _stat_slide_state(slide):
    from django.utils import timezone

    now = timezone.now()
    if not slide.is_active:
        return "paused"
    if slide.show_from and now < slide.show_from:
        return "scheduled"
    if slide.show_until and now > slide.show_until:
        return "ended"
    return "live"


_STAT_SLIDE_STATE_LABELS = {
    "live": "در حال پخش",
    "scheduled": "زمان‌بندی‌شده (شروع نشده)",
    "paused": "متوقف‌شده",
    "ended": "پایان‌یافته",
}


def _stat_slides_list_url(request):
    params = {k: v for k, v in request.GET.items() if k != "page"}
    url = reverse("adminpanel:stat_slides_list")
    if params:
        url += "?" + urlencode(params)
    return url


@staff_required
def stat_slides_list(request):
    """فهرست اسلایدهای اسلایدشوی آمار + جمع هزینهٔ دریافتی + تنظیمات."""
    q = (request.GET.get("q") or "").strip()
    box = (request.GET.get("box") or "").strip()
    active = request.GET.get("active") or ""
    status = (request.GET.get("status") or "").strip()

    qs = StatSlide.objects.all().order_by("sort_order", "updated_at", "id")
    if box:
        qs = qs.filter(boxes__code=box).distinct()
    if active == "1":
        qs = qs.filter(is_active=True)
    elif active == "0":
        qs = qs.filter(is_active=False)
    if status == "pending":
        qs = qs.filter(status=AD_STATUS_PENDING)
    elif status == "approved":
        qs = qs.filter(status=AD_STATUS_APPROVED)
    elif status == "rejected":
        qs = qs.filter(status=AD_STATUS_REJECTED)
    if q:
        qs = qs.filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(link_url__icontains=q)
        ).distinct()

    items = [
        {
            "obj": slide,
            "state": _stat_slide_state(slide),
            "state_label": _STAT_SLIDE_STATE_LABELS[_stat_slide_state(slide)],
        }
        for slide in qs
    ]
    # جمع «هزینه‌های دریافتی» — مشابه ستون هزینه ماژول تبلیغات؛
    # بر پایهٔ کل رکوردهای اسلاید (بدون فیلتر جستجو) برای گزارش مالی ادمن.
    from django.db.models import Sum

    coins_total = StatSlide.objects.aggregate(total=Sum("coins_paid"))["total"] or 0
    pending_count = StatSlide.objects.filter(status=AD_STATUS_PENDING).count()
    boxes = StatSlideBox.objects.all().order_by("sort_order", "id")
    return render(
        request,
        "adminpanel/stat_slides_list.html",
        {
            "items": items,
            "boxes": boxes,
            "q": q,
            "box": box,
            "active": active,
            "status": status,
            "ad_status_pending": AD_STATUS_PENDING,
            "ad_status_approved": AD_STATUS_APPROVED,
            "ad_status_rejected": AD_STATUS_REJECTED,
            "coins_total": coins_total,
            "pending_count": pending_count,
            "slide_setting": StatSlideSetting.get(),
            "next_url": _stat_slides_list_url(request),
        },
    )


@staff_required
def stat_slide_add(request):
    """افزودن اسلاید جدید به اسلایدشوی آمار (مشابه ثبت تبلیغ).

    اسلایدِ ثبت‌شده از پنل مدیریت مستقیماً «تأییدشده» است (ادمین خودش تأیید می‌کند).
    """
    form = StatSlideForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.status = AD_STATUS_APPROVED
        item.save()
        item.boxes.set(form.cleaned_data["stat_boxes"])
        messages.success(request, f"اسلاید «{item.title}» ثبت و تأیید شد.")
        return redirect(_stat_slides_list_url(request))
    return render(
        request,
        "adminpanel/stat_slide_form.html",
        {"form": form, "mode": "add", "is_edit": False, "item": None,
         "next_url": _stat_slides_list_url(request)},
    )


@staff_required
def stat_slide_edit(request, pk):
    """ویرایش اسلاید: تصویر/متن/لینک + بازهٔ نمایش (تقویم شمسی) + باکس‌ها."""
    item = get_object_or_404(StatSlide, pk=pk)
    form = StatSlideForm(request.POST or None, request.FILES or None, instance=item)
    boxes_before = list(item.boxes.values_list("pk", flat=True))
    if request.method == "POST" and form.is_valid():
        form.save()
        item.boxes.set(form.cleaned_data["stat_boxes"])
        # ویرایش توسط ادمین؛ اگر اسلاید «ردشده» بود به «در انتظار» برنگردد:
        # نسخهٔ اصلاح‌شده را مستقیماً تأیید کنیم (تعریف گردش کار ادمین).
        if item.status == AD_STATUS_REJECTED and item.refunded_at is None:
            item.status = AD_STATUS_APPROVED
            item.save(update_fields=["status"])
        messages.success(request, f"اسلاید «{item.title}» به‌روزرسانی شد.")
        return redirect(_stat_slides_list_url(request))
    return render(
        request,
        "adminpanel/stat_slide_form.html",
        {"form": form, "mode": "edit", "is_edit": True, "item": item,
         "boxes_before": boxes_before, "next_url": _stat_slides_list_url(request)},
    )


@staff_required
@require_POST
def stat_slide_toggle(request, pk):
    """توقف/ادامهٔ پخش اسلاید (مشابه تبلیغ)."""
    item = get_object_or_404(StatSlide, pk=pk)
    item.is_active = not item.is_active
    item.save(update_fields=["is_active"])
    messages.success(
        request,
        f"اسلاید «{item.title}» {'ادامهٔ پخش' if item.is_active else 'متوقف'} شد.",
    )
    return redirect(_stat_slides_list_url(request))


@staff_required
@require_POST
def stat_slide_delete(request, pk):
    """حذف کامل اسلاید (تصویر هم از دیسک پاک می‌شود)."""
    item = get_object_or_404(StatSlide, pk=pk)
    title = item.title
    if item.image:
        item.image.delete(save=False)
    item.delete()
    messages.success(request, f"اسلاید «{title}» حذف شد.")
    return redirect(_stat_slides_list_url(request))


@staff_required
@require_POST
def stat_slide_move(request, pk, direction):
    """جابه‌جایی ترتیب پخش اسلاید در اسلایدشو (up = جلوتر)."""
    item = get_object_or_404(StatSlide, pk=pk)
    if direction == "up":
        item.sort_order = max(0, item.sort_order - 1)
    elif direction == "down":
        item.sort_order = item.sort_order + 1
    else:
        messages.error(request, "جهت جابه‌جایی نامعتبر است.")
        return redirect(_stat_slides_list_url(request))
    item.save(update_fields=["sort_order"])
    messages.success(request, f"ترتیب اسلاید «{item.title}» تغییر کرد.")
    return redirect(_stat_slides_list_url(request))


@staff_required
def stat_slides_settings(request):
    """ذخیرهٔ «زمان پیش‌فرض هر اسلاید (ثانیه)» اسلایدشوی آمار."""
    setting = StatSlideSetting.get()
    raw = (request.POST.get("switch_seconds") or "").strip()
    try:
        value = int(raw)
    except (TypeError, ValueError):
        messages.error(request, "عدد معتبری برای «زمان هر اسلاید» وارد کنید.")
        return redirect(_stat_slides_list_url(request))
    if not (3 <= value <= 120):
        messages.error(request, "زمان هر اسلاید باید بین ۳ تا ۱۲۰ ثانیه باشد.")
        return redirect(_stat_slides_list_url(request))
    setting.switch_seconds = value
    setting.save(update_fields=["switch_seconds", "updated_at"])
    messages.success(request, f"زمان هر اسلاید = {value} ثانیه ذخیره شد.")
    return redirect(_stat_slides_list_url(request))


@staff_required
def stat_box_update(request, pk):
    """تنظیم زمانِ نمایش اسلایدِ یک باکس (۳ تا ۱۲۰ ثانیه؛ ۰ = پیش‌فرض سراسری)."""
    item = get_object_or_404(StatSlideBox, pk=pk)
    raw = (request.POST.get("switch_seconds") or "").strip()
    try:
        value = int(raw)
    except (TypeError, ValueError):
        messages.error(request, "عدد معتبری برای «زمان هر اسلاید» وارد کنید.")
        return redirect(_stat_slides_list_url(request))
    if not (0 <= value <= 120):
        messages.error(request, "زمان هر اسلاید باید بین ۰ تا ۱۲۰ ثانیه باشد (۰ = پیش‌فرض سراسری).")
        return redirect(_stat_slides_list_url(request))
    item.switch_seconds = value
    item.save(update_fields=["switch_seconds", "updated_at"])
    messages.success(
        request,
        f"زمان هر اسلایدِ باکس «{item.title}» ذخیره شد"
        + (" — از پیش‌فرض سراسری پیروی می‌کند." if value == 0 else f" ({value} ثانیه)."),
    )
    return redirect(_stat_slides_list_url(request))


@staff_required
@require_POST
def stat_slide_approve(request, pk):
    """تأیید اسلاید کاربر → اسلاید در «اسلایدشو A» در حال پخش قرار می‌گیرد."""
    from ads.approvals import approve_item

    item = get_object_or_404(StatSlide, pk=pk)
    ok, code = approve_item(item, request.user, request=request)
    if ok:
        messages.success(request, f"اسلاید «{item.title}» تأیید و در اسلایدشو پخش می‌شود.")
    elif code == "refunded":
        messages.error(
            request,
            f"اسلاید «{item.title}» قبلاً رد و وجه آن بازگردانده شده؛ کاربر باید دوباره ثبت کند.",
        )
    else:
        messages.info(request, f"اسلاید «{item.title}» قبلاً تأیید شده است.")
    return redirect(_stat_slides_list_url(request))


@staff_required
@require_POST
def stat_slide_reject(request, pk):
    """رد اسلاید کاربر → از اسلایدشو حذف می‌شود (ظرفیت آزاد می‌گردد).

    برای اسلاید «در انتظار»، ۱۰٪ کارمزد کسر و مابقی به کیف پول کاربر بازمی‌گردد
    (یک‌بار) و با تیکت به کاربر و مدیران اعلام می‌شود.
    """
    from ads.approvals import reject_item

    item = get_object_or_404(StatSlide, pk=pk)
    res = reject_item(item, request.user, request=request,
                      reason=(request.POST.get("reason") or "").strip())
    if res["code"] == "already":
        messages.info(request, f"اسلاید «{item.title}» قبلاً رد شده است.")
    elif res["refunded"]:
        messages.success(
            request,
            f"اسلاید «{item.title}» رد شد؛ {res['refund']} سکه به کیف پول کاربر بازگشت "
            f"(کارمزد {res['fee']} سکه).",
        )
    else:
        messages.success(request, f"اسلاید «{item.title}» رد شد و از اسلایدشو حذف می‌شود.")
    return redirect(_stat_slides_list_url(request))


@staff_required
@require_POST
def stat_box_toggle(request, pk):
    """فعال/غیرفعال‌کردن پخش اسلایدشو در یک باکس (با غیرفعال، آمار معمولی برمی‌گردد)."""
    item = get_object_or_404(StatSlideBox, pk=pk)
    item.is_active = not item.is_active
    item.save(update_fields=["is_active"])
    messages.success(
        request,
        f"پخش اسلایدشو در باکس «{item.title}» {'فعال' if item.is_active else 'غیرفعال'} شد.",
    )
    return redirect(_stat_slides_list_url(request))
