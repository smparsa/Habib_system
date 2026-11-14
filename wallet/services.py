"""لایهٔ سرویس‌های سکه/کیف پول — تمام منطق مالی این‌جاست، نه در ویوها.

اصول:
- همهٔ تغییرات موجودی در transaction.atomic + SELECT FOR UPDATE اعمال می‌شود
  (جلوگیری از خرج مضاعف در تراکنش‌های هم‌زمان).
- هر رکورد دفتر کل، ماندهٔ پس از تراکنش (balance_after) را نگه می‌دارد.
- هر جابه‌جایی (خرید/فروش/انتقال/کسر/تنظیم) با «تیکت» به طرفین اعلام می‌شود
  (موتور تیکت) و در لاگ حسابرسی (TicketAuditLog) ثبت می‌گردد.
- قیمت هر سکه هنگام ثبت سفارش عکس‌برداری می‌شود.
"""

import os
import re
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (
    CoinLedger,
    CoinOrder,
    CoinPriceHistory,
    CoinTransfer,
    FeatureCost,
    Wallet,
    WalletSetting,
)
from .numbering import next_code


class WalletError(Exception):
    """خطای فارسیِ قابل نمایش به کاربر برای عملیات کیف پول."""


_IBAN_RE = re.compile(r"^IR\d{24}$")
_FA_AR_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


# --------------------------------------------------------------------------- #
# ابزارهای کمکی
# --------------------------------------------------------------------------- #
def _ip(request):
    if request is None:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or None


def _close_related_ticket(order, admin, request=None, note=""):
    """بستن/حل تیکت‌های درخواست خرید مرتبط با سفارش پس از تأیید یا ابطال.

    تیکتِ «درخواست خرید سکه — WAL-...» با کد سفارش در موضوعش پیدا می‌شود و اگر
    هنوز باز باشد، به «حل‌شده» می‌رود و پاسخ نتیجه به آن افزوده می‌شود — تا
    فهرست تیکت‌های ادمین فقط مواردِ در انتظار کار را نشان دهد.
    شکستِ بستن تیکت هرگز عملیات مالی را متوقف نمی‌کند.
    """
    from tickets import constants as tkt_c
    from tickets.models import Ticket
    from tickets.services import add_message, change_status

    tickets = Ticket.objects.filter(
        subject__icontains=order.code,
        subject__istartswith="درخواست خرید سکه",
    ).exclude(status__in=(tkt_c.STATUS_RESOLVED, tkt_c.STATUS_CLOSED))
    for t in tickets:
        try:
            if note:
                add_message(t, admin, note, request=request)
            change_status(t, admin, tkt_c.STATUS_RESOLVED,
                          note=f"سفارش {order.code} بررسی شد",
                          request=request)
        except Exception:  # noqa: BLE001 - بستن تیکت نباید مالی را بشکند
            continue


def _audit(request, actor, action, object_type, object_id=None, meta=None):
    """ثبت رویداد در لاگ حسابرسی تیکت‌ها (تک‌نقطهٔ حسابرسی کل برنامه)."""
    from tickets.services import audit

    audit(
        actor, action, object_type, object_id,
        request=request, meta=meta or {},
    )


def _staff_ids():
    from django.contrib.auth import get_user_model

    return list(
        get_user_model().objects.filter(is_active=True, is_staff=True)
        .values_list("id", flat=True)
    )


def _user_label(user):
    try:
        full = user.profile.full_name
    except Exception:  # noqa: BLE001 - پروفایلِ ناقص نباید تراکنش را بشکند
        full = ""
    return full or user.mobile_number


def _movement_ticket(request, author, subject, body, recipient_user_ids=None,
                     include_staff=True, attachments=(), priority="high",
                     category_code="financial"):
    """«هر حرکت سکه → تیکت به طرفین».

    یک تیکت می‌سازد که فرستنده، نویسندهٔ آن است و گیرنده(های) اصلی + (اختیاری)
    کارکنان فعال، گیرندهٔ تیکت می‌شوند؛ هر دو طرف حرکت، تیکت را می‌بینند و
    اعلان درون‌برنامه‌ای می‌گیرند. شکست تیکت هرگز گردش کار مالی را متوقف نمی‌کند.
    attachments: فایل‌های پیوست (مثل فیش واریز) که به نخستین پیام اضافه می‌شوند.

    تیکت‌های مالی با دستهٔ «مالی» و اولویتِ بالا (high) ساخته می‌شوند تا در
    سیاست پاسخگویی ادمین (SLA ۸ ساعته) جلوی چشم باشند؛ پاداش‌ها با اولویت
    عادی می‌مانند.
    """
    from tickets.exceptions import TicketError
    from tickets.services import add_message, create_ticket

    recipient_ids = [u for u in (recipient_user_ids or []) if u != author.id]
    if include_staff:
        for uid in _staff_ids():
            if uid != author.id and uid not in recipient_ids:
                recipient_ids.append(uid)

    try:
        ticket, _ = create_ticket(
            author=author, subject=subject, description=body,
            specific_user_ids=recipient_ids or None, request=request,
            duplicate_window=0, priority=priority,
            category_code=category_code,
        )
        for af in attachments or ():
            if af is None:
                continue
            try:
                add_message(ticket, author, "📎 پیوست: فیش واریز", attachments=[af],
                            request=request)
            except Exception:  # noqa: BLE001 - پیوست نباید تیکت را بشکند
                pass
        return ticket
    except TicketError:
        return None


def get_wallet(user):
    """کیف پول کاربر را برمی‌گرداند (در صورت نبود، می‌سازد)."""
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet


def current_rate():
    return WalletSetting.get().coin_value_rial


def normalize_iban(value):
    iban = re.sub(r"\s+", "", (value or "")).upper()
    if not _IBAN_RE.fullmatch(iban):
        raise WalletError(
            "شماره شبا معتبر نیست؛ باید ۲۶ نویسه و با IR شروع شود "
            "(مثال: IR123456789012345678901234)."
        )
    return iban


