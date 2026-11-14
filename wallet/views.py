"""ویوهای کاربری «سکه و کیف پول»: داشبورد (خرید/فروش/انتقال)، تأیید انتقال و تاریخچه.

- خطاهای خرید/فروش/انتقال (مثل «حداقل خرید 10.00 سکه است.») با پارامترهای
  wallet_err/wallet_field/wallet_action به داشبورد برمی‌گردند تا در همان فریم
  عملیات و زیر فیلد مربوطه نمایش داده شوند و فوکوس روی فیلد برود.
- فرم انتقال با API «receiver_lookup» نام گیرنده را به‌صورت زنده (Query) نشان
  می‌دهد؛ سپس پس از «انتقال سکه»، دو مرحله تأیید در صفحهٔ تأیید انجام می‌شود.
"""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from .forms import BuyForm, SellForm, TransferForm
from .models import CoinLedger, CoinOrder, CoinTransfer, WalletSetting
from .services import (
    WalletError,
    clear_transfer_pin,
    create_buy_order,
    create_sell_order,
    find_user_by_national_id,
    convert_unconverted_points,
    get_wallet,
    has_transfer_pin,
    lookup_receiver_preview,
    mark_buy_receipt_sent,
    set_transfer_pin,
    submit_buy_receipt,
    transfer_coins,
    validate_sell_request,
    verify_transfer_pin,
)

# انواع دفتر کل مربوط به «خرید سکه / فروش سکه / انتقال سکه» — بخش
# «تراکنش‌های اخیر» داشبورد فقط همین‌ها را نشان می‌دهد (امتیاز/پاداش و
# هزینهٔ ماژول‌ها اینجا نمایش داده نمی‌شوند). KIND_BUY_REQUEST = لحظهٔ
# کامل‌شدن فرایند «کارت به کارت + ارسال رسید» (بدون تغییر موجودی).
DASHBOARD_LEDGER_KINDS = [
    CoinLedger.KIND_BUY,
    CoinLedger.KIND_BUY_REQUEST,
    CoinLedger.KIND_SELL,
    CoinLedger.KIND_SELL_REFUND,
    CoinLedger.KIND_TRANSFER_OUT,
    CoinLedger.KIND_TRANSFER_IN,
]

# نگه‌داشت «قصد انتقال/فروش» در session (تا محل تأیید دوم، دستکاری‌ناپذیر باشند)
TRANSFER_INTENT_KEY = "wallet_transfer_intent"
SELL_INTENT_KEY = "wallet_sell_intent"


def _dashboard_error_redirect(action, message, field="coins", extra=None):
    """بازگشت خطای عملیات کیف پول به داشبورد برای نمایش درون فریم + فوکوس فیلد."""
    params = {"wallet_action": action, "wallet_err": str(message)}
    if field:
        params["wallet_field"] = field
    if extra:
        params.update(extra)
    return redirect(f"{reverse('wallet:dashboard')}?{params_urlencode(params)}")


def params_urlencode(params):
    from urllib.parse import urlencode

    return urlencode(params)


