"""موتور پالایش محتوای تیکت‌ها (فیلتر واژه/عبارت‌های حساس).

اصل طراحی — لایهٔ قطعیِ «قانون»:
- متنِ کاربر و واژه‌های ذخیره‌شده هر دو «نرمال‌سازی» می‌شوند (حذف حرکت، یکسان‌سازی
  حروف عربی/فارسی مانند ي/ی و ك/ک و أإآ/ا، حذف نیم‌فاصله و فاصله‌های تکراری) تا
  املای متفاوت یک واژه دور نزند.
- «مرز واژه» رعایت می‌شود تا واژهٔ قانونیِ داخلِ واژهٔ دیگر مسدود نشود؛ حالت‌های
  «ابتدای واژه»، «هر جای متن» و «regex» برای واژه‌های صرف‌شده/عبارات در اختیار ادمین است.
- کارکنان (ادمین/کارشناس) از فیلتر معاف‌اند و پالایش برای محتوای کاربران عادی اعمال می‌شود.
- درگیری فقط به «دستهٔ تخلف» اشاره می‌کند (متن ممنوع تکرار نمی‌شود) و اصل متن هرگز
  ذخیره/لاگ نمی‌شود؛ فقط رویداد «content.blocked» با دسته‌ها ثبت می‌شود.

برای لایه‌های نرم‌افزاریِ تکمیلی (تشخیص معنایی، مباحث خاکستریِ سیاسی/مذهبی، صف بازبینی
انسانی و ...) به مستندات مراجعه شود — این ماژول فقط بخش قطعی و قابل‌مدیریتِ ادمین است.
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# نرمال‌سازی متن فارسی/عربی
# ---------------------------------------------------------------------------

# یکسان‌سازی حروف عربی به املای رایج فارسی؛ نگاشت برای «تطبیق» است تا نگارش‌های
# گوناگونِ یک واژه همگی گرفته شوند.
_CHAR_MAP = {
    "\u064a": "ی",  # ي عربی
    "\u0649": "ی",  # ى
    "\u06cc": "ی",  # ی فارسی
    "\u0643": "ک",  # ك عربی
    "\u06a9": "ک",  # ک فارسی
    "\u0623": "ا",  # أ
    "\u0625": "ا",  # إ
    "\u0622": "ا",  # آ
    "\u0671": "ا",  # ٱ
    "\u0629": "ه",  # ة
    "\u06c0": "ه",  # ۀ
    "\u06be": "ه",  # ھ
    "\u0624": "و",  # ؤ
    "\u0626": "ی",  # ئ
}

# نویسه‌های بی‌صدا: حرکت‌گذاری/تشدید، تنوین، tatweel (ـ)، ZWNJ/ZWJ، LRM/RLM و ...
_SILENT = re.compile(
    r"[\u064b-\u065f\u0670\u06d6-\u06dc\u06df-\u06e8\u06ea-\u06ed\u0640"
    r"\u200c\u200d\u200e\u200f\u0610-\u061a]"
)
_WS = re.compile(r"\s+")

_TRANSLATE_RE = None


def _translate_re():
    global _TRANSLATE_RE
    if _TRANSLATE_RE is None:
        _TRANSLATE_RE = re.compile("[%s]" % re.escape("".join(_CHAR_MAP.keys())))
    return _TRANSLATE_RE


def normalize(text):
    """نرمال‌سازی متن برای تطبیق: NFC + یکسان‌سازی حروف + حذف حرکت/نیم‌فاصله."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", str(text))
    text = _translate_re().sub(lambda m: _CHAR_MAP[m.group(0)], text)
    text = _SILENT.sub("", text)
    text = text.lower()
    text = _WS.sub(" ", text).strip()
    return text


# ---------------------------------------------------------------------------
# تطبیق الگوها
# ---------------------------------------------------------------------------


def _pattern_source(term, mode):
    """واژه برای ساخت الگو: در حالت regex الگوی خام (بدون نرمال‌سازی) استفاده می‌شود
    تا کلاس‌هایی مانند [A-Z] و ساختارهای regex دست‌نخورده بمانند."""
    return term if mode == "regex" else normalize(term)


def _regex_for(term, mode):
    """ساخت الگوی regex برای یک واژه بر اساس حالت انتخابی ادمین."""
    src = _pattern_source(term, mode)
    if mode == "contains":
        return re.compile(re.escape(src))
    if mode == "word":
        return re.compile(r"(?<![\w]){}(?![\w])".format(re.escape(src)))
    if mode == "prefix":
        return re.compile(r"(?<![\w]){}".format(re.escape(src)))
    if mode == "regex":
        return re.compile(src, re.IGNORECASE)
    return None


def is_valid_pattern(term, mode):
    """اعتبارسنجی الگو هنگام ذخیره توسط ادمین (مخصوص حالت regex)."""
    try:
        _regex_for(term, mode)
        return True
    except re.error:
        return False


def term_matches(term, mode, norm_text):
    """آیا متنِ نرمال‌شده شامل این واژه/الگو است؟"""
    pat = _regex_for(term, mode)
    if pat is None:
        return False
    try:
        return pat.search(norm_text) is not None
    except re.error:
        return False


def find_violations(text):
    """بررسی یک متن و برگرداندن واژه‌های فعالِ گرفته‌شده (لیست نمونه‌های مدل).

    فقط متنِ کاربران عادی باید بررسی شود؛ معافیت کارکنان در فراخواننده انجام می‌شود.
    """
    if not (text or "").strip():
        return []
    from .models import SensitiveTerm

    norm = normalize(text)
    if not norm:
        return []
    hits = []
    for item in SensitiveTerm.objects.filter(is_active=True):
        if term_matches(item.term, item.mode, norm):
            hits.append(item)
    return hits


def block_message(hits):
    """پیام تذکر فارسی برای کاربر؛ نام دقیق واژه تکرار نمی‌شود، فقط دستهٔ تخلف."""
    labels = []
    for item in hits:
        label = item.get_category_display()
        if label and label not in labels:
            labels.append(label)
    if not labels:
        labels = ["مغایر با اصول اخلاقی"]
    joined = "، ".join(labels)
    return (
        "پیام شما ارسال نشد؛ متن شامل عبارت‌هایی از دستهٔ «%s» است. "
        "لطفاً متن را اصلاح کنید و دوباره ارسال کنید." % joined
    )
