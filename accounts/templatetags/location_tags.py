"""برچسب قالب برای تزریقِ پیکربندی «سرویس موقعیت» به سربرگ صفحات.

استفاده در هر قالبِ دارای نقشه/GPS (پروفایل، داشبورد، مجله و ...):
    {% load location_tags %}
    {% location_service_config %}

خروجی، متاهایی است که app.js با آن‌ها ارائه‌دهندهٔ نقشه و حالتِ GPS را
می‌خواند:
    <meta name='map-provider-config' content='neshan|osm|google'>
    <meta name='gps-mode-config' content='all|browser|mobile'>
"""

from django import template
from django.utils.html import mark_safe

register = template.Library()


@register.simple_tag
def location_service_config():
    from accounts.location_settings import location_service_context

    ctx = location_service_context()
    out = ""
    if ctx.get("map_provider_active"):
        out += (
            f"<meta name='map-provider-config' "
            f"content='{ctx['map_provider_active']}'>"
        )
    out += f"<meta name='gps-mode-config' content='{ctx['gps_mode']}'>"
    return mark_safe(out)
