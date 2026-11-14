import functools
import logging
from decimal import Decimal

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

logger = logging.getLogger(__name__)

from accounts.models import Profile

from .models import (
    MAX_TOTAL_BYTES,
    REACTION_EMOJIS,
    WATCH_SECONDS,
    MagazineAttachment,
    MagazinePost,
    MagazineReaction,
    MagazineTicket,
    MagazineUserState,
    kind_for_file,
)

ALLOWED_KINDS = {"image", "video", "audio"}
MAX_FILES_PER_POST = 10

KIND_LABELS = {
    "text": "مطلب متنی",
    "image": "تصویر",
    "video": "کلیپ ویدئویی",
    "audio": "آهنگ / صوتی",
    "mixed": "ترکیبی",
}


def member_required(view_func):
    """
    فقط کاربرانی به مجله دسترسی دارند که (۱) وارد شده‌اند و (۲) کد ملی ثبت‌شده دارند.
    وقتی کاربرِ مهمان با لینکِ اشتراک‌گذاری‌شده می‌آید، مقصدِ او در session نگه داشته
    می‌شود تا بعد از ورود (و ثبت کد ملی در صورت نیاز) به همان مطلب برگردد.
    """

    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            # لینک خارج از برنامه باز شده: بعد از ورود، به همین مقصد برمی‌گردد
            # (اولین مقصدِ ذخیره‌شده نگه داشته می‌شود تا لینکِ فوکوس از دست نرود)
            if not request.session.get("mag_next"):
                request.session["mag_next"] = request.get_full_path()
            return redirect("core:index")
        profile = request.user.profile
        if not profile.national_id:
            if not request.session.get("mag_next"):
                request.session["mag_next"] = request.get_full_path()
            messages.warning(
                request,
                "برای دسترسی به «مجله دانستنی‌ها» ابتدا کد ملی خود را در بخش "
                "«اطلاعات شخصی» پروفایل ثبت کنید.",
            )
            return redirect("core:profile")
        return view_func(request, profile, *args, **kwargs)

    return wrapper


def _mag_next_url(request):
    """مقصدِ امنِ ذخیره‌شده برای بازگشت پس از ورود/ثبت کد ملی (فقط مسیر داخلی)."""
    target = request.session.get("mag_next")
    if (
        isinstance(target, str)
        and target.startswith("/")
        and not target.startswith("//")
    ):
        return target
    request.session.pop("mag_next", None)
    return None


def _state_for(profile):
    state, _ = MagazineUserState.objects.get_or_create(profile=profile)
    return state


def _watch_remaining(state):
    """چند ثانیه تا امکان دریافت سکهٔ بعدی مانده است؟"""
    now = timezone.now()
    anchor = state.last_award_at or state.watch_started_at
    if anchor is None:
        return WATCH_SECONDS
    elapsed = (now - anchor).total_seconds()
    return max(0, WATCH_SECONDS - elapsed)


def _watch_rule():
    """قانون پاداش «ماندن/مطالعه در مجله» (عنوان و میزان را ادمین تعیین می‌کند)."""
    try:
        from wallet.models import RewardRule

        return RewardRule.get_active("magazine_watch")
    except Exception:  # noqa: BLE001 - دیتابیس قدیمی بدون جدول پاداش
        logger.exception("reward rule lookup failed")
        return None


def _wallet_coins(user):
    """موجودی سکهٔ واقعیِ کیف پول کاربر (پاداش‌ها همین‌جا جمع می‌شوند)."""
    try:
        from wallet.services import wallet_balance

        return wallet_balance(user)
    except Exception:  # noqa: BLE001
        return Decimal("0")


def _ticket_unread(user):
    return MagazineTicket.objects.filter(recipient=user, is_read=False).count()


def _reward_ticket(request, user, rule, points):
    """تیکت «پاداش امتیاز» برای کاربرِ دریافت‌کننده + مدیران (ادمین).

    نویسندهٔ تیکت، خودِ کاربر است (پس تیکت را در مرکز تیکت می‌بیند) و مدیرانِ
    فعال هم گیرنده می‌شوند تا جریان پاداش‌دهی قابل پیگیری باشد. شکست تیکت هرگز
    جریان امتیازدهی را متوقف نمی‌کند. متن طبق دستورالعمل فقط از امتیاز سخن
    می‌گوید (بدون سکه/کیف پول).
    """
    from tickets.services import create_ticket

    staff_ids = list(
        type(user).objects.filter(is_active=True, is_staff=True).values_list("pk", flat=True)
    )
    try:
        create_ticket(
            author=user,
            subject="پاداش امتیاز — مطالعه در مجله دانستنی‌ها",
            description=(
                f"بر اساس قانون «{rule.title}»، مبلغ {points} امتیاز به امتیاز کاربری "
                f"شما اضافه شد (سطح شما به‌روز شد).\n\n"
                f"واحد پاداش: {rule.unit_label or 'هر ۳۰ دقیقه مطالعه در مجله'}\n"
                f"تاریخ: {timezone.now():%Y/%m/%d %H:%M}"
            ),
            specific_user_ids=staff_ids or None,
            request=request,
            duplicate_window=0,
        )
    except Exception:  # noqa: BLE001 - تیکت نباید جریان پاداش را بشکند
        logger.exception("magazine reward ticket failed")


