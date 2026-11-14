"""ابزارهای خواندنِ «تنظیمات سرویس موقعیت» (نقشه و GPS) برای ویوها و قالب‌ها.

تنظیمات در LocationSetting (تک‌رکوردی) نگه‌داری و از پنل مدیریت ویرایش می‌شود؛
این ماژول فقط خواندن را ساده می‌کند. کلیدهای نشان/گوگل هرگز به مرورگر نمی‌روند؛
فقط «وجود/نبودِ» کلید این‌جا برای انتخاب نقشهٔ نمایشیِ در دسترس بررسی می‌شود.

قاعدهٔ نقشه: اول انتخاب ادمین؛ اگر کلیدِ آن تنظیم نشده باشد، به ترتیبِ
نشان ← گوگل ← OpenStreetMap به نزدیک‌ترین گزینهٔ در دسترس می‌افتیم تا کاربر
همیشه نقشه‌ای تعاملی ببیند. OpenStreetMap کلید نمی‌خواهد و همیشه در دسترس است.

قاعدهٔ GPS: حالت «فقط GPS مرورگر» یعنی بدون مختصاتِ ارسالیِ کاربر، جایگزینِ IP
سمت سرور استفاده نمی‌شود (هر سه حالت دیگر: همه / موبایل مثل امروز رفتار می‌کنند).
"""

import os

from .models import LocationSetting

# ترتیبِ جایگزین‌های نقشه وقتی انتخاب ادمین در دسترس نباشد
MAP_PROVIDER_FALLBACK_ORDER = ("neshan", "google", "osm")


def neshan_key_set():
    """آیا کلید «نشان» روی سرور تنظیم شده است؟ (فقط وجود، نه خودِ کلید)"""
    return bool(os.environ.get("NESHAN_API_KEY", "").strip())


def google_key_set():
    """آیا کلید Google Maps روی سرور تنظیم شده است؟ (فقط وجود، نه خودِ کلید)"""
    return bool(os.environ.get("GOOGLE_MAPS_API_KEY", "").strip())


def get_location_setting():
    """نمونهٔ تک‌رکوردی تنظیمات سرویس موقعیت (در صورت نبود می‌سازد)."""
    return LocationSetting.get()


def effective_map_provider(setting=None):
    """ارائه‌دهندهٔ نقشهٔ نمایشیِ مؤثر.

    اول انتخاب ادمین (map_provider)؛ اگر کلیدش روی سرور نباشد، اولین گزینهٔ
    در دسترس از ترتیب نشان ← گوگل ← OpenStreetMap برمی‌گردد. OpenStreetMap
    همیشه در دسترس است، بنابراین خروجی هرگز خالی نمی‌ماند.
    """
    setting = setting or get_location_setting()
    chosen = (
        setting.map_provider
        if setting.map_provider in MAP_PROVIDER_FALLBACK_ORDER
        else "neshan"
    )
    ordered = (chosen,) + tuple(
        p for p in MAP_PROVIDER_FALLBACK_ORDER if p != chosen
    )
    for provider in ordered:
        if provider == "neshan" and neshan_key_set():
            return "neshan"
        if provider == "google" and google_key_set():
            return "google"
        if provider == "osm":
            return "osm"
    return "osm"


def gps_mode(setting=None):
    """حالت «منبع موقعیت»: all | browser | mobile (با مقدار امن پیش‌فرض)."""
    setting = setting or get_location_setting()
    mode = setting.location_provider
    return mode if mode in ("all", "browser", "mobile") else "all"


def ip_fallback_allowed(setting=None):
    """آیا در حالت جاری، سقوطِ بدون-مختصات به IP مجاز است؟

    در حالت «فقط GPS مرورگر» خیر؛ در «همه» و «موبایل» بله (رفتارِ فعلی).
    """
    return gps_mode(setting) != "browser"


def location_service_context(setting=None):
    """دادهٔ موردنیاز قالب‌ها/متا برای پیکربندی سمت مرورگر.

    خروجی: نقشهٔ نمایشیِ مؤثر (map_provider_active)، حالت GPS (gps_mode) و
    وضعیتِ وجود کلیدها (neshan_key_set / google_key_set) — برای نشان دادنِ
    وضعیت در صفحهٔ تنظیمات پنل مدیریت.
    """
    setting = setting or get_location_setting()
    return {
        "map_provider_active": effective_map_provider(setting),
        "gps_mode": gps_mode(setting),
        "neshan_key_set": neshan_key_set(),
        "google_key_set": google_key_set(),
    }
