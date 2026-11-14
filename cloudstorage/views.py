"""ویوهای ماژول «فضای ذخیره‌سازی ابری» — فقط برای کاربر مالک.

امنیت:
- همهٔ دسترسی‌ها با بررسی مالکیت در DB (account__user) انجام می‌شوند؛
  کد ملی/نام پوشه هرگز مجوز نیست.
- پرداخت/آپلود با توکن سشن (secret token) و گذار وضعیت قفل‌شده idempotent.
- لینک دانلود آرشیو توکن زمان‌دار دارد.
- همهٔ ورودی‌ها (JSON مانیفست) سمت سرور نرمال و اعتبارسنجی می‌شوند.
"""
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from . import services as S
from .models import (
    ArchiveJob,
    CloudSpacePurchase,
    StorageAccount,
    StorageFolder,
    StorageObject,
    StorageSettings,
    SyncJob,
    UploadSession,
)


# --------------------------------------------------------------------------- #
# کمکی‌ها
# --------------------------------------------------------------------------- #
def _json_body(request):
    """بدنهٔ JSON درخواست؛ در صورت نبود یا خطا، خطا می‌دهد."""
    from django.core.exceptions import RequestDataTooBig

    try:
        body = request.body
    except RequestDataTooBig:
        # پیام فنی Django به فارسی قابل فهم برای کاربر تبدیل می‌شود
        raise S.StorageError(
            "حجم اطلاعات انتخاب‌شدهٔ شما بیش از حد مجاز سرور است؛ "
            "تعداد فایل‌ها/پوشه‌های همزمان را کاهش دهید و در صورت نیاز به‌صورت بخش‌بخش همگام‌سازی کنید."
        )
    if not body:
        return {}
    try:
        data = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise S.StorageError("دادهٔ ارسالی JSON معتبر نیست.")
    if not isinstance(data, dict):
        raise S.StorageError("ساختار دادهٔ ارسالی معتبر نیست.")
    return data


def _space_price():
    """تعرفهٔ فعال خرید فضای ابری (سکه به ازای هر GB در هر 24 ساعت) یا None."""
    from wallet.models import FeatureCost

    fc = FeatureCost.objects.filter(code="cloud_storage", is_active=True).first()
    return fc.coins if fc else None


def _wallet_balance(user):
    """موجودی فعلی سکهٔ کاربر (Decimal) یا None اگر کیف پولی ندارد."""
    from wallet.models import Wallet

    w = Wallet.objects.filter(user=user).only("balance").first()
    return w.balance if w else None


def _purchase_rows(purchases):
    """ردیف‌های نمایشی خریدهای فعال: مقدار، مهلت و زمان باقی‌مانده."""
    now = timezone.now()
    rows = []
    for p in purchases:
        secs = max(0, int((p.active_until - now).total_seconds()))
        rows.append({
            "purchase": p,
            "gb": p.storage_gb,
            "until": p.active_until,
            "days_left": secs // 86400,
            "hours_left": (secs % 86400) // 3600,
        })
    return rows


def _err(request, exc, status=400):
    """پاسخ خطای JSON با کد مناسب (۱۰ = PageNotAnInteger → ۴۰۴ برای ناموجود)."""
    from django.http import Http404
    if isinstance(exc, Http404):
        status = 404
    elif isinstance(exc, PermissionDenied) or isinstance(exc, S.StorageSecurityError):
        status = 403
    elif isinstance(exc, S.StorageError):
        status = 400
    else:
        status = 500
    return JsonResponse({"ok": False, "error": str(exc) if str(exc) else exc.__class__.__name__}, status=status)


def _owned_folder(user, uid):
    """پوشهٔ ابری متعلق به کاربر — در غیر این صورت 403."""
    folder = get_object_or_404(StorageFolder, uid=uid, account__user=user)
    if folder.account.user_id != user.pk or folder.status == StorageFolder.STATUS_DELETED:
        raise PermissionDenied()
    return folder