# کد سه‌رقمی بانک‌های ایرانی (شماره اختصاصی نزد بانک مرکزی) که در نویسه‌های ۵ تا ۷
# شماره شبا درج می‌شود؛ برای تشخیص خودکار نام بانک از همان شبا استفاده می‌شود تا
# کاربر فقط یک شماره شبا اعلام کند و نیازی به انتخاب نام بانک نداشته باشد.
_IBAN_BANK_CODES = {
    "010": "بانک مرکزی جمهوری اسلامی ایران",
    "011": "بانک صنعت و معدن",
    "012": "بانک ملت",
    "013": "بانک رفاه کارگران",
    "014": "بانک مسکن",
    "015": "بانک سپه",
    "016": "بانک کشاورزی",
    "017": "بانک ملی ایران",
    "018": "بانک تجارت",
    "019": "بانک صادرات ایران",
    "020": "بانک توسعه صادرات ایران",
    "021": "بانک توسعه تعاون",
    "022": "پست بانک ایران",
    "051": "بانک مهر اقتصاد",
    "053": "بانک آینده",
    "054": "بانک سرمایه",
    "055": "بانک شهر",
    "056": "بانک دی",
    "057": "بانک سینا",
    "058": "بانک قوامین",
    "059": "بانک انصار",
    "060": "بانک خاورمیانه",
    "061": "بانک ایران زمین",
    "062": "بانک پارسیان",
    "063": "بانک اقتصاد نوین",
    "064": "بانک گردشگری",
    "065": "بانک کارآفرین",
    "066": "بانک سامان",
    "069": "بانک پاسارگاد",
    "070": "بانک قرض‌الحسنه رسالت",
    "078": "بانک حکمت ایرانیان",
    "080": "بانک قرض‌الحسنه مهر ایران",
}


def iban_bank_name(iban):
    """تشخیص نام بانک از کد سه‌رقمی داخل شماره شبا (نویسه‌های ۵ تا ۷).

    کاربر در «اطلاعات مالی» پروفایل فقط یک شماره شبا اعلام می‌کند؛ نام بانک
    به‌صورت خودکار از همین شبا تشخیص داده می‌شود و در کیف پول نمایش داده می‌شود.
    برای کدهای ناشناخته، بانک پیش‌فرض «بانک ملی ایران» برگردانده می‌شود.
    """
    iban = re.sub(r"\s+", "", (iban or "")).upper()
    if len(iban) >= 7 and iban.startswith("IR"):
        return _IBAN_BANK_CODES.get(iban[4:7], "بانک ملی ایران")
    return "بانک ملی ایران"


def is_valid_national_id(nid):
    """بررسی شکل کد ملی: دقیقاً ۱۰ رقم (۰-۹ لاتین).

    عمداً «رقم کنترل» (checksum) بررسی نمی‌شود؛ دقیقاً هم‌راستا با ماژول
    ثبت‌نام (accounts.forms.clean_national_id) که فقط الگوی ۱۰ رقمی را
    می‌پذیرد. برخی کدهای ملی واقعیِ ثبت‌شده (مثل 0054413063) طبق الگوریتم
    checksum استاندارد نامعتبر شمرده می‌شوند؛ اگر همین‌جا checksum را الزام
    کنیم، انتقال سکه به کاربری که سیستم او را با همان کد ثبت کرده رد
    می‌شود در حالی که جست‌وجوی زنده او را پیدا می‌کند. اعتبارِ نهاییِ
    «کاربر بودن» کد با جست‌وجو در Profile بررسی می‌شود.
    """
    nid = (nid or "").strip()
    return len(nid) == 10 and nid.isdigit()


def normalize_national_id(value):
    """کد ملی: تبدیل ارقام فارسی/عربی به لاتین + اعتبارسنجی الگوی ۱۰ رقمی.

    ورودی‌های با ارقام فارسی یا عربی (مثل ۰۰۱۳۵۴۲۴۱۹) پذیرفته و نرمال می‌شوند؛
    ورودیِ غیر ۱۰ رقمی با پیام فارسی WalletError رد می‌شود (بدون checksum —
    هم‌راستا با ماژول ثبت‌نام).
    """
    raw = (value or "").strip()
    nid = raw.translate(_FA_AR_DIGITS)
    if not is_valid_national_id(nid):
        raise WalletError("کد ملی معتبر نیست؛ باید دقیقاً ۱۰ رقم باشد.")
    return nid


def _check_amount(coins, minimum, maximum, label):
    try:
        coins = Decimal(str(coins))
    except (InvalidOperation, TypeError, ValueError):
        raise WalletError("تعداد سکه معتبر نیست.")
    if coins <= 0:
        raise WalletError("تعداد سکه باید بیشتر از صفر باشد.")
    if coins != coins.quantize(Decimal("0.01")):
        raise WalletError("تعداد سکه حداکثر ۲ رقم اعشار می‌پذیرد.")
    if minimum is not None and coins < Decimal(str(minimum)):
        raise WalletError(f"حداقل {label} {minimum} سکه است.")
    if maximum is not None and coins > Decimal(str(maximum)):
        raise WalletError(f"حداکثر {label} {maximum} سکه است.")
    return coins


# --------------------------------------------------------------------------- #
# هستهٔ تغییر موجودی (اتمی + دفتر کل)
# --------------------------------------------------------------------------- #
def _apply(user, delta, kind, ref_code="", note="", request=None):
    """اعمال تغییر موجودی به‌صورت اتمی با قفل ردیف.

    delta مثبت = افزایش (اعتبار)، منفی = کاهش (بدهی). مانده هرگز منفی نمی‌شود.
    فراخوان باید داخل transaction.atomic باشد.
    """
    delta = Decimal(str(delta))
    if delta == 0:
        return get_wallet(user)
    wallet = Wallet.objects.select_for_update().get_or_create(user=user)[0]
    new_balance = wallet.balance + delta
    if new_balance < 0:
        raise WalletError(
            "موجودی سکه کافی نیست. ابتدا سکه بخرید یا مقدار کمتری درخواست دهید."
        )
    wallet.balance = new_balance
    wallet.save(update_fields=["balance", "updated_at"])
    CoinLedger.objects.create(
        user=user, kind=kind, amount=delta, balance_after=new_balance,
        ref_code=ref_code, note=note, ip=_ip(request),
    )
    return wallet


