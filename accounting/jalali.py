"""تقویم شمسی (هجری شمسی/جلالی) — پیاده‌سازی مستقل، بدون وابستگی خارجی.

الگوریتم تبدیل همان الگوریتم رایج jalaali/jdatetime است و برای بازهٔ سال‌های
۱۱۷۸ تا ۱۶۳۳ شمسی دقیق است (پوشش کامل سال‌های مالی موردنیاز).

توابع کمکی: تبدیل ارقام فارسی/لاتین، فرمت و پارسِ تاریخ شمسی برای فرم‌ها.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
EN_DIGITS = "0123456789"

JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


def en_to_fa(text) -> str:
    """تبدیل ارقام لاتین به فارسی (مثل 1405 -> ۱۴۰۵)."""
    text = str(text)
    return text.translate(str.maketrans(EN_DIGITS, FA_DIGITS))


def fa_to_en(text) -> str:
    """تبدیل ارقام فارسی/عربی به لاتین (برای پارس ورودی کاربر)."""
    text = str(text)
    return text.translate(str.maketrans(FA_DIGITS + "٠١٢٣٤٥٦٧٨٩", EN_DIGITS + EN_DIGITS))


def format_thousands(value) -> str:
    """۱٬۲۳۴٬۵۶۷ — جداکنندهٔ هزار با «،» فارسی."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return str(value)
    s = f"{value:,}".replace(",", "٬")
    return en_to_fa(s) if False else s  # ارقام لاتین می‌مانند؛ نمایش ارقام با فیلتر جدا انجام می‌شود


def _is_gregorian_leap(gy: int) -> bool:
    return (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)


