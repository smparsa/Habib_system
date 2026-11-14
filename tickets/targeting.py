"""موتور هدف‌گیری — تمام فیلترها سمت دیتابیس (Q/extra) اجرا می‌شوند.

کاربران هرگز به پایتون لود نمی‌شوند تا فیلتر شوند؛ قواعدِ AND/OR به یک QuerySet
تبدیل می‌شوند و شمارش/گیرنده‌سازی از روی همان QuerySet انجام می‌شود.

ساختار قواعد (JSON):
rules = {"logic": "and", "items": [leaf_or_group, ...]}
leaf  = {"kind": AUD_*, "values": [...], "value": x}
گروه  = {"logic": "or", "items": [...]}
"""

import math

from django.db.models import Q

from accounts.models import Profile

from . import constants as C
from .exceptions import TargetingError

RADIUS_METERS = (50, 100, 500, 1000, 5000, 10000)


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [v for v in value if v not in (None, "")]
    return [value]


def _normalize_kind(kind):
    """نام‌های کوتاهِ سازگار با فرم/تست‌ها (score/level) ← ثابت‌های رسمی.

    فرم ساخت تیکت (create.html) و تست‌ها از «score»/«level» استفاده می‌کنند درحالی‌که
    ثابت‌های رسمی «user_score»/«user_level» هستند؛ این تابع هر دو را می‌پذیرد.
    """
    return {"score": C.AUD_SCORE, "level": C.AUD_LEVEL}.get(kind, kind)


def leaf_q(kind, params):
    kind = _normalize_kind(kind)
    values = _as_list(params.get("values", params.get("value")))
    if kind == C.AUD_ALL:
        return Q()
    if kind == C.AUD_JOB:
        titles = [str(v).strip() for v in values if str(v).strip()]
        if not titles:
            raise TargetingError("فهرست مشاغل خالی است.")
        return Q(job_title__in=titles) | Q(jobs__title__in=titles)
    if kind == C.AUD_COUNTRY:
        return Q(country__in=[str(v).strip() for v in values])
    if kind == C.AUD_PROVINCE:
        return Q(province__in=[str(v).strip() for v in values])
    if kind == C.AUD_CITY:
        return Q(city__in=[str(v).strip() for v in values])
    if kind == C.AUD_LEVEL:
        try:
            return Q(user_level__gte=int(params.get("value", 0)))
        except (TypeError, ValueError):
            raise TargetingError("سطح نامعتبر است.")
    if kind == C.AUD_SCORE:
        try:
            return Q(user_score__gte=int(params.get("value", 0)))
        except (TypeError, ValueError):
            raise TargetingError("امتیاز نامعتبر است.")
    if kind == C.AUD_GROUP:
        codes = [str(v).strip() for v in values]
        return Q(user__user_groups__code__in=codes)
    if kind == C.AUD_USERS:
        ids = [int(v) for v in values if str(v).isdigit()]
        if not ids:
            raise TargetingError("کاربری انتخاب نشده است.")
        return Q(user_id__in=ids)
    if kind == C.AUD_MOBILE_PREFIX:
        prefixes = [str(v).strip() for v in values if str(v).strip()]
        if not prefixes:
            raise TargetingError("شروع شماره موبایل خالی است.")
        q = Q()
        for prefix in prefixes:
            q |= Q(user__mobile_number__startswith=prefix)
        return q
    if kind == C.AUD_AGE:
        from django.utils import timezone

        today = timezone.localdate()
        q = Q(date_of_birth__isnull=False)
        min_age = params.get("age_min")
        max_age = params.get("age_max")
        try:
            if min_age not in (None, ""):
                q &= Q(date_of_birth__lte=today - timezone.timedelta(
                    days=int(float(min_age) * 365.2425)))
            if max_age not in (None, ""):
                q &= Q(date_of_birth__gte=today - timezone.timedelta(
                    days=int((float(max_age) + 1) * 365.2425)))
        except (TypeError, ValueError):
            raise TargetingError("بازهٔ سنی نامعتبر است.")
        return q
    if kind in (C.AUD_JOB_SECTOR, C.AUD_JOB_INDUSTRY, C.AUD_JOB_CATEGORY,
                C.AUD_JOB_TITLE, C.AUD_JOB_SPEC):
        field = C.JOB_LAYER_FIELDS[kind]
        names = [str(v).strip() for v in values if str(v).strip()]
        if not names:
            raise TargetingError("فهرست ردهٔ شغلی خالی است.")
        q = Q()
        for name in names:
            q |= Q(**{f"jobs__{field}__name__icontains": name})
        return q
    raise TargetingError(f"نوع مخاطب «{kind}» پشتیبانی نمی‌شود.")


def radius_params(params):
    """بازگرداندن (lat, lng, km) برای فیلتر جغرافیایی — مقادیر به دیتابیس می‌روند."""
    try:
        lat = float(params.get("lat"))
        lng = float(params.get("lng"))
        km = float(params.get("km", 1))
    except (TypeError, ValueError):
        raise TargetingError("مختصات مرکز (lat/lng) و شعاع لازم است.")
    if km <= 0:
        raise TargetingError("شعاع باید بزرگ‌تر از صفر باشد.")
    return lat, lng, km