# --------------------------------------------------------------------------- #
# خرید / فروش
# --------------------------------------------------------------------------- #
def create_buy_order(user, coins, request=None, notify=True):
    """ثبت سفارش خرید سکه (وضعیت: در انتظار). سکه‌ای کسر نمی‌شود.

    notify=False: فقط سفارش ساخته می‌شود؛ کاربر به صفحهٔ «پرداخت و بارگذاری
    فیش» هدایت می‌شود و تیکت به مدیر پس از ثبت فیش فرستاده می‌شود
    (submit_buy_receipt).
    notify=True (پیش‌فرض؛ سازگاری قدیمی): بلافاصله تیکت درخواست خرید ارسال می‌شود.
    """
    setting = WalletSetting.get()
    if not setting.buy_enabled:
        raise WalletError("خرید سکه در حال حاضر توسط مدیر سیستم غیرفعال است.")
    coins = _check_amount(coins, setting.min_buy_coins, setting.max_buy_coins, "خرید")

    rate = setting.coin_value_rial
    total = (coins * rate).quantize(Decimal("0.01"))
    code = next_code("order", "WAL")
    order = CoinOrder.objects.create(
        code=code, user=user, kind=CoinOrder.KIND_BUY, coins=coins,
        unit_price_rial=rate, total_rial=total,
    )
    _audit(request, user, "wallet.buy.requested", "CoinOrder", order.id,
           meta={"code": code, "coins": str(coins), "total_rial": str(total)})
    if notify:
        _notify_buy_request(request, order)
    return order


def _notify_buy_request(request, order, attachments=()):
    """تیکت درخواست خرید سکه به مدیران (پس از ثبت فیش واریز؛ همراه پیوست فیش)."""
    setting = WalletSetting.get()
    receipt_part = (
        "فیش واریز توسط خریدار بارگذاری شده و در همین تیکت پیوست است."
        if order.payment_receipt
        else "خریدار هنوز فیش واریز بارگذاری نکرده است."
    )
    pay_to = f"حساب «{setting.bank_name}»"
    if setting.receiving_card_number:
        pay_to += f" (کارت: {setting.receiving_card_number})"
    if setting.receiving_iban:
        pay_to += f" (شبا: {setting.receiving_iban})"
    body = (
        f"کاربر درخواست خرید سکه ثبت کرده است.\n\n"
        f"کد سفارش: {order.code}\nتعداد سکه: {order.coins}\n"
        f"نرخ هر سکه (در لحظهٔ ثبت): {order.unit_price_rial} ریال\n"
        f"مبلغ کل: {order.total_rial} ریال\n\n"
        f"{receipt_part}\n"
        f"پس از وصول وجه به {pay_to}، "
        f"سفارش را از پنل مدیریت تأیید کنید تا سکه به کیف پول کاربر افزوده شود."
    )
    _movement_ticket(request, order.user, f"درخواست خرید سکه — {order.code}", body,
                     attachments=attachments)


def submit_buy_receipt(order, upload, request=None):
    """ثبت فیش واریز سفارش خرید + تیکت به مدیران با پیوست فیش.

    - فقط سفارش خریدِ «در انتظار بررسی» و بدون فیش قبلی قابل ثبت است.
    - فایل با اعتبارسنجی نوع/حجم (شبه پیوست تیکت) سنجیده می‌شود.
    - فیش در سفارش ذخیره، زمان ثبت درج و تیکت حاوی تصویر فیش برای مدیران
      ساخته می‌شود تا ادمین با دیدن رسید، واریز را تأیید کند.
    """
    if order.kind != CoinOrder.KIND_BUY:
        raise WalletError("فقط سفارش خرید فیش واریز دارد.")
    if order.status != CoinOrder.STATUS_PENDING:
        raise WalletError("این سفارش قبلاً بررسی شده است.")
    if order.payment_receipt:
        raise WalletError("برای این سفارش قبلاً فیش واریز ثبت شده است.")
    if upload is None or not getattr(upload, "size", 0):
        raise WalletError("تصویر فیش واریز انتخاب نشده است.")

    ext = os.path.splitext(upload.name or "")[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".pdf"}:
        raise WalletError("فقط تصویر فیش (JPG، PNG، WEBP) یا PDF مجاز است.")
    if upload.size > 5 * 1024 * 1024:
        raise WalletError("حجم فایل فیش نباید بیشتر از ۵ مگابایت باشد.")

    with transaction.atomic():
        locked = CoinOrder.objects.select_for_update().get(pk=order.pk)
        if locked.status != CoinOrder.STATUS_PENDING or locked.payment_receipt:
            raise WalletError("این سفارش قبلاً بررسی یا فیش آن ثبت شده است.")
        locked.payment_receipt = upload
        locked.receipt_uploaded_at = timezone.now()
        locked.save(update_fields=["payment_receipt", "receipt_uploaded_at"])
        order = locked

    _audit(request, order.user, "wallet.buy.receipt_uploaded", "CoinOrder", order.id,
           meta={"code": order.code, "file": upload.name})
    # تیکت به مدیر: بدنهٔ توضیح + پیوست تصویر فیش واریز
    _notify_buy_request(request, order, attachments=[upload])
    # «تراکنش‌های اخیر»: فرایند خرید با ثبت فیش/ارسال تیکت نهایی کامل شده است؛
    # همین‌جا (و نه هنگام ثبت سفارش) رکورد دفتر کل ثبت می‌شود — بدون تغییر موجودی
    # (سکهٔ خرید هنوز تأیید نشده و بعداً با تأیید ادمین به‌صورت «خرید سکه» اعتبار می‌گیرد).
    mark_buy_receipt_sent(order, request=request)
    return order


def mark_buy_receipt_sent(order, request=None):
    """ثبت رویداد «ارسال رسید/تیکت خرید» در دفتر کل (بدون تغییر موجودی).

    بخش «تراکنش‌های اخیر» داشبورد، این رکورد را به‌عنوان لحظهٔ کامل‌شدن فرایند
    «کارت به کارت + ارسال رسید» نشان می‌دهد. مبلغ صفر است تا جمع‌های مالی
    دست‌نخورده بمانند؛ کد مرجع، کد سفارش است.
    """
    from django.db.models import Q

    # هر سفارش فقط یک‌بار ثبت شود (جلوگیری از رکورد تکراری در آپلود مجدد)
    exists = CoinLedger.objects.filter(
        Q(kind=CoinLedger.KIND_BUY_REQUEST), ref_code=order.code, user=order.user
    ).exists()
    if exists:
        return None
    wallet = get_wallet(order.user)
    CoinLedger.objects.create(
        user=order.user, kind=CoinLedger.KIND_BUY_REQUEST, amount=Decimal("0"),
        balance_after=wallet.balance, ref_code=order.code,
        note=(
            f"ارسال فیش واریز سفارش خرید {order.code} — مبلغ {order.total_rial} ریال؛ "
            "در انتظار تایید مدیر"
        ),
        ip=_ip(request),
    )
    return True


