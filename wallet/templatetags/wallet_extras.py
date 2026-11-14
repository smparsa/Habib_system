"""فیلترهای قالب ماژول کیف پول: نمایش اعداد فارسی با جداکنندهٔ هزارگان."""

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


@register.filter
def fa_num(value):
    """تبدیل عدد به فارسی با جداکنندهٔ هزارگان (مثال: 12345.5 → ۱۲٬۳۴۵٫۵)."""
    try:
        num = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return value
    negative = num < 0
    num = abs(num)
    whole = int(num)
    frac = num - whole
    text = f"{whole:,}"
    if frac:
        text += "٫" + format(frac, "f").split(".")[1].rstrip("0")
    text = text.translate(_FA_DIGITS)
    return ("−" if negative else "") + text