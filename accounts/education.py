"""پاداش تکمیل اطلاعات تحصیلی.

این سرویس فقط پس از ذخیرهٔ موفق فرم تحصیلات فراخوانی می‌شود و با پرچم داخل
extra_data و سقفِ «هر کاربر» (max_per_user قانون) از تکرار جلوگیری می‌کند.
میزان پاداش «به امتیاز» از قانون قابل ویرایش «education_completion» در «فهرست
امتیازها» پنل ادمین خوانده می‌شود؛ طبق دستورالعمل این پاداش‌ها فقط امتیازند و
هیچ سکه‌ای به کیف پول افزوده نمی‌شود.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

EDUCATION_COMPLETION_CODE = "education_completion"
# امتیاز پیش‌فرضِ fallback؛ میزان واقعی از فیلد میزانِ قانون (فهرست امتیازها) خوانده می‌شود
EDUCATION_COMPLETION_POINTS = 10


def grant_education_completion_reward(user, request=None):
    """برای ذخیرهٔ اطلاعات تحصیلی، امتیاز پاداش می‌دهد (فقط امتیاز؛ بدون سکه).

    اگر قانون پاداش وجود نداشته باشد/غیرفعال باشد، امتیاز هم پرداخت نمی‌شود تا
    تغییر میزان یا توقف پاداش کاملاً از پنل ادمین کنترل شود. سقفِ «هر کاربر»
    (max_per_user قانون) رعایت می‌شود.
    """
    from .models import Profile
    from .scoring import award, score_times
    from wallet.models import RewardRule

    profile = user.profile
    rule = RewardRule.get_active(EDUCATION_COMPLETION_CODE)
    if rule is None or rule.coins <= 0:
        return False
    try:
        reward_points = int(rule.coins or 0)
    except Exception:  # noqa: BLE001
        reward_points = 0
    if reward_points <= 0:
        return False

    try:
        with transaction.atomic():
            locked = Profile.objects.select_for_update().get(pk=profile.pk)
            extra = dict(locked.extra_data or {})
            # دو لایهٔ ضدِ تکرار: پرچمِ یک‌بارِ اجرا + سقفِ «هر کاربر» قانون
            if extra.get("education_completion_rewarded"):
                return False
            if rule.max_per_user and score_times(locked, EDUCATION_COMPLETION_CODE) >= rule.max_per_user:
                return False
            extra["education_completion_rewarded"] = True
            extra["education_completion_rewarded_at"] = timezone.now().isoformat()
            locked.extra_data = extra
            award(
                locked,
                reward_points,
                "پاداش تکمیل اطلاعات تحصیلی",
                commit=False,
                rule_code=EDUCATION_COMPLETION_CODE,
            )
    except Exception:  # noqa: BLE001 - پاداش نباید ذخیرهٔ تحصیلات را بشکند
        logger.exception("education completion reward failed for user %s", user.pk)
        return False
    return True
