"""«ساخت اسلایدشو» (Create Slideshow): تبدیل هر تصویرِ ناسازگار به بنر استاندارد ۲۴۰۰×۶۰۰.

تصویر کاربر **بدون برش و بدون کج‌شدگی** داخل «ناحیهٔ امن» مرکزی (۱۲۰۰×۶۰۰) قرار می‌گیرد
(در دسکتاپ کامل، در تبلت و موبایل هم کامل دیده می‌شود) و بقیهٔ بوم با نسخهٔ محو و
تیره‌شدهٔ همان تصویر پر می‌شود؛ لبه‌های تصویر اصلی نرم در پس‌زمینه ذوب می‌شود.

نتیجه به‌صورت فایل موقتِ ``slideshow_tmp/<user_id>/<token>.jpg`` نگه داشته می‌شود تا کاربر
پس از دیدن پیش‌نمایش «تأیید» کند؛ با تأیید، توکن همراه فرم ثبت ارسال و فایل همان‌جا
به‌جای تصویر آپلودی استفاده می‌شود (``create`` در views).
"""

import io
import re
import secrets
import time
from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageOps

CANVAS = (2400, 600)          # بنر ۴:۱
SAFE = (1200, 600)            # ناحیهٔ امنِ مرکزی (در موبایل تنها همین بخش دیده می‌شود)
MAX_BYTES = 8 * 1024 * 1024   # ورودیِ «ساخت» مجازتر از آپلودِ مستقیم (۲ مگابایت) است
MIN_SIDE = 200                # کوچک‌تر از این، کیفیت قابل‌قبول نمی‌دهد
MAX_PIXELS = 40_000_000       # سقف ایمنی حافظه
MAX_UPSCALE = 3.0
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
OUT_MAX_BYTES = 1_900_000     # زیر سقف ۲ مگابایتیِ اعتبارسنجی فرم
TMP_DIR = "slideshow_tmp"
TMP_TTL = timedelta(hours=24)
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
_NAVY = (13, 20, 38)


class BuildError(Exception):
    """خطای قابل‌نمایش به کاربر (پیام فارسی)."""


def inspect_image(upload):
    """فایل آپلودی را بررسی و به‌صورت تصویر RGB بارگذاری می‌کند؛ در غیر این صورت BuildError."""
    if upload is None:
        raise BuildError("تصویری ارسال نشده است.")
    if upload.size > MAX_BYTES:
        raise BuildError(f"حجم تصویر بیش از {MAX_BYTES // 1048576} مگابایت است.")
    try:
        data = upload.read()
        img = Image.open(io.BytesIO(data))
        fmt = (img.format or "").upper()
        img.load()
    except Exception as exc:  # noqa: BLE001 - Pillow انواع خطا می‌دهد (از جمله DecompressionBomb)
        raise BuildError("فایل انتخاب‌شده تصویر معتبر نیست یا خراب است.") from exc
    if fmt not in ALLOWED_FORMATS:
        raise BuildError("فرمت تصویر باید PNG، JPG یا WEBP باشد.")
    if img.width < MIN_SIDE or img.height < MIN_SIDE:
        raise BuildError(f"تصویر خیلی کوچک است؛ هر ضلع حداقل {MIN_SIDE} پیکسل باشد.")
    if img.width * img.height > MAX_PIXELS:
        raise BuildError("ابعاد تصویر بیش‌ازحد بزرگ است.")
    return _to_rgb(img)


def _to_rgb(img):
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        base = Image.new("RGB", rgba.size, _NAVY)
        base.paste(rgba, mask=rgba.split()[-1])
        return base
    return img.convert("RGB")


def build_banner(src):
    """تصویر RGB را به بنر ۲۴۰۰×۶۰۰ (JPEG) تبدیل می‌کند و بایت‌ها را برمی‌گرداند."""
    W, H = CANVAS
    sw, sh = SAFE
    # --- پس‌زمینه: نسخهٔ cover محو و تیره
    scale = max(W / src.width, H / src.height)
    bw, bh = max(W, round(src.width * scale)), max(H, round(src.height * scale))
    bg = src.resize((bw, bh), Image.LANCZOS)
    left, top = (bw - W) // 2, (bh - H) // 2
    bg = bg.crop((left, top, left + W, top + H)).filter(ImageFilter.GaussianBlur(38))
    bg = ImageEnhance.Brightness(bg).enhance(0.62)
    # --- پیش‌زمینه: کامل و بدون برش داخل ناحیهٔ امن
    fs = min(sw / src.width, sh / src.height, MAX_UPSCALE)
    fw, fh = max(1, round(src.width * fs)), max(1, round(src.height * fs))
    fg = src.resize((fw, fh), Image.LANCZOS)
    # لبه‌های نرم؛ لبهٔ بالا/پایین فقط وقتی که تصویر به لبهٔ بوم نمی‌رسد
    f = 18
    mask = Image.new("L", (fw, fh), 0)
    d = ImageDraw.Draw(mask)
    y0, y1 = (0, fh) if fh >= H else (f, fh - f)
    d.rectangle((f, y0, fw - f - 1, y1 - 1), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(f / 2))
    canvas = bg.copy()
    canvas.paste(fg, ((W - fw) // 2, (H - fh) // 2), mask)
    out = None
    for quality in (88, 82, 76, 70, 62):
        buf = io.BytesIO()
        canvas.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
        out = buf.getvalue()
        if len(out) <= OUT_MAX_BYTES:
            break
    return out


# --------------------------------------------------------------------------- #
# فایل موقت (بین «ساخت و پیش‌نمایش» و «ثبت نهایی»)
# --------------------------------------------------------------------------- #
def _path(user, token):
    return f"{TMP_DIR}/{user.pk}/{token}.jpg"


def valid_token(token):
    return bool(token) and bool(_TOKEN_RE.match(token))


def save_temp(user, data):
    cleanup_old(user)
    token = secrets.token_urlsafe(18)
    default_storage.save(_path(user, token), ContentFile(data))
    return token


def load_temp(user, token):
    """بایت‌های بنر ساخته‌شدهٔ همین کاربر یا None (توکن نامعتبر/نبودِ فایل)."""
    if not valid_token(token):
        return None
    path = _path(user, token)
    try:
        if not default_storage.exists(path):
            return None
        with default_storage.open(path, "rb") as fh:
            return fh.read()
    except Exception:  # noqa: BLE001
        return None


def temp_url(user, token):
    return default_storage.url(_path(user, token))


def delete_temp(user, token):
    if not valid_token(token):
        return
    try:
        default_storage.delete(_path(user, token))
    except Exception:  # noqa: BLE001
        pass


def cleanup_old(user):
    """فایل‌های موقتِ قدیمی‌تر از TTL این کاربر را پاک می‌کند (بهترین تلاش)."""
    folder = f"{TMP_DIR}/{user.pk}"
    try:
        _dirs, files = default_storage.listdir(folder)
    except Exception:  # noqa: BLE001 - پوشه هنوز ساخته نشده
        return
    cutoff = time.time() - TMP_TTL.total_seconds()
    for name in files:
        try:
            p = f"{folder}/{name}"
            if default_storage.get_modified_time(p).timestamp() < cutoff:
                default_storage.delete(p)
        except Exception:  # noqa: BLE001
            continue
