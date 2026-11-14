"""بخش مدیریتی «فضای ذخیره‌سازی ابری» در پنل مدیریت (فقط is_staff).

صفحات:
- ``storage_home``   : فعال/غیرفعال‌سازی ماژول، سقف‌ها، تعرفه‌ها، سیاست‌ها + آمار + تاریخچهٔ تعرفه
- ``storage_queues``  : صف آپلود/Sync/دانلود و عملیات ناموفق
- ``storage_reports`` : گزارش مصرف، صورتحساب‌ها و تراکنش‌ها
- ``storage_audit``   : دفتر ممیزی (تغییرات حساس ادمین با مقادیر قبل/بعد)

هر ذخیرهٔ حساس در ``StorageAuditLog`` با شناسهٔ مدیر، زمان و مقادیر قبل/بعد ثبت می‌شود.
"""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from adminpanel.views import staff_required

from . import services as S
from .forms import StorageSettingsForm
from .models import (
    ArchiveJob,
    StorageAccount,
    StorageAuditLog,
    StorageInvoice,
    StoragePricing,
    StorageSettings,
    StorageTransaction,
    SyncJob,
    UploadSession,
)


@staff_required
def storage_home(request):
    """تنظیمات کامل ماژول + آمار کلی + تاریخچهٔ تعرفه‌ها."""
    settings_obj = StorageSettings.get()
    form = StorageSettingsForm(request.POST or None, instance=settings_obj)

    if request.method == "POST" and form.is_valid():
        before = StorageSettings.snapshot()
        obj = form.save()
        after = StorageSettings.snapshot()
        changed = {k: {"before": before.get(k), "after": after.get(k)}
                   for k in after
                   if k not in ("id", "updated_at") and before.get(k) != after.get(k)}
        if changed:
            # عکس‌برداری تعرفه در صورت تغییر نرخ‌ها (تاریخچهٔ قیمت‌گذاری)
            rates_changed = any(k in changed for k in
                                ("storage_coin_per_gb", "transfer_coin_per_gb", "archive_coin_per_gb"))
            if rates_changed:
                StoragePricing.objects.filter(is_active=True).update(is_active=False)
                StoragePricing.objects.create(
                    storage_coin_per_gb=obj.storage_coin_per_gb,
                    transfer_coin_per_gb=obj.transfer_coin_per_gb,
                    archive_coin_per_gb=obj.archive_coin_per_gb,
                    is_active=True, created_by=request.user,
                )
            S.audit(request.user, "storage_settings_changed", "StorageSettings", obj.pk,
                    {"changed": changed}, request=request)
            messages.success(request, f"تنظیمات فضای ابری ذخیره شد ({len(changed)} مقدار تغییر کرد).")
        else:
            messages.info(request, "تغییری برای ذخیره وجود نداشت.")
        return redirect("adminpanel:storage_home")

    accounts = StorageAccount.objects.all()
    stats = {
        "users": accounts.count(),
        "used_bytes": accounts.aggregate(t=Sum("used_bytes"))["t"] or 0,
        "folders": _active_folder_count(),
        "objects": _active_object_count(),
        "sessions_by_status": dict(
            UploadSession.objects.values_list("status").annotate(c=Count("id")).order_by()),
        "archives_pending": ArchiveJob.objects.filter(status=ArchiveJob.STATUS_BUILDING).count(),
        "archives_failed": ArchiveJob.objects.filter(status=ArchiveJob.STATUS_FAILED).count(),
        "sync_failed": SyncJob.objects.filter(status=SyncJob.STATUS_FAILED).count(),
        "sessions_failed": UploadSession.objects.filter(
            status=UploadSession.STATUS_FAILED).count(),
    }
    return render(request, "cloudstorage/admin_home.html", {
        "form": form,
        "settings_obj": settings_obj,
        "stats": stats,
        "pricing_history": StoragePricing.objects.select_related("created_by")[:15],
        "nav_active": "admin",
    })


def _active_folder_count():
    from .models import StorageFolder
    return StorageFolder.objects.filter(status=StorageFolder.STATUS_ACTIVE).count()