@login_required(login_url="core:index")
@require_http_methods(["GET", "POST"])
def dashboard(request):
    """صفحهٔ اصلی کیف پول: موجودی، نرخ، فرم‌های خرید/فروش/انتقال و تراکنش‌های اخیر."""
    user = request.user
    setting = WalletSetting.get()
    # «تعرفه امتیازها»: هر امتیاز تبدیل‌نشدهٔ کاربر (نرخ: ارزش هر سکه به امتیاز)
    # بلافاصله به سکه تبدیل و با موجودی کیف پول تجمیع می‌شود؛ هر امتیاز فقط
    # یک‌بار تبدیل می‌شود (watermark در پروفایل) و امتیازِ سطح حفظ می‌ماند.
    try:
        convert_unconverted_points(user.profile, request=request)
    except Exception:
        pass
    wallet = get_wallet(user)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "set_pin":
            new_pin = request.POST.get("new_pin", "")
            confirm_pin = request.POST.get("confirm_pin", "")
            if new_pin != confirm_pin:
                messages.error(request, "رمز جدید و تکرار آن یکسان نیستند.")
            else:
                try:
                    set_transfer_pin(user, new_pin)
                    messages.success(
                        request,
                        "رمز انتقال سکه تنظیم شد. از این پس هر انتقال به این رمز نیاز دارد.",
                    )
                except WalletError as exc:
                    messages.error(request, str(exc))
            return redirect("wallet:dashboard")

        if action == "clear_pin":
            try:
                clear_transfer_pin(user)
                messages.success(request, "رمز انتقال حذف شد.")
            except WalletError as exc:
                messages.error(request, str(exc))
            return redirect("wallet:dashboard")

        if action == "buy":
            form = BuyForm(request.POST)
            if form.is_valid():
                try:
                    order = create_buy_order(
                        user, form.cleaned_data["coins"], request=request, notify=False
                    )
                    # گام بعدی: صفحهٔ پرداخت (کارت‌به‌کارت) + بارگذاری فیش واریز
                    return redirect("wallet:buy_payment", code=order.code)
                except WalletError as exc:
                    # خطای سرویس (مثل «حداقل خرید 10.00 سکه است.») روی فیلد
                    # تعداد سکه در همان فریم خرید نمایش داده می‌شود.
                    return _dashboard_error_redirect("buy", exc, field="coins")
            first_field, first_err = _first_form_error(form)
            return _dashboard_error_redirect("buy", first_err, field=first_field)

        if action == "sell":
            # مرحلهٔ ۱: اعتبارسنجی ورودی و ذخیرهٔ «قصد فروش» در session؛
            # رزرو سکه و ثبت سفارش فقط پس از تأیید دومرحله‌ای انجام می‌شود.
            form = SellForm(request.POST)
            if form.is_valid():
                try:
                    # پیش‌اعتبارسنجی سرویس (موجودی/شبا/محدودیت‌ها) پیش از تأیید
                    validate_sell_request(user, form.cleaned_data["coins"])
                except WalletError as exc:
                    return _dashboard_error_redirect("sell", exc, field="coins")
                request.session[SELL_INTENT_KEY] = {
                    "coins": str(form.cleaned_data["coins"]),
                }
                return redirect("wallet:sell_confirm")
            first_field, first_err = _first_form_error(form)
            return _dashboard_error_redirect("sell", first_err, field=first_field)

        if action == "transfer":
            # مرحلهٔ ۱: اعتبارسنجی ورودی و ذخیرهٔ «قصد انتقال» در session؛
            # اجرای واقعی پس از دو مرحلهٔ تأیید در صفحهٔ جداگانه انجام می‌شود.
            form = TransferForm(request.POST)
            if form.is_valid():
                try:
                    receiver = find_user_by_national_id(
                        form.cleaned_data["receiver_national_id"]
                    )
                except WalletError as exc:
                    return _dashboard_error_redirect(
                        "transfer", exc, field="receiver_national_id"
                    )
                if setting.transfer_pin_required and not has_transfer_pin(user):
                    messages.error(
                        request,
                        "برای انتقال سکه ابتدا یک رمز چهار رقمی در «امنیت انتقال» تنظیم کنید.",
                    )
                    return redirect("wallet:dashboard")
                request.session[TRANSFER_INTENT_KEY] = {
                    "receiver_national_id": form.cleaned_data["receiver_national_id"],
                    "coins": str(form.cleaned_data["coins"]),
                    "note": form.cleaned_data.get("note", ""),
                }
                return redirect("wallet:transfer_confirm")
            first_field, first_err = _first_form_error(form)
            return _dashboard_error_redirect("transfer", first_err, field=first_field)

        messages.error(request, "عملیات ناشناخته است.")
        return redirect("wallet:dashboard")

    sell_form = SellForm()
    transfer_form = TransferForm()
    buy_form = BuyForm()
    # شبأ واریز وجه فروش از «اطلاعات مالی» پروفایل خوانده می‌شود (تنها منبع)
    profile_iban = (user.profile.iban or "").strip()
    has_bank_info = bool(profile_iban)
    # خطای درون-فریمی (پارامترهای URL): همان خطا در فرمِ همان فریم رندر می‌شود
    # تا حتی بدون جاوااسکریپت، پیام زیر فیلد مربوطه دیده شود و JS فقط فوکوس
    # و اسکرول را اضافه می‌کند.
    wallet_action = request.GET.get("wallet_action") or ""
    wallet_field = request.GET.get("wallet_field") or "coins"
    wallet_err = request.GET.get("wallet_err") or ""
    if wallet_err:
        try:
            if wallet_action == "buy":
                buy_form = BuyForm()
                if wallet_field == "coins":
                    buy_form.add_error("coins", wallet_err)
                else:
                    buy_form.add_error(None, wallet_err)
            elif wallet_action == "sell":
                sell_form = SellForm()
                sell_form.add_error("coins", wallet_err)
            elif wallet_action == "transfer":
                transfer_form = TransferForm()
                if wallet_field in transfer_form.fields:
                    transfer_form.add_error(wallet_field, wallet_err)
                else:
                    transfer_form.add_error("coins", wallet_err)
        except Exception:  # noqa: BLE001 - نمایش خطا هرگز صفحه را نشکند
            pass
    # آخرین سفارش خریدِ بدون فیش برای یادآوری «ادامهٔ پرداخت و ارسال فیش»
    pending_buy_order = (
        CoinOrder.objects.filter(
            user=user, kind=CoinOrder.KIND_BUY, status=CoinOrder.STATUS_PENDING,
        )
        .filter(payment_receipt__in=["", None])
        .order_by("-created_at")
        .first()
    )

    # «تراکنش‌های اخیر»: فقط خرید سکه / فروش سکه / انتقال سکه
    recent_ledger = (
        CoinLedger.objects.filter(user=user, kind__in=DASHBOARD_LEDGER_KINDS)
        .select_related("user")[:15]
    )
    recent_orders = CoinOrder.objects.filter(user=user)[:5]
    recent_transfers = (
        CoinTransfer.objects.filter(sender=user) | CoinTransfer.objects.filter(receiver=user)
    ).order_by("-created_at")[:10]

    return render(
        request,
        "wallet/dashboard.html",
        {
            "profile": user.profile,
            "wallet": wallet,
            "setting": setting,
            "buy_form": buy_form,
            "sell_form": sell_form,
            "transfer_form": transfer_form,
            "recent_ledger": recent_ledger,
            "recent_orders": recent_orders,
            "recent_transfers": recent_transfers,
            "has_pin": has_transfer_pin(user),
            "pin_required": setting.transfer_pin_required,
            "has_bank_info": has_bank_info,
            "profile_iban": profile_iban,
            "pending_buy_order": pending_buy_order,
            "profile_bank_name": (user.profile.bank_name or "").strip()
            or "بانک ملی ایران",
            "user_score": int(user.profile.user_score or 0),
            "point_rate": int(setting.coin_value_point or 0),
        },
    )


