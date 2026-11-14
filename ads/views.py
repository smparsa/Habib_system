"""ماژول «تبلیغات» — ثبت تبلیغ لوگویی توسط کاربر و پرداخت هزینهٔ سکه.

گردش کار: کاربر لوگو/عنوان/توضیح/لینک را ثبت می‌کند و <b>تاریخ شروع و پایان
را خودش تعیین می‌کند</b> (تقویم شمسی)؛ ساعت شروع و پایان یکسان است. هزینه
= تعداد روزها × تعرفهٔ ۲۴ ساعتهٔ «هزینه‌های سکهٔ ماژول‌ها» (کد
``ad_submission``) از کیف پول او کسر می‌شود. تبلیغِ پرداخت‌شده پس از تأیید
ادمین (پنل مدیریت، مشابه «اخبار فوری»)، در نوار متحرک پایین داشبورد پخش
می‌شود.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from adminpanel.forms import AdvertisementForm
from adminpanel.models import AD_STATUS_APPROVED, AD_STATUS_PENDING, AD_STATUS_REJECTED, Advertisement
from wallet.services import WalletError, _audit, charge_module_days
from wallet.models import FeatureCost

from ads.approvals import open_approval_request, reject_fee_percent
from slideshow.views import (
    _cost as _slide_cost, _create_cost as _slide_create_cost,
    _effective_code as _slide_cost_code, boxes_capacity,
)


def _split_history(items):
    """(جاری, تاریخچه): تاریخچه = منقضی‌شده یا ردشده؛ جاری = در انتظار/زمان‌بندی‌شده/در حال پخش."""
    current, history = [], []
    for it in items:
        (history if it.status == AD_STATUS_REJECTED or it.is_expired else current).append(it)
    return current, history


@login_required(login_url="core:index")
@require_POST
def delete_ad(request, pk):
    """حذف کاملِ تبلیغِ خودِ کاربر (فقط تمام‌شده/ردشده) — هم‌قاعدهٔ حذفِ اسلایدشو.

    فایل لوگو فقط وقتی پاک می‌شود که هیچ تبلیغ دیگری (مثل نسخهٔ «تمدیدشده») به آن اشاره نکند.
    سکه‌ای بازگردانده نمی‌شود؛ رویداد در لاگ حسابرسی ثبت می‌شود.
    """
    ad = get_object_or_404(Advertisement, pk=pk, advertiser=request.user)   # تبلیغ دیگران = ۴۰۴
    if not ad.user_can_delete:
        messages.error(
            request,
            "فقط تبلیغ‌های تمام‌شده یا ردشده قابل حذف‌اند؛ تبلیغِ در انتظار تأیید یا در حال پخش را نمی‌توان حذف کرد.",
        )
        return redirect("ads:home")
    title, status, paid = ad.title, ad.status, ad.coins_paid
    logo_name, storage = ad.logo.name, ad.logo.storage
    with transaction.atomic():
        ad.delete()
    if logo_name and not Advertisement.objects.filter(logo=logo_name).exists():
        try:
            storage.delete(logo_name)
        except Exception:  # noqa: BLE001 - نبودنِ فایل مانع حذف رکورد نیست
            pass
    _audit(request, request.user, "ads.advertisement.deleted", "Advertisement", pk,
           meta={"title": title, "status": status, "coins_paid": str(paid)})
    messages.success(request, f"تبلیغ «{title}» برای همیشه حذف شد.")
    return redirect("ads:home")


@login_required(login_url="core:index")
def home(request):
    """صفحهٔ ماژول تبلیغات: ثبت تبلیغ و اسلایدشو (اسلایدشو A) + فهرست جاری و تاریخچهٔ هر دو.

    هزینهٔ هر دو بخش از «هزینه‌های سکهٔ ماژول‌ها» در پنل مدیریت خوانده می‌شود
    (تبلیغ: ``ad_submission``؛ اسلایدشو: ``stat_slide_submission`` یا در نبود آن، تعرفهٔ تبلیغات).
    """
    cost = FeatureCost.objects.filter(code="ad_submission", is_active=True).first()
    slide_cost = _slide_cost()
    my_ads = list(request.user.advertisements.prefetch_related("header_modules").order_by("-created_at"))
    my_slides = list(request.user.stat_slides.prefetch_related("boxes").order_by("-created_at"))
    ads_current, ads_history = _split_history(my_ads)
    slides_current, slides_history = _split_history(my_slides)
    return render(request, "ads/home.html", {
        "ad_cost": cost,
        "slide_cost": slide_cost,
        "slide_cost_code": _slide_cost_code(slide_cost),
        "slide_create_cost": _slide_create_cost(),
        "boxes_capacity": boxes_capacity(),
        "reject_fee_percent": reject_fee_percent().normalize(),
        "ads_current": ads_current, "ads_history": ads_history,
        "slides_current": slides_current, "slides_history": slides_history,
    })


@login_required(login_url="core:index")
def _renew_target(request, renew_id):
    """تبلیغ منقضی‌شدهٔ قابل‌تمدید برای کاربر جاری (در صورت درخواست ``?renew=<id>``).

    فقط تبلیغ متعلق به خود کاربر و با «تمام شدن بازهٔ نمایش» ``is_expired``
    پذیرفته می‌شود؛ تبلیغ در حال پخش/در انتظار/ردشده قابل تمدید نیست.
    """
    if not renew_id:
        return None
    try:
        ad = request.user.advertisements.get(pk=renew_id)
    except (Advertisement.DoesNotExist, ValueError, TypeError):
        return None
    return ad if ad.is_expired else None


def _ad_initial(ad):
    """مقادیر پیش‌پُرِ فرم تمدید از تبلیغ قبلی (به‌جز تاریخ، که باید جدید باشد)."""
    initial = {
        "title": ad.title,
        "description": ad.description,
        "link_url": ad.link_url,
        "header_modules": ad.header_modules.values_list("pk", flat=True),
    }
    start = ad.show_from
    if start:
        from django.utils import timezone
        local = timezone.localtime(start) if timezone.is_aware(start) else start
        initial["ad_time"] = local.strftime("%H:%M")
    return initial


@login_required(login_url="core:index")
def create(request):
    """ثبت تبلیغ جدید / «تمدید» تبلیغ منقضی + کسر هزینهٔ سکه.

    حالت عادی: کاربر لوگو + تاریخ/ساعت + هدر(های) نوار تبلیغ را تعیین می‌کند؛
    هزینه = روزها × تعداد هدرهای انتخابی × تعرفهٔ ۲۴ ساعتهٔ ``ad_submission``—
    یک تراکنشِ واحد از کیف پول کسر می‌شود؛ در صورت شکست، تبلیغ ثبت نمی‌شود.

    حالت تمدید: ``?renew=<id>`` — برای تبلیغِ «تأییدشده»ای که بازهٔ نمایشش
    تمام شده، فرم با متن/لینک/هدرها و لوگوی تبلیغ قبلی پیش‌پُر می‌شود؛ کاربر
    فقط تاریخ جدید را انتخاب و هزینهٔ دورهٔ جدید را می‌پردازد. همان تبلیغِ
    قبلی دست‌نخورده در تاریخچه می‌ماند و رکوردِ جدید «در انتظار تأیید» ثبت
    می‌شود.
    """
    cost = FeatureCost.objects.filter(code="ad_submission", is_active=True).first()
    renew_ad = _renew_target(request, request.GET.get("renew") or request.POST.get("renew_ref"))
    initial = _ad_initial(renew_ad) if renew_ad else None
    form = AdvertisementForm(
        request.POST or None, request.FILES or None,
        renew_ad=renew_ad, initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        if cost is None or cost.coins <= 0:
            messages.error(
                request,
                "تعرفهٔ ثبت تبلیغ فعال نیست؛ لطفاً با پشتیبانی تماس بگیرید.",
            )
        else:
            days = form.cleaned_data.get("days") or 1
            slots = form.cleaned_data["header_modules"].count()  # تعداد هدرهای انتخابی
            total = cost.coins * days * slots
            item = form.save(commit=False)
            item.advertiser = request.user
            item.status = AD_STATUS_PENDING
            try:
                # کسر هزینه = روزها × هدرها × تعرفهٔ ۲۴ ساعته (یک تراکنش واحد)
                charge_module_days(
                    request.user, "ad_submission", days * slots, request=request,
                    note=(f"تمدید تبلیغ «{renew_ad.title}» ({days} روز × {slots} هدر)"
                          if renew_ad else f"تبلیغ ({days} روز × {slots} هدر)"),
                )
            except WalletError as exc:
                # برچسب «goto-wallet» → قالب، دکمهٔ انتقال به «کیف پول و سکه» نشان می‌دهد.
                messages.error(request, str(exc), extra_tags="goto-wallet")
            else:
                item.coins_paid = total
                item.save()  # ابتدا رکورد (برای pk لازمِ M2M)
                item.header_modules.set(form.cleaned_data["header_modules"])
                open_approval_request(item, request)  # تیکت درخواست تأیید برای مدیر
                if renew_ad:
                    messages.success(
                        request,
                        f"تبلیغ «{renew_ad.title}» برای {days} روز در {slots} هدر «تمدید» شد و "
                        f"{total} سکه ({cost.coins} × {days} روز × {slots} هدر) "
                        "از کیف پول کسر شد و برای تأیید مدیر (تیکت) ارسال گردید؛ پس از تأیید در همان نوارها پخش می‌شود. "
                        f"در صورت عدم تأیید، {reject_fee_percent().normalize():f}٪ هزینه کسر و مابقی به کیف پول بازمی‌گردد.",
                    )
                else:
                    messages.success(
                        request,
                        f"تبلیغ شما برای {days} روز در {slots} هدر ثبت شد و "
                        f"{total} سکه ({cost.coins} × {days} روز × {slots} هدر) "
                        "از کیف پول کسر شد و برای تأیید مدیر (تیکت) ارسال گردید؛ پس از تأیید در نوار هدرهای "
                        "انتخاب‌شده پخش می‌شود. "
                        f"در صورت عدم تأیید، {reject_fee_percent().normalize():f}٪ هزینه کسر و مابقی به کیف پول بازمی‌گردد.",
                    )
                return redirect("ads:home")
    # برای تیک‌دار بودن چک‌باکس‌ها در قالب: فهرستِ رشته‌ای هدرهای انتخابی
    # (در حالت تمدید از تبلیغ قبلی، در خطای POST از دادهٔ ارسالی کاربر).
    if form.is_bound:
        checked_ids = [str(pk) for pk in form.data.getlist("header_modules")]
    else:
        checked_ids = [str(pk) for pk in (initial.get("header_modules") or [])] if initial else []
    return render(request, "ads/create.html", {
        "form": form, "ad_cost": cost, "renew_ad": renew_ad,
        "header_checked": checked_ids,
    })