def _active_object_count():
    from .models import StorageObject
    return StorageObject.objects.filter(status=StorageObject.STATUS_ACTIVE).count()


@staff_required
def storage_queues(request):
    """صف آپلودها، همگام‌سازی‌ها و آرشیوهای دانلود + عملیات ناموفق."""
    kind = request.GET.get("kind") or "sessions"
    status = request.GET.get("status") or ""

    rows, statuses = [], []
    if kind == "sync":
        statuses = [c for c, _ in SyncJob.STATUS_CHOICES]
        qs = SyncJob.objects.select_related("account__user", "folder").order_by("-started_at")
        if status:
            qs = qs.filter(status=status)
        rows = qs[:200]
    elif kind == "archives":
        statuses = [c for c, _ in ArchiveJob.STATUS_CHOICES]
        qs = ArchiveJob.objects.select_related("account__user", "folder").order_by("-id")
        if status:
            qs = qs.filter(status=status)
        rows = qs[:200]
    else:
        statuses = [c for c, _ in UploadSession.STATUS_CHOICES]
        qs = UploadSession.objects.select_related("account__user", "target_folder").order_by("-priced_at")
        if status:
            qs = qs.filter(status=status)
        rows = qs[:200]

    return render(request, "cloudstorage/admin_queues.html", {
        "kind": kind, "status": status, "statuses": statuses, "rows": rows,
        "failures": {
            "sessions_failed": UploadSession.objects.filter(status=UploadSession.STATUS_FAILED).count(),
            "archives_failed": ArchiveJob.objects.filter(status=ArchiveJob.STATUS_FAILED).count(),
            "sync_failed": SyncJob.objects.filter(status=SyncJob.STATUS_FAILED).count(),
        },
        "nav_active": "admin",
    })


@staff_required
def storage_reports(request):
    """گزارش مصرف کاربران + صورتحساب‌ها + تراکنش‌های مالی ماژول."""
    usage_qs = StorageAccount.objects.select_related("user").order_by("-used_bytes")
    q = (request.GET.get("q") or "").strip()
    if q:
        usage_qs = usage_qs.filter(user__mobile_number__icontains=q)

    page_obj = Paginator(usage_qs, 25).get_page(request.GET.get("page"))

    invoices = StorageInvoice.objects.select_related("account__user")[:50]
    tx_rows = StorageTransaction.objects.select_related("account__user", "invoice")[:50]
    charged = sum(t.amount_coins for t in StorageTransaction.objects.filter(kind=StorageTransaction.KIND_CHARGE))
    refunded = sum(t.amount_coins for t in StorageTransaction.objects.filter(kind=StorageTransaction.KIND_REFUND))

    return render(request, "cloudstorage/admin_reports.html", {
        "page_obj": page_obj, "q": q,
        "invoices": invoices, "tx_rows": tx_rows,
        "total_charged": charged, "total_refunded": refunded,
        "nav_active": "admin",
    })


@staff_required
def storage_audit(request):
    """دفتر ممیزی: تغییرات حساس ادمین و رویدادهای امنیتی/مالی (بدون اطلاعات حساس)."""
    qs = StorageAuditLog.objects.select_related("actor")
    action = (request.GET.get("action") or "").strip()
    if action:
        qs = qs.filter(action=action)
    page_obj = Paginator(qs, 40).get_page(request.GET.get("page"))
    actions = StorageAuditLog.objects.values_list("action", flat=True).distinct().order_by("action")
    return render(request, "cloudstorage/admin_audit.html", {
        "page_obj": page_obj, "action": action, "actions": actions,
        "nav_active": "admin",
    })


@staff_required
@require_POST
def storage_purge_archives(request):
    """پاک‌سازی دستی آرشیوهای منقضی (فایل فیزیکی + رکورد)."""
    removed = S.purge_expired_archives()
    messages.success(request, f"{removed} آرشیوی منقضی پاک‌سازی شد.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("adminpanel:storage_home"))