def _snippet(post, limit=90):
    """خلاصهٔ کوتاه مطلب برای نمایش در تیکت."""
    text = (post.text or "").strip()
    if text:
        flat = " ".join(text.split())
        return flat if len(flat) <= limit else flat[:limit].rstrip() + "…"
    label = KIND_LABELS.get(post.display_kind, "مطلب")
    if label == "مطلب متنی":
        return "مطلب بدون متن"
    return label


@member_required
@require_http_methods(["GET", "POST"])
def magazine_list(request, profile):
    """صفحهٔ کانال مجله (فهرست مطالب). پست‌کردن مطلب فقط برای ادمین (is_staff)."""

    if request.method == "POST":
        if not request.user.is_staff:
            messages.error(request, "فقط ادمین می‌تواند مطلب منتشر کند.")
            return redirect("magazine:list")

        text = (request.POST.get("text") or "").strip()
        files = request.FILES.getlist("files")

        # اعتبارسنجی: حداقل یک متن یا یک فایل
        if not text and not files:
            messages.error(request, "مطلب خالی است؛ متن بنویسید یا فایل پیوست کنید.")
            return redirect("magazine:list")
        if len(files) > MAX_FILES_PER_POST:
            messages.error(
                request, f"حداکثر {MAX_FILES_PER_POST} فایل برای هر مطلب مجاز است."
            )
            return redirect("magazine:list")

        # اعتبارسنجی حجم (زیر ۵۰ مگابایت در مجموع) و نوع فایل — پیش از ذخیره
        total = sum(f.size for f in files)
        if total >= MAX_TOTAL_BYTES:
            messages.error(
                request, "حجم کل فایل‌ها باید زیر ۵۰ مگابایت باشد."
            )
            return redirect("magazine:list")
        bad = []
        for f in files:
            kind = kind_for_file(f.name, f.content_type)
            if kind not in ALLOWED_KINDS or f.size <= 0:
                bad.append(f.name)
        if bad:
            messages.error(
                request,
                "فقط تصویر، کلیپ ویدئویی و آهنگ/صوتی مجاز است: "
                + "، ".join(bad[:3]),
            )
            return redirect("magazine:list")

        post = MagazinePost.objects.create(author=request.user, text=text)
        for f in files:
            MagazineAttachment.objects.create(
                post=post,
                file=f,
                kind=kind_for_file(f.name, f.content_type),
                name=f.name,
                size=f.size,
            )
        messages.success(
            request,
            f"مطلب «{KIND_LABELS.get(post.display_kind, 'مطلب')}» با موفقیت منتشر شد.",
        )
        return redirect("magazine:list")

    posts = MagazinePost.objects.prefetch_related("attachments", "reactions")
    my_emojis = set(
        MagazineReaction.objects.filter(user=request.user).values_list(
            "post_id", "emoji"
        )
    )
    list_base = request.build_absolute_uri(reverse("magazine:list"))
    enriched = []
    for post in posts:
        counts = post.emoji_counts()
        enriched.append(
            {
                "post": post,
                "kind_label": KIND_LABELS.get(post.display_kind, "مطلب"),
                # لینک دائمیِ همین مطلب (بعد از انتشار، برای همه در دسترس است)
                "permalink": f"{list_base}?focus={post.id}",
                "reactions": [
                    {
                        "emoji": e,
                        "count": counts.get(e, 0),
                        "active": (post.id, e) in my_emojis,
                    }
                    for e in REACTION_EMOJIS
                ],
            }
        )

    # فهرست اعضای دارای کد ملی (برای انتخاب آبشاری در دیالوگ فوروارد)
    forward_targets = [
        {
            "nid": p.national_id,
            "name": p.full_name,
            "mobile": p.user.mobile_number,
        }
        for p in Profile.objects.select_related("user")
        .filter(national_id__isnull=False)
        .exclude(user_id=request.user.id)
        .order_by("user__mobile_number")
    ]

    state = _state_for(profile)
    rule = _watch_rule()
    return render(
        request,
        "magazine/list.html",
        {
            "profile": profile,
            "is_admin": request.user.is_staff,
            "emojis": REACTION_EMOJIS,
            "posts": enriched,
            "state": state,
            "watch_remaining": int(_watch_remaining(state)),
            "watch_seconds": WATCH_SECONDS,
            "ticket_unread": _ticket_unread(request.user),
            "forward_targets": forward_targets,
            # پاداش «مطالعه در مجله»: میزان و عنوان از قانونِ ادمین (RewardRule) می‌آید
            "watch_rule": rule,
            "watch_reward_coins": int(rule.coins) if rule and rule.coins > 0 else 0,
            "watch_unit": (rule.unit_label or "") if rule else "",
            # موجودی واقعیِ کیف پول برای نمایش «سکه‌های شما» در هدر مجله
            "wallet_coins": _wallet_coins(profile.user),
        },
    )


