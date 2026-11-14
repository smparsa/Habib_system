"""فیلترهای قالب حسابداری: ارقام فارسی، جداکنندهٔ هزار، تاریخ شمسی."""

from django import template

from .. import jalali
from ..jalali import en_to_fa

register = template.Library()


@register.filter
def fa_digits(value):
    """۱۴۰۵ — تبدیل ارقام لاتین به فارسی."""
    try:
        return jalali.en_to_fa(value)
    except Exception:
        return value


@register.filter
def rial(value):
    """۱٬۲۳۴٬۵۶۷ — عدد با جداکنندهٔ هزار (ارقام لاتین)."""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return value


@register.filter
def rial_fa(value):
    """۵۰٬۰۰۰٬۰۰۰ — جداکنندهٔ فارسی «٬» با ارقام فارسی."""
    try:
        return en_to_fa(f"{int(value):,}").replace(",", "٬")
    except (TypeError, ValueError):
        return value


@register.filter
def jdate(value):
    """date/datetime -> ۱۴۰۵/۰۷/۰۲ با ارقام فارسی."""
    formatted = jalali.format_jalali(value)
    return jalali.en_to_fa(formatted) if formatted else ""


@register.filter
def jdate_en(value):
    """date/datetime -> 1405/07/02 با ارقام لاتین."""
    return jalali.format_jalali(value)


@register.filter
def jmonth(value):
    """ماه شمسی تاریخ (عدد ۱ تا ۱۲) — برای مقداردهی اولیهٔ تقویم شمسی."""
    try:
        jy, jm, jd = jalali.gregorian_to_jalali(value.year, value.month, value.day)
        return jm
    except Exception:
        return 1


@register.filter
def toman(value):
    """نمایش تومانی (÷۱۰) با جداکننده."""
    try:
        return f"{int(value) // 10:,}"
    except (TypeError, ValueError):
        return value


@register.filter
def amount_class(value):
    """کلاس رنگ مانده: بدهکار (مثبت) / بستانکار (منفی)."""
    try:
        return "pos" if int(value) >= 0 else "neg"
    except (TypeError, ValueError):
        return ""
