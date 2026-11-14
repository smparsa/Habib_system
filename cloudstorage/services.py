"""سرویس‌های هستهٔ فضای ابری: برآورد، پرداخت، آپلود، تسویه، آرشیو، Sync.

قواعد کلیدی:
- همهٔ مبلغ‌ها «سکه» و از دفتر کل wallet.CoinLedger می‌گذرند (کسر اتمی؛ ماندهٔ منفی نمی‌شود).
- برآورد/سقف‌ها همیشه سمت سرور محاسبه می‌شوند؛ دادهٔ کلاینت فقط پیشنهاد است.
- پرداخت با گذار وضعیتِ قفل‌شدهٔ سشن (select_for_update) idempotent است —
  هرگز دوبار کسر نمی‌شود؛ مازاد پرداخت در تسویه بازگردانده می‌شود.
- هش محتوا (SHA-256) سمت سرور محاسبه و معیار واقعی تشخیص است؛ هش کلاینت فقط متادیتاست.
- مالکیت همه‌جا در DB چک می‌شود؛ مسیر نسبی نرمال و بدون Path Traversal است.
"""
from __future__ import annotations

import hashlib
import secrets
import zipfile

from decimal import Decimal, ROUND_UP
from pathlib import Path

from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from wallet.models import CoinLedger
from wallet.services import WalletError, _apply
try:
    from tickets.services import create_ticket
except Exception:  # noqa: BLE001
    create_ticket = None


def resolve_sync_direction(request_data, folder=None, accounts_same=True):
    """بررسی جهت sync — فهم جهت آپلود/دانلود (فرمت FreeFileSync)."""
    direction = str((request_data or {}).get('direction') or 'upload').strip().lower()
    if direction not in ('upload', 'download'):
        raise StorageError("جهت همگام‌سازی نامعتبر است (فقط upload/download).")
    return direction

from .models import (
    ArchiveJob,
    StorageAccount,
    StorageAuditLog,
    StorageFolder,
    StorageInvoice,
    StorageObject,
    StorageSettings,
    StorageTransaction,
    SyncJob,
    UploadSession,
)


class StorageError(Exception):
    pass


class StorageSecurityError(StorageError):
    """خطای امنیتی (مسیر نامعتبر، تلاش دسترسی غیرمجاز و …)."""


def _num(value):
    try:
        return Decimal(str(value))
    except Exception:  # noqa: BLE001
        return Decimal("0")


def _coin(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_UP)


def _gb(amount_bytes):
    return Decimal(amount_bytes or 0) / Decimal(1024 ** 3)


