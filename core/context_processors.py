"""
Context processors مشترک برنامه:

* ``info_pages``      → متن صفحات اطلاعات (core/templates/core/info_page.html)
* ``breaking_news``   → خبرهای فوریِ در حال پخش هدر (core/_breaking_news_bar.html)
* ``dashboard_ads``   → تبلیغات زندهٔ هدرِ فعلی + فهرست محل‌های تبلیغ
  (dashboard = نوار پایین داشبورد اصلی؛ core/templates/core/dashboard.html)
* ``dashboard_ads_wallet / _accounting / _tickets`` → همان خروجی برای
  هدرهای کیف پول / حسابداری / تیکت با فیکسِ placement آن ماژول.
"""

import logging

from django.http import HttpRequest

from adminpanel.models import Advertisement, AdHeaderPlacement, BreakingNews

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# خبرهای فوری هدر
# ---------------------------------------------------------------------------

def breaking_news(request: HttpRequest):
    """خبرهای «فوری» در حال پخش — برای نوار هدر همهٔ کاربران."""
    try:
        items = [
            {
                'id': n.pk,
                'text': n.text,
                'speed': n.speed,
                'sort_order': n.sort_order,
            }
            for n in BreakingNews.active_news()
        ]
    except Exception:
        logger.exception('breaking_news context processor failed')
        items = []
    return {'breaking_news': items}


# ---------------------------------------------------------------------------
# صفحات اطلاعات (core info pages) — چون فهرست صفحات اطلاعات در settings ثبت
# شده بود و در قالبِ info_page.html استفاده می‌شد، لقب کمکی دارد.
# ---------------------------------------------------------------------------

def footer_pages(request: HttpRequest):
    """لینک‌های پانویس (درباره ما، قوانین و مقررات، تماس با ما و …) از InfoPage.

    قالب‌های داشبورد/فیدبک/صفحات اطلاعات با ``{% for fp in footer_pages %}``
    می‌خوانند؛ بدون این processor متغیر خالی بود و لینک‌ها حذف می‌شدند.
    """
    try:
        from core.models import InfoPage

        pages = list(InfoPage.footer_pages().order_by('sort_order'))
        items = [
            {
                'slug': p.slug,
                'title': p.title,
                'icon': p.icon,
            }
            for p in pages
        ]
    except Exception:
        logger.exception('footer_pages context processor failed')
        items = []
    return {'footer_pages': items}


def info_pages(request: HttpRequest):
    """فهرست لینک‌های صفحات اطلاعات در هدر/فوتر (بدون اتصال به DB کامل)."""
    try:
        from core.models import InfoPage

        pages = list(
            InfoPage.objects.filter(is_active=True).order_by('sort_order')
        )
        items = [
            {
                'id': p.pk,
                'slug': p.slug,
                'title': p.title,
            }
            for p in pages
        ]
    except Exception:
        logger.exception('info_pages context processor failed')
        items = []
    return {'info_pages': items}


# ---------------------------------------------------------------------------
# تبلیغات نوار متحرک
# ---------------------------------------------------------------------------

def _resolve_placement_code(request: HttpRequest) -> str:
    """کد محل پخش نوار را از مسیر درخواست استخراج می‌کند.

    داشبورد اصلی = dashboard؛ wallet/accounting/tickets = همان کد.
    اگر نامشخص باشد، پیش‌فرض dashboard است (نوار پایین داشبورد).
    """
    path = getattr(request, 'path', '') or ''
    # پنل مدیریت روی داشبوردِ داشبوردپنل تبلیغ نشان نمی‌دهد، اما context
    # processor همیشه مقدار معتبر برگرداند تا قالب‌ها نشکنند.
    cleaned = path.strip('/')
    if not cleaned:
        return 'dashboard'
    last = cleaned.split('/')[-1]
    if last in {'wallet', 'accounting', 'tickets'}:
        return last
    return 'dashboard'


def _placement_ads(placement_code: str):
    """تبلیغ‌های زندهٔ همان placement (شمارندهٔ نمایش هم ثبت می‌شود)."""
    ads = Advertisement.active_ads(placement=placement_code)
    for ad in ads:
        ad.increment_views(save=False)
    return ads