def _first_form_error(form):
    """نخستین خطای فرم را همراه فیلدش برمی‌گرداند (برای فوکوس و نمایش درون فریم)."""
    for field_name, errors in form.errors.items():
        if field_name != "__all__" and errors:
            return field_name, errors[0]
    for errors in form.errors.values():
        if errors:
            return "coins", errors[0]
    return "coins", "ورودی معتبر نیست."


def _latin_digits(raw):
    """ارقام فارسی/عربی را به لاتین تبدیل و فاصله‌ها را حذف می‌کند."""
    return (raw or "").strip().translate(
        str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    )


@login_required(login_url="core:index")
@require_GET
def receiver_lookup(request):
    """جست‌وجوی زندهٔ گیرندهٔ انتقال با کد ملی (Query) → نام کاربر.

    دو حالت پشتیبانی می‌شود (خروجی JSON برای فرم «انتقال سکه به دیگران»):
    - «q»: پیشوند کد ملی (حداقل ۴ رقم) → فهرست آبشاری «کد ملی + نام» کاربران
      متناظر (حداکثر ۱۲ مورد) — مشابه انتخاب‌گر زندهٔ فیلدهای نام در پروفایل.
    - «national_id»: کد ملی کامل ۱۰ رقمی → نام/موبایل همان کاربر برای جعبهٔ
      تأیید گیرنده؛ سپس با دکمهٔ «انتقال سکه»، دو مرحلهٔ تأیید طی می‌شود.
    """
    if "q" in request.GET:
        prefix = _latin_digits(request.GET.get("q"))
        if len(prefix) < 4 or not prefix.isdigit():
            return JsonResponse({"results": []})
        from accounts.models import Profile

        profiles = (
            Profile.objects.select_related("user", "first_name", "last_name")
            .filter(national_id__startswith=prefix, user__is_active=True)
            .order_by("national_id")[:12]
        )
        return JsonResponse(
            {
                "results": [
                    {
                        "national_id": p.national_id,
                        "full_name": p.full_name,
                    }
                    for p in profiles
                ]
            }
        )

    raw = _latin_digits(request.GET.get("national_id"))
    if len(raw) < 10:
        return JsonResponse({"found": False, "reason": "کد ملی باید ۱۰ رقم باشد."})
    info = lookup_receiver_preview(raw)
    if info is None:
        return JsonResponse(
            {"found": False, "reason": "کاربری با این کد ملی یافت نشد."}
        )
    return JsonResponse({"found": True, **info})


