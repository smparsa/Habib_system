"""سرویس «پاداش تکمیل اطلاعات شخصی و معرفی» — وقتی کاربر اطلاعات شخصی خود (از جمله
کد ملی) را در پروفایل تکمیل کند:

- به خودِ کاربر امتیاز کاربری پاداش می‌رسد (قانون «profile_completion» در
  RewardRule / «فهرست امتیازها» پنل ادمین) — حتی اگر معرف نداشته باشد؛ با رعایت
  سقفِ max_per_user همان قانون (پیش‌فرض: فقط یک‌بار برای هر کاربر).
- اگر کاربر هنگام ورود با کد ملیِ یک عضو ثبت‌نام کرده باشد (معرف دارد)، به معرف هم
  امتیاز پاداش می‌رسد (قانون «referral») — یک‌بار برای هر معرفی‌شده و با رعایت
  سقفِ تعیین‌شده توسط ادمین برای معرف.
- طبق دستورالعمل، پاداش‌های «فهرست امتیازها» فقط امتیازند و هیچ سکه‌ای از/به کیف
  پول جابه‌جا نمی‌شود؛ سطح کاربر از روی امتیاز به‌روز می‌شود.

برای کاربر، معرف و مدیران (ادمین) هرکدام جداگانه تیکت ساخته می‌شود. میزان هر
پاداش (به امتیاز) از قانون RewardRule خوانده می‌شود که ادمین در «پنل مدیریت ←
فهرست امتیازها» عنوان و میزان آن را تعیین می‌کند. پرچم‌های یک‌بارِ اجرا در
extra_data هم حفظ شده‌اند تا هیچ مسیری پاداش تکراری ندهد."""

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)

PROFILE_COMPLETION_CODE = "profile_completion"
REFERRAL_CODE = "referral"

# امتیاز پیش‌فرضِ fallback در نبودِ قانون/دیتابیس؛ مقدار واقعی همیشه از فیلد
# «امتیاز» همان قانون در «فهرست امتیازها» (RewardRule.coins) خوانده می‌شود.
COMPLETION_POINTS = 10
REFERRAL_POINTS = 10


def _get_rule(code):
    """قانونِ پاداشِ فعال با کد داده‌شده یا None (جدول پاداش موجود نباشد)."""
    from wallet.models import RewardRule

    try:
        return RewardRule.get_active(code)
    except Exception:  # noqa: BLE001 - جدول پاداش در دیتابیس قدیمی موجود نباشد
        logger.exception("reward rule table unavailable")
        return None


def _resolve_referrer(user, referrer_nid):
    """کاربرِ معرف (صاحب همان کد ملی ثبت‌شده در پروفایل‌ها) یا None در نبود/نامعتبر بودن."""
    from .models import Profile

    referrer_profile = (
        Profile.objects.select_related("user").filter(national_id=referrer_nid).first()
    )
    if referrer_profile is None:
        return None
    referrer = referrer_profile.user
    if referrer.id == user.id or not referrer.is_active:
        return None
    return referrer


def _rule_points(rule, default):
    """میزان پاداشِ «به امتیاز» طبق فهرست امتیازها؛ فیلد coins همان میزان امتیاز است."""
    try:
        value = int(rule.coins or 0)
    except Exception:  # noqa: BLE001
        value = 0
    return value if value > 0 else default