@member_required
@require_POST
def react(request, profile):
    """ثبت/حذف واکنش ایموجی روی یک مطلب (مثل تلگرام، کلیک دوباره = برداشتن)."""
    try:
        post = MagazinePost.objects.get(id=request.POST.get("post_id"))
    except (MagazinePost.DoesNotExist, TypeError, ValueError):
        return JsonResponse({"status": "error", "message": "مطلب یافت نشد."})
    emoji = (request.POST.get("emoji") or "").strip()
    if emoji not in REACTION_EMOJIS:
        return JsonResponse({"status": "error", "message": "ایموجی نامعتبر است."})

    reaction = MagazineReaction.objects.filter(
        post=post, user=request.user, emoji=emoji
    ).first()
    if reaction:
        reaction.delete()
        active = False
    else:
        MagazineReaction.objects.create(post=post, user=request.user, emoji=emoji)
        active = True

    return JsonResponse(
        {
            "status": "ok",
            "active": active,
            "counts": post.emoji_counts(),
            "my": sorted(
                {
                    e
                    for (pid, e) in MagazineReaction.objects.filter(
                        user=request.user
                    ).values_list("post_id", "emoji")
                    if pid == post.id
                }
            ),
        }
    )


@member_required
@require_POST
def forward(request, profile):
    """فوروارد مطلب برای عضوی دیگر (با کد ملی گیرنده).
    برای گیرنده تیکتی با لینک همان مطلب ساخته می‌شود؛ چیزی کپی نمی‌شود.
    """
    try:
        post = MagazinePost.objects.get(id=request.POST.get("post_id"))
    except (MagazinePost.DoesNotExist, TypeError, ValueError):
        return JsonResponse({"status": "error", "message": "مطلب یافت نشد."})

    # کد ملی: ارقام فارسی/عربی هم پذیرفته و به لاتین تبدیل می‌شود
    raw = (request.POST.get("national_id") or "").strip()
    nid = (
        raw.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    )
    if len(nid) != 10 or not nid.isdigit():
        return JsonResponse(
            {"status": "error", "message": "کد ملی گیرنده باید دقیقاً ۱۰ رقم باشد."}
        )

    target = (
        Profile.objects.select_related("user")
        .filter(national_id=nid)
        .first()
    )
    if target is None:
        return JsonResponse(
            {"status": "error", "message": "عضوی با این کد ملی در حبیب‌هاب یافت نشد."}
        )
    if target.user_id == request.user.id:
        return JsonResponse(
            {"status": "error", "message": "نمی‌توانید مطلب را برای خودتان فوروارد کنید."}
        )

    MagazineTicket.objects.create(
        recipient=target.user, sender=request.user, post=post
    )
    return JsonResponse(
        {
            "status": "ok",
            "recipient": target.full_name,
            "message": f"مطلب برای «{target.full_name}» ارسال شد (به‌صورت تیکت).",
        }
    )


@member_required
def inbox(request, profile):
    """تیکت‌های مجله — هماهنگ با مرکز تیکت (tickets:center?box=magazine)."""
    return redirect("tickets:center")


@member_required
@require_GET
def ticket_open(request, profile, ticket_id):
    """بازکردن تیکت: خوانده‌شده علامت می‌خورد و کاربر به همان مطلب فوکوس می‌شود."""
    ticket = get_object_or_404(
        MagazineTicket, id=ticket_id, recipient=request.user
    )
    if not ticket.is_read:
        ticket.is_read = True
        ticket.save(update_fields=["is_read"])
    return redirect(reverse("magazine:list") + f"?focus={ticket.post_id}")


@member_required
@require_POST
def tickets_read_all(request, profile):
    """علامت‌گذاری همهٔ تیکت‌ها به‌عنوان خوانده‌شده."""
    MagazineTicket.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True)
    return redirect("magazine:inbox")


@member_required
@require_POST
def watch_start(request, profile):
    """آغاز/همگام‌سازی تایمر ۳۰ دقیقه‌ای هنگام باز شدن صفحهٔ مجله."""
    state = _state_for(profile)
    now = timezone.now()
    if state.last_award_at is not None:
        since_award = (now - state.last_award_at).total_seconds()
    else:
        since_award = WATCH_SECONDS  # هنوز جایزه‌ای نداده → چرخهٔ تازه مجاز است

    if since_award < WATCH_SECONDS:
        # چرخه‌ای در جریان است (مثلاً از تب دیگر)؛ شروع را جابه‌جا نکن
        if state.watch_started_at is None:
            state.watch_started_at = now
    else:
        state.watch_started_at = now  # چرخهٔ تازهٔ ۳۰ دقیقه
    state.save(update_fields=["watch_started_at", "updated_at"])

    return JsonResponse(
        {"status": "ok", "remaining": int(_watch_remaining(state))}
    )


@member_required
@require_POST
def watch_award(request, profile):
    """پاداش امتیاز پس از ماندن ۳۰ دقیقه در صفحهٔ مجله (با کنترل سمت سرور).

    میزان پاداش ثابت نیست؛ از قانون «magazine_watch» در جدول RewardRule (فهرست
    امتیازها) خوانده می‌شود که ادمین در «پنل مدیریت ← فهرست امتیازها» عنوان و
    میزان آن را تعیین می‌کند. طبق دستورالعمل، این پاداش فقط امتیاز کاربری است
    (سطح به‌روز می‌شود) و هیچ سکه‌ای به کیف پول افزوده نمی‌شود؛ سقفِ «هر کاربر»
    قانون (max_per_user) هم رعایت می‌شود. شمارندهٔ داخلی حالت مجله برای آمار
    همگام می‌ماند.
    """
    state = _state_for(profile)
    now = timezone.now()

    def wait_response():
        return JsonResponse(
            {
                "status": "wait",
                "coins": str(_wallet_coins(profile.user)),
                "remaining": int(_watch_remaining(state)),
            }
        )

    # شرط ۱: حداقل ۳۰ دقیقه از آخرین جایزه گذشته باشد (جلوگیری از سواستفاده)
    if state.last_award_at is not None:
        since_award = (now - state.last_award_at).total_seconds()
        if since_award < WATCH_SECONDS:
            return wait_response()

    # شرط ۲: کاربر واقعاً از آغاز باز شدن صفحه، ۳۰ دقیقه در صفحه بوده است
    if state.watch_started_at is None:
        state.watch_started_at = now
        state.save(update_fields=["watch_started_at", "updated_at"])
        return wait_response()
    since_start = (now - state.watch_started_at).total_seconds()
    if since_start < WATCH_SECONDS:
        return wait_response()

    rule = _watch_rule()
    points = int(rule.coins) if rule and rule.coins > 0 else 0
    state.last_award_at = now
    state.watch_started_at = now  # چرخهٔ بعدی از همین لحظه
    state.save(update_fields=["last_award_at", "watch_started_at", "updated_at"])

    awarded = 0
    if points > 0:
        # امتیاز کاربری (دفترچهٔ امتیاز در پروفایل) — فقط امتیاز؛ بدون سکه
        try:
            from accounts.scoring import award, score_times

            # سقفِ «هر کاربر» طبق فهرست امتیازها
            if rule.max_per_user and score_times(profile, "magazine_watch") >= rule.max_per_user:
                awarded = 0
            else:
                award(profile, points, "پاداش ماندن و مطالعه در مجله", rule_code="magazine_watch")
                awarded = points
                # تیکت برای دریافت‌کننده + مدیران
                _reward_ticket(request, profile.user, rule, points)
        except Exception:  # noqa: BLE001 - امتیاز مجله نباید جریان را بشکند
            logger.exception("magazine watch reward failed")

    return JsonResponse(
        {
            "status": "ok",
            "coins": str(_wallet_coins(profile.user)),
            "remaining": WATCH_SECONDS,
            "awarded": awarded,
            "title": (rule.title if rule else "") or "ماندن در مجله",
        }
    )