_G_DAY_OF_MONTH_START = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """تبدیل تاریخ میلادی به شمسی؛ خروجی (jy, jm, jd)."""
    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1

    g_day_no = 365 * gy2 + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
    g_day_no += _G_DAY_OF_MONTH_START[gm2] + gd2
    if gm2 > 1 and _is_gregorian_leap(gy):
        g_day_no += 1

    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365

    if j_day_no < 186:
        jm = 1 + j_day_no // 31
        jd = 1 + j_day_no % 31
    else:
        jm = 7 + (j_day_no - 186) // 30
        jd = 1 + (j_day_no - 186) % 30
    return jy, jm, jd


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    """تبدیل تاریخ شمسی به میلادی؛ خروجی (gy, gm, gd)."""
    jy2 = jy - 979
    jm2 = jm - 1
    jd2 = jd - 1

    j_day_no = 365 * jy2 + (jy2 // 33) * 8 + ((jy2 % 33) + 3) // 4
    j_day_no += jm2 * 31 if jm2 < 7 else jm2 * 30 + 6
    j_day_no += jd2

    g_day_no = j_day_no + 79
    gy = 1600 + 400 * (g_day_no // 146097)
    g_day_no %= 146097
    leap = True
    if g_day_no >= 36525:
        g_day_no -= 1
        gy += 100 * (g_day_no // 36524)
        g_day_no %= 36524
        if g_day_no >= 365:
            g_day_no += 1
        else:
            leap = False
    gy += 4 * (g_day_no // 1461)
    g_day_no %= 1461
    if g_day_no >= 366:
        leap = False
        g_day_no -= 1
        gy += g_day_no // 365
        g_day_no %= 365

    gd = g_day_no + 1
    month_lengths = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    while gm < 12 and gd > month_lengths[gm]:
        gd -= month_lengths[gm]
        gm += 1
    return gy, gm + 1, gd


def is_jalali_leap(jy: int) -> bool:
    """سال کبیسهٔ شمسی: طول سال ۳۶۶ روز باشد (فاصلهٔ فروردین ۱ امسال تا فردا)."""
    gy1, gm1, gd1 = jalali_to_gregorian(jy, 1, 1)
    gy2, gm2, gd2 = jalali_to_gregorian(jy + 1, 1, 1)
    d1 = date(gy1, gm1, gd1)
    d2 = date(gy2, gm2, gd2)
    return (d2 - d1).days == 366


def jalali_month_length(jy: int, jm: int) -> int:
    """تعداد روزهای ماه شمسی: ۶ ماه اول ۳۱، ۵ ماه بعد ۳۰ و اسفند ۲۹/۳۰."""
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if is_jalali_leap(jy) else 29


def days_in_jalali_month(jy: int, jm: int) -> int:
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if is_jalali_leap(jy) else 29


class JalaliDate:
    """تاریخ شمسی با API سبکِ jdatetime.date."""

    __slots__ = ("year", "month", "day")

    def __init__(self, year: int, month: int, day: int):
        if not 1 <= month <= 12:
            raise ValueError(f"ماه نامعتبر: {month}")
        if not 1 <= day <= days_in_jalali_month(year, month):
            raise ValueError(f"روز نامعتبر برای {year}/{month}: {day}")
        self.year = year
        self.month = month
        self.day = day

    # ---------- سازنده‌ها ----------
    @classmethod
    def fromgregorian(cls, *, date: date = None, year: int = None, month: int = None, day: int = None):
        if date is not None:
            jy, jm, jd = gregorian_to_jalali(date.year, date.month, date.day)
            return cls(jy, jm, jd)
        gy, gm, gd = jalali_to_gregorian(year, month, day)
        jy, jm, jd = gregorian_to_jalali(gy, gm, gd)
        return cls(jy, jm, jd)

    @classmethod
    def today(cls) -> "JalaliDate":
        t = date.today()
        jy, jm, jd = gregorian_to_jalali(t.year, t.month, t.day)
        return cls(jy, jm, jd)

    # ---------- تبدیل‌ها ----------
    def togregorian(self) -> date:
        gy, gm, gd = jalali_to_gregorian(self.year, self.month, self.day)
        return date(gy, gm, gd)

    def toordinal(self) -> int:
        return self.togregorian().toordinal()

    @property
    def month_name(self) -> str:
        return JALALI_MONTHS[self.month - 1]

    # ---------- مقایسه/هش ----------
    def __eq__(self, other):
        if isinstance(other, JalaliDate):
            return (self.year, self.month, self.day) == (other.year, other.month, other.day)
        return NotImplemented

    def __hash__(self):
        return hash((self.year, self.month, self.day))

    def __lt__(self, other):
        if not isinstance(other, JalaliDate):
            return NotImplemented
        return (self.year, self.month, self.day) < (other.year, other.month, other.day)

    def __le__(self, other):
        return self == other or self < other

    # ---------- نمایش ----------
    def __str__(self):
        return f"{self.year:04d}/{self.month:02d}/{self.day:02d}"

    def __repr__(self):
        return f"accounting.jalali.JalaliDate({self.year}, {self.month}, {self.day})"

    def strftime_fa(self) -> str:
        """۱۴۰۵/۰۷/۰۲ با ارقام فارسی."""
        return en_to_fa(str(self))


# ---------- ابزارهای پارس/فرمت برای فرم‌ها ----------

def jalali_today_str() -> str:
    return str(JalaliDate.today())


def format_jalali(value) -> str:
    """date/datetime -> '1405/07/02'؛ None -> ''."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        value = value.date() if hasattr(value, "date") else value
    if isinstance(value, date):
        return str(JalaliDate.fromgregorian(date=value))
    return str(value)


def parse_jalali_str(text: str):
    """'۱۴۰۵/۰۷/۰۲' یا '1405-7-2' یا '02/07/1405' باقی‌مانده -> datetime.date | None.

    جداکنندهٔ پذیرفته: / ، - و . — ارقام فارسی هم پذیرفته می‌شود.
    """
    if not text:
        return None
    cleaned = fa_to_en(str(text).strip()).replace("٫", "/").replace("٫", "/")
    for sep in ("-", ".", " "):
        cleaned = cleaned.replace(sep, "/")
    parts = [p for p in cleaned.split("/") if p != ""]
    if len(parts) != 3:
        return None
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    # پشتیبانی از dd/mm/yyyy (سال ۴ رقمی آخر)
    if nums[2] > 999 and nums[0] <= 31:
        nums = [nums[2], nums[1], nums[0]]
    jy, jm, jd = nums
    if jy < 100:  # سال دو رقمی → 14xx
        jy += 1400 if jy < 50 else 1300
    try:
        return JalaliDate(jy, jm, jd).togregorian()
    except ValueError:
        return None