@login_required(login_url="core:index")
@require_GET
def coin_image_url(request):
    """URL تصویر/لوگوی سکهٔ آپلودشدهٔ ادمین (WalletSetting.coin_image).

    برای اورلی سراسری «لطفاً منتظر بمانید» (Please Wait) استفاده می‌شود؛ اگر
    ادمین تصویری بارگذاری نکرده باشد، url خالی برمی‌گردد و فرانت‌اند از
    تصویر پیش‌فرض static (core/assets/coin.jpg) بهره می‌گیرد.
    """
    setting = WalletSetting.get()
    url = ""
    if setting.coin_image:
        try:
            url = setting.coin_image.url
        except (ValueError, OSError):
            url = ""
    return JsonResponse({"url": url})


@login_required(login_url="core:index")
@require_http_methods(["GET", "POST"])
def buy_payment(request, code):
    """صفحهٔ پرداخت سفارش خرید سکه (کارت‌به‌کارت): حساب مقصد + بارگذاری فیش واریز.

    کاربر پس از ثبت درخواست خرید (با تکمیل تعداد سکه و دیدن «اطلاعات سفارش و
    حساب مقصد» زیر فیلد) به این صفحه هدایت می‌شود؛ مبلغ و کارت/شبأ مقصد را
    می‌بیند، وجه را کارت‌به‌کارت واریز می‌کند و فیش را بارگذاری می‌کند. با ثبت
    فیش، تیکت درخواست خرید (با پیوست) به مدیران ارسال می‌شود.
    """
    user = request.user
    setting = WalletSetting.get()
    order = get_object_or_404(
        CoinOrder, code=code, user=user, kind=CoinOrder.KIND_BUY
    )

    if request.method == "POST":
        if request.POST.get("cancel"):
            messages.info(
                request,
                f"پرداخت سفارش «{order.code}» ناتمام ماند؛ تا پیش از تأیید مدیر "
                "می‌توانید فیش واریز را ارسال کنید.",
            )
            return redirect("wallet:dashboard")
        upload = request.FILES.get("receipt")
        try:
            submit_buy_receipt(order, upload, request=request)
        except WalletError as exc:
            messages.error(request, str(exc))
            return redirect("wallet:buy_payment", code=order.code)
        messages.success(
            request,
            f"فیش واریز سفارش «{order.code}» ثبت شد و برای بررسی به مدیر ارسال گردید. "
            "پس از تأیید، سکه به کیف پول شما افزوده می‌شود.",
        )
        return redirect("wallet:dashboard")

    card = (setting.receiving_card_number or "").replace(" ", "")
    card_groups = [card[i:i + 4] for i in range(0, len(card), 4)] if card else []

    return render(
        request,
        "wallet/buy_payment.html",
        {
            "profile": user.profile,
            "wallet": get_wallet(user),
            "setting": setting,
            "order": order,
            "card_groups": card_groups,
        },
    )