def grant_personal_info_rewards(user, request=None):
    """پس از تکمیل اطلاعات شخصی، امتیاز کاربری به خودِ کاربر (با سقف) و در صورت
    داشتن معرفِ معتبر، به معرف هم پرداخت می‌شود و برای کاربر/معرف/ادمین هرکدام
    جداگانه تیکت ساخته می‌شود.

    شرایط اجرا (همه): پروفایل کاربر کد ملی ثبت کرده باشد؛ قانونِ فعال موجود
    باشد؛ سقفِ max_per_user آن قانون برای همین کاربر پر نشده باشد و پرچمِ
    یک‌بارِ اجرا (extra_data) هم گذاشته نشده باشد — دو لایهٔ مستقل ضدِ تکرار.
    پاداش فقط امتیاز است: طبق دستورالعمل «فهرست امتیازها»، هیچ سکه‌ای به کیف
    پول افزوده نمی‌شود. خروجی: True در صورت اعطا، یا None. شکست هرگز ذخیرهٔ
    پروفایل کاربر را نمی‌شکند (خطاها لاگ و بی‌صدا رد می‌شوند).
    """
    profile = user.profile
    if not (profile.national_id or "").strip():
        return None

    from django.db import transaction

    from .scoring import award as award_score, score_times

    completion_rule = _get_rule(PROFILE_COMPLETION_CODE)
    referrer_nid = (user.referrer_national_id or "").strip()
    referrer = _resolve_referrer(user, referrer_nid) if referrer_nid else None
    referral_rule = _get_rule(REFERRAL_CODE) if referrer is not None else None

    # میزان هر پاداش «به امتیاز» از همان فیلد میزانِ قانون خوانده می‌شود
    completion_points = _rule_points(completion_rule, COMPLETION_POINTS)
    referral_points = _rule_points(referral_rule, REFERRAL_POINTS) if referral_rule else 0

    user_awarded = False
    referrer_awarded = False
    locked_referrer = None
    try:
        with transaction.atomic():
            # قفل صف پروفایلِ کاربر تا دو درخواست هم‌زمان دوبار پاداش ندهند
            locked = type(profile).objects.select_for_update().get(pk=profile.pk)
            locked_extra = dict(locked.extra_data or {})

            # سقفِ «هر کاربر» طبق فهرست امتیازها: اگر پر شده باشد، پاداش پرداخت
            # نمی‌شود. پرچمِ یک‌بارِ اجرا همیشه بررسی می‌شود (حتی وقتی ادمین سقف را
            # تنظیم نکرده باشد) تا پاداش فقط یک‌بار پرداخت شود؛ سقفِ تعیین‌شده
            # (شمارش تاریخچهٔ امتیاز) محدودیتِ اضافهٔ بعدی است.
            completion_capped = bool(
                completion_rule is not None
                and (
                    locked_extra.get("profile_completion_rewarded")
                    or (
                        completion_rule.max_per_user
                        and score_times(locked, PROFILE_COMPLETION_CODE)
                        >= completion_rule.max_per_user
                    )
                )
            )
            if completion_rule is not None and completion_points > 0 and not completion_capped:
                locked_extra["profile_completion_rewarded"] = True
                locked_extra["profile_completion_rewarded_at"] = timezone.now().isoformat()
                # پرچم‌ها قبل از award_score روی نمونهٔ قفل‌شده بنشینند تا در
                # همان ذخیرهٔ امتیاز (commit=False) هم‌زمان نوشته شوند
                locked.extra_data = locked_extra
                award_score(
                    locked,
                    completion_points,
                    "پاداش تکمیل اطلاعات شخصی",
                    commit=False,
                    rule_code=PROFILE_COMPLETION_CODE,
                )
                user_awarded = True

            referrer_capped = False
            if (
                referral_rule is not None
                and referral_rule.max_per_user
                and referrer is not None
            ):
                locked_referrer = (
                    type(profile).objects.select_for_update().get(pk=referrer.profile.pk)
                )
                referrer_capped = bool(
                    score_times(locked_referrer, REFERRAL_CODE)
                    >= referral_rule.max_per_user
                    or locked_extra.get("referral_rewarded")
                )

            if (
                not locked_extra.get("referral_rewarded")
                and referrer is not None
                and referral_rule is not None
                and referral_points > 0
                and not referrer_capped
            ):
                if locked_referrer is None:
                    locked_referrer = (
                        type(profile).objects.select_for_update().get(pk=referrer.profile.pk)
                    )
                locked_extra["referral_rewarded"] = True
                locked_extra["referral_rewarded_at"] = timezone.now().isoformat()
                locked_extra["referral_rewarder"] = str(referrer_nid)
                locked.extra_data = locked_extra
                award_score(
                    locked_referrer,
                    referral_points,
                    "پاداش معرفی کاربر جدید",
                    commit=False,
                    rule_code=REFERRAL_CODE,
                )
                referrer_awarded = True

            if not (user_awarded or referrer_awarded):
                return None  # هیچ پاداشی قابل پرداخت نبود (سقف/تکرار)

            # اگر امتیازِ کاربر award نشده بود، پرچم‌های ذخیره‌شده در extra_data
            # اینجا نوشته می‌شوند (در مسیر award_score همین ذخیره انجام شده است).
            locked.save(update_fields=["extra_data", "updated_at"])
    except Exception:  # noqa: BLE001
        logger.exception("personal info reward failed for user %s", user.pk)
        return None

    referrer_capped = referrer_capped if referrer is not None else False
    _notify(
        request, user, referrer,
        completion_rule=completion_rule,
        referral_rule=referral_rule,
        user_awarded=user_awarded,
        referrer_awarded=referrer_awarded,
        referrer_capped=referrer_capped,
        completion_points=completion_points,
        referral_points=referral_points,
    )
    return True


def _ticket(request, author, subject, body, recipient_id=None, staff_ids=None):
    """ساخت یک تیکتِ اطلاع‌رسانی؛ شکست آن هرگز جریان پاداش را نمی‌شکند.

    recipient_id → تیکتِ اختصاصی برای همان کاربر؛ staff_ids → تیکتِ گزارش به
    کارکنان/مدیران. فرستنده (author) همیشه گیرندهٔ تیکت می‌شود.
    """
    from tickets.services import create_ticket

    try:
        ticket, _ = create_ticket(
            author=author,
            subject=subject,
            description=body,
            specific_user_ids=(
                [recipient_id] if recipient_id is not None else (staff_ids or None)
            ),
            request=request,
            duplicate_window=0,
        )
        return ticket.pk
    except Exception:  # noqa: BLE001 - تیکت نباید جریان پاداش را بشکند
        logger.exception("reward ticket failed: %s", subject)
        return None