def _json_safe(value):
    """تبدیل مقادیر غیرقابل JSON (مثل Decimal) به رشته برای ذخیرهٔ متا در ممیزی."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {_json_safe(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def audit(actor, action, object_type="", object_id="", meta=None, request=None):
    """ثبت رویداد ممیزی بدون اطلاعات حساس (بدون محتوای فایل/هش کامل)."""
    ip = None
    if request is not None:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = (xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")) or None
    actor_user = getattr(actor, "user", actor) if actor is not None else None
    StorageAuditLog.objects.create(
        actor=actor_user,
        action=str(action)[:80],
        object_type=str(object_type)[:60],
        object_id=str(object_id)[:60],
        meta=_json_safe(meta or {}),
        ip=ip,
    )


# --------------------------------------------------------------------------- #
# مسیر نسبی امن (ضد Path Traversal)
# --------------------------------------------------------------------------- #
def normalize_relpath(raw):
    """نرمال‌سازی مسیر نسبی داخل پوشه و خطای امنیتی در هر تلاش گریز."""
    if raw is None:
        return ""
    raw = str(raw).replace("\\", "/")
    parts = []
    for part in raw.split("/"):
        part = part.strip()
        if not part or part == ".":
            continue
        if part == "..":
            raise StorageSecurityError("مسیر فایل نامعتبر است (Path Traversal).")
        if any(ch in part for ch in '<>:"|?*'):
            raise StorageSecurityError("نام فایل/پوشه شامل کاراکتر ممنوع است.")
        parts.append(part)
    return "/".join(parts)


def _safe_name(name, max_len=120):
    """نام امن برای پوشه/فایل: حذف کاراکترهای کنترلی و محدودسازی طول."""
    name = (name or "").strip()
    bad = '<>:"|?*\x00'
    name = "".join(ch for ch in name if ch not in bad)
    name = name.rstrip(". ")[:max_len]
    return name or "بدون‌نام"


# --------------------------------------------------------------------------- #
# تنظیمات فعال
# --------------------------------------------------------------------------- #
def settings_active():
    """تنظیمات ماژول؛ اگر کل ماژول خاموش باشد خطای دسترسی."""
    sts = StorageSettings.get()
    if not sts.module_enabled:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("ماژول «فضای ذخیره‌سازی ابری» در حال حاضر غیرفعال است.")
    return sts


# --------------------------------------------------------------------------- #
# برآورد/پیش‌فاکتور
# --------------------------------------------------------------------------- #
def quote_manifest(items, folders=(), existing_folder=None, sts=None):
    """برآورد کامل یک مجموعهٔ فایل — سمت سرور.

    items: [{relpath, size, sha256?, mtime?}] (فایل‌ها)
    folders: [«مسیر نسبی پوشه» (شامل پوشه‌های خالی)]
    existing_folder: وقتی روی پوشهٔ موجود سینک/افزودن می‌شود تفاضل می‌گیرد.
    """
    sts = sts or settings_active()

    norm_items, seen_paths = [], set()
    for item in items or []:
        try:
            rel = normalize_relpath(item.get("relpath") if isinstance(item, dict) else item)
        except StorageSecurityError:
            raise
        if not rel or rel in seen_paths:
            continue  # مسیر خالی یا تکراری — فاقد فایل واقعی
        seen_paths.add(rel)
        try:
            size = int(item.get("size") or 0) if isinstance(item, dict) else 0
        except (TypeError, ValueError):
            size = 0
        item_sha = (item.get("sha256") if isinstance(item, dict) else "") or ""
        item_mtime = item.get("mtime") if isinstance(item, dict) else None
        norm_items.append({
            "relpath": rel, "size": max(size, 0),
            "sha256": str(item_sha)[:64],
            "mtime": item_mtime if isinstance(item_mtime, int) else None,
            "state": "new",
        })

    norm_folders = sorted({normalize_relpath(f) for f in folders or [] if str(f).strip()})

    existing = {}
    if existing_folder is not None:
        for obj in StorageObject.objects.filter(folder=existing_folder, status=StorageObject.STATUS_ACTIVE).only(
                "rel_path", "size_bytes", "sha256", "client_mtime_ms"):
            existing[obj.rel_path] = obj

    new_items, changed_items, unchanged_items = [], [], []
    for item in norm_items:
        prev = existing.get(item["relpath"])
        if prev is not None:
            # قاعدهٔ Sync دستگاه ← ابر (مبدأ = دستگاه):
            #   مسیر در ابر نیست            → new      (آپلود)
            #   حجم متفاوت                  → changed  (آپلود)
            #   حجم برابر + هش هر دو موجود  → هش برابر؟ unchanged : changed
            #   حجم برابر + زمان هر دو موجود → زمان برابر؟ unchanged : changed (Modify شده)
            #   حجم برابر و معیار دیگری نیست → unchanged
            if (prev.size_bytes or 0) != item["size"]:
                is_same = False
            elif prev.sha256 and item["sha256"]:
                is_same = prev.sha256 == item["sha256"]
            elif item["mtime"] is not None and prev.client_mtime_ms is not None:
                is_same = item["mtime"] == prev.client_mtime_ms
            else:
                is_same = True
            if is_same:
                item["state"] = "unchanged"
                unchanged_items.append(item)
            else:
                item["state"] = "changed"
                changed_items.append(item)
        if item["state"] == "new":
            new_items.append(item)

    # فایل‌های تکراری محتوایی داخل مجموعه (همان هش)
    seen_sha = {}
    duplicate_count = 0
    for item in norm_items:
        if item["sha256"]:
            if item["sha256"] in seen_sha:
                duplicate_count += 1
            else:
                seen_sha[item["sha256"]] = item["relpath"]

    bytes_new = sum(i["size"] for i in new_items)
    bytes_changed = sum(i["size"] for i in changed_items)
    bytes_unchanged = sum(i["size"] for i in unchanged_items)
    uploaded_bytes = bytes_new + bytes_changed  # فایل‌هایی که واقعاً منتقل می‌شوند

    storage_cost = _coin(_num(sts.storage_coin_per_gb) * _gb(uploaded_bytes))
    transfer_cost = _coin(_num(sts.transfer_coin_per_gb) * _gb(uploaded_bytes))

    invalid = []
    max_file = sts.max_file_size_mb * 1024 * 1024
    if len(norm_items) > sts.max_folder_files:
        invalid.append(f"تعداد فایل ({len(norm_items)}) بیش از سقف ({sts.max_folder_files}).")
    if len(norm_folders) > sts.max_subfolders:
        invalid.append(f"تعداد زیرپوشه ({len(norm_folders)}) بیش از سقف ({sts.max_subfolders}).")
    for i in norm_items:
        if i["size"] > max_file:
            invalid.append(f"حجم فایل «{i['relpath'][:60]}» بیش از سقف هر فایل ({sts.max_file_size_mb} MB).")
            break
    if bytes_new + bytes_changed + bytes_unchanged > sts.max_operation_size_mb * 1024 * 1024:
        invalid.append(f"حجم کل عملیات more از سقف عملیات ({sts.max_operation_size_mb} MB).")

    return {
        "files_count": len(norm_items),
        "folders_count": len(norm_folders),
        "new_count": len(new_items),
        "changed_count": len(changed_items),
        "unchanged_count": len(unchanged_items),
        "duplicate_count": duplicate_count,
        "bytes_new": bytes_new,
        "bytes_changed": bytes_changed,
        "bytes_unchanged": bytes_unchanged,
        "bytes_total": bytes_new + bytes_changed + bytes_unchanged,
        "storage_cost": str(storage_cost),
        "transfer_cost": str(transfer_cost),
        "total_cost": str(storage_cost + transfer_cost),
        "rates": {
            "storage": str(sts.storage_coin_per_gb),
            "transfer": str(sts.transfer_coin_per_gb),
            "archive": str(sts.archive_coin_per_gb),
        },
        "items": norm_items,
        "folders": norm_folders,
        "invalid": invalid,
    }


# --------------------------------------------------------------------------- #
# شمارندهٔ هزینهٔ روز/ماه (سقف)
# --------------------------------------------------------------------------- #
def check_cost_limits(account, extra_cost):
    """کنترل سقف هزینهٔ روز/ماه کاربر (۰ = بدون سقف) — قبل از پرداخت."""
    sts = StorageSettings.get()
    today = timezone.localdate()
    month = today.strftime("%Y-%m")
    extra = _num(extra_cost)
    total_day = extra + (_num(account.daily_spent) if account.daily_spent_at == today else Decimal("0"))
    total_month = extra + (_num(account.monthly_spent) if account.monthly_spent_month == month else Decimal("0"))
    if sts.daily_cost_limit > 0 and total_day > sts.daily_cost_limit:
        raise StorageError(f"سقف هزینهٔ روزانه شما ({sts.daily_cost_limit} سکه) تکمیل است.")
    if sts.monthly_cost_limit > 0 and total_month > sts.monthly_cost_limit:
        raise StorageError(f"سقف هزینهٔ ماهانه شما ({sts.monthly_cost_limit} سکه) تکمیل است.")


def bump_cost_counters(account, coins, save=True):
    """اضافه/کم کردن هزینه در شمارندهٔ روز/ماه (مثبت = هزینهٔ جدید)."""
    today = timezone.localdate()
    month = today.strftime("%Y-%m")
    if account.daily_spent_at != today:
        account.daily_spent_at = today
        account.daily_spent = Decimal("0")
    if account.monthly_spent_month != month:
        account.monthly_spent_month = month
        account.monthly_spent = Decimal("0")
    account.daily_spent += _num(coins)
    account.monthly_spent += _num(coins)
    if save:
        account.save(update_fields=[
            "daily_spent_at", "daily_spent", "monthly_spent_month", "monthly_spent", "updated_at"])


def maybe_rate_limit(user, key, limit, seconds=60):
    """محدودهٔ نرخ درخواست (cache محلی) — بدون سرویس خارجی."""
    try:
        cache_key = f"cs-rate:{user.pk}:{key}"
        count = int(cache.get(cache_key) or 0) + 1
        if count > limit:
            raise StorageError("تعداد درخواست‌ها بیش از حد مجاز است؛ کمی صبر کنید.")
        cache.set(cache_key, count, seconds)
    except StorageError:
        raise
    except Exception:  # noqa: BLE001 — cache غیر در دسترس نباید سرویس را ببندد
        pass


# --------------------------------------------------------------------------- #
# ساخت سشن + پیش‌فاکتور
# --------------------------------------------------------------------------- #
def create_upload_session(user, source, folder_name, files, folders, target_folder=None, force_new=False, direction=None):
    """ساخت سشن و پیش‌فاکتور (بدون پرداخت؛ پرداخت با ``pay_session``)."""
    sts = settings_active()
    # رابط اصلی فقط پوشه/مجموعه رسانه را می‌پذیرد (UI بدون دکمهٔ فایل منفرد)؛
    # تشخیص «فایل منفرد» تنها وقتی معنا دارد که نه فایل داری و نه زیرپوشه‌ای،
    # اما پوشهٔ واقعی می‌تواند دقیقاً یک فایل داشته باشد، پس این حالت مجاز است.
    if source == UploadSession.SOURCE_FOLDER and not sts.folder_upload_enabled:
        raise StorageError("امکان «انتخاب پوشه» فعال نیست.")
    if source == UploadSession.SOURCE_GALLERY and not sts.gallery_enabled:
        raise StorageError("امکان «انتخاب از گالری» فعال نیست.")
    if source == UploadSession.SOURCE_SYNC and not sts.sync_enabled:
        raise StorageError("همگام‌سازی فعال نیست.")

    maybe_rate_limit(user, "session", 30)

    if target_folder is not None and target_folder.account.user_id != user.pk:
        raise PermissionDenied()  # مالکیت پوشهٔ هدف

    account = StorageAccount.ensure_for(user)
    n_files = len([f for f in files or []])
    incoming_bytes = sum(_num(f.get("size") if isinstance(f, dict) else 0) for f in files or [])
    if account.used_bytes + incoming_bytes > account.quota_bytes:
        raise StorageError(
            f"فضای باقی‌مانده شما برای این حجم کافی نیست (سقف مؤثر: {account.quota_gb_display:.2f} GB). "
            "پیش‌فرض هر کاربر 25 مگابایت است؛ برای افزایش سقف، از بخش «مدیریت فضای ابری» "
            "در صفحهٔ فضای ابری خرید کنید و سپس دوباره تلاش کنید.",
        )

    folder_name = _safe_name(folder_name)
    if source == UploadSession.SOURCE_GALLERY and (not folder_name or folder_name == "بدون‌نام"):
        folder_name = "Gallery Import"
    if not folder_name:
        folder_name = "پوشهٔ جدید"

    # نام پوشه تکراری → اتصال خودکار به پوشهٔ هم‌نام
    # بر اساس درخواست: در صورت تکراری بودن نام پوشه، فقط sync انجام شود
    if target_folder is None and force_new is not True:
        dup = (StorageFolder.objects
               .filter(account=account, name=folder_name, status=StorageFolder.STATUS_ACTIVE)
               .order_by("-created_at").first())
        if dup is not None:
            target_folder = dup
            force_new = False
    # قانون Sync دوطرفه (مشابه FreeFileSync): برای جهت دانلود، پوشهٔ هدف باید
    # از قبل در فضای ابری موجود باشد؛ در غیر این صورت سینک انجام نمی‌شود.
    direction = (direction or "upload").strip().lower()
    if direction == "download" and target_folder is None and source == UploadSession.SOURCE_SYNC:
        raise StorageError("برای همگام‌سازی دانلود، پوشهٔ ابری مقصد باید موجود باشد؛ پوشهٔ هم‌نام پیدا نشد.")

    item_dicts = []
    for f in files or []:
        if isinstance(f, dict):
            item_dicts.append(f)
        else:
            item_dicts.append({"relpath": str(f)})
    q = quote_manifest(item_dicts, folders, existing_folder=target_folder, sts=sts)
    if q["invalid"]:
        raise StorageError("؛ ".join(q["invalid"]))
    if q["files_count"] == 0 and q["folders_count"] == 0 and q["bytes_total"] == 0 and not (q["items"] or q["folders"]):
        # آپلود واقعاً خالی: مجاز است (ساختار خالی ثبت می‌شود) اما فایل هم نباید و هم نمی‌تواند باشد
        pass

    extra_cost = _num(q["total_cost"])
    check_cost_limits(account, extra_cost)

    session = UploadSession.objects.create(
        account=account,
        token=secrets.token_urlsafe(32),
        source=source,
        folder_name=folder_name,
        target_folder=(target_folder if target_folder is not None and target_account_ok(target_folder, account) else None),
        manifest=q["items"],
        folders=q["folders"],
        stats={
            k: q[k] for k in
            ("files_count", "folders_count",
             "new_count", "changed_count", "unchanged_count", "duplicate_count",
             "bytes_new", "bytes_changed", "bytes_unchanged", "bytes_total",
             "storage_cost", "transfer_cost", "total_cost", "rates")
        },
        created_note=(f"direction={direction}" if direction else ""),
    )
    audit(user, "session_created", "UploadSession", session.pk,
          {"source": source, "cost": q["total_cost"], "files": q["files_count"],
           "auto_attached": bool(target_folder is not None)})
    return session


def target_account_ok(folder, account):
    return folder.account_id == account.pk


# --------------------------------------------------------------------------- #
# پوشهٔ هدف (اتصال به پوشهٔ موجود یا ساخت پوشهٔ مستقل)
# --------------------------------------------------------------------------- #
def ensure_target_folder(session):
    """پوشهٔ هدف سشن؛ برای «ربط» به پوشهٔ موجود یا ساخت پوشهٔ منطقی جدید."""
    if session.target_folder and session.target_folder.account_id == session.account_id:
        folder = session.target_folder
        if folder.status == StorageFolder.STATUS_DELETED:
            folder.status = StorageFolder.STATUS_ACTIVE
            folder.save(update_fields=["status"])
        # به‌روزرسانی ساختار زیرپوشه‌ها برای همگام‌سازی (شامل پوشه‌های خالی)
        if session.folders:
            existing = set(folder.subtree_dirs or [])
            merged = sorted(existing.union(set(session.folders)))
            if merged != (folder.subtree_dirs or []):
                folder.subtree_dirs = merged
                folder.save(update_fields=["subtree_dirs"])
        return folder
    folder = StorageFolder.objects.create(
        account=session.account,
        name=session.folder_name,
        parent=None,
        path_display=session.folder_name,
    )
    # ثبت ساختار زیرپوشه‌ها (شامل پوشه‌های خالی) روی پوشهٔ ابری
    if session.folders:
        folder.subtree_dirs = sorted(set(session.folders))
        folder.save(update_fields=["subtree_dirs"])
    session.target_folder = folder
    session.save(update_fields=["target_folder"])
    session.account.refresh_from_db()
    session.account.folders_count = session.account.folders.filter(status=StorageFolder.STATUS_ACTIVE).count()
    session.account.save(update_fields=["folders_count"])
    return folder


# --------------------------------------------------------------------------- #
# پرداخت (idempotent) و لغو
# --------------------------------------------------------------------------- #
def pay_session(user, token):
    """پرداخت سشن از کیف پول؛ idempotent: دو بار فراخوانی = یک‌بار کسر."""
    with transaction.atomic():
        session = (UploadSession.objects.select_related("account").select_for_update()
                   .filter(token=token, account__user=user).first())
        if session is None:
            raise StorageSecurityError("سشن نامعتبر است.")
        if session.status == UploadSession.STATUS_DRAFT:
            amount = _num(session.stats.get("total_cost") or 0)
            check_cost_limits(session.account, amount)
            try:
                _apply(user, -amount, CoinLedger.KIND_CHARGE, ref_code=session.token[:40],
                       note="فضای ابری — پیش‌پرداخت آپلود")
            except WalletError as exc:
                raise StorageError(str(exc))
            invoice = StorageInvoice.objects.create(
                number=f"CST-{session.pk:08d}",
                session=session, account=session.account,
                amount_coins=amount, status=StorageInvoice.STATUS_PAID,
                paid_at=timezone.now(), details=session.stats,
            )
            session.status = UploadSession.STATUS_PAID
            session.paid_at = timezone.now()
            session.save(update_fields=["status", "paid_at"])
            StorageTransaction.objects.create(
                account=session.account, session=session, invoice=invoice,
                kind=StorageTransaction.KIND_CHARGE, amount_coins=amount,
                ref_code=session.token[:40], note="پیش‌پرداخت آپلود فضای ابری",
            )
            bump_cost_counters(session.account, amount)
            audit(user, "session_paid", "UploadSession", session.pk, {"amount": str(amount)})
            return {"paid": True, "amount": str(amount), "invoice": invoice.number}
        # قبلاً پرداخت/آغاز شده — بدون کسر مجدد
        if session.status in (UploadSession.STATUS_PAID, UploadSession.STATUS_UPLOADING, UploadSession.STATUS_FINISHED):
            return {"paid": True, "amount": str(_num(session.stats.get("total_cost") or 0))}
        raise StorageError("این سشن در وضعیت قابل پرداخت نیست.")


def cancel_session(user, token):
    """لغو سشن. اگر پرداخت شده ولی هیچ فایلی آپلود نشده → بازپرداخت کامل."""
    with transaction.atomic():
        session = (UploadSession.objects.select_related("account").select_for_update()
                   .filter(token=token, account__user=user).first())
        if session is None:
            raise StorageSecurityError("سشن نامعتبر است.")
        if session.status in (UploadSession.STATUS_FINISHED, UploadSession.STATUS_REFUNDED,
                              UploadSession.STATUS_CANCELLED):
            raise StorageError("این عملیات قابل لغو نیست.")
        if session.status in (UploadSession.STATUS_PAID, UploadSession.STATUS_UPLOADING) and session.uploaded_count == 0:
            amount = _num(session.stats.get("total_cost") or 0)
            if amount > 0:
                _apply(user, amount, CoinLedger.KIND_REFUND, ref_code=session.token[:40],
                       note="لغو آپلود — بازپرداخت کامل")
                StorageTransaction.objects.create(
                    account=session.account, session=session,
                    kind=StorageTransaction.KIND_REFUND, amount_coins=amount,
                    ref_code=session.token[:40], note="بازپرداخت لغو آپلود",
                )
                inv = session.invoices.order_by("-id").first()
                if inv:
                    inv.status = StorageInvoice.STATUS_REFUNDED
                    inv.refunded_coins = amount
                    inv.save(update_fields=["status", "refunded_coins"])
                bump_cost_counters(session.account, -amount)
        # پاک‌سازی فایل‌های staged (اگر خطای آپلود ناقص بود)
        for obj in session.staged_objects.all():
            obj.file.delete(save=False)
            obj.delete()
        session.status = (UploadSession.STATUS_REFUNDED
                          if session.paid_at is not None and session.uploaded_count == 0
                          else UploadSession.STATUS_CANCELLED)
        session.save(update_fields=["status"])
        audit(user, "session_cancelled", "UploadSession", session.pk, {})
        return {"cancelled": True}


# --------------------------------------------------------------------------- #
# آپلود فایل‌ها (در چارچوب سشن پرداخت‌شده)
# --------------------------------------------------------------------------- #
def get_user_session(user, token):
    session = UploadSession.objects.select_related("account", "target_folder").filter(
        token=token, account__user=user).first()
    if session is None:
        raise StorageSecurityError("سشن نامعتبر است.")
    return session


def ensure_space(account, sts, extra_bytes):
    """رزرو سهمیه (چک بر پایهٔ مصرف فعلی) — بدون پیاده‌سازی رزرو مشترک بین‌سешنی."""
    if account.used_bytes + extra_bytes > account.quota_bytes:
        raise StorageError("با این تغییر، سهمیهٔ فضای شما پر می‌شود؛ فضای کمتری انتخاب کنید.")


def upload_session_file(user, token, upload, relative_path, client_sha256=""):
    """دریافت یک فایل در چارچوب سشن پرداخت‌شده؛ بروزرسانی وضعیت سشن."""
    sts = settings_active()
    with transaction.atomic():
        session = (UploadSession.objects.select_related("account").select_for_update()
                   .filter(token=token, account__user=user).first())
        if session is None:
            raise StorageSecurityError("سشن نامعتبر است.")
        if session.status not in (UploadSession.STATUS_PAID, UploadSession.STATUS_UPLOADING):
            raise StorageError("این سشن در وضعیت قابل آپلود نیست؛ پیش‌فاکتور را مجدداً بسازید.")
        rel = normalize_relpath(relative_path)
        manifest = {i["relpath"]: i for i in session.manifest if i.get("state") in ("new", "changed")}
        entry = manifest.get(rel)
        if entry is None:
            raise StorageSecurityError("این مسیر در مانیفست پرداخت‌شدهٔ سشن نیست.")
        max_file = sts.max_file_size_mb * 1024 * 1024
        try:
            size = int(upload.size or 0)
        except Exception:  # noqa: BLE001
            size = 0
        if size > max_file:
            raise StorageError(f"حجم فایل بیش از سقف هر فایل ({sts.max_file_size_mb} MB) است.")
        if entry.get("size") and size and abs(size - int(entry["size"])) > 4096:
            raise StorageError("حجم واقعی فایل با پیش‌فاکتور همخوان نیست؛ مجموعه را مجدداً انتخاب کنید.")

        folder = ensure_target_folder(session)

        data = upload.read()
        sha = hashlib.sha256(data).hexdigest()
        if client_sha256 and client_sha256 != sha:
            audit(user, "sha_mismatch", "UploadSession", session.pk, {"rel": rel[:100]})

        # retry/تکرار: اگر همین مسیر قبلاً در همین سشن آپلود شده با هش برابر — بدون ذخیرهٔ مجدد
        staged = session.staged_objects.filter(rel_path=rel).order_by("-id").first()
        if staged is not None and staged.sha256 == sha:
            # duplicate upload attempt — بدون هزینهٔ ذخیره‌سازی جدید
            return {"ok": True, "dedup": True, "relpath": rel}

        # محتوای یکسان در همین مسیر روی ابر؟ (تغییر بی‌معنی با محتوای برابر) — ذخیره و در تسویه برچسب خواهد خورد
        if staged is not None:
            staged.file.delete(save=False)
            staged.delete()

        objs = StorageObject.objects.create(
            folder=folder,
            session=session,
            rel_path=rel,
            name=rel.split("/")[-1],
            size_bytes=len(data),
            sha256=sha,
            mime=upload.content_type or "",
            status=StorageObject.STATUS_ACTIVE,
            client_mtime_ms=entry.get("mtime"),
        )
        objs.file.save(objs.rel_path, ContentFile(data), save=True)

        # وضعیت سشن
        session.uploaded_count = session.staged_objects.values("rel_path").distinct().count()
        if session.status == UploadSession.STATUS_PAID:
            session.status = UploadSession.STATUS_UPLOADING
        session.save(update_fields=["uploaded_count", "status"])
        return {"ok": True, "relpath": rel, "size": len(data)}


def finalize_session(user, token):
    """پایان آپلود: نسخه‌بندی + تسویهٔ واقعی (بازپرداخت مازاد) + شمارنده‌ها."""
    with transaction.atomic():
        session = (UploadSession.objects.select_related("account").select_for_update()
                   .filter(token=token, account__user=user).first())
        if session is None:
            raise StorageSecurityError("سشن نامعتبر است.")
        if session.status in (UploadSession.STATUS_FINISHED, UploadSession.STATUS_REFUNDED):
            folder_uid = session.target_folder.uid if session.target_folder_id and session.target_folder else ""
            return {"finished": True, "folder_uid": folder_uid}

        folder = ensure_target_folder(session)
        account = StorageAccount.objects.select_for_update().get(pk=session.account_id)
        sts = StorageSettings.get()  # noqa: F841 — سقف‌ها پیش‌تر در پیش‌فاکتور اعمال شده‌اند

        powered = list(session.staged_objects.select_related("folder"))
        version_keep = folder.version_policy  # 0 → جایگزینی کامل؛ N → نگهداری N نسخهٔ قدیمی
        bytes_added = 0
        for obj in powered:
            prev = StorageObject.objects.select_for_update().filter(
                folder=folder, rel_path=obj.rel_path, status=StorageObject.STATUS_ACTIVE
            ).exclude(pk=obj.pk).order_by("-version").first()
            if prev is not None:
                if prev.sha256 and obj.sha256 and prev.sha256 == obj.sha256:
                    # محتوای یکسان — بدون هزینهٔ ذخیره‌سازی جدید؛ نسخهٔ قدیمی باقی می‌ماند
                    # زمان اصلاح دستگاه ثبت می‌شود تا همگام‌سازی بعدی دوباره «changed» نشان ندهد
                    if obj.client_mtime_ms is not None and prev.client_mtime_ms != obj.client_mtime_ms:
                        prev.client_mtime_ms = obj.client_mtime_ms
                        prev.save(update_fields=["client_mtime_ms"])
                    obj.file.delete(save=False)
                    obj.delete()
                    continue
                # نسخهٔ جدید
                obj.version = prev.version + 1
                if version_keep == 0:
                    prev.file.delete(save=False)
                    prev.delete()
                else:
                    prev.status = StorageObject.STATUS_REPLACED
                    prev.save(update_fields=["status"])
                # نگهداری بیشتر از سیاست؟ قدیمی‌ترین نسخه‌ها پاک می‌شوند
                keep_old = StorageObject.objects.filter(
                    folder=folder, rel_path=obj.rel_path, status=StorageObject.STATUS_REPLACED
                ).order_by("-version")[version_keep:]
                for old in keep_old:
                    old.file.delete(save=False)
                    old.delete()
            obj.folder = folder
            obj.session = None
            obj.status = StorageObject.STATUS_ACTIVE
            obj.save()
            bytes_added += obj.size_bytes or 0

        # بروزرسانی شمارنده‌ها
        active = StorageObject.objects.filter(folder=folder, status=StorageObject.STATUS_ACTIVE)
        folder.files_count = active.count()
        folder.size_bytes = sum(o.size_bytes or 0 for o in active)
        folder.save(update_fields=["files_count", "size_bytes", "updated_at"])
        account.refresh_from_db()
        acct_active = StorageObject.objects.filter(
            folder__account=account, status=StorageObject.STATUS_ACTIVE)
        account.files_count = acct_active.count()
        account.used_bytes = sum(o.size_bytes or 0 for o in acct_active)
        account.folders_count = account.folders.filter(status=StorageFolder.STATUS_ACTIVE).count()
        account.save(update_fields=["files_count", "used_bytes", "folders_count", "updated_at"])

        # تسویه واقعی: پیش‌پرداخت بر پایهٔ این برآورد بود؛ فقط «بایت واقعاً منتقل و ذخیره‌شده» هزینه دارد
        rates = session.stats.get("rates") or {}
        actual_storage = _coin(_num(rates.get("storage", "0")) * _gb(bytes_added))
        actual_transfer = _coin(_num(rates.get("transfer", "0")) * _gb(bytes_added))
        actual_total = actual_storage + actual_transfer
        paid_coins = _num(session.stats.get("total_cost") or 0)
        refunded = max(paid_coins - actual_total, Decimal("0"))
        if refunded > 0:
            invoice = session.invoices.order_by("-id").first()
            _apply(account.user, refunded, CoinLedger.KIND_REFUND, ref_code=session.token[:40],
                   note="تسویهٔ فضای ابری — بازپرداخت مازاد پیش‌پرداخت")
            StorageTransaction.objects.create(
                account=account, session=session, invoice=invoice,
                kind=StorageTransaction.KIND_REFUND, amount_coins=refunded,
                ref_code=session.token[:40], note="بازپرداخت مازاد پیش‌پرداخت",
            )
            if invoice:
                invoice.status = StorageInvoice.STATUS_SETTLED
                invoice.actual_coins = actual_total
                invoice.refunded_coins = refunded
                invoice.settled_at = timezone.now()
                invoice.save(update_fields=["status", "actual_coins", "refunded_coins", "settled_at"])
            bump_cost_counters(account, -refunded)

        session.status = UploadSession.STATUS_FINISHED
        session.finished_at = timezone.now()
        session.save(update_fields=["status", "finished_at"])
        audit(account.user, "session_finished", "UploadSession", session.pk, {
            "files": session.uploaded_count, "folder": folder.uid,
            "refunded": str(refunded), "bytes_added": bytes_added})
        # ثبت SyncJob و ارسال تیکت برای خبرداد سینک
        try:
            sync_job = SyncJob.objects.filter(session=session).first()
            if sync_job is None:
                sync_job = SyncJob.objects.create(
                    account=account,
                    folder=folder,
                    source=SyncJob.SOURCE_MANUAL,
                    status=SyncJob.STATUS_DONE,
                    session=session,
                    diff={
                        "new": session.stats.get("new_count", 0),
                        "changed": session.stats.get("changed_count", 0),
                        "unchanged": session.stats.get("unchanged_count", 0),
                    },
                    note=f"سینک برای {session.folder_name} تکمیل شد",
                )
            else:
                finish_sync_job(sync_job)
            if create_ticket is not None:
                try:
                    new_cnt = session.stats.get("new_count", 0)
                    ch_cnt = session.stats.get("changed_count", 0)
                    total_cost = session.stats.get("total_cost", "0")
                    subject = f"عملیات یکسان‌سازی (سینک) تکمیل شد: {folder.name}"
                    desc = (
                        f"پوشهٔ موجود در فضای ابری: {folder.name}\n"
                        f"تعداد فایل‌های جدید: {new_cnt}\n"
                        f"تعداد فایل‌های تغییرکرده: {ch_cnt}\n"
                        f"هزینه وارد شده: {total_cost} سکه\n"
                        f"توکن سشن: {session.token}\n"
                    )
                    create_ticket(author=account.user, subject=subject, description=desc, priority="normal")
                except Exception:
                    pass
        except Exception:
            pass
        return {"finished": True, "folder_uid": folder.uid, "refunded": str(refunded)}


def fail_session_and_refund(user, token, reason=""):
    """شکست عملیات: بازگشت مبلغ بخش انجام‌نشده (اوایل آپلود، بدون فایل منتقل‌شده)."""
    try:
        return cancel_session(user, token)
    except StorageError:
        raise


# --------------------------------------------------------------------------- #
# همگام‌سازی
# --------------------------------------------------------------------------- #
def compare_for_sync(user, folder, files):
    """تفاوت مانیفست محلی با وضعیت ابری «یک پوشهٔ مالک‌شده»."""
    if folder.account.user_id != user.pk:
        raise PermissionDenied()
    sts = settings_active()
    item_dicts = [f if isinstance(f, dict) else {"relpath": str(f)} for f in files or []]
    q = quote_manifest(item_dicts, [i.get("relpath", "").rsplit("/", 1)[0] for i in item_dicts if isinstance(i, dict) and "/" in i.get("relpath", "")], existing_folder=folder, sts=sts)
    cloud_paths = {o.rel_path for o in StorageObject.objects.filter(folder=folder, status=StorageObject.STATUS_ACTIVE)}
    local_paths = {i["relpath"] for i in q["items"]}
    missing_local = sorted(cloud_paths - local_paths)  # ابر دارد، محلی ندارد (به‌طور پیش‌فرض دست نمی‌زنیم)
    return q, missing_local


def plan_download(user, folder, files):
    """برنامهٔ دانلود (ابر ← دستگاه): کدام فایل‌های ابری باید منتقل شوند.

    files: مانیفست پوشهٔ محلی [{relpath, size, mtime?}] (فقط پیشنهاد است؛
    تصمیم نهایی سمت سرور بر پایهٔ وضعیت ابری گرفته می‌شود).

    قاعدهٔ Sync ابر ← دستگاه (مبدأ = ابر؛ مشابه FreeFileSync با مقایسهٔ حجم+زمان):
    - مسیر در دستگاه نیست → «new» (دانلود)
    - حجم متفاوت → «changed» (دانلود)
    - حجم برابر و نسخهٔ ابری جدیدتر است (زمان ابر > زمان دستگاه) → «changed» (Modify شده؛ دانلود)
    - حجم برابر و زمان برابر/ابر قدیمی‌تر → «unchanged» (بازنویسی لازم نیست)
    - حجم برابر و زمان نایاب → «unchanged»
    چرا «جدیدتر» و نه «متفاوت»؟ مرورگر نمی‌تواند زمان اصلاح فایل ذخیره‌شده را برابر نسخهٔ ابری
    بگذارد؛ پس بعد از هر دانلود، زمان دستگاه «الان» است و مقایسهٔ «متفاوت» همهٔ فایل‌ها را
    در هر همگام‌سازی دوباره دانلود (و هزینه) می‌کرد.

    خروجی: (items, folders, stats)
    - items: [{relpath, size, state, url, sha256}]  url لینک دانلودِ مالک-محدود است.
    - folders: زیرپوشه‌های منطقی ابر (برای ساخت پوشه‌های خالی سمت دستگاه).
    """
    if folder.account.user_id != user.pk:
        raise PermissionDenied()
    from django.urls import reverse  # بارگذاری تنبل برای جلوگیری از چرخهٔ import
    settings_active()  # ماژول باید فعال باشد
    sts = StorageSettings.get()
    if not sts.sync_enabled:
        raise StorageError("همگام‌سازی در حال حاضر غیرفعال است.")

    local = {}
    for f in files or []:
        d = f if isinstance(f, dict) else {"relpath": str(f)}
        try:
            rel = normalize_relpath(d.get("relpath"))
        except StorageSecurityError:
            raise
        if not rel:
            continue
        try:
            size = int(d.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        mtime = d.get("mtime")
        local[rel] = {"size": size, "mtime": mtime if isinstance(mtime, int) else None}

    objs = list(StorageObject.objects.filter(
        folder=folder, status=StorageObject.STATUS_ACTIVE).only(
        "rel_path", "name", "size_bytes", "client_mtime_ms"))

    items, bytes_total = [], 0
    files_new = files_changed = files_unchanged = 0
    all_dirs = set(folder.subtree_dirs or [])
    for obj in objs:
        parts = obj.rel_path.split("/")[:-1]
        for i in range(len(parts)):
            all_dirs.add("/".join(parts[: i + 1]))
        entry = local.get(obj.rel_path)
        if entry is None:
            state = "new"
        elif (obj.size_bytes or 0) != entry["size"]:
            state = "changed"
        elif entry["mtime"] is not None and obj.client_mtime_ms is not None:
            state = "changed" if obj.client_mtime_ms > entry["mtime"] else "unchanged"
        else:
            state = "unchanged"  # حجم برابر و معیار دیگری در دسترس نیست
        if state == "new":
            files_new += 1
        elif state == "changed":
            files_changed += 1
        else:
            files_unchanged += 1
        if state != "unchanged":
            bytes_total += obj.size_bytes or 0
            items.append({
                "relpath": obj.rel_path,
                "name": obj.name,
                "size": obj.size_bytes or 0,
                "state": state,
                "sha256": "",  # هش هرگز به کلاینت لو داده نمی‌شود — نیت امنیتی
                "url": reverse("cloudstorage:object_download", args=[folder.uid, obj.pk]),
            })

    stats = {
        "files_total_cloud": len(objs),
        "files_download": len(items),
        "files_new": files_new,
        "files_changed": files_changed,
        "files_unchanged": files_unchanged,
        "bytes_download": bytes_total,
        "folders_to_create": len(all_dirs),
        # هزینهٔ دانلود = «تعرفهٔ آرشیوسازی (سکه در GB) Download» پنل مدیریت × حجم قابل‌دانلود
        "rate_per_gb": str(_num(sts.archive_coin_per_gb)),
        "total_cost": str(_coin(_num(sts.archive_coin_per_gb) * _gb(bytes_total))),
    }
    return items, sorted(all_dirs), stats


def charge_download(user, folder, files=None):
    """کسر هزینهٔ دانلود (ابر ← دستگاه) از کیف پول و اعلام به ادمین و کاربر (تیکت).

    - مبلغ همیشه سمت سرور از تعرفهٔ ادمین (archive_coin_per_gb) × حجم واقعی محاسبه می‌شود.
    - کسر اتمی با رعایت سقف هزینهٔ روز/ماه؛ موجودی ناکافی = خطا و هیچ دانلودی شروع نمی‌شود.
    - خروجی: مبلغ کسرشده، موجودی جدید و برنامهٔ دانلود تازه (همان چیزی که هزینه‌اش کسر شد).
    """
    with transaction.atomic():
        account = StorageAccount.objects.select_for_update().get(pk=folder.account_id)
        if account.user_id != user.pk:
            raise PermissionDenied()
        # فقط تفاوت (جدید/تغییرحجم/Modify) هزینه دارد و دانلود می‌شود — مانیفست دستگاه لازم است
        items, dirs, stats = plan_download(user, folder, files or [])
        amount = _num(stats["total_cost"])
        if amount > 0 and items:
            check_cost_limits(account, amount)
            try:
                wallet = _apply(user, -amount, CoinLedger.KIND_CHARGE,
                                ref_code=("DL-" + folder.uid)[:40],
                                note=f"فضای ابری — هزینهٔ دانلود/یکسان‌سازی ابر ← دستگاه ({folder.name})")
            except WalletError as exc:
                raise StorageError(str(exc))
            StorageTransaction.objects.create(
                account=account, kind=StorageTransaction.KIND_CHARGE, amount_coins=amount,
                ref_code=("DL-" + folder.uid)[:40],
                note=f"هزینهٔ دانلود ابر ← دستگاه: {folder.name}",
            )
            bump_cost_counters(account, amount)
            audit(user, "download_charged", "StorageFolder", folder.pk, {
                "amount": str(amount), "files": stats["files_download"],
                "bytes": stats["bytes_download"], "rate": stats["rate_per_gb"]})
            balance = wallet.balance
        else:
            amount = Decimal("0")
            balance = None
    if balance is None:
        from wallet.models import Wallet
        w = Wallet.objects.filter(user=user).only("balance").first()
        balance = w.balance if w else Decimal("0")

    # اعلام کسر هزینه: تیکت ← کاربر (نویسنده) + کارکنان/ادمین (گیرندگان)
    if amount > 0 and create_ticket is not None:
        try:
            now = timezone.localtime()
            create_ticket(
                author=user,
                subject=f"کسر هزینهٔ دانلود (ابر ← دستگاه): {folder.name}",
                description=(
                    f"پوشهٔ ابری: {folder.name}\n"
                    f"تعداد فایل دانلودشونده: {stats['files_download']}\n"
                    f"حجم: {_gb(stats['bytes_download']).quantize(Decimal('0.0001'))} GB\n"
                    f"تعرفهٔ دانلود: {stats['rate_per_gb']} سکه در هر GB\n"
                    f"مبلغ کسرشده از کیف پول: {amount} سکه\n"
                    f"موجودی جدید: {balance} سکه\n"
                    f"زمان: {now:%Y-%m-%d %H:%M:%S}\n"
                ),
                priority="normal",
            )
        except Exception:  # noqa: BLE001 — خطای اعلان نباید دانلود را مختل کند
            pass
    return {
        "amount": str(amount), "balance": str(balance),
        "items": items, "folders": dirs, "stats": stats,
    }


def finish_sync_job(sync_job):
    """پس از finalize سشنِ سینک؛ ثبت نتیجهٔ Synchronise و وضعیت پوشه."""
    session = sync_job.session
    sync_job.status = SyncJob.STATUS_DONE
    sync_job.finished_at = timezone.now()
    if session is not None:
        sync_job.diff = {
            "new": session.stats.get("new_count", 0),
            "changed": session.stats.get("changed_count", 0),
            "unchanged": session.stats.get("unchanged_count", 0),
        }
    folder = session.target_folder if session else sync_job.folder
    if folder is not None:
        folder.last_sync_at = timezone.now()
        folder.last_sync_status = SyncJob.STATUS_DONE
        folder.save(update_fields=["last_sync_at", "last_sync_status", "updated_at"])
    sync_job.save(update_fields=["status", "finished_at", "diff"])
    return sync_job


# --------------------------------------------------------------------------- #
# آرشیو ZIP لینک‌دار زمان‌دار
# --------------------------------------------------------------------------- #
def create_archive_job(user, folder, selected_paths=None, client_name=""):
    """ساخت آرشیو ZIP با تأیید مالکیت، سقف ادمین، هزینهٔ آرشیوسازی و توکن زمان‌دار."""
    sts = settings_active()
    if not sts.archive_enabled:
        raise StorageError("دانلود آرشیو فعال نیست.")
    if folder.account.user_id != user.pk:
        raise PermissionDenied()

    qs = StorageObject.objects.filter(folder=folder, status=StorageObject.STATUS_ACTIVE)
    if selected_paths:
        norm = {normalize_relpath(p) for p in selected_paths if p}
        qfilter = Q()
        for p in norm:
            qfilter |= Q(rel_path=p) | Q(rel_path__startswith=p + "/")
        qs = qs.filter(qfilter)
    objs = list(qs)
    if not objs:
        raise StorageError("موردی برای آرشیو یافت نشد.")
    if len(objs) > sts.max_archive_files:
        raise StorageError(f"تعداد فایل‌های انتخابی بیش از سقف آرشیو ({sts.max_archive_files}).")
    total_size = sum(o.size_bytes or 0 for o in objs)
    if total_size > sts.max_archive_size_gb * 1024 ** 3:            raise StorageError(f"حجم آرشیو بیش از سقف ({sts.max_archive_size_gb} GB).")

    cost = _coin(_num(sts.archive_coin_per_gb) * _gb(total_size))
    if cost > 0:
        try:
            _apply(user, -cost, CoinLedger.KIND_CHARGE, ref_code="ZIP-ARCHIVE",
                   note="هزینهٔ آرشیوسازی (دانلود ZIP)")
        except WalletError as exc:
            raise StorageError(str(exc))

    with transaction.atomic():
        job = ArchiveJob.objects.create(
            account=folder.account, folder=folder,
            download_token=secrets.token_urlsafe(32),
            selected_paths=sorted(o.rel_path for o in objs),
            client_name=_safe_name(client_name or folder.name) + ".zip",
            status=ArchiveJob.STATUS_BUILDING,
            size_bytes=total_size,
            files_count=len(objs),
            cost_coins=cost,
            expires_at=timezone.now() + timezone.timedelta(hours=sts.archive_retention_hours),
        )
        bump_cost_counters(folder.account, cost)
    build_archive_zip(job)
    return job


def build_archive_zip(job):
    """ساخت فیزیکی ZIP از فایل‌های ابری (فراخوانی هم‌زمان با درخواست)."""
    from .storage import archive_path_for

    path = archive_path_for(job.download_token)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as zf:
            for obj in StorageObject.objects.filter(
                    folder=job.folder, status=StorageObject.STATUS_ACTIVE):
                if job.selected_paths and obj.rel_path not in job.selected_paths:
                    continue
                if obj.file and obj.file.storage.exists(obj.file.name):
                    with obj.file.open("rb") as fh:
                        zf.writestr(obj.rel_path, fh.read())
        job.status = ArchiveJob.STATUS_READY
        job.ready_at = timezone.now()
    except Exception as exc:  # noqa: BLE001
        job.status = ArchiveJob.STATUS_FAILED
        job.note = str(exc)[:280]
    job.save(update_fields=["status", "note", "ready_at", "size_bytes", "files_count"])
    audit(job.account.user, f"archive_{job.status}", "ArchiveJob", job.pk, {"files": job.files_count})
    return job


def get_downloadable_archive(user, token):
    """آرشیو آماده و غیرمنقضی برای کاربر مالک — در غیر این صورت پاک‌سازی/خطا."""
    from .storage import archive_path_for

    job = ArchiveJob.objects.filter(download_token=token, account__user=user.pk).first()
    if job is None:
        raise PermissionDenied()
    purge_expired_archives()
    job.refresh_from_db()
    if job.status == ArchiveJob.STATUS_EXPIRED or job.is_expired():
        raise StorageError("لینک دانلود منقضی شده است؛ آرشیو جدید بسازید.")
    if job.status != ArchiveJob.STATUS_READY:
        raise StorageError("آرشیو در دسترس نیست.")
    path = archive_path_for(job.download_token)
    if not path.exists():
        raise StorageError("فایل آرشیو یافت نشد؛ آرشیو جدید بسازید.")
    ArchiveJob.objects.filter(pk=job.pk).update(download_count=job.download_count + 1)
    return job, path


def purge_expired_archives():
    """حذف امن آرشیوهای منقضی (فایل فیزیکی + رکورد → منقضی)."""
    now = timezone.now()
    stale = ArchiveJob.objects.filter(expires_at__lt=now).exclude(status=ArchiveJob.STATUS_EXPIRED)
    from .storage import archive_path_for

    for job in stale:
        path = archive_path_for(job.download_token)
        try:
            if Path(path).exists():
                Path(path).unlink()
        except OSError:
            pass
        job.status = ArchiveJob.STATUS_EXPIRED
        job.save(update_fields=["status"])
    return stale.count()


# --------------------------------------------------------------------------- #
# حذف دوطرفه (فقط صریح؛ پیش‌فرض غیر فعال)
# --------------------------------------------------------------------------- #
def remove_locally_missing(user, folder, missing_paths):
    """حذف ابریِ مسیرهایی که محلی دیگر وجود ندارند — فقط با تأیید صریح کاربر و
    فعال بودن سیاست حذف دوطرفه در تنظیمات ادمین."""
    sts = StorageSettings.get()
    if not (sts.two_way_delete_enabled and not sts.keep_deleted_files):
        raise StorageError("سیاست حذف دوطرفه فعال نیست.")
    if folder.account.user_id != user.pk:
        raise PermissionDenied()
    removed = 0
    for rel in missing_paths:
        raw = str(rel).replace("\\", "/")
        if not raw or ".." in raw.split("/"):
            continue  # مسیر نامعتبر — رد می‌شود (ضد Path Traversal)
        obj = StorageObject.objects.filter(
            folder=folder, rel_path=raw, status=StorageObject.STATUS_ACTIVE).first()
        if obj is None:
            continue
        obj.file.delete(save=False)
        obj.delete()
        removed += 1
    active_qs = StorageObject.objects.filter(folder=folder, status=StorageObject.STATUS_ACTIVE)
    folder.files_count = active_qs.count()
    folder.size_bytes = sum(o.size_bytes or 0 for o in active_qs)
    folder.save(update_fields=["files_count", "size_bytes", "updated_at"])
    account = folder.account
    act = StorageObject.objects.filter(folder__account=account, status=StorageObject.STATUS_ACTIVE)
    account.used_bytes = sum(o.size_bytes or 0 for o in act)
    account.files_count = act.count()
    account.save(update_fields=["used_bytes", "files_count", "updated_at"])
    audit(user, "two_way_delete", "StorageFolder", folder.pk, {"removed": removed})
    return removed

# --------------------------------------------------------------------------- #
# خرید فضای ابری توسط کاربر (مدیریت سهمیه)
# --------------------------------------------------------------------------- #
def purchase_cloud_space(user, gb, days, request=None):
    """خرید/گسترش فضای ابری کاربر.

    تعرفه از «هزینه‌های سکهٔ ماژول‌ها» (کد: cloud_storage) خوانده می‌شود و
    مبلغ = تعرفه × حجم (GB) × تعداد روزها در یک تراکنش اتمی کسر و سابقه‌ای
    از خرید (active_until) ثبت می‌شود؛ سقف مؤثر کاربر با خرید فعال بالا می‌رود.
    """
    from decimal import InvalidOperation
    from datetime import timedelta
    from django.utils import timezone as dj_tz
    from wallet.models import FeatureCost
    from .models import CloudSpacePurchase, StorageSettings

    if not StorageSettings.get().module_enabled:
        raise StorageError("ماژول «فضای ذخیره‌سازی ابری» فعال نیست.")
    try:
        gb_dec = Decimal(str(gb))
    except (InvalidOperation, ArithmeticError, ValueError, TypeError):
        raise StorageError("حجم درخواستی نامعتبر است.")
    days = int(days or 0)
    if gb_dec < Decimal("0.25") or gb_dec > 2048:
        raise StorageError("فضای درخواستی باید بین ۰٫۲۵ تا ۲۰۴۸ گیگابایت باشد.")
    if days < 1 or days > 365:
        raise StorageError("مدت خرید باید بین ۱ تا ۳۶۵ روز باشد.")
    fc = FeatureCost.objects.filter(code="cloud_storage", is_active=True).first()
    if fc is None:
        raise StorageError("تعرفهٔ خرید فضای ابری فعال نیست؛ با پشتیبانی تماس بگیرید.")

    total_units = gb_dec * days
    from wallet.services import WalletError, charge_module_scaled
    try:
        charged = charge_module_scaled(
            user, "cloud_storage", total_units, request=request,
            note=f"خرید {gb_dec} GB فضای ابری برای {days} روز",
        )
    except WalletError as e:
        raise StorageError(str(e))

    now = dj_tz.now()
    purchase = CloudSpacePurchase.objects.create(
        user=user,
        storage_gb=gb_dec,
        days=days,
        coins_charged=(charged if charged is not None else Decimal("0")),
        active_from=now,
        active_until=now + timedelta(days=days),
    )
    return purchase


# --------------------------------------------------------------------------- #
# حذف پوشهٔ ابری توسط کاربر (آزادسازی حجم سقف)
# --------------------------------------------------------------------------- #
def delete_cloud_folder(user, folder_uid, request=None):
    """حذف نرم پوشهٔ ابری توسط مالک + آزادسازی کامل حجم آن.

    - همهٔ فایل‌های فعال/نسخه‌های قدیمی پوشه (به همراه فایل فیزیکی روی ذخیره‌ساز) حذف
      می‌شوند و شمارنده‌های حساب بازمحاسبه می‌شوند؛ فضای سقف کاربر آزاد می‌شود.
    - سشن‌های آپلود بازِ همین پوشه لغو می‌شوند (در صورت عدم آپلود، بازپرداخت کامل).
    - Sync خودکار پوشه متوقف می‌شود؛ خود ردیف پوشه حذف نمی‌شود تا
      تاریخچهٔ Sync/آرشیو سالم بماند.
    """
    with transaction.atomic():
        folder = (StorageFolder.objects.select_for_update()
                  .select_related("account")
                  .filter(uid=folder_uid, account__user=user).first())
        if folder is None or folder.account.user_id != user.pk:
            raise PermissionDenied()  # مالکیت پوشهٔ ابری
        if folder.status == StorageFolder.STATUS_DELETED:
            return {"deleted": True, "bytes_freed": 0, "name": folder.name}  # idempotent

        freed = 0
        objs = list(StorageObject.objects.filter(folder=folder))
        for obj in objs:
            freed += obj.size_bytes or 0
            if obj.file:
                try:
                    obj.file.delete(save=False)  # حذف فایل فیزیکی از ذخیره‌ساز
                except OSError:  # noqa: BLE001 — فایل فیزیکی از قبل موجود نیست
                    pass
            obj.delete()

        # لغو سشن‌های بازِ همین پوشه (پیش‌پرداخت‌شده‌ها بازپرداخت می‌شوند)
        open_sessions = UploadSession.objects.filter(
            target_folder=folder,
            status__in=(UploadSession.STATUS_DRAFT, UploadSession.STATUS_PAID, UploadSession.STATUS_UPLOADING),
        )
        for session in open_sessions:
            try:
                cancel_session(user, session.token)
            except StorageError:  # noqa: BLE001 — وضعیت قابل لغو نبود؛ همان را رها می‌کنیم
                pass

        folder.status = StorageFolder.STATUS_DELETED
        folder.files_count = 0
        folder.size_bytes = 0
        folder.auto_sync_enabled = False
        folder.save(update_fields=["status", "files_count", "size_bytes", "auto_sync_enabled", "updated_at"])

        account = StorageAccount.objects.select_for_update().get(pk=folder.account_id)
        acct_active = StorageObject.objects.filter(
            folder__account=account, status=StorageObject.STATUS_ACTIVE)
        account.files_count = acct_active.count()
        account.used_bytes = sum(o.size_bytes or 0 for o in acct_active)
        account.folders_count = account.folders.filter(status=StorageFolder.STATUS_ACTIVE).count()
        account.save(update_fields=["files_count", "used_bytes", "folders_count", "updated_at"])

        audit(user, "folder_deleted", "StorageFolder", folder.pk,
              {"name": folder.name, "bytes_freed": freed}, request=request)
        return {"deleted": True, "bytes_freed": freed, "name": folder.name}