# --------------------------------------------------------------------------- #
# صفحهٔ اصلی ماژول
# --------------------------------------------------------------------------- #
@login_required(login_url="core:index")
def home(request):
    """صفحهٔ فضای ابری: سهمیه، پوشه‌ها، سشن‌های اخیر و کنترل‌های آپلود."""
    try:
        sts = S.settings_active()
    except PermissionDenied:
        messages.error(request, "ماژول «فضای ذخیره‌سازی ابری» در حال حاضر غیرفعال است.")
        return redirect("core:dashboard")

    account = StorageAccount.ensure_for(request.user)
    folders = account.folders.filter(status=StorageFolder.STATUS_ACTIVE).order_by("-created_at")
    recent = account.upload_sessions.all()[:10]
    recovery = account.upload_sessions.filter(
        status__in=(UploadSession.STATUS_PAID, UploadSession.STATUS_UPLOADING)
    ).first()
    return render(request, "cloudstorage/home.html", {
        "sts": sts,
        "account": account,
        "quota_gb": account.quota_override_gb or sts.user_quota_gb,
        "purchased_gb": account.active_space_gb(),
        "space_price": _space_price(),
        "used_pct": min(100, int(account.used_bytes * 100 / account.quota_bytes)) if account.quota_bytes else 0,
        "folders": folders,
        "recent": recent,
        "recovery": recovery,
        "existing_folders": list(folders.values("uid", "name")),
        "free_mb": StorageAccount.FREE_CLOUD_MB,
        "purchases": list(account.active_purchases()),
        "purchase_rows": _purchase_rows(list(account.active_purchases())),
        "wallet_balance": _wallet_balance(request.user),
    })


# --------------------------------------------------------------------------- #
# خرید فضای ابری (مدیریت سهمیه توسط کاربر)
# --------------------------------------------------------------------------- #
@login_required(login_url="core:index")
@require_POST
def api_purchase_space(request):
    """خرید/گسترش فضای ابری: تعرفهٔ cloud_storage × GB × روز با کسر اتمی سکه."""
    from datetime import timedelta
    from decimal import Decimal, InvalidOperation
    from django.utils import timezone
    from wallet.services import WalletError

    try:
        data = _json_body(request)
        gb = Decimal(str(data.get("gb") or 0))
        days = int(data.get("days") or 0)
        purchase = S.purchase_cloud_space(request.user, gb, days, request=request)
        account = StorageAccount.ensure_for(request.user)
        return JsonResponse({
            "ok": True,
            "purchased_gb": account.active_space_gb(),
            "quota_bytes": round(account.quota_bytes),
            "purchase": {
                "storage_gb": str(purchase.storage_gb),
                "days": purchase.days,
                "coins": str(purchase.coins_charged),
                "active_until": purchase.active_until.strftime("%Y-%m-%d %H:%M"),
            },
        })
    except (S.StorageError, WalletError) as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    except (InvalidOperation, TypeError) as e:
        return JsonResponse({"ok": False, "error": "ورودی نامعتبر است."}, status=400)