def validate_sell_request(user, coins):
    """پیش‌اعتبارسنجی درخواست فروش — بدون رزرو سکه/ثبت سفارش.

    برای مرحلهٔ ۱ تأیید دومرحله‌ای فروش: همهٔ قواعد create_sell_order
    (فعال بودن، محدودهٔ مقدار، شبأ مالی و موجودی) پیش از نمایش صفحهٔ تأیید
    سنجیده می‌شود تا کاربر فقط سفارش‌های قابل اجرا را تأیید کند.
    """
    setting = WalletSetting.get()
    if not setting.sell_enabled:
        raise WalletError("فروش سکه در حال حاضر توسط مدیر سیستم غیرفعال است.")
    coins = _check_amount(coins, setting.min_sell_coins, setting.max_sell_coins, "فروش")
    iban = (user.profile.iban or "").strip()
    if not iban:
        raise WalletError(
            "برای فروش سکه، ابتدا «شماره شبا» حساب بانکی خود را در بخش «اطلاعات "
            "مالی» پروفایل ثبت کنید؛ کیف پول همین اطلاعات را برای واریز وجه می‌خواند."
        )
    try:
        normalize_iban(iban)
    except WalletError:
        raise WalletError(
            "شماره شبأ ثبت‌شده در «اطلاعات مالی» پروفایل معتبر نیست "
            "(باید ۲۶ نویسه و با IR شروع شود). لطفاً آن را در پروفایل اصلاح کنید."
        )
    wallet = get_wallet(user)
    if wallet.balance < coins:
        raise WalletError(
            "موجودی سکه کافی نیست. ابتدا سکه بخرید یا مقدار کمتری درخواست دهید."
        )
    return coins


def create_sell_order(user, coins, request=None):
    """ثبت سفارش فروش سکه؛ سکه بلافاصله کسر (رزرو) می‌شود تا خرج مضاعف نشود.

    شبأ واریز وجه از «اطلاعات مالی» پروفایلِ خودِ کاربر خوانده می‌شود (بخش مالی
    پروفایل تنها منبع اطلاعات بانکی است)؛ اگر ثبت نشده باشد، با پیام فارسی کاربر
    به همان بخش هدایت می‌شود. پس از تأیید ادمین، واریز وجه به همین شبا انجام
    می‌شود و در صورت ابطال، سکه به کاربر بازگردانده می‌شود.
    """
    setting = WalletSetting.get()
    if not setting.sell_enabled:
        raise WalletError("فروش سکه در حال حاضر توسط مدیر سیستم غیرفعال است.")
    coins = _check_amount(coins, setting.min_sell_coins, setting.max_sell_coins, "فروش")

    profile = user.profile
    bank_name = (profile.bank_name or "").strip() or "بانک ملی ایران"
    iban = (profile.iban or "").strip()
    if not iban:
        raise WalletError(
            "برای فروش سکه، ابتدا «شماره شبا» حساب بانکی خود را در بخش «اطلاعات "
            "مالی» پروفایل ثبت کنید؛ کیف پول همین اطلاعات را برای واریز وجه می‌خواند."
        )
    try:
        iban = normalize_iban(iban)
    except WalletError:
        raise WalletError(
            "شماره شبأ ثبت‌شده در «اطلاعات مالی» پروفایل معتبر نیست "
            "(باید ۲۶ نویسه و با IR شروع شود). لطفاً آن را در پروفایل اصلاح کنید."
        )

    rate = setting.coin_value_rial
    total = (coins * rate).quantize(Decimal("0.01"))
    code = next_code("order", "WAL")
    with transaction.atomic():
        _apply(user, -coins, CoinLedger.KIND_SELL, ref_code=code,
               note="کسر سکه هنگام ثبت سفارش فروش (تا بررسی توسط ادمین)",
               request=request)
        order = CoinOrder.objects.create(
            code=code, user=user, kind=CoinOrder.KIND_SELL, coins=coins,
            unit_price_rial=rate, total_rial=total, payout_iban=iban,
        )
    _audit(request, user, "wallet.sell.requested", "CoinOrder", order.id,
           meta={"code": code, "coins": str(coins), "total_rial": str(total),
                 "payout_iban": iban, "bank_name": bank_name})
    body = (
        f"کاربر درخواست فروش سکه ثبت کرده است.\n\n"
        f"کد سفارش: {code}\nتعداد سکه: {coins}\n"
        f"نرخ هر سکه (در لحظهٔ ثبت): {rate} ریال\nمبلغ کل: {total} ریال\n"
        f"بانک: {bank_name}\nشبأ واریز وجه (از اطلاعات مالی پروفایل): {iban}\n\n"
        f"سکه به‌محض ثبت سفارش از کیف پول کاربر رزرو شده است. پس از واریز وجه "
        f"به حساب کاربر، سفارش را تأیید کنید؛ در صورت ابطال، سکه بازگردانده می‌شود."
    )
    _movement_ticket(request, user, f"درخواست فروش سکه — {code}", body)
    return order


def approve_order(order, admin, request=None):
    """تأیید سفارش توسط ادمین: خرید → اعتبار سکه؛ فروش → تثبیت (وجه واریز شد)."""
    if order.status != CoinOrder.STATUS_PENDING:
        raise WalletError("فقط سفارش‌های «در انتظار بررسی» قابل تأیید هستند.")
    with transaction.atomic():
        order = CoinOrder.objects.select_for_update().get(pk=order.pk)
        if order.status != CoinOrder.STATUS_PENDING:
            raise WalletError("این سفارش قبلاً بررسی شده است.")
        if order.kind == CoinOrder.KIND_BUY:
            _apply(order.user, order.coins, CoinLedger.KIND_BUY,
                   ref_code=order.code, note="تأیید خرید — وصول وجه",
                   request=request)
        order.status = CoinOrder.STATUS_APPROVED
        order.processed_by = admin
        order.processed_at = timezone.now()
        order.save(update_fields=["status", "processed_by", "processed_at"])

    _audit(request, admin, "wallet.order.approved", "CoinOrder", order.id,
           meta={"code": order.code, "kind": order.kind})
    body = (
        f"سفارش «{order.code}» تأیید شد.\n\n"
        f"نوع: {order.get_kind_display()}\nتعداد سکه: {order.coins}\n"
        f"مبلغ کل: {order.total_rial} ریال\n"
        + (
            "سکهٔ خرید به کیف پول شما افزوده شد."
            if order.kind == CoinOrder.KIND_BUY
            else "درخواست واریز وجه به شبأ شما به بانک ارسال شد."
        )
    )
    _movement_ticket(request, admin, f"تأیید سفارش سکه — {order.code}", body,
                     recipient_user_ids=[order.user_id], include_staff=False)
    _close_related_ticket(
        order, admin, request=request,
        note="نتیجه: سفارش «" + order.code + "» تأیید شد"
             + (" و سکه به کیف پول شما افزوده شد." if order.kind == CoinOrder.KIND_BUY else "."),
    )
    return order


