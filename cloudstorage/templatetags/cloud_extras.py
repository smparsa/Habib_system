"""فیلترهای قالب ماژول فضای ابری (بخش مدیریتی)."""
from django import template

register = template.Library()


@register.filter
def get_field(form, name):
    """دسترسی به BoundField فرم با نام فیلد (در قالب: {{ form|get_field:'name' }})."""
    try:
        return form[name]
    except Exception:  # noqa: BLE001 — فیلد ناموجود → خروجی خالی
        return ""


@register.filter
def field_label(form, name):
    """برچسب فیلد فرم (یا نام خام در صورت نبود)."""
    try:
        return form[name].label or name
    except Exception:  # noqa: BLE001
        return name


@register.filter
def split(value, sep=","):
    """تبدیل رشته به فهرست (برای حلقهٔ قالب)."""
    if not value:
        return []
    return [part.strip() for part in str(value).split(sep) if part.strip()]