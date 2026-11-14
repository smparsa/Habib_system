"""امتیاز و سطح کاربر — سرویس سادهٔ بدون وابستگی به ماژول تیکت.

سطح از روی امتیاز محاسبه می‌شود (نردبان آستانه). این ماژول نقطهٔ اتصال
(interface) سرویس‌های امتیازدهی سایر ماژول‌ها (مثل تیکت) است؛ به‌علاوه، طبق
«تعرفه امتیازها» معادل سکهٔ امتیازهای جدید (نرخ: «ارزش هر سکه (امتیاز)») نیز
به‌صورت خودکار به کیف پول کاربر تجمیع می‌شود.
"""

import logging

from django.db import transaction

logger = logging.getLogger(__name__)

# آستانه‌های سطح: سطح k ام وقتی امتیاز >= LEVELS[k-1][0] باشد
LEVELS = (
    (0, "کاربر جدید"),
    (100, "عضو فعال"),
    (300, "عضو همراه"),
    (700, "عضو حرفه‌ای"),
    (1500, "کارشناس"),
    (3000, "متخصص"),
    (6000, "کارشناس ارشد"),
    (12000, "حرفه‌ای طلایی"),
)


def level_for_score(score):
    level = 1
    for cutoff, _name in LEVELS:
        if score >= cutoff:
            level += 1
        else:
            break
    return level


def level_label(level):
    idx = max(0, min(level - 1, len(LEVELS) - 1))
    return LEVELS[idx][1]


def award(profile, points, reason="", commit=True, rule_code=""):
    """افزودن امتیاز به پروفایل و همگام‌سازی سطح. ذخیرهٔ log در extra_data است.

    rule_code: کد سرفصلِ «تعرفه امتیازها» در پنل ادمین (RewardRule.code) که در
    تاریخچهٔ امتیاز ذخیره می‌شود تا «سقف هر کاربر» هر سرفصل قابل شمارش باشد
    (score_times). به‌علاوه، معادل سکهٔ امتیازهای جدید بر اساس «ارزش هر سکه
    (امتیاز)» به‌صورت خودکار به کیف پول کاربر افزوده و با موجودی قبلی تجمیع
    می‌شود (امتیازِ سطح کاربری حفظ می‌شود).
    """
    if not points:
        return None
    score = (profile.user_score or 0) + points
    level = level_for_score(score)

    def _do():
        # پایهٔ extra_data از رکورد تازهٔ دیتابیس خوانده می‌شود تا نوشتنِ تاریخچه،
        # مقدارِ به‌روزِ آن (مثلاً آبخست تبدیل امتیاز به سکه: points_converted)
        # را از بین نبرد؛ خودِ نمونهٔ ورودی هم به‌روز می‌شود (user_score/سطح).
        fresh = type(profile).objects.filter(pk=profile.pk).first()
        base = (fresh.extra_data if fresh is not None else None) or profile.extra_data or {}
        history = list(base.get("score_history", []))
        history.append({
            "pts": points, "reason": reason or "", "after": score,
            **({"rule": rule_code} if rule_code else {}),
        })
        profile.extra_data = {**base, "score_history": history[-200:]}
        profile.user_score = score
        profile.user_level = level
        profile.save(update_fields=["user_score", "user_level", "extra_data", "updated_at"])

    def _convert_points_to_coins():
        """تجمیع معادل سکهٔ امتیازهای جدید در کیف پول (طبق تعرفه امتیازها)."""
        try:
            from wallet.services import convert_unconverted_points

            convert_unconverted_points(profile)
        except Exception:  # خطای تبدیل نباید امتیازدهی/سطح کاربر را متوقف کند
            logger.exception(
                "تبدیل امتیاز به سکه برای پروفایل %s انجام نشد", profile.pk
            )

    if commit:
        transaction.on_commit(_do)
        transaction.on_commit(_convert_points_to_coins)
    else:
        _do()
        _convert_points_to_coins()
    return {"score": score, "level": level}


def score_times(profile, rule_code):
    """تعداد دفعاتی که کاربر پاداشِ قانون داده‌شده را گرفته است (برای سقف هر کاربر).

    شمارش از تاریخچهٔ امتیاز (score_history) انجام می‌شود؛ رکوردهای بدون «rule"
    (قدیمی) در شمارش نمی‌آیند.
    """
    if not rule_code:
        return 0
    history = (profile.extra_data or {}).get("score_history", [])
    return sum(1 for row in history if isinstance(row, dict) and row.get("rule") == rule_code)