def reject_order(order, admin, note="", request=None):
    """ابطال سفارش توسط ادمین: در فروش، سکهٔ رزروشده به کاربر بازگردانده می‌شود."""
    if order.status != CoinOrder.STATUS_PENDING:
        raise WalletError("فقط سفارش‌های «در انتظار بررسی» قابل ابطال هستند.")
    with transaction.atomic():
        order = CoinOrder.objects.select_for_update().get(pk=order.pk)
        if order.status != CoinOrder.STATUS_PENDING:
            raise WalletError("این سفارش قبلاً بررسی شده است.")
        if order.kind == CoinOrder.KIND_SELL:
            _apply(order.user, order.coins, CoinLedger.KIND_SELL_REFUND,
                   ref_code=order.code,
                   note="بازگشت سکهٔ سفارش فروش ابطال‌شده", request=request)
        order.status = CoinOrder.STATUS_REJECTED
        order.admin_note = (note or "")[:500]
        order.processed_by = admin
        order.processed_at = timezone.now()
        order.save(update_fields=["status", "admin_note", "processed_by", "processed_at"])

    _audit(request, admin, "wallet.order.rejected", "CoinOrder", order.id,
           meta={"code": order.code, "kind": order.kind, "note": note})
    body = (
        f"سفارش «{order.code}» ابطال شد.\n\n"
        f"نوع: {order.get_kind_display()}\nتعداد سکه: {order.coins}\n"
        + (f"دلیل: {note}\n" if note else "")
        + (
            "هیچ سکه‌ای جابه‌جا نشد."
            if order.kind == CoinOrder.KIND_BUY
            else "سکهٔ رزروشدهٔ این سفارش به کیف پول شما بازگردانده شد."
        )
    )
    _movement_ticket(request, admin, f"ابطال سفارش سکه — {order.code}", body,
                     recipient_user_ids=[order.user_id], include_staff=False)
    _close_related_ticket(
        order, admin, request=request,
        note="نتیجه: سفارش «" + order.code + "» ابطال شد"
             + (" — دلیل: " + note if note else "."),
    )
    return order


# --------------------------------------------------------------------------- #
# امنیت انتقال: رمز (PIN) اختیاری + محدودیت نرخ
# --------------------------------------------------------------------------- #
def set_transfer_pin(user, pin):
    """تنظیم رمز انتقال (۴ تا ۶ رقم) — فقط هش ذخیره می‌شود."""
    pin = (pin or "").strip()
    if not pin.isdigit() or not (4 <= len(pin) <= 6):
        raise WalletError("رمز انتقال باید ۴ تا ۶ رقم باشد.")
    profile = user.profile
    profile.transfer_pin = make_password(pin)
    profile.save(update_fields=["transfer_pin"])
    return True


def clear_transfer_pin(user):
    """حذف رمز انتقال؛ در صورت الزامی‌بودن رمز توسط مدیر، مسدود می‌شود."""
    setting = WalletSetting.get()
    if setting.transfer_pin_required:
        raise WalletError(
            "سیستم نیاز به رمز انتقال دارد؛ پاک‌کردن رمز ممکن نیست. "
            "برای تغییر، رمز جدید تعیین کنید."
        )
    profile = user.profile
    profile.transfer_pin = ""
    profile.save(update_fields=["transfer_pin"])
    return True


def has_transfer_pin(user):
    return bool((user.profile.transfer_pin or "").strip())


def verify_transfer_pin(user, pin):
    """بررسی صحت رمز انتقال؛ اگر کاربر رمزی نداشته باشد، قبول می‌کند (برای حالت اختیاری)."""
    stored = (user.profile.transfer_pin or "").strip()
    if not stored:
        return True
    return bool(pin) and check_password(pin, stored)


def _check_rate_limits(user, coins):
    """محدودیت نرخ انتقال برای جلوگیری از سواستفاده (تنظیم توسط ادمین)."""
    setting = WalletSetting.get()
    now = timezone.now()
    if setting.max_transfers_per_hour:
        since = now - timedelta(hours=1)
        recent = CoinTransfer.objects.filter(
            sender=user, created_at__gte=since
        ).count()
        if recent >= setting.max_transfers_per_hour:
            raise WalletError(
                f"سقف {setting.max_transfers_per_hour} انتقال در یک ساعت است؛ "
                "برای انتقال بعدی کمی صبر کنید."
            )
    if setting.max_transfer_coins_per_day > 0:
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        sent = CoinTransfer.objects.filter(
            sender=user, created_at__gte=day_start
        ).aggregate(total=Sum("coins"))["total"] or Decimal("0")
        if Decimal(sent) + coins > setting.max_transfer_coins_per_day:
            raise WalletError(
                f"سقف {setting.max_transfer_coins_per_day} سکه انتقال در روز است؛ "
                "سقف امروز شما کافی نیست."
            )