@login_required(login_url="core:index")
@require_http_methods(["GET", "POST"])
def sell_confirm(request):
    """تأیید دومرحله‌ای فروش سکه: خلاصهٔ سفارش + دو بار تأیید از کاربر.

    برای امنیت، رزرو سکه و ثبت سفارش فروش فقط پس از دو تأیید متوالی انجام
    می‌شود؛ «قصد فروش» (تعداد سکه) در session نگه‌داری شده و مستقیم از POST
    خوانده نمی‌شود تا دستکاری‌ناپذیر باشد.
    """
    user = request.user
    setting = WalletSetting.get()
    intent = request.session.get(SELL_INTENT_KEY)

    if request.method == "POST":
        if request.POST.get("cancel"):
            request.session.pop(SELL_INTENT_KEY, None)
            messages.info(request, "درخواست فروش لغو شد.")
            return redirect("wallet:dashboard")

        if not intent:
            messages.error(request, "درخواست فروش منقضی شده است؛ دوباره اقدام کنید.")
            return redirect("wallet:dashboard")

        # دو مرحلهٔ تأیید: confirm1 سپس confirm2 (اجرای واقعی فقط با confirm2)
        if not request.POST.get("confirm2"):
            if request.POST.get("confirm1"):
                request.session["wallet_sell_confirmed_once"] = True
            return render(
                request,
                "wallet/sell_confirm.html",
                _sell_confirm_context(user, setting, intent, confirmed=True),
            )

        if not request.session.pop("wallet_sell_confirmed_once", False):
            messages.error(
                request,
                "تأیید مرحلهٔ اول ثبت نشده است؛ دوباره از ابتدا اقدام کنید.",
            )
            return redirect("wallet:dashboard")

        try:
            order = create_sell_order(
                user, intent["coins"], request=request,
            )
        except WalletError as exc:
            request.session.pop(SELL_INTENT_KEY, None)
            messages.error(request, str(exc))
            return redirect("wallet:dashboard")
        request.session.pop(SELL_INTENT_KEY, None)
        messages.success(
            request,
            f"درخواست فروش با کد «{order.code}» ثبت شد و {order.coins} سکه "
            "از کیف پول شما رزرو شد. تیکت درخواست فروش برای مدیر ارسال گردید؛ "
            "پس از تأیید، مبلغ "
            f"{order.total_rial} ریال به شبأ ثبت‌شده در «اطلاعات مالی» "
            "پروفایل شما واریز می‌شود.",
        )
        return redirect("wallet:dashboard")

    if not intent:
        messages.info(request, "هیچ درخواست فروشِ در انتظار تأییدی وجود ندارد.")
        return redirect("wallet:dashboard")
    return render(
        request,
        "wallet/sell_confirm.html",
        _sell_confirm_context(user, setting, intent, confirmed=False),
    )


def _sell_confirm_context(user, setting, intent, confirmed):
    coins = intent["coins"]
    rate = setting.coin_value_rial
    return {
        "profile": user.profile,
        "wallet": get_wallet(user),
        "setting": setting,
        "coins": coins,
        "rate": rate,
        "total_rial": (Decimal(str(coins)) * Decimal(str(rate))),
        "confirmed": confirmed,
    }