# --------------------------------------------------------------------------- #
# API های آپلود (JSON): برآورد → پرداخت → آپلود → تسویه
# --------------------------------------------------------------------------- #
@login_required(login_url="core:index")
@require_POST
def api_quote(request):
    """ساخت سشن + پیش‌فاکتور از مانیفست ارسالی کلاینت (فقط پیشنهاد است)."""
    try:
        data = _json_body(request)
        source = data.get("source")
        if source not in (UploadSession.SOURCE_FOLDER, UploadSession.SOURCE_GALLERY):
            raise S.StorageError("روش آپلود نامعتبر است (فقط پوشه یا گالری).")
        target = None
        force_new = False
        uid = (data.get("target_uid") or "").strip()
        if uid:
            if uid == "new":
                force_new = True
                target = None
            else:
                target = _owned_folder(request.user, uid)  # اتصال به پوشهٔ موجود
        direction = S.resolve_sync_direction(data)
        session = S.create_upload_session(
            request.user, source,
            folder_name=str(data.get("folder_name") or ""),
            files=data.get("files") or [],
            folders=data.get("folders") or [],
            target_folder=target,
            force_new=force_new,
            direction=direction,
        )
        attached = False
        attached_name = session.folder_name
        attached_path = session.folder_name + "/"
        if session.target_folder_id:
            attached = True
            attached_name = session.target_folder.name
            attached_path = session.target_folder.path_display or (session.target_folder.name + "/")
        return JsonResponse({
            "ok": True, "token": session.token,
            "status": session.status,
            "folder_name": session.folder_name,
            "stats": session.stats,
            "manifest": session.manifest,
            "wallet_balance": str(request.user.wallet.balance if hasattr(request.user, "wallet") else "0"),
            "attached": attached,
            "attached_name": attached_name,
            "attached_path": attached_path,
        })
    except Exception as exc:  # noqa: BLE001 — پاسخ خطای ساخت‌یافته
        if not isinstance(exc, (S.StorageError, PermissionDenied, S.StorageSecurityError)):
            import traceback; traceback.print_exc()
        return _err(request, exc)


@login_required(login_url="core:index")
@require_POST
def api_pay(request, token):
    """پرداخت سشن از کیف پول — idempotent (دوبار = یک‌بار کسر)."""
    try:
        result = S.pay_session(request.user, token)
        balance = getattr(request.user, "wallet", None)
        result["ok"] = True
        result["balance"] = str(balance.balance) if balance else "0"
        return JsonResponse(result)
    except Exception as exc:  # noqa: BLE001
        return _err(request, exc, status=400 if isinstance(exc, S.StorageError) else 403)


@login_required(login_url="core:index")
@require_POST
def api_upload(request, token):
    """دریافت یک فایل از مانیفست پرداخت‌شده (فقط مسیرهای new/changed)."""
    try:
        upload = request.FILES.get("file")
        if upload is None:
            raise S.StorageError("فایلی ارسال نشده است.")
        rel = request.POST.get("relpath") or upload.name
        sha = request.POST.get("sha256") or ""
        return JsonResponse(S.upload_session_file(
            request.user, token, upload, rel, client_sha256=sha))
    except Exception as exc:  # noqa: BLE001
        return _err(request, exc)


@login_required(login_url="core:index")
@require_POST
def api_finalize(request, token):
    """پایان آپلود: نسخه‌بندی + تسویهٔ واقعی (بازپرداخت مازاد)."""
    try:
        result = S.finalize_session(request.user, token)
        result["ok"] = True
        return JsonResponse(result)
    except Exception as exc:  # noqa: BLE001
        return _err(request, exc)


# --------------------------------------------------------------------------- #
# سشن (بازیابی پس از قطع ارتباط)
# --------------------------------------------------------------------------- #
@login_required(login_url="core:index")
def session_detail(request, token):
    """نمایش پیش‌فاکتور/وضعیت سشن؛ کاربر می‌تواند پرداخت یا آپلود را ادامه دهد."""
    session = S.get_user_session(request.user, token)
    return render(request, "cloudstorage/session.html", {
        "session": session,
        "stats": session.stats,
        "manifest_upload": [m for m in session.manifest if m.get("state") in ("new", "changed")],
        "sts": StorageSettings.get(),
    })


@login_required(login_url="core:index")
@require_POST
def session_cancel(request, token):
    """لغو سشن (بازپرداخت کامل اگر هیچ فایلی آپلود نشده باشد)."""
    try:
        S.cancel_session(request.user, token)
        messages.success(request, "عملیات لغو شد؛ در صورت پرداخت، مبلغ بازگردانده شد.")
    except S.StorageError as exc:
        messages.error(request, str(exc))
    return redirect("cloudstorage:home")


