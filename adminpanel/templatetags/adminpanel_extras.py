from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """دسترسی به مقدار دیکشنری با کلید متغیر در قالب."""
    if mapping is None:
        return ""
    try:
        return mapping[key]
    except (KeyError, TypeError):
        return ""


@register.simple_tag
def form_field(form, name):
    """برگرداندن فیلد باندشدهٔ یک فرم با نام دلخواه (برای چیدمان بخش‌بندی‌شده)."""
    return form[name]