# --------------------------------------------------------------------------- #
# انتقال سکه بین کاربران (P2P)
# --------------------------------------------------------------------------- #
def transfer_coins(sender, receiver, coins, note="", request=None, author=None):
    """انتقال سکه از فرستنده به گیرنده — اتمی؛ تیکت برای هر دو طرف.

    امنیت: پیش از انتقال، محدودیت نرخ (سقف ساعتی/روزانهٔ تنظیم‌شده توسط ادمین)
    بررسی می‌شود. تأیید رمز انتقال (PIN) وظیفهٔ لایهٔ بالاتر (ویوی مرحلهٔ دوم)
    است تا سرویس عمومی بماند.

    author: نویسندهٔ تیکت/حسابرسی. در انتقالِ کاربر، خودِ فرستنده است (پیش‌فرض)؛
    وقتی ادمین از پنل انتقال «بین دو کاربر» ثبت می‌کند، author=admin می‌شود و تیکت
    برای هر دو طرف (فرستنده و گیرنده) ارسال می‌شود.
    """
    setting = WalletSetting.get()
    if not setting.transfer_enabled:
        raise WalletError("انتقال سکه در حال حاضر توسط مدیر سیستم غیرفعال است.")
    if receiver is None:
        raise WalletError("کاربر گیرنده یافت نشد.")
    if receiver.id == sender.id:
        raise WalletError("انتقال سکه به حساب خودتان ممکن نیست.")
    if not receiver.is_active:
        raise WalletError("حساب کاربر گیرنده فعال نیست.")
    coins = _check_amount(coins, None, None, "انتقال")
    note = (note or "").strip()[:300]
    _check_rate_limits(sender, coins)

    code = next_code("transfer", "TRF")
    with transaction.atomic():
        _apply(sender, -coins, CoinLedger.KIND_TRANSFER_OUT, ref_code=code,
               note=note or "انتقال سکه به کاربر", request=request)
        _apply(receiver, coins, CoinLedger.KIND_TRANSFER_IN, ref_code=code,
               note=note or "دریافت سکه از کاربر", request=request)
        transfer = CoinTransfer.objects.create(
            code=code, sender=sender, receiver=receiver, coins=coins, note=note,
        )

    actor = author or sender
    _audit(request, actor, "wallet.transfer", "CoinTransfer", transfer.id,
           meta={"code": code, "sender": sender.id, "receiver": receiver.id,
                 "coins": str(coins), "note": note})
    base_body = (
        f"کد انتقال: {code}\nمبلغ: {coins} سکه\n"
        + (f"توضیح: {note}\n" if note else "")
        + "موجودی کیف پول شما به‌روزرسانی شد."
    )
    if actor.id != sender.id:
        # انتقالِ ثبت‌شده توسط ادمین: هر دو طرف (فرستنده و گیرنده) گیرندهٔ تیکت می‌شوند
        recipient_ids = [sender.id, receiver.id]
    else:
        recipient_ids = [receiver.id]
    # تیکت «دریافت سکه» برای گیرنده (اعلام افزایش موجودی)
    _movement_ticket(
        request, actor, f"دریافت سکه — {code}",
        f"کاربر «{_user_label(sender)}» مبلغ {coins} سکه به شما منتقل کرد.\n\n"
        + base_body,
        recipient_user_ids=[receiver.id], include_staff=True,
    )
    # تیکت «پرداخت سکه» برای فرستنده (اعلام کسر موجودی)
    _movement_ticket(
        request, actor, f"پرداخت سکه — {code}",
        f"شما مبلغ {coins} سکه به کاربر «{_user_label(receiver)}» منتقل کردید.\n\n"
        + base_body,
        recipient_user_ids=[sender.id], include_staff=True,
    )
    return transfer


def lookup_receiver_preview(value):
    """پیش‌نمایش «کد ملی → نام گیرنده» برای جست‌وجوی زنده در فرم انتقال.

    کد ملی ۱۰ رقمی نرمال‌شده را می‌پذیرد (بدون checksum برای جست‌وجوی زنده) و
    اگر کاربری یافت شود، نام و موبایل او را برمی‌گرداند تا کاربر پیش از ثبت،
    گیرنده را تأیید کند؛ در نبود کاربر، None برمی‌گرداند.
    """
    from accounts.models import Profile

    raw = (value or "").strip().translate(_FA_AR_DIGITS)
    if not raw.isdigit() or len(raw) != 10:
        return None
    profile = (
        Profile.objects.select_related("user", "first_name", "last_name")
        .filter(national_id=raw, user__is_active=True)
        .first()
    )
    if profile is None:
        return None
    return {
        "full_name": profile.full_name,
        "mobile_number": profile.user.mobile_number,
        "national_id": profile.national_id,
    }


def find_user_by_national_id(value):
    """یافتن کاربر با کد ملی معتبر؛ خطای فارسی برای ورودی نامعتبر یا ناموجود.

    فقط «کد ملی ۱۰ رقمی» لازم است — هیچ شناسهٔ دیگری (موبایل و ...) دریافت
    نمی‌شود. ارقام فارسی/عربی پذیرفته و نرمال می‌شوند و الگوی ۱۰ رقمی پیش از
    جستجو بررسی می‌شود (بدون checksum — هم‌راستا با ماژول ثبت‌نام).
    """
    nid = normalize_national_id(value)
    from accounts.models import Profile

    profile = Profile.objects.select_related("user").filter(national_id=nid).first()
    if profile is None:
        raise WalletError("کاربری با این کد ملی در سیستم یافت نشد.")
    return profile.user


# --------------------------------------------------------------------------- #
# هزینهٔ سکهٔ استفاده از ماژول‌ها (تعریف‌شده توسط ادمین)
# --------------------------------------------------------------------------- #
def charge_module_scaled(user, code, units, request=None, note=""):
    """کسر هزینهٔ متغیر یک ماژول: تعرفه × مقدار (مثلاً GB × روز برای فضای ابری).

    برای هزینه‌هایی که به‌ازای «مقدار» (حجم/زمان/...) محاسبه می‌شوند است؛
    مقدار (units) عدد/Decimal است و مبلغ = تعرفهٔ ثبت‌شده × مقدار. با یک
    رکورد دفتر کل و تیکت اطلاع‌رسانی، در یک تراکنش اتمی کسر می‌شود.
    مثال:
        from wallet.services import charge_module_scaled
        charge_module_scaled(user, "cloud_storage", gb * days)
    """
    cost = FeatureCost.objects.filter(code=code, is_active=True).first()
    if cost is None:
        raise WalletError("هزینهٔ سکهٔ تعریف‌شده برای این بخش فعال نیست.")
    try:
        units_dec = Decimal(str(units))
    except (ArithmeticError, ValueError, TypeError):
        raise WalletError("مقدار خرید نامعتبر است.")
    if units_dec <= 0:
        raise WalletError("مقدار خرید باید بزرگ‌تر از صفر باشد.")
    if cost.coins <= 0:
        return None
    total = (Decimal(str(cost.coins)) * units_dec).quantize(Decimal("0.01"))
    with transaction.atomic():
        _apply(user, -total, CoinLedger.KIND_CHARGE, ref_code=cost.code,
               note=note or cost.title, request=request)
    _audit(request, user, "wallet.module.charged", "FeatureCost", cost.id,
           meta={"code": cost.code, "units": str(units_dec), "coins": str(total)})
    _movement_ticket(
        request, user, f"کسر سکه برای «{cost.title}»",
        f"برای «{cost.title}» به تعداد {units_dec} واحد، مبلغ {total} سکه از کیف "
        f"پول شما کسر شد (کد: {cost.code}).",
    )
    return total