def _ads_context(request: HttpRequest, placement: str) -> dict:
    """ساخت یکدست context تبلیغ‌ها برای placement مشخص + نام‌های مستعار قالب‌ها.

    کلید اصلی ``dashboard_ads`` برای سازگاری، به‌علاوهٔ کلید سفارشی هر هدر
    (``dashboard_ads_wallet`` / ``dashboard_ads_accounting`` /
    ``dashboard_ads_tickets``) که includeهای قالب‌ها مستقیماً مصرف می‌کنند.
    """
    placements = AdHeaderPlacement.active_placements()
    placement_list = [
        {
            'code': p.code,
            'title': p.title,
            'description': p.description,
            'is_active': p.is_active,
        }
        for p in placements
    ]
    try:
        live = _placement_ads(placement)
    except Exception:
        logger.exception('ads context placement=%s failed', placement)
        live = Advertisement.objects.none()
    items = [
        {
            'id': a.pk,
            'logo': a.logo.url if a.logo else '',
            'title': a.title,
            'description': a.description,
            'link_url': a.link_url,
            'speed': a.speed,
            'views': a.views,
            'placement': placement,
        }
        for a in live
    ]
    return {
        'dashboard_ads': items,
        f'dashboard_ads_{placement}': items,
        'dashboard_ads_placement': placement,
        'dashboard_ads_placements': placement_list,
    }


def dashboard_ads(request: HttpRequest):
    """تبلیغ‌های زندهٔ هدرِ فعلی (placement از مسیر درخواست)."""
    return _ads_context(request, _resolve_placement_code(request))


def _fixed_ads_processor(placement_code):
    def processor(request: HttpRequest):
        return _ads_context(request, placement_code)
    return processor


dashboard_ads_wallet = _fixed_ads_processor('wallet')
dashboard_ads_accounting = _fixed_ads_processor('accounting')
dashboard_ads_tickets = _fixed_ads_processor('tickets')


# ---------------------------------------------------------------------------
# اسلایدشوی آمار داشبورد — ۴ باکس بالای «ماژول‌های کسب‌وکار»
# (فقط «اسلایدشو A»)
# ---------------------------------------------------------------------------

def dashboard_stat_slides(request: HttpRequest):
    """اسلایدهای زندهٔ هر باکس آمار + زمان تعویض اسلاید — برای داشبورد اصلی.

    خروجی: ``stat_slides_data`` = دیکشنری کد باکس به فهرست اسلایدها؛ اسلایدشو فقط
    یک باکس دارد («اسلایدشو A»، کد stat_tasks)
    + کلید ``stat_slides_seconds`` = زمان پیش‌فرض تعویض (ثانیه).
    هر اسلاید پس از رندر، شمارندهٔ نمایشش (اتمیک) بالا می‌رود.
    """
    from adminpanel.models import StatSlide, StatSlideBox, StatSlideSetting

    empty: dict[str, list] = {'stat_tasks': []}
    try:
        setting = StatSlideSetting.get()
        default_seconds = setting.switch_seconds or 6
        boxes = {b.code: b for b in StatSlideBox.objects.all()}
        seconds_by_box = {
            code: (boxes[code].effective_switch_seconds(default_seconds) if code in boxes else default_seconds)
            for code in empty
        }
        slots = {}
        for code in empty:
            box = boxes.get(code)
            if box is None or not box.is_active:
                slots[code] = []
                continue
            slides = StatSlide.active_slides(box=code)
            for slide in slides:
                slide.increment_views(save=False)
            slots[code] = [
                {
                    'id': s.pk,
                    'image': s.image.url if s.image else '',
                    'title': s.title,
                    'description': s.description,
                    'link_url': s.link_url,
                }
                for s in slides
            ]
        return {
            'stat_slides_data': slots,
            'stat_slides_seconds': default_seconds,
            'stat_slides_seconds_by_box': seconds_by_box,
            'stat_slides_has_any': any(slots.values()),
        }
    except Exception:
        logger.exception('dashboard_stat_slides context processor failed')
        return {
            'stat_slides_data': empty,
            'stat_slides_seconds': 6,
            'stat_slides_seconds_by_box': {},
            'stat_slides_has_any': False,
        }