# --------------------------------------------------------------------------- #
# مرور درختی پوشه‌ها
# --------------------------------------------------------------------------- #
@login_required(login_url="core:index")
@require_GET
def browse(request):
    """فهرست پوشه‌های ابری کاربر با جستجو و مرتب‌سازی."""
    account = StorageAccount.ensure_for(request.user)
    sts = StorageSettings.get()
    q = (request.GET.get("q") or "").strip()
    sort = request.GET.get("sort") or "new"
    qs = account.folders.filter(status=StorageFolder.STATUS_ACTIVE)
    if q:
        qs = qs.filter(name__icontains=q)
    order = {"name": "name", "size": "-size_bytes", "files": "-files_count"}.get(sort, "-created_at")
    return render(request, "cloudstorage/browse.html", {
        "folders": qs.order_by(order),
        "account": account,
        "sts": sts,
        "q": q, "sort": sort,
        "quota_gb": account.quota_override_gb or sts.user_quota_gb,
        "purchased_gb": account.active_space_gb(),
        "space_price": _space_price(),
        "sync_jobs": account.sync_jobs.select_related("folder")[:10],
        "archive_jobs": account.archive_jobs.select_related("folder")[:10],
    })


@login_required(login_url="core:index")
@require_GET
def folder_detail(request, uid):
    """مرور محتوای یک پوشه: زیرپوشه‌ها (درختی) + فایل‌های همین مسیر + جستجو/مرتب‌سازی."""
    folder = _owned_folder(request.user, uid)
    sts = StorageSettings.get()
    cur = (request.GET.get("path") or "").strip()
    try:
        cur = S.normalize_relpath(cur) if cur else ""
    except S.StorageSecurityError:
        cur = ""

    # مجموع زیرپوشه‌های استخراج‌شده از فایل‌ها + ساختار ذخیره‌شده (شامل خالی‌ها)
    active_qs = StorageObject.objects.filter(folder=folder, status=StorageObject.STATUS_ACTIVE)
    derived_dirs, objects = set(), []
    prefix = (cur + "/") if cur else ""
    for obj in active_qs.only("rel_path", "name", "size_bytes", "mime", "uploaded_at", "version", "id"):
        parent = obj.rel_path.rsplit("/", 1)[0] if "/" in obj.rel_path else ""
        parts = obj.rel_path.split("/")[:-1]
        for i in range(len(parts)):  # همهٔ اجداد
            derived_dirs.add("/".join(parts[: i + 1]))
        if parent == cur:
            objects.append(obj)
    all_dirs = derived_dirs | set(folder.subtree_dirs or [])
    child_paths = sorted(
        d for d in all_dirs
        if (d.rsplit("/", 1)[0] if "/" in d else "") == cur and d != cur)
    # زیرپوشه‌های مستقیم مسیر فعلی

    q = (request.GET.get("q") or "").strip()
    if q:
        objects = [o for o in active_qs if q.lower() in o.rel_path.lower()
                   and (o.rel_path.rsplit("/", 1)[0] if "/" in o.rel_path else "") == cur]
        child_paths = [c for c in all_dirs if q.lower() in c.lower()]
    sort = request.GET.get("sort") or "name"
    if sort == "size":
        objects.sort(key=lambda o: -(o.size_bytes or 0))
    elif sort == "date":
        objects.sort(key=lambda o: o.uploaded_at, reverse=True)
    else:
        objects.sort(key=lambda o: o.name.lower())

    children = [
        {"path": c,
         "name": c.rsplit("/", 1)[-1],
         "size": sum(o.size_bytes or 0 for o in active_qs if o.rel_path.startswith(c + "/"))}
        for c in sorted(child_paths)
    ]
    crumbs, acc = [], ""
    for part in cur.split("/") if cur else []:
        acc = f"{acc}/{part}" if acc else part
        crumbs.append({"path": acc, "label": part})

    tree = [f for f in folder.account.folders.filter(status=StorageFolder.STATUS_ACTIVE)]
    return render(request, "cloudstorage/folder.html", {
        "folder": folder, "objects": objects, "children": children,
        "breadcrumbs": crumbs,
        "cur": cur, "q": q, "sort": sort, "sts": sts, "tree": tree,
        "total_size": sum(o.size_bytes or 0 for o in objects),
    })


