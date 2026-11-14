"""محدودکنندهٔ نرخ درخواست (Rate limit) برای ویوهای ماژول «تقویم و ساعت جاری».

پنجرهٔ ثابت (fixed window) روی کش Django؛ کلید = کاربر واردشده یا IP مستقیم اتصال.
(عمداً X-Forwarded-For خوانده نمی‌شود چون توسط کلاینت قابل جعل است.)
"""
import functools

from django.core.cache import cache
from django.http import JsonResponse


def _client_key(request):
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        return 'u%s' % user.pk
    return 'ip%s' % request.META.get('REMOTE_ADDR', 'unknown')


def ratelimit(key_prefix, limit, window):
    """حداکثر `limit` درخواست در هر `window` ثانیه برای هر کلاینت؛ بیشتر از آن → HTTP 429 (JSON)."""

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            key = 'calconv:rl:%s:%s' % (key_prefix, _client_key(request))
            if cache.add(key, 1, timeout=window):
                count = 1
            else:
                try:
                    count = cache.incr(key)
                except ValueError:  # کلید بین add و incr منقضی شد
                    cache.set(key, 1, timeout=window)
                    count = 1
            if count > limit:
                response = JsonResponse({
                    'success': False,
                    'error': 'تعداد درخواست‌ها بیش از حد مجاز است؛ کمی بعد دوباره تلاش کنید.',
                }, status=429)
                response['Retry-After'] = str(window)
                return response
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