def _notify(request, referred_user, referrer, *, completion_rule, referral_rule,
            user_awarded, referrer_awarded, referrer_capped,
            completion_points=COMPLETION_POINTS, referral_points=REFERRAL_POINTS):
    """سه تیکتِ جداگانه: به کاربر، به معرف و به مدیران (ادمین) + ثبت رویداد حسابرسی.

    هر تیکت جداگانه ساخته می‌شود تا هر طرف فقط تیکتِ مخصوص خودش را دریافت کند
    (کاربر ← پاداش تکمیل اطلاعات شخصی، معرف ← پاداش معرفی، مدیران ← گزارش هر دو).
    """
    from django.contrib.auth import get_user_model
    from tickets.services import audit

    name = referred_user.profile.full_name or referred_user.mobile_number
    when = f"{timezone.now():%Y/%m/%d %H:%M}"
    ticket_ids = []

    # ۱) تیکت به خودِ کاربر — «دریافت امتیاز» بابت تکمیل اطلاعات شخصی
    if user_awarded:
        user_body = (
            f"اطلاعات شخصی شما (کد ملی: {referred_user.profile.national_id}) با موفقیت "
            f"ثبت شد.\n\n"
            f"بر اساس قانون «{completion_rule.title}»، مبلغ {completion_points} امتیاز "
            f"به امتیاز کاربری شما اضافه شد (سطح شما به‌روز شد).\n"
            f"واحد پاداش: {completion_rule.unit_label or 'تکمیل اطلاعات شخصی'}\n"
            f"تاریخ: {when}"
        )
        ticket_ids.append(
            _ticket(request, referred_user,
                    "دریافت امتیاز پاداش تکمیل اطلاعات شخصی", user_body,
                    recipient_id=referred_user.pk)
        )

    # ۲) تیکت به معرف — «دریافت امتیاز» بابت معرفی این کاربر
    if referrer_awarded:
        referrer_body = (
            f"کاربر «{name}» (شمارهٔ موبایل: {referred_user.mobile_number}) که با "
            f"کد ملی شما ثبت‌نام کرده بود، اطلاعات شخصی خود (کد ملی: "
            f"{referred_user.profile.national_id}) را در «{when}» تکمیل کرد.\n\n"
            f"بر اساس قانون «{referral_rule.title}»، مبلغ {referral_points} امتیاز "
            f"به امتیاز کاربری شما اضافه شد (سطح شما به‌روز شد).\n"
            f"واحد پاداش: {referral_rule.unit_label or 'معرفی یک کاربر'}"
        )
        ticket_ids.append(
            _ticket(request, referred_user, "پاداش معرفی کاربر جدید", referrer_body,
                    recipient_id=referrer.pk)
        )

    # ۳) تیکت به مدیران (ادمین) — گزارش هر دو پرداخت
    admin_body = (
        f"پاداش تکمیل اطلاعات شخصی و معرفی:\n\n"
        f"کاربر: «{name}» (شمارهٔ موبایل: {referred_user.mobile_number}، "
        f"کد ملی: {referred_user.profile.national_id})\n"
    )
    if user_awarded:
        admin_body += (
            f"پاداش کاربر: {completion_points} امتیاز "
            f"(قانون: «{completion_rule.title}»)\n"
        )
    if referrer_awarded:
        ref_label = referrer.profile.full_name or referrer.mobile_number
        admin_body += (
            f"پاداش معرف «{ref_label}» (شمارهٔ موبایل: {referrer.mobile_number}): "
            f"{referral_points} امتیاز "
            f"(قانون: «{referral_rule.title}»)\n"
        )
    elif referrer is not None and referrer_capped:
        admin_body += (
            f"معرف «{referrer.mobile_number}» به سقف پاداش رسیده بود و پاداشی نگرفت.\n"
        )
    admin_body += f"تاریخ: {when}"

    staff_ids = list(
        get_user_model().objects.filter(is_active=True, is_staff=True)
        .values_list("pk", flat=True)
    )
    ticket_ids.append(
        _ticket(request, referred_user,
                "گزارش پاداش تکمیل اطلاعات شخصی و معرفی", admin_body,
                staff_ids=staff_ids)
    )

    try:
        audit(referred_user, "personal_info.rewarded", "User", referred_user.pk,
              request=request,
              meta={
                  "referrer": referrer.pk if referrer else None,
                  "completion": completion_rule.code if user_awarded else None,
                  "referral": referral_rule.code if referrer_awarded else None,
                  "referrer_capped": bool(referrer_capped),
                  "tickets": ticket_ids,
              })
    except Exception:  # noqa: BLE001
        logger.exception("personal info reward audit failed")