@login_required(login_url="core:index")
@require_GET
def object_download(request, uid, object_id):
    """دانلود مستقیم یک فایل — فقط مالک (بررسی سمت سرور)."""
    folder = _owned_folder(request.user, uid)
    obj = get_object_or_404(
        StorageObject, pk=object_id, folder=folder, status=StorageObject.STATUS_ACTIVE)
    if not obj.file:
        raise PermissionDenied()
    try:
        if not obj.file.storage.exists(obj.file.name):
            raise S.StorageError("فایل موردنظر روی ذخیره‌ساز وجود ندارد.")
    except S.StorageError as exc:
        messages.error(request, str(exc))
        return redirect("cloudstorage:folder_detail", uid=uid)
    S.audit(request.user, "object_download", "StorageObject", obj.pk, {"rel": obj.rel_path[:100]})
    return FileResponse(obj.file.open("rb"), as_attachment=True, filename=obj.name)


# --------------------------------------------------------------------------- #
# آرشیو ZIP زمان‌دار (دانلود بخشی یا کل پوشه)
# --------------------------------------------------------------------------- #
@login_required(login_url="core:index")
@require_POST
def archive_create(request, uid):
    """ساخت آرشیو از کل پوشه یا مسیرهای انتخاب‌شده (مالکیت بررسی می‌شود)."""
    try:
        folder = _owned_folder(request.user, uid)
        data = _json_body(request)
        paths = data.get("paths") or []
        if not paths:  # بدون انتخاب = کل پوشه
            paths = [folder.uid]  # نشانهٔ «کل پوشه» در سرویس رفتارش را عوض می‌کند
            if paths == [folder.uid]:
                paths = []  # خالی = همهٔ فایل‌های فعال پوشه
        job = S.create_archive_job(
            request.user, folder, selected_paths=paths,
            client_name=str(data.get("name") or folder.name))
        job.refresh_from_db()
        return JsonResponse({
            "ok": True, "token": job.download_token, "status": job.status,
            "files": job.files_count, "size": job.size_bytes,
            "cost": str(job.cost_coins), "expires_at": job.expires_at.isoformat(),
            "download_url": f"/cloud-storage/archive/{job.download_token}/download/",
        })
    except Exception as exc:  # noqa: BLE001
        return _err(request, exc)


@login_required(login_url="core:index")
@require_GET
def archive_download(request, token):
    """دانلود آرشیو با لینک زمان‌دار (مالکیت + انقضا)."""
    try:
        job, path = S.get_downloadable_archive(request.user, token)
    except PermissionDenied:
        raise
    except S.StorageError as exc:
        messages.error(request, str(exc))
        return redirect("cloudstorage:browse")
    response = FileResponse(open(path, "rb"), as_attachment=True, filename=job.client_name or "archive.zip")
    return response


# --------------------------------------------------------------------------- #
# همگام‌سازی (Sync)
# --------------------------------------------------------------------------- #
@login_required(login_url="core:index")
@require_POST
def sync_download_plan(request, uid):
    """برنامهٔ دانلود (ابر ← دستگاه): فهرست فایل‌های ابری سمت کلاینت + شمارش‌ها."""
    try:
        folder = _owned_folder(request.user, uid)
        data = _json_body(request)
        items, dirs, stats = S.plan_download(
            request.user, folder, data.get("files") or [])
        S.audit(request.user, "sync_download_plan", "StorageFolder", folder.pk,
                {"files": stats["files_download"], "bytes": stats["bytes_download"]}, request=request)
        return JsonResponse({
            "ok": True, "folder": folder.name, "folder_uid": folder.uid,
            "items": items, "folders": dirs, "stats": stats,
            "wallet_balance": str(request.user.wallet.balance if hasattr(request.user, "wallet") else "0"),
        })
    except Exception as exc:  # noqa: BLE001
        if not isinstance(exc, (S.StorageError, PermissionDenied, S.StorageSecurityError)):
            import traceback; traceback.print_exc()
        return _err(request, exc)