@login_required(login_url="core:index")
@require_http_methods(["GET", "POST"])
def transfer_confirm(request):
    """مراحل تأیید انتقال: خلاصهٔ انتقال + دو بار تأیید از کاربر (+ رمز در صورت نیاز).

    - مرحلهٔ ۱: نمایش خلاصه (نام گیرنده، کد ملی، تعداد سکه) و دکمهٔ «تأیید مرحلهٔ ۱».
    - مرحلهٔ ۲: دکمهٔ «تأیید نهایی و انتقال» — پس از آن انتقال اتمی انجام می‌شود،
      موجودی هر دو طرف از دفتر کل آپدیت می‌شود و برای فرستنده تیکت «پرداخت سکه»
      و برای گیرنده تیکت «دریافت سکه» ارسال می‌گردد.
    قصدِ ذخیره‌شده در session پس از اجرا یا انصراف حذف می‌شود.
    """
    user = request.user
    setting = WalletSetting.get()
    intent = request.session.get(TRANSFER_INTENT_KEY)

    if request.method == "POST":
        if request.POST.get("cancel"):
            request.session.pop(TRANSFER_INTENT_KEY, None)
            messages.info(request, "انتقال سکه لغو شد.")
            return redirect("wallet:dashboard")

        if not intent:
            request.session.pop(TRANSFER_INTENT_KEY, None)
            messages.error(request, "درخواست انتقال منقضی شده است؛ دوباره اقدام کنید.")
            return redirect("wallet:dashboard")
        try:
            receiver = find_user_by_national_id(intent["receiver_national_id"])
        except WalletError as exc:
            request.session.pop(TRANSFER_INTENT_KEY, None)
            messages.error(request, str(exc))
            return redirect("wallet:dashboard")

        # دو مرحلهٔ تأیید: confirm1 سپس confirm2 (اجرای واقعی فقط با confirm2)
        if not request.POST.get("confirm2"):
            if request.POST.get("confirm1"):
                request.session["wallet_transfer_confirmed_once"] = True
            return render(
                request,
                "wallet/transfer_confirm.html",
                _transfer_confirm_context(
                    user, setting, intent, receiver, confirmed=True
                ),
            )

        if not request.session.pop("wallet_transfer_confirmed_once", False):
            messages.error(
                request,
                "تأیید مرحلهٔ اول ثبت نشده است؛ دوباره از ابتدا اقدام کنید.",
            )
            return redirect("wallet:dashboard")

        need_pin = setting.transfer_pin_required or has_transfer_pin(user)
        pin = request.POST.get("pin", "")
        if need_pin and not verify_transfer_pin(user, pin):
            messages.error(request, "رمز انتقال اشتباه است؛ دوباره تلاش کنید.")
            request.session["wallet_transfer_confirmed_once"] = True
            return redirect("wallet:transfer_confirm")

        try:
            transfer = transfer_coins(
                user, receiver, intent["coins"],
                note=intent.get("note", ""), request=request,
            )
        except WalletError as exc:
            messages.error(request, str(exc))
            return redirect("wallet:transfer_confirm")
        request.session.pop(TRANSFER_INTENT_KEY, None)
        messages.success(
            request,
            f"{transfer.coins} سکه با کد «{transfer.code}» به «{receiver.profile.full_name}» "
            f"با کد ملی «{receiver.profile.national_id}» منتقل شد. تیکت «پرداخت سکه» برای "
            "شما و تیکت «دریافت سکه» برای گیرنده ارسال گردید و موجودی هر دو طرف به‌روزرسانی شد.",
        )
        return redirect("wallet:dashboard")

    if not intent:
        messages.info(request, "هیچ درخواست انتقالِ در انتظار تأییدی وجود ندارد.")
        return redirect("wallet:dashboard")
    try:
        receiver = find_user_by_national_id(intent["receiver_national_id"])
    except WalletError as exc:
        request.session.pop(TRANSFER_INTENT_KEY, None)
        messages.error(request, str(exc))
        return redirect("wallet:dashboard")

    return render(
        request,
        "wallet/transfer_confirm.html",
        _transfer_confirm_context(user, setting, intent, receiver, confirmed=False),
    )


def _transfer_confirm_context(user, setting, intent, receiver, confirmed):
    need_pin = setting.transfer_pin_required or has_transfer_pin(user)
    return {
        "profile": user.profile,
        "wallet": get_wallet(user),
        "setting": setting,
        "receiver": receiver,
        "receiver_name": receiver.profile.full_name,
        "coins": intent["coins"],
        "note": intent.get("note", ""),
        "need_pin": need_pin,
        "has_pin": has_transfer_pin(user),
        "pin_required": setting.transfer_pin_required,
        "confirmed": confirmed,
    }


@login_required(login_url="core:index")
def history(request):
    """تاریخچهٔ کامل: دفتر کل + سفارش‌ها + انتقال‌ها (با تب و صفحه‌بندی)."""
    user = request.user
    tab = request.GET.get("tab", "ledger")
    if tab not in ("ledger", "orders", "transfers"):
        tab = "ledger"
    kind = request.GET.get("kind") or ""

    if tab == "ledger":
        qs = CoinLedger.objects.filter(user=user)
        if kind:
            qs = qs.filter(kind=kind)
        page_obj = Paginator(qs, 30).get_page(request.GET.get("page"))
        object_list = page_obj.object_list
    elif tab == "orders":
        qs = CoinOrder.objects.filter(user=user)
        page_obj = Paginator(qs, 30).get_page(request.GET.get("page"))
        object_list = page_obj.object_list
    else:
        qs = CoinTransfer.objects.filter(sender=user) | CoinTransfer.objects.filter(
            receiver=user
        )
        page_obj = Paginator(qs, 30).get_page(request.GET.get("page"))
        object_list = page_obj.object_list

    return render(
        request,
        "wallet/history.html",
        {
            "profile": user.profile,
            "wallet": get_wallet(user),
            "setting": WalletSetting.get(),
            "tab": tab,
            "kind": kind,
            "object_list": object_list,
            "page_obj": page_obj,
            "ledger_kinds": CoinLedger.KIND_CHOICES,
        },
    )