def _build_q(node):
    logic = node.get("logic", "and").lower()
    items = node.get("items") or node.get("rules") or []
    if logic not in ("and", "or"):
        raise TargetingError("منطق قواعد فقط and/or است.")
    q = Q()
    for item in items:
        if isinstance(item, dict) and "items" in item:
            sub = _build_q(item)
        elif isinstance(item, dict) and "kind" in item:
            if item["kind"] == C.AUD_RADIUS:
                # برگِ شعاع توسط resolve() جداگانه (bounding-box + haversine) اعمال
                # می‌شود؛ این‌جا نادیده گرفته می‌شود تا درخت نشکند.
                continue
            sub = leaf_q(item["kind"], item)
        else:
            raise TargetingError("قاعدهٔ نامعتبر در درخت هدف‌گیری.")
        q = (q & sub) if logic == "and" else (q | sub)
    return q


def resolve(rules, exclude_user_id=None, base=None, active_only=True):
    """
    اجرای درخت قواعد روی Profile و بازگرداندن QuerySet.
    قواعد شعاع جغرافیایی جداگانه (فقط در سطح بالا) جمع‌آوری می‌شوند و در پایان
    با عبارت haversine روی دیتابیس اعمال می‌شوند (bounding-box + محاسبهٔ دقیق).
    """
    if not isinstance(rules, dict) or ("items" not in rules and "kind" not in rules):
        raise TargetingError("ساختار قواعد نامعتبر است.")

    radii = []

    def collect(node):
        items = node.get("items")
        if items is None:
            leaf = node
            if leaf.get("kind") == C.AUD_RADIUS:
                radii.append(leaf)
                return True  # درخت این برگ را نادیده می‌گیرد
            return False
        for item in items:
            if isinstance(item, dict):
                collect(item)
        return False

    collect(rules)

    base = base or Profile.objects.all()
    qs = base.filter(_build_q(rules)).distinct()
    if exclude_user_id:
        qs = qs.exclude(user_id=exclude_user_id)
    if active_only:
        qs = qs.filter(user__is_active=True)

    # شعاع جغرافیایی (دقیق؛ همه سمت دیتابیس)
    for leaf in radii:
        lat, lng, km = radius_params(leaf)
        # bounding-box برای استفاده از ایندکس مختصات
        deg_lat = km / 110.574
        deg_lng = km / (111.320 * max(math.cos(math.radians(lat)), 1e-9))
        qs = qs.filter(latitude__range=(lat - deg_lat, lat + deg_lat),
                       longitude__range=(lng - deg_lng, lng + deg_lng))
        expr = (
            "(6371 * 2 * ASIN(SQRT(POW(SIN(RADIANS(accounts_profile.latitude - %s) / 2), 2)"
            "+ COS(RADIANS(%s)) * COS(RADIANS(accounts_profile.latitude))"
            "* POW(SIN((RADIANS(accounts_profile.longitude - %s) / 2)), 2)))) <= %s"
        )
        qs = qs.extra(where=[expr], params=[lat, lat, lng, km])
    return qs


def label_for(rules):
    """توضیح فارسیِ هدف برای نمایش/گزارش (خلاصه)."""
    parts = []

    def walk(node, depth=0):
        if depth > 3:
            return
        for item in node.get("items", []):
            if "items" in item:
                walk(item, depth + 1)
                continue
            kind = _normalize_kind(item.get("kind"))
            values = _as_list(item.get("values", item.get("value")))
            if kind == C.AUD_ALL:
                parts.append("همهٔ کاربران")
            elif kind == C.AUD_JOB:
                parts.append("شغل: " + "، ".join(str(v) for v in values))
            elif kind == C.AUD_COUNTRY:
                parts.append("کشور: " + "، ".join(str(v) for v in values))
            elif kind == C.AUD_PROVINCE:
                parts.append("استان: " + "، ".join(str(v) for v in values))
            elif kind == C.AUD_CITY:
                parts.append("شهر: " + "، ".join(str(v) for v in values))
            elif kind == C.AUD_RADIUS:
                parts.append(f"شعاع {item.get('km', 1)} کیلومتر")
            elif kind == C.AUD_LEVEL:
                parts.append(f"سطح ≥ {item.get('value')}")
            elif kind == C.AUD_SCORE:
                parts.append(f"امتیاز ≥ {item.get('value')}")
            elif kind == C.AUD_GROUP:
                parts.append("گروه: " + "، ".join(str(v) for v in values))
            elif kind == C.AUD_USERS:
                parts.append(f"{len(values)} کاربر مشخص")
            elif kind == C.AUD_MOBILE_PREFIX:
                parts.append("موبایل: " + "، ".join(str(v) for v in values))
            elif kind == C.AUD_AGE:
                parts.append("سن: " + " تا ".join(
                    str(item.get(k)) for k in ("age_min", "age_max")
                    if item.get(k) not in (None, "")) + " سال")
            elif kind in (C.AUD_JOB_SECTOR, C.AUD_JOB_INDUSTRY, C.AUD_JOB_CATEGORY,
                          C.AUD_JOB_TITLE, C.AUD_JOB_SPEC):
                parts.append(C.AUD_LABELS[kind] + ": " + "، ".join(str(v) for v in values))
        logic = node.get("logic")
        if len(parts) > 1 and depth == 0 and logic == "and":
            pass  # نمایش ساده کافی است

    walk(rules)
    return " و ".join(parts) or "بدون هدف"