def charge_module(user, code, request=None, note=""):
    """کسر سکه برای استفاده از یک بخش/ماژول (هزینه در پنل مدیریت تعریف می‌شود).

    اگر هزینه فعال نباشد یا موجودی کافی نباشد، WalletError با پیام فارسی می‌دهد.
    مثال استفاده در هر ماژول:
        from wallet.services import charge_module
        charge_module(request.user, "bulk_ticket", request=request)
    """
    cost = FeatureCost.objects.filter(code=code, is_active=True).first()
    if cost is None:
        raise WalletError("هزینهٔ سکهٔ تعریف‌شده برای این بخش فعال نیست.")
    if cost.coins <= 0:
        return None
    with transaction.atomic():
        _apply(user, -cost.coins, CoinLedger.KIND_CHARGE, ref_code=cost.code,
               note=note or cost.title, request=request)
    _audit(request, user, "wallet.module.charged", "FeatureCost", cost.id,
           meta={"code": cost.code, "coins": str(cost.coins)})
    _movement_ticket(
        request, user, f"کسر سکه برای «{cost.title}»",
        f"برای استفاده از «{cost.title}» مبلغ {cost.coins} سکه از کیف پول شما "
        f"کسر شد (کد: {cost.code}).",
    )
    return cost


def charge_module_days(user, code, days, request=None, note=""):
    """کسر هزینهٔ یک ماژول به‌ازای چند روز (تعرفهٔ ۲۴ ساعته).

    مبلغ = هزینهٔ روزانهٔ تعرفه × تعداد روزها؛ در یک تراکنش واحد، با یک
    رکورد دفتر کل و یک تیکت اطلاع‌رسانی کسر می‌شود.
    مثال (ماژول تبلیغات):
        from wallet.services import charge_module_days
        charge_module_days(user, "ad_submission", days, request=request)
    """
    cost = FeatureCost.objects.filter(code=code, is_active=True).first()
    if cost is None:
        raise WalletError("هزینهٔ سکهٔ تعریف‌شده برای این بخش فعال نیست.")
    days = int(days or 0)
    if days < 1:
        raise WalletError("تعداد روزها باید حداقل ۱ روز باشد.")
    if cost.coins <= 0:
        return None
    total = (Decimal(str(cost.coins)) * Decimal(days)).quantize(Decimal("0.01"))
    with transaction.atomic():
        _apply(user, -total, CoinLedger.KIND_CHARGE, ref_code=cost.code,
               note=note or f"{cost.title} ({days} روز)", request=request)
    _audit(request, user, "wallet.module.charged", "FeatureCost", cost.id,
           meta={"code": cost.code, "days": days, "coins": str(total)})
    _movement_ticket(
        request, user, f"کسر سکه برای «{cost.title}»",
        f"برای «{cost.title}» به‌ازای {days} روز، مبلغ {total} سکه "
        f"(روزانه {cost.coins} سکه) از کیف پول شما کسر شد (کد: {cost.code}).",
    )
    return cost


def refund_module_charge(user, coins, *, fee_percent=0, ref_code="", subject="",
                         note="", admin=None, request=None, notify=True):
    """بازگشت (بخشی از) هزینهٔ کسرشدهٔ یک ماژول به کیف پول، پس از کسر کارمزد.

    ``coins`` = مبلغ کسرشده؛ ``fee_percent`` = درصد کارمزدِ نگه‌داشته‌شده (مثلاً ۱۰).
    مبلغ بازگشتی = coins − کارمزد با نوع «refund» در دفتر کل ثبت می‌شود. با
    ``notify=True`` تیکت مالی به کاربر و کارکنان ساخته می‌شود؛ جلوگیری از بازگشتِ
    مضاعف وظیفهٔ فراخواننده است (هم‌زمان با تغییر وضعیت رکورد، داخل
    transaction.atomic فراخوانی شود).
    خروجی: (refund, fee) به‌صورت Decimal.
    """
    try:
        coins = Decimal(str(coins))
        pct = Decimal(str(fee_percent or 0))
    except (InvalidOperation, TypeError, ValueError):
        raise WalletError("مبلغ بازگشت نامعتبر است.")
    if coins <= 0:
        raise WalletError("مبلغ قابل بازگشت باید بیشتر از صفر باشد.")
    if pct < 0 or pct > 100:
        raise WalletError("درصد کارمزد نامعتبر است.")
    fee = (coins * pct / Decimal(100)).quantize(Decimal("0.01"))
    refund = (coins - fee).quantize(Decimal("0.01"))
    with transaction.atomic():
        if refund > 0:
            _apply(user, refund, CoinLedger.KIND_REFUND, ref_code=ref_code or "REFUND",
                   note=note or "بازگشت هزینهٔ ماژول", request=request)
    _audit(request, admin or user, "wallet.module.refunded", "Wallet", None,
           meta={"user_id": user.id, "paid": str(coins), "fee": str(fee),
                 "refund": str(refund), "ref_code": ref_code})
    if notify:
        _movement_ticket(
            request, admin or user, subject or "بازگشت هزینه به کیف پول",
            f"از مبلغ {coins} سکهٔ پرداختی، کارمزد {fee} سکه کسر و {refund} سکه به کیف پول "
            f"{_user_label(user)} بازگردانده شد. {note}".strip(),
            recipient_user_ids=[user.id],
        )
    return refund, fee


def require_charge(user, code, request=None, exempt_staff=True):
    """کسر سکه برای یک بخش/ماژول با پیام خطای واضح در صورت نبودن هزینه یا موجودی.

    - اگر هزینه تعریف/فعال نباشد یا صفر باشد، بدون خطا عبور می‌کند (ماژول‌ها
      می‌توانند به‌صورت شرطی متصل شوند).
    - اگر کاربر کارکن باشد و exempt_staff=True باشد، هزینه گرفته نمی‌شود
      (کارکنان اپراتورند، نه مصرف‌کننده).
    """
    if exempt_staff and user.is_staff:
        return None
    cost = FeatureCost.objects.filter(code=code, is_active=True).first()
    if cost is None or cost.coins <= 0:
        return None
    charge_module(user, code, request=request)
    return cost


# --------------------------------------------------------------------------- #
# پاداش سکه بر اساس قانونِ تعریف‌شده توسط ادمین (معرف، مطالعه در مجله و ...)
# --------------------------------------------------------------------------- #
_REWARD_REF_PREFIXES = {
    "referral": "REF",
    "magazine_watch": "MAG",
}


def reward_count(user, code):
    """تعداد پاداش‌های قبلیِ همان قانون برای کاربر (برای سقف «هر کاربر»).

    با پیشوندِ ref_code هر قانون شمارش می‌شود تا پاداش‌های دیگر انواع (خرید و ...)
    در شمارش نیایند؛ اگر قانونِ ناشناخته‌ای باشد، سه حرف نخست کد پیش‌فرض است.
    """
    prefix = _REWARD_REF_PREFIXES.get(code, (code or "")[:3].upper())
    return CoinLedger.objects.filter(
        user=user, kind=CoinLedger.KIND_REWARD, ref_code__startswith=prefix
    ).count()


