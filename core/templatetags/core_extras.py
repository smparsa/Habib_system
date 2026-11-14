"""فیلترهای مشترک قالب‌ها — تاریخ و ساعت شمسی (جلالی) برای کل سیستم.

منطق تبدیل از ``accounting.jalali`` (پیاده‌سازی مستقل و بدون وابستگی خارجی)
استفاده می‌کند؛ فیلترهای این ماژول در همهٔ اپ‌ها قابل بارگذاری‌اند:

    {% load core_extras %}
    {{ obj.created_at|jdatetime }}   ← ۱۴۰۵/۰۷/۰۵ ۱۴:۳۰
    {{ obj.created_at|jdate }}       ← ۱۴۰۵/۰۷/۰۵
    {{ obj.created_at|jtime }}       ← ۱۴:۳۰
"""

from datetime import date, datetime

from django import template
from django.utils import timezone

from accounting.jalali import en_to_fa, gregorian_to_jalali

register = template.Library()


def _local(value):
    """datetime آگاه از منطقهٔ زمانی (Asia/Tehran) برای نمایش محلی."""
    if isinstance(value, datetime) and timezone.is_aware(value):
        return timezone.localtime(value)
    return value


def _jparts(value):
    """(jy, jm, jd, hour, minute) از date/datetime؛ برای ورودی نامعتبر None."""
    value = _local(value)
    if isinstance(value, datetime):
        jy, jm, jd = gregorian_to_jalali(value.year, value.month, value.day)
        return jy, jm, jd, value.hour, value.minute
    if isinstance(value, date):
        jy, jm, jd = gregorian_to_jalali(value.year, value.month, value.day)
        return jy, jm, jd, None, None
    return None


@register.filter
def jdatetime(value):
    """۱۴۰۵/۰۷/۰۵ ۱۴:۳۰ — تاریخ و ساعت شمسی با ارقام فارسی."""
    parts = _jparts(value)
    if not parts:
        return "" if value is None else value
    jy, jm, jd, hh, mm = parts
    out = f"{jy:04d}/{jm:02d}/{jd:02d}"
    if hh is not None:
        out += f" {hh:02d}:{mm:02d}"
    return en_to_fa(out)


@register.filter
def jdate(value):
    """۱۴۰۵/۰۷/۰۵ — فقط تاریخ شمسی با ارقام فارسی."""
    parts = _jparts(value)
    if not parts:
        return "" if value is None else value
    jy, jm, jd, _, _ = parts
    return en_to_fa(f"{jy:04d}/{jm:02d}/{jd:02d}")


@register.filter
def jtime(value):
    """۱۴:۳۰ — ساعت محلی (به وقت تهران) برای datetime."""
    value = _local(value)
    if isinstance(value, datetime):
        return en_to_fa(f"{value.hour:02d}:{value.minute:02d}")
    return "" if value is None else value


@register.filter
def jdatetime_en(value):
    """1405/07/05 14:30 — تاریخ و ساعت شمسی با ارقام لاتین (برای داده/چاپ)."""
    parts = _jparts(value)
    if not parts:
        return "" if value is None else value
    jy, jm, jd, hh, mm = parts
    out = f"{jy:04d}/{jm:02d}/{jd:02d}"
    if hh is not None:
        out += f" {hh:02d}:{mm:02d}"
    return out


@register.filter
def jyear(value):
    """سال شمسی (مثلاً ۱۴۰۵) — برای شماره‌دهی و فیلترها."""
    parts = _jparts(value)
    if not parts:
        return ""
    return parts[0]
