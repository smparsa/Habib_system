"""جایگزینی سراسری کد ملی پس از تغییر آن در پروفایل.

وقتی کاربر کد ملی خود را (در صورت امکان) در پروفایل تغییر می‌دهد، کد جدید باید
در سراسر برنامه و دیتابیس جایگزین قدیم شود:

- ایمیل خودکار (national_id@HabibHub.com) — همیشه هم‌گام با کد ملی.
- «کد ملی معرف» کاربرانی که با کد قدیمیِ این کاربر ثبت‌نام کرده‌اند — تا زنجیرهٔ
  معرفی نشکند.
- پوشهٔ مدارک کاربر (Docs/<کد ملی>) و مسیرهای رسانه (media) که با کد ملی
  ساخته شده‌اند (مثل jobs/<کد ملی>/status) — فایل‌ها به پوشهٔ جدید منتقل و
  مسیرهای ذخیره‌شده در دیتابیس به‌روزرسانی می‌شوند.
- دفتر کل کیف پول (CoinLedger): ارجاع به کاربر با FK است؛ فقط متنِ توضیحاتِ
  حاوی کد قدیم به‌روز می‌شود تا سازگاری گزارش‌های متنی حفظ شود.
- ردیف‌های سند حسابداری: ارجاع «شخص» با FK به رکورد کاربر است و خودبه‌خود با
  کد جدید نمایش داده می‌شود؛ نیازی به تغییر داده نیست.

عملیات دیتابیسی اتمی است؛ جابه‌جایی فایل‌ها پس از commit انجام می‌شود و شکستش
هرگز تغییر کد را بازنمی‌گرداند (فقط لاگ می‌شود).
"""

import logging
import os
import shutil

from django.conf import settings as dj_settings
from django.db import transaction

logger = logging.getLogger(__name__)


def propagate_national_id_change(profile, old_nid, new_nid, request=None):
    """کد ملی قدیم را در سراسر دیتابیس/فایل‌ها با کد جدید جایگزین می‌کند.

    profile باید ذخیره شده و national_id=new_nid داشته باشد.
    """
    from accounts.models import User

    old_nid = (old_nid or "").strip()
    new_nid = (new_nid or "").strip()
    if not old_nid or not new_nid or old_nid == new_nid:
        return False

    user = profile.user
    with transaction.atomic():
        # ۱) ایمیل خودکارِ پروفایل همیشه تابع کد ملی است (فیلد email روی Profile است)
        if (profile.email or "").strip().lower() == f"{old_nid}@habibhub.com":
            profile.email = f"{new_nid}@HabibHub.com"
            profile.save(update_fields=["email"])

        # ۲) «کد ملی معرف» کاربرانی که با کد قدیمی این کاربر ثبت‌نام کرده‌اند
        User.objects.filter(referrer_national_id=old_nid).update(
            referrer_national_id=new_nid
        )

        # ۳) متنِ توضیحاتِ دفتر کل که حاوی کد قدیم است (گزارش‌های متنی)
        from wallet.models import CoinLedger

        for ledger in CoinLedger.objects.filter(note__contains=old_nid)[:500]:
            ledger.note = ledger.note.replace(old_nid, new_nid)
            ledger.save(update_fields=["note"])

        # ۴) رویداد حسابرسی
        try:
            from tickets.services import audit

            audit(
                user, "profile.national_id_changed", "Profile", profile.pk,
                request=request, meta={"old": old_nid, "new": new_nid},
            )
        except Exception:  # noqa: BLE001 - حسابرسی نباید تغییر را بشکند
            logger.exception("national id change audit failed")

    # ۵) جابه‌جایی پوشه‌های فایل و اصلاح مسیرهای ذخیره‌شده (پس از commit)
    _move_docs_folder(old_nid, new_nid)
    _rewrite_media_paths(old_nid, new_nid)
    return True


def _move_docs_folder(old_nid, new_nid):
    """انتقال پوشهٔ مدارک کاربر: Docs/<old> → Docs/<new> (ادغام در صورت وجود)."""
    try:
        from accounts.models import user_docs_root

        old_dir = user_docs_root() / old_nid
        new_dir = user_docs_root() / new_nid
        if not old_dir.exists():
            return
        new_dir.parent.mkdir(parents=True, exist_ok=True)
        if new_dir.exists():
            # پوشهٔ جدید از قبل هست: محتوا را ادغام کن و قدیمی را خالی‌کن
            for item in old_dir.iterdir():
                target = new_dir / item.name
                if not target.exists():
                    shutil.move(str(item), str(target))
            old_dir.rmdir()
        else:
            shutil.move(str(old_dir), str(new_dir))
    except Exception:  # noqa: BLE001 - فایل‌ها نباید تغییر کد را بشکنند
        logger.exception("docs folder move failed for %s -> %s", old_nid, new_nid)


def _rewrite_media_paths(old_nid, new_nid):
    """اصلاح مسیرهای FileField که کد قدیم درشان است + جابه‌جایی فیزیکی پوشه‌ها."""
    # ۱) مسیرهای ذخیره‌شده در دیتابیس
    try:
        from accounts.models import JobStatus, Profile, UserDocument

        for p in Profile.objects.filter(avatar__contains=old_nid):
            p.avatar.name = p.avatar.name.replace(old_nid, new_nid)
            p.save(update_fields=["avatar"])
        for doc in UserDocument.objects.filter(file__contains=old_nid):
            doc.file.name = doc.file.name.replace(old_nid, new_nid)
            doc.save(update_fields=["file"])
        for st in JobStatus.objects.filter(image__contains=old_nid):
            st.image.name = st.image.name.replace(old_nid, new_nid)
            st.save(update_fields=["image"])
    except Exception:  # noqa: BLE001
        logger.exception("media path rewrite failed for %s -> %s", old_nid, new_nid)

    # ۲) جابه‌جایی فیزیکی: media/jobs/<old> → media/jobs/<new> و هر پوشهٔ مستقیم
    media_root = str(getattr(dj_settings, "MEDIA_ROOT", "") or "")
    if not media_root or not os.path.isdir(media_root):
        return
    pairs = [
        (os.path.join(media_root, "jobs", old_nid), os.path.join(media_root, "jobs", new_nid)),
        (os.path.join(media_root, old_nid), os.path.join(media_root, new_nid)),
    ]
    for old_dir, new_dir in pairs:
        try:
            if not os.path.isdir(old_dir):
                continue
            os.makedirs(os.path.dirname(new_dir), exist_ok=True)
            if os.path.isdir(new_dir):
                for item in os.listdir(old_dir):
                    src, dst = os.path.join(old_dir, item), os.path.join(new_dir, item)
                    if not os.path.exists(dst):
                        shutil.move(src, dst)
                os.rmdir(old_dir)
            else:
                shutil.move(old_dir, new_dir)
        except Exception:  # noqa: BLE001
            logger.exception("media folder move failed: %s -> %s", old_dir, new_dir)