@login_required(login_url="core:index")
@require_POST
def sync_quote(request, uid):
    """مقایسهٔ مانیفست محلی با وضعیت ابری و ساخت سشن Sync (فقط new/changed هزینه دارد)."""
    try:
        folder = _owned_folder(request.user, uid)
        sts = S.settings_active()
        if not sts.sync_enabled:
            raise S.StorageError("همگام‌سازی در حال حاضر غیرفعال است.")
        data = _json_body(request)
        files = data.get("files") or []
        q, missing_local = S.compare_for_sync(request.user, folder, files)
        # فایل‌های بدون تغییر از مانیفست حذف می‌شوند تا هزینه/آپلود نداشته باشند
        uploadable = [i for i in q["items"] if i["state"] in ("new", "changed")]
        session = S.create_upload_session(
            request.user, UploadSession.SOURCE_SYNC,
            folder_name=folder.name, files=uploadable,
            folders=q["folders"], target_folder=folder)
        job = SyncJob.objects.create(
            account=folder.account, folder=folder,
            source=SyncJob.SOURCE_MANUAL, status=SyncJob.STATUS_DONE,
            session=session,
            diff={"new": q["new_count"], "changed": q["changed_count"],
                  "unchanged": q["unchanged_count"]},
            note="", )
        return JsonResponse({
            "ok": True, "token": session.token, "stats": session.stats,
            "diff": job.diff,
            "cloud_only": missing_local,  # در ابر هست و محلی نیست (حذف نمی‌شود مگر سیاست دوطرفه)
        })
    except Exception as exc:  # noqa: BLE001
        return _err(request, exc)


@login_required(login_url="core:index")
@require_POST
def sync_download_charge(request, uid):
    """کسر هزینهٔ دانلود (ابر ← دستگاه) بر پایهٔ تعرفهٔ ادمین + ارسال برنامهٔ دانلود تازه."""
    try:
        folder = _owned_folder(request.user, uid)
        data = _json_body(request)
        result = S.charge_download(request.user, folder, data.get("files") or [])
        result.update({"ok": True, "folder": folder.name, "folder_uid": folder.uid})
        return JsonResponse(result)
    except Exception as exc:  # noqa: BLE001
        if not isinstance(exc, (S.StorageError, PermissionDenied, S.StorageSecurityError)):
            import traceback; traceback.print_exc()
        return _err(request, exc)


@login_required(login_url="core:index")
@require_POST
def folder_delete(request, uid):
    """حذف پوشهٔ ابری توسط مالک — حجم آن برای فعالیت‌های بعدی آزاد می‌شود."""
    try:
        result = S.delete_cloud_folder(request.user, uid, request=request)
        freed_mb = (result.get("bytes_freed") or 0) / (1024 * 1024)
        if freed_mb >= 0.1:
            messages.success(request, 
                f"پوشهٔ ابری «{result['name']}» حذف شد و {freed_mb:.1f} مگابایت از فضای شما آزاد گردید.")
        else:
            messages.success(request, f"پوشهٔ ابری «{result['name']}» حذف شد؛ فضای آن آزاد است.")
    except PermissionDenied:
        raise
    except S.StorageError as exc:
        messages.error(request, str(exc))
    return redirect("cloudstorage:browse")


@login_required(login_url="core:index")
@require_POST
def sync_toggle(request, uid):
    """فعال/غیرفعال کردن Sync خودکار یک پوشه (توسط مالک)."""
    folder = _owned_folder(request.user, uid)
    folder.auto_sync_enabled = not bool(folder.auto_sync_enabled)
    folder.save(update_fields=["auto_sync_enabled", "updated_at"])
    S.audit(request.user, "sync_toggle", "StorageFolder", folder.pk,
            {"auto_sync_enabled": folder.auto_sync_enabled})
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "auto_sync_enabled": folder.auto_sync_enabled})
    messages.success(request, (
        "Sync خودکار پوشه فعال شد." if folder.auto_sync_enabled
        else "Sync خودکار پوشه متوقف شد."))
    return redirect("cloudstorage:folder_detail", uid=uid)