def reward_coins(user, coins, *, ref_code="", note="", request=None):
    """افزودن سکهٔ پاداش به کیف پول کاربر (میزان طبق قانون RewardRule ادمین).

    فقط «افزایش» انجام می‌دهد و در دفتر کل با نوع «reward» ثبت می‌شود. تیکت
    اطلاع‌رسانی/حسابرسیِ تخصصی هر پاداش (مثل معرفی) وظیفهٔ فراخواننده است تا
    هر بخش بتواند پیام مخصوص خودش را بسازد.
    """
    try:
        coins = Decimal(str(coins))
    except (InvalidOperation, TypeError, ValueError):
        raise WalletError("میزان پاداش معتبر نیست.")
    if coins <= 0:
        raise WalletError("میزان پاداش باید بیشتر از صفر باشد.")
    with transaction.atomic():
        wallet = _apply(user, coins, CoinLedger.KIND_REWARD,
                        ref_code=ref_code or "REW",
                        note=note or "پاداش سکه", request=request)
    _audit(request, user, "wallet.reward", "Wallet", wallet.id,
           meta={"coins": str(coins), "note": note, "ref_code": ref_code})
    return wallet


def wallet_balance(user):
    """موجودی کیف پول کاربر (بدون ساخت کیف پول در صورت نبود)."""
    wallet = Wallet.objects.filter(user=user).first()
    return wallet.balance if wallet else Decimal("0")


# --------------------------------------------------------------------------- #
# تبدیل خودکار امتیاز به سکه (اتصال «تعرفه امتیازها» به کیف پول)
# --------------------------------------------------------------------------- #
def convert_unconverted_points(profile, request=None):
    """تبدیل امتیازهای هنوز-تبدیل‌نشدهٔ کاربر به سکه و تجمیع با موجودی کیف پول.

    طبق دستورالعمل، هر امتیازی که کاربر می‌گیرد (طبق «تعرفه امتیازها») معادل
    سکه‌اش نیز بر اساس نرخ «ارزش هر سکه (امتیاز)» به کیف پول او افزوده می‌شود:
    coins = امتیازهای جدید ÷ coin_value_point. برای اینکه هر امتیاز فقط یک‌بار
    تبدیل شود، نقطهٔ آبخست (watermark) در profile.extra_data["points_converted"]
    نگه داشته می‌شود؛ اگر ادمین نرخ را تغییر دهد، فقط امتیازهای جدید با نرخ
    جدید تبدیل می‌شوند. امتیازِ سطح کاربری دست‌نخورده می‌ماند. اگر نرخ صفر
    باشد، تبدیل انجام نمی‌شود. خروجی: کیف پول به‌روزشده یا None.
    """
    from accounts.models import Profile as _Profile

    setting = WalletSetting.get()
    rate = int(setting.coin_value_point or 0)
    if rate <= 0:
        return None
    with transaction.atomic():
        fresh = (
            _Profile.objects.select_for_update()
            .select_related("user")
            .get(pk=profile.pk)
        )
        score = int(fresh.user_score or 0)
        converted = int((fresh.extra_data or {}).get("points_converted") or 0)
        delta = score - converted
        if delta <= 0:
            return None
        coins = (Decimal(delta) / Decimal(rate)).quantize(Decimal("0.01"))
        if coins <= 0:
            return None
        wallet = _apply(
            fresh.user, coins, CoinLedger.KIND_REWARD, ref_code="PTS",
            note="تبدیل امتیاز به سکه (تعرفه)", request=request,
        )
        merged = dict(fresh.extra_data or {})
        merged["points_converted"] = score
        fresh.extra_data = merged
        fresh.save(update_fields=["extra_data", "updated_at"])
    return wallet


# --------------------------------------------------------------------------- #
# تنظیم دستی / تغییر نرخ (فقط ادمین)
# --------------------------------------------------------------------------- #
def adjust_balance(admin, user, amount, note="", request=None):
    """تنظیم دستی موجودی توسط ادمین (amount مثبت یا منفی)."""
    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        raise WalletError("مبلغ تنظیم معتبر نیست.")
    if amount == 0:
        raise WalletError("مبلغ تنظیم باید غیرصفر باشد.")
    with transaction.atomic():
        wallet = _apply(user, amount, CoinLedger.KIND_ADJUST,
                        ref_code="ADM", note=note or "تنظیم دستی توسط ادمین",
                        request=request)
    _audit(request, admin, "wallet.adjust", "Wallet", wallet.id,
           meta={"user": user.id, "amount": str(amount), "note": note})
    body = (
        f"موجودی سکهٔ حساب شما توسط مدیر سیستم تنظیم شد.\n\n"
        f"مبلغ: {amount} سکه\n"
        + (f"دلیل: {note}\n" if note else "")
        + f"ماندهٔ فعلی: {wallet.balance} سکه"
    )
    _movement_ticket(request, admin, "تنظیم موجودی سکه توسط مدیر", body,
                     recipient_user_ids=[user.id], include_staff=False)
    return wallet


def set_coin_value(admin, value_rial, note="", request=None):
    """تغییر نرخ هر سکه توسط ادمین + ثبت تاریخچه و حسابرسی."""
    try:
        value_rial = Decimal(str(value_rial))
    except (InvalidOperation, TypeError, ValueError):
        raise WalletError("نرخ سکه معتبر نیست.")
    if value_rial <= 0:
        raise WalletError("نرخ هر سکه باید بیشتر از صفر باشد.")
    setting = WalletSetting.get()
    old = setting.coin_value_rial
    if value_rial == old:
        return setting, False
    setting.coin_value_rial = value_rial
    setting.save(update_fields=["coin_value_rial", "updated_at"])
    CoinPriceHistory.objects.create(
        value_rial=value_rial, changed_by=admin, note=note,
    )
    _audit(request, admin, "wallet.rate.changed", "WalletSetting", setting.pk,
           meta={"old": str(old), "new": str(value_rial), "note": note})
    return setting, True


# --------------------------------------------------------------------------- #
# آمار (برای پنل مدیریت)
# --------------------------------------------------------------------------- #
def total_coins_in_circulation():
    """مجموع سکه‌های موجود در کیف پول همهٔ کاربران."""
    from django.db.models import Sum

    return Wallet.objects.aggregate(total=Sum("balance"))["total"] or Decimal("0")