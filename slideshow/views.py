"""ماژول کاربری «اسلایدشوی آمار داشبورد» — مشابه ماژول تبلیغات.

گردش کار (کپی‌شدن الگوی ``ads``):
  ۱. کاربر از ``/slideshow/`` اسلاید ثبت می‌کند: تصویر + عنوان/توضیح/لینک +
     بازهٔ نمایش (تقویم شمسی، ساعت واحد) + باکس(های) چهارگانهٔ آمار داشبورد.
  ۲. هزینه = تعداد روزها × تعداد باکس‌های انتخابی × تعرفهٔ ۲۴ ساعتهٔ
     «هزینه‌های سکهٔ ماژول‌ها» (کد اختصاصی ``stat_slide_submission``؛ اگر ادمین
     تعریفش نکرده باشد، از تعرفهٔ تبلیغات ``ad_submission`` پیروی می‌شود).
  ۳. اسلاید با وضعیت «در انتظار تأیید» ذخیره می‌شود؛ پس از تأیید ادمین در
     باکس(های) انتخابیِ داشبورد پخش می‌شود.
  ۴. باکس‌ها ظرفیت‌دارند: حداکثر ۱۰ اسلاید در هر باکس (اعتبارسنجی در فرم).
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from adminpanel.forms import StatSlideUserForm
from adminpanel.models import AD_STATUS_PENDING, STAT_SLIDE_MAX_PER_BOX, StatSlide, StatSlideBox
from wallet.models import FeatureCost
from wallet.services import (
    WalletError, _audit, charge_module, charge_module_days, refund_module_charge, wallet_balance,
)

from ads.approvals import open_approval_request, reject_fee_percent

from . import builder

# کد تعرفهٔ اختصاصی این ماژول؛ تعریفش اختیاری است و پیش‌فرض به تعرفهٔ تبلیغات
# (ad_submission) برمی‌گردد تا ادمین نیازی به تنظیم اولیه نداشته باشد.
COST_CODE = "stat_slide_submission"
FALLBACK_COST_CODE = "ad_submission"

# هزینهٔ دومِ اسلایدشو: «ساخت اسلایدشو» (Create Slideshow) — تبدیل تصویرِ ناسازگار به بنر
# مناسب؛ مبلغ آن را ادمین در «هزینه‌های سکهٔ ماژول‌ها» با همین کد تعریف/تغییر می‌دهد.
CREATE_COST_CODE = "stat_slide_create"


def _cost():
    """تعرفهٔ فعال ثبت اسلاید: اختصاصی این ماژول، وگرنه تعرفهٔ تبلیغات."""
    cost = FeatureCost.objects.filter(code=COST_CODE, is_active=True).first()
    if cost is None:
        cost = FeatureCost.objects.filter(code=FALLBACK_COST_CODE, is_active=True).first()
    return cost


def _create_cost():
    """تعرفهٔ فعال «ساخت اسلایدشو» (مبلغ مثبت) یا None؛ تا ادمین فعالش نکند، دکمه نمایش داده نمی‌شود."""
    cost = FeatureCost.objects.filter(code=CREATE_COST_CODE, is_active=True).first()
    return cost if cost is not None and cost.coins > 0 else None


def _effective_code(cost):
    return COST_CODE if cost and cost.code == COST_CODE else FALLBACK_COST_CODE


def boxes_capacity():
    """ظرفیت «اسلایدشو A» (تنها باکس): تعداد اسلاید جای‌گیر از سقف مجاز (فهرست تک‌عضوی)."""
    out = []
    the_box = StatSlideBox.the_box()
    for box in ([the_box] if the_box else []):
        if not box.is_active:
            in_box = 0
        else:
            in_box = min(STAT_SLIDE_MAX_PER_BOX, StatSlide.slides_in_box(box.code).count())
        out.append({
            "obj": box,
            "in_box": in_box,
            "capacity": STAT_SLIDE_MAX_PER_BOX,
        })
    return out


@login_required(login_url="core:index")
def home(request):
    """ثبت و فهرست اسلایدها اکنون بخشی از ماژول «تبلیغات» است؛ لینک‌های قدیمی هدایت می‌شوند."""
    return redirect("ads:home")


@login_required(login_url="core:index")
def _renew_target(request, renew_id):
    """اسلاید منقضی‌شدهٔ قابل‌تمدید برای کاربر جاری (در صورت درخواست ``?renew=<id>``).

    فقط اسلاید متعلق به خود کاربر و با «تمام شدن بازهٔ نمایش» ``is_expired``
    پذیرفته می‌شود؛ اسلاید در حال پخش/در انتظار/ردشده قابل تمدید نیست.
    """
    if not renew_id:
        return None
    try:
        slide = request.user.stat_slides.get(pk=renew_id)
    except (StatSlide.DoesNotExist, ValueError, TypeError):
        return None
    return slide if slide.is_expired else None


def _renew_days(slide):
    """مدتِ اسلاید قبلی به «روز» (حداقل ۱) — مبنای بازهٔ پیشنهادیِ تمدید."""
    try:
        seconds = (slide.show_until - slide.show_from).total_seconds()
    except (TypeError, AttributeError):
        return 1
    return max(1, round(seconds / 86400))


def _suggested_period(slide):
    """بازهٔ پیشنهادیِ تمدید: «شروع از همین الان» + «همان مدتِ قبلی».

    ساعتِ شروع/پایان (یکسان) = اکنون، گردشده به ۵ دقیقهٔ بعد؛ تاریخ پایان = تاریخ شروع + همان تعداد
    روز (هزینه = روز × تعرفه، پس مبلغ همان دورهٔ قبلی است). کاربر می‌تواند همه را عوض کند؛
    برای زمان‌های محلی (Asia/Tehran) از ``timezone.localtime`` استفاده می‌شود.
    """
    from datetime import timedelta
    from django.utils import timezone

    start = timezone.localtime(timezone.now()).replace(second=0, microsecond=0) + timedelta(minutes=5)
    start += timedelta(minutes=(-start.minute) % 5)          # گرد به مضرب ۵ دقیقه (رو به بالا)
    end_day = start.date() + timedelta(days=_renew_days(slide))
    return {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end_day.strftime("%Y-%m-%d"),
        "ad_time": start.strftime("%H:%M"),
    }


def _slide_initial(slide):
    """مقادیر پیش‌پُرِ فرم تمدید: متن/لینک از اسلاید قبلی + بازهٔ پیشنهادی (از همین الان، همان مدت)."""
    initial = {
        "title": slide.title,
        "description": slide.description,
        "link_url": slide.link_url,
    }
    initial.update(_suggested_period(slide))
    return initial


@login_required(login_url="core:index")
@require_POST
def delete_slide(request, pk):
    """حذف کاملِ اسلایدِ خودِ کاربر (فقط اسلایدِ تمام‌شده/ردشده).

    رکورد (و اتصال به اسلایدشو) پاک می‌شود؛ فایل تصویر فقط وقتی پاک می‌شود که هیچ اسلاید دیگری
    (مثلاً نسخهٔ «تمدید‌شده» که از همان تصویر استفاده می‌کند) به آن اشاره نکند. رویداد در لاگ
    حسابرسی ثبت می‌شود. سکه‌ای بازگردانده نمی‌شود (هزینه برای نمایشِ انجام‌شده بوده است).
    """
    slide = get_object_or_404(StatSlide, pk=pk, advertiser=request.user)   # اسلاید دیگران = ۴۰۴
    if not slide.user_can_delete:
        messages.error(
            request,
            "فقط اسلایدهای تمام‌شده یا ردشده قابل حذف‌اند؛ اسلایدِ در انتظار تأیید یا در حال پخش را نمی‌توان حذف کرد.",
        )
        return redirect("ads:home")
    title, status, paid = slide.title, slide.status, slide.coins_paid
    image_name, storage = slide.image.name, slide.image.storage
    with transaction.atomic():
        slide.delete()
    if image_name and not StatSlide.objects.filter(image=image_name).exists():
        try:
            storage.delete(image_name)
        except Exception:  # noqa: BLE001 - نبودنِ فایل مانع حذف رکورد نیست
            pass
    _audit(request, request.user, "slideshow.slide.deleted", "StatSlide", pk,
           meta={"title": title, "status": status, "coins_paid": str(paid)})
    messages.success(request, f"اسلاید «{title}» برای همیشه حذف شد.")
    return redirect("ads:home")


@login_required(login_url="core:index")
@require_POST
def build_preview(request):
    """«ساخت اسلایدشو»: کسر هزینهٔ ساخت، ساخت بنر ۲۴۰۰×۶۰۰ از تصویر کاربر و بازگرداندن پیش‌نمایش.

    ترتیب: ۱) بررسی تعرفه و تصویر (پیش از کسر) ۲) کسر هزینه از کیف پول (+ تیکت مالی برای
    کاربر و مدیران) ۳) ساخت ۴) ذخیرهٔ موقت و ارسال توکن/آدرس پیش‌نمایش. اگر ساخت پس از کسر
    ناموفق شود، هزینه کامل بازگردانده می‌شود. کاربر پس از دیدن پیش‌نمایش «تأیید» می‌کند؛
    تصویر ساخته‌شده فقط با ثبتِ نهایی (و هزینهٔ ثبت و تأیید مدیر) نمایش داده می‌شود.
    """
    cost = _create_cost()
    if cost is None:
        return JsonResponse(
            {"ok": False, "error": "ساخت اسلایدشو در حال حاضر فعال نیست."}, status=400)
    try:
        src = builder.inspect_image(request.FILES.get("image"))
    except builder.BuildError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    try:
        charge_module(request.user, CREATE_COST_CODE, request=request,
                      note="ساخت اسلایدشو (Create Slideshow)")
    except WalletError as exc:
        return JsonResponse({"ok": False, "error": str(exc), "wallet": True}, status=402)
    try:
        data = builder.build_banner(src)
    except Exception:  # noqa: BLE001 - پس از کسر، هر خطای ساخت = بازگشت کامل هزینه
        refund_module_charge(
            request.user, cost.coins, fee_percent=0, ref_code=CREATE_COST_CODE,
            subject="بازگشت هزینهٔ ساخت اسلایدشو",
            note="ساخت اسلایدشو ناموفق بود؛ هزینه کامل بازگردانده شد.", request=request,
        )
        return JsonResponse(
            {"ok": False, "error": "ساخت اسلایدشو ناموفق بود؛ هزینه کامل به کیف پول بازگشت."},
            status=500)
    token = builder.save_temp(request.user, data)
    return JsonResponse({
        "ok": True, "token": token, "url": builder.temp_url(request.user, token),
        "cost": str(cost.coins), "balance": str(wallet_balance(request.user)),
    })


@login_required(login_url="core:index")
def create(request):
    """ثبت اسلاید جدید / «تمدید» اسلاید منقضی + کسر هزینهٔ سکه.

    حالت عادی: کاربر «تاریخ شروع/پایان» (تقویم شمسی با ساعت واحد) را انتخاب
    می‌کند؛ هزینه = روزها × تعرفهٔ ۲۴ ساعته در یک تراکنش واحد کسر می‌شود؛ در
    صورت شکست، اسلاید ثبت نمی‌شود. اسلایدشو فقط یک باکس دارد («اسلایدشو A»).
    اسلاید ثبت‌شده «در انتظار تأیید» است و پس از تأییدِ ادمین پخش می‌شود.

    حالت تمدید: ``?renew=<id>`` — برای اسلایدِ «تأییدشده»ای که بازهٔ نمایشش
    تمام شده، فرم با عنوان/توضیح/لینک و تصویر اسلاید قبلی پیش‌پُر
    می‌شود؛ کاربر فقط تاریخ جدید را انتخاب و هزینهٔ دورهٔ جدید را می‌پردازد.
    همان اسلایدِ قبلی دست‌نخورده در تاریخچه می‌ماند و رکوردِ جدید «در انتظار
    تأیید» ثبت می‌شود.
    """
    cost = _cost()
    renew_slide = _renew_target(request, request.GET.get("renew") or request.POST.get("renew_ref"))
    initial = _slide_initial(renew_slide) if renew_slide else None
    # بنرِ «ساخته‌شده و تأییدشده» توسط کاربر (توکن فایل موقت) جای تصویر آپلودی می‌نشیند.
    built_token, built = "", None
    files = request.FILES or None
    if request.method == "POST":
        token = (request.POST.get("built_token") or "").strip()
        data = builder.load_temp(request.user, token)
        if data:
            built_token = token
            built = {"token": token, "url": builder.temp_url(request.user, token)}
            files = request.FILES.copy()
            files["image"] = SimpleUploadedFile("slide.jpg", data, content_type="image/jpeg")
    form = StatSlideUserForm(
        request.POST or None, files,
        renew_slide=renew_slide, initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        if cost is None or cost.coins <= 0:
            messages.error(
                request,
                "تعرفهٔ ثبت اسلاید فعال نیست؛ لطفاً با پشتیبانی تماس بگیرید.",
                extra_tags="goto-wallet",
            )
        else:
            show_from = form.cleaned_data.get("show_from")
            show_until = form.cleaned_data.get("show_until")
            days = max(1, (show_until.date() - show_from.date()).days)
            total = cost.coins * days
            item = form.save(commit=False)
            item.advertiser = request.user
            item.status = AD_STATUS_PENDING
            try:
                # کسر هزینه = روزها × تعرفهٔ ۲۴ ساعته (یک تراکنش واحد)
                charge_module_days(
                    request.user, _effective_code(cost), days, request=request,
                    note=(f"تمدید اسلاید «{renew_slide.title}» ({days} روز)"
                          if renew_slide else f"ثبت اسلاید ({days} روز)"),
                )
            except WalletError as exc:
                # برچسب «goto-wallet» → قالب، دکمهٔ انتقال به «کیف پول و سکه» نشان می‌دهد.
                messages.error(request, str(exc), extra_tags="goto-wallet")
            else:
                item.coins_paid = total
                item.save()  # ابتدا رکورد (برای pk لازمِ M2M)
                if built_token:
                    builder.delete_temp(request.user, built_token)
                item.boxes.set(form.cleaned_data["stat_boxes"])
                open_approval_request(item, request)  # تیکت درخواست تأیید برای مدیر
                if renew_slide:
                    messages.success(
                        request,
                        f"اسلاید «{renew_slide.title}» برای {days} روز «تمدید» شد و "
                        f"{total} سکه ({cost.coins} × {days} روز) "
                        "از کیف پول کسر شد و برای تأیید مدیر (تیکت) ارسال گردید؛ پس از تأیید در اسلایدشو پخش می‌شود. "
                        f"در صورت عدم تأیید، {reject_fee_percent().normalize():f}٪ هزینه کسر و مابقی به کیف پول بازمی‌گردد.",
                    )
                else:
                    messages.success(
                        request,
                        f"اسلاید شما برای {days} روز ثبت شد و "
                        f"{total} سکه ({cost.coins} × {days} روز) "
                        "از کیف پول کسر شد و برای تأیید مدیر (تیکت) ارسال گردید؛ پس از تأیید در اسلایدشو پخش می‌شود. "
                        f"در صورت عدم تأیید، {reject_fee_percent().normalize():f}٪ هزینه کسر و مابقی به کیف پول بازمی‌گردد.",
                    )
                return redirect("ads:home")
    return render(request, "slideshow/create.html", {
        "form": form, "slide_cost": cost, "renew_slide": renew_slide,
        "create_cost": _create_cost(), "built": built,
        "renew_days": _renew_days(renew_slide) if renew_slide else None,
    })
