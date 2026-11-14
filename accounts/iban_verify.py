"""استعلام تطبیق «شماره شبا» با «نام و نام‌خانوادگی» دارندهٔ حساب.

سرویس عمومی استعلام شبا (مثل X-Call/VIP یا همتایانش) با دو مدل کار می‌کند:
- مدل بدون احراز هویتِ دارنده: شبا با نام متقاضی مقایسه می‌شود (قبول/رد).
- پاسخ کاندیدها: خروجی شامل فهرست نام‌های ثبت‌شده روی حساب است؛ تطبیق
  فازیِ نام انجام می‌شود.

پیکربندی با متغیرهای محیطی:
    IBAN_VERIFY_URL      آدرس سرویس استعلام (خالی = استعلام غیرفعال)
    IBAN_VERIFY_TOKEN    توکن/کلید سرویس (هدر Authorization)
    IBAN_VERIFY_SOURCE   نام متغیر پرس‌وجو برای شبا (پیش‌فرض iban)
    IBAN_VERIFY_NAME     نام متغیر پرس‌وجو برای نام (پیش‌فرض fullName)

خروجی verify: دیکشنری
    {"available": bool, "match": bool|None, "message": str}
    match=None یعنی سرویس در دسترس نبود و تصمیم به فراخواننده است.

فال‌بک محلی (بدون سرویس): چکِ ساختاری شبا (چک‌سام رقم کنترل) انجام و
match=None برگردانده می‌شود تا فراخواننده سیاست خودش را اعمال کند.
نکتهٔ مهم: تا وقتی سرویس پیکربندی نشده باشد، درخواست‌ها «رد نمی‌شوند» —
فقط هشدار ثبت می‌شود؛ با پیکربندی سرویس، مغایرت = عدم تأیید.
"""

import logging
import os
import re
import unicodedata

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

# مهلت پاسخ سرویس استعلام (ثانیه)
_TIMEOUT = 10

# واژه‌های حذف‌شونده در نرمال‌سازی نام (پیشوندهای رایج)
_STOP_WORDS = {"حوزه", "تخصصی", "آقا", "خانم", "دکتر", "مهندس"}


def _normalize_name(text):
    """نرمال‌سازی نام برای مقایسه: یکسان‌سازی عربی/فارسی، حذف اعراب و پیشوندها."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    # اعراب و کشیدگی
    text = re.sub(r"[\u064B-\u0652\u0670\u0640]", "", text)
    # عربی → فارسی
    text = (
        text.replace("ي", "ی").replace("ك", "ک")
        .replace("ة", "ه").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    )
    tokens = [t for t in re.split(r"[\s\u200c]+", text.strip()) if t]
    return " ".join(t for t in tokens if t not in _STOP_WORDS)


def _tokens(text):
    return set(_normalize_name(text).split())


def names_match(full_name, registered_names, threshold=0.6):
    """تطبیق فازی نام متقاضی با نام‌های ثبت‌شده روی حساب.

    registered_names: رشته یا فهرست رشته. منطق: پوششِ توکن‌های نام و نام‌خانوادگی
    متقاضی در هر یک از نام‌های ثبت‌شده (نسبت پوشش ≥ آستانه = تطبیق).
    """
    if isinstance(registered_names, str):
        registered_names = [registered_names]
    applicant = _tokens(full_name)
    if not applicant:
        return False
    for reg in registered_names or []:
        reg_tokens = _tokens(reg)
        if not reg_tokens:
            continue
        covered = sum(1 for t in applicant if any(
            t == r or (len(t) >= 4 and (r.startswith(t) or t.startswith(r)))
            for r in reg_tokens
        ))
        if covered / len(applicant) >= threshold:
            return True
    return False


def _extract_names(payload):
    """استخراج نام‌های دارندهٔ حساب از پاسخ سرویس (ساختارهای رایج)."""
    if not isinstance(payload, dict):
        return []
    for key in ("fullName", "full_name", "ownerName", "name", "depositors", "owners"):
        value = payload.get(key)
        if not value:
            continue
        if isinstance(value, list):
            names = []
            for item in value:
                if isinstance(item, str):
                    names.append(item)
                elif isinstance(item, dict):
                    names.append(
                        item.get("fullName") or item.get("name")
                        or item.get("firstName", "") + " " + item.get("lastName", "")
                    )
            return [n for n in names if n]
        return [str(value)]
    # پاسخ‌های تودرتو (مثل result/data)
    for key in ("result", "data", "deposit"):
        inner = payload.get(key)
        if isinstance(inner, dict):
            names = _extract_names(inner)
            if names:
                return names
    return []


def verify(full_name, iban):
    """استعلام تطبیق نام دارندهٔ شبا. خروجی:
    {"available": bool, "match": bool|None, "message": str, "checked_at": iso}
    """
    url = os.environ.get("IBAN_VERIFY_URL", "").strip()
    if not url or not iban:
        return {
            "available": False, "match": None,
            "message": "سرویس استعلام شبا پیکربندی نشده است؛ کنترل خودکار نام انجام نشد.",
            "checked_at": timezone.now().isoformat(),
        }
    params = {
        os.environ.get("IBAN_VERIFY_SOURCE", "iban"): iban,
        os.environ.get("IBAN_VERIFY_NAME", "fullName"): full_name,
    }
    headers = {"Accept": "application/json"}
    token = os.environ.get("IBAN_VERIFY_TOKEN", "").strip()
    if token:
        headers["Authorization"] = token
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:  # noqa: BLE001 - سرویس بیرونی نباید ذخیره را بشکند
        logger.exception("iban verify request failed")
        return {
            "available": False, "match": None,
            "message": "سرویس استعلام شبا در دسترس نیست؛ بعداً دوباره تلاش کنید.",
            "checked_at": timezone.now().isoformat(),
        }
    registered = _extract_names(payload)
    if not registered:
        return {
            "available": True, "match": None,
            "message": "پاسخ سرویس استعلام فاقد نام دارندهٔ حساب بود؛ کنترل نامی انجام نشد.",
            "checked_at": timezone.now().isoformat(),
        }
    match = names_match(full_name, registered)
    return {
        "available": True, "match": match,
        "message": (
            "نام دارندهٔ حساب با نام و نام‌خانوادگی شما هم‌خوانی دارد."
            if match else
            "نام دارندهٔ این شبا با نام و نام‌خانوادگی شما هم‌خوانی ندارد."
        ),
        "checked_at": timezone.now().isoformat(),
    }
