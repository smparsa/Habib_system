"""مدل‌های ماژول «سکه و کیف پول».

اصول امنیتی:
- هر تغییر موجودی از «دفتر کل» (CoinLedger) می‌گذرد که فقط-افزودنی است
  (هیچ endpoint ویرایش/حذف ندارد) و ماندهٔ پس از هر تراکنش (balance_after)
  در آن ثبت می‌شود تا بازسازی موجودی در هر لحظه ممکن باشد.
- همهٔ جابه‌جایی‌ها با SELECT ... FOR UPDATE اتمی اعمال می‌شوند تا دو
  تراکنش هم‌زمان نتوانند از یک موجودی دوبار برداشت کنند (جلوگیری از خرج مضاعف).
- قیمت هر سکه هنگام سفارش «عکس‌برداری» (snapshot) می‌شود و تغییرات نرخ در
  CoinPriceHistory ثبت می‌گردد.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models


# --------------------------------------------------------------------------- #
# تنظیمات کیف پول (تک‌رکوردی)
# --------------------------------------------------------------------------- #
class WalletSetting(models.Model):
    """تنظیمات سراسری سکه/کیف پول که ادمین در پنل مدیریت ویرایش می‌کند."""

    coin_value_rial = models.DecimalField(
        "ارزش هر سکه (ریال)", max_digits=14, decimal_places=2, default=1000,
    )
    coin_value_point = models.PositiveIntegerField(
        "ارزش هر سکه (امتیاز)", default=1,
        help_text="هر یک سکه معادل چند امتیازِ کاربری است (برای کل برنامه).",
    )
    buy_enabled = models.BooleanField("فعال بودن خرید سکه", default=True)
    sell_enabled = models.BooleanField("فعال بودن فروش سکه", default=True)
    transfer_enabled = models.BooleanField("فعال بودن انتقال سکه به دیگران", default=True)
    # امنیت انتقال: رمز (PIN) اختیاری + محدودیت نرخ برای جلوگیری از سواستفاده
    transfer_pin_required = models.BooleanField(
        "الزامی بودن رمز انتقال برای همهٔ کاربران", default=False,
        help_text="اگر فعال شود، هیچ انتقالی بدون رمزِ تنظیم‌شده توسط کاربر انجام نمی‌شود.",
    )
    max_transfers_per_hour = models.PositiveSmallIntegerField(
        "سقف تعداد انتقال در یک ساعت (۰ = بدون محدودیت)", default=0,
    )
    max_transfer_coins_per_day = models.DecimalField(
        "سقف مجموع سکهٔ انتقال در یک روز (۰ = بدون محدودیت)",
        max_digits=14, decimal_places=2, default=0,
    )
    min_buy_coins = models.PositiveIntegerField(
        "حداقل سکهٔ خرید (عدد صحیح)", default=1,
    )
    max_buy_coins = models.PositiveIntegerField(
        "حداکثر سکهٔ خرید (عدد صحیح)", default=100000,
    )
    min_sell_coins = models.PositiveIntegerField(
        "حداقل سکهٔ فروش (عدد صحیح)", default=1,
    )
    max_sell_coins = models.PositiveIntegerField(
        "حداکثر سکهٔ فروش (عدد صحیح)", default=100000,
    )
    bank_name = models.CharField("نام بانک", max_length=100, default="بانک ملی ایران")
    receiving_iban = models.CharField(
        "شبأ دریافت وجه (خرید سکه)", max_length=34, blank=True,
        help_text="شماره شبأ بانک ملی که خریداران مبلغ سکه را به آن واریز می‌کنند.",
    )
    receiving_card_number = models.CharField(
        "شماره کارت دریافت وجه (خرید سکه)", max_length=20, blank=True,
        help_text="شماره کارت بانکی که خریداران مبلغ سکه را به آن واریز می‌کنند "
                  "(۱۶ رقم، در کنار شبا نمایش داده می‌شود).",
    )
    coin_image = models.FileField(
        "تصویر/لوگوی سکه", upload_to="coin/", blank=True, null=True,
        help_text="تصویر سکهٔ هاب در صفحهٔ پرداخت خرید نمایش داده می‌شود "
                  "(JPG/PNG/WebP؛ ترجیحاً مربعی).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات کیف پول"
        verbose_name_plural = "تنظیمات کیف پول"

    def __str__(self):
        return f"هر سکه = {self.coin_value_rial} ریال"

    @classmethod
    def get(cls):
        """نمونهٔ تک‌رکوردی تنظیمات (pk=1) را برمی‌گرداند و اگر نبود می‌سازد."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class CoinPriceHistory(models.Model):
    """تاریخچهٔ تغییر نرخ هر سکه — سند حسابرسی تغییرات قیمت."""

    value_rial = models.DecimalField("نرخ جدید (ریال)", max_digits=14, decimal_places=2)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+", verbose_name="تغییردهنده",
    )
    note = models.CharField("توضیح", max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تاریخچهٔ نرخ سکه"
        verbose_name_plural = "تاریخچهٔ نرخ سکه"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.value_rial} ریال ({self.created_at:%Y-%m-%d %H:%M})"


# --------------------------------------------------------------------------- #
# هزینهٔ سکهٔ استفاده از ماژول‌ها (تعریف‌شده توسط ادمین)
# --------------------------------------------------------------------------- #
class FeatureCost(models.Model):
    """هزینهٔ سکه برای هر بخش از برنامه/ماژول — توسط ادمین در پنل تعریف می‌شود.

    موتور اجرا: wallet.services.charge_module(user, code) — کافی است هر ماژول
    هنگام استفاده، این تابع را صدا بزند؛ اگر موجودی کافی نباشد خطای فارسی می‌گیرد.
    """

    code = models.CharField("کد", max_length=60, unique=True)
    title = models.CharField("عنوان (بخش/ماژول)", max_length=150)
    description = models.CharField("توضیح", max_length=300, blank=True)
    coins = models.DecimalField(
        "هزینه (سکه)", max_digits=14, decimal_places=2, default=0,
        help_text="تعداد سکه‌ای که هنگام استفادهٔ کاربر از این بخش کسر می‌شود.",
    )
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "هزینهٔ سکهٔ ماژول"
        verbose_name_plural = "هزینه‌های سکهٔ ماژول‌ها"
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.coins} سکه)"


# --------------------------------------------------------------------------- #
# پاداش سکه (RewardRule): عنوان و میزان پاداشِ هر فعالیت را ادمین تعیین می‌کند
# --------------------------------------------------------------------------- #
class RewardRule(models.Model):
    """سرفصل «تعرفه امتیازها» برای فعالیت‌های کاربر — عنوان و میزان را ادمین تعیین می‌کند.

    هر سرفصل یک «کد» دارد که بخش مربوطه هنگام امتیازدهی صدا می‌زند:
    - referral       → معرفی کاربر جدید (هر نفرِ معرفی‌شده پس از تکمیل اطلاعات شخصی)
    - magazine_watch → ماندن/مطالعه در «مجله دانستنی‌ها» (هر چرخهٔ ۳۰ دقیقه)
    ادمین در «پنل مدیریت ← تعرفه امتیازها» عنوان، واحد، میزان امتیاز و فعال/غیرفعال
    بودن هر سرفصل را مدیریت می‌کند؛ موتور اجرا: accounts.scoring.award(user, code).
    """

    code = models.CharField("کد", max_length=60, unique=True)
    title = models.CharField("عنوان پاداش", max_length=150)
    unit_label = models.CharField(
        "واحد (به‌ازای چه چیزی؟)", max_length=150, blank=True,
        help_text="مثل: «هر نفر معرفی‌شده»، «هر ۳۰ دقیقه مطالعه در مجله».",
    )
    description = models.CharField("توضیح", max_length=300, blank=True)
    coins = models.DecimalField(
        "میزان پاداش (سکه)", max_digits=14, decimal_places=2, default=0,
        help_text="تعداد سکه‌ای که به‌ازای هر واحد به کیف پول کاربر افزوده می‌شود.",
    )
    max_per_user = models.PositiveIntegerField(
        "سقف دریافت برای هر کاربر", null=True, blank=True,
        help_text="حداکثر چند بار یک کاربر می‌تواند این پاداش را بگیرد "
                  "(مثلاً برای «معرفی»: هر معرف حداکثر چند نفر را معرفی کند). "
                  "خالی = بدون محدودیت.",
    )
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "سرفصل تعرفه امتیاز"
        verbose_name_plural = "تعرفه امتیازها"
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.coins} سکه)"

    @classmethod
    def get_active(cls, code):
        """قانون فعال با کد داده‌شده (یا None در نبود/غیرفعال بودن)."""
        return cls.objects.filter(code=code, is_active=True).first()


# --------------------------------------------------------------------------- #
# کیف پول کاربر
# --------------------------------------------------------------------------- #
class Wallet(models.Model):
    """کیف پول هر کاربر — موجودی صرفاً از طریق دفتر کل تغییر می‌کند."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="wallet", verbose_name="کاربر",
    )
    balance = models.DecimalField(
        "موجودی (سکه)", max_digits=16, decimal_places=2, default=0,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "کیف پول"
        verbose_name_plural = "کیف پول‌ها"

    def __str__(self):
        return f"{self.user} — {self.balance} سکه"

    @property
    def value_rial(self):
        from .services import current_rate

        return (self.balance * current_rate()).quantize(Decimal("0.01"))


class CoinLedger(models.Model):
    """دفتر کل سکه — فقط-افزودنی؛ هیچ عملیات ویرایش/حذفی ندارد."""

    KIND_BUY = "buy"
    KIND_BUY_REQUEST = "buy_request"
    KIND_SELL = "sell"
    KIND_SELL_REFUND = "sell_refund"
    KIND_TRANSFER_OUT = "transfer_out"
    KIND_TRANSFER_IN = "transfer_in"
    KIND_CHARGE = "charge"
    KIND_REFUND = "refund"
    KIND_ADJUST = "adjust"
    KIND_REWARD = "reward"
    KIND_CHOICES = [
        (KIND_BUY, "خرید سکه"),
        (KIND_BUY_REQUEST, "ارسال فیش واریز خرید"),
        (KIND_SELL, "فروش سکه"),
        (KIND_SELL_REFUND, "بازگشت سکه (ابطال فروش)"),
        (KIND_TRANSFER_OUT, "انتقال سکه به کاربر"),
        (KIND_TRANSFER_IN, "دریافت سکه از کاربر"),
        (KIND_CHARGE, "هزینهٔ استفاده از ماژول"),
        (KIND_REFUND, "بازگشت هزینه"),
        (KIND_ADJUST, "تنظیم توسط ادمین"),
        (KIND_REWARD, "پاداش (امتیاز)"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="coin_ledger", verbose_name="کاربر",
    )
    kind = models.CharField("نوع تراکنش", max_length=20, choices=KIND_CHOICES)
    amount = models.DecimalField(
        "مبلغ (سکه)", max_digits=16, decimal_places=2,
        help_text="مثبت = افزایش موجودی، منفی = کاهش موجودی",
    )
    balance_after = models.DecimalField(
        "ماندهٔ پس از تراکنش", max_digits=16, decimal_places=2,
    )
    ref_code = models.CharField(
        "کد مرجع", max_length=40, blank=True,
        help_text="کد سفارش (WAL-...) یا انتقال (TRF-...) مرتبط",
    )
    note = models.CharField("توضیح", max_length=300, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "رکورد دفتر کل"
        verbose_name_plural = "دفتر کل سکه"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="ledger_user_dt"),
        ]

    def __str__(self):
        return f"{self.user} {self.amount:+} ({self.kind})"


# --------------------------------------------------------------------------- #
# سفارش‌های خرید/فروش سکه (مشابه سامانهٔ معاملاتی)
# --------------------------------------------------------------------------- #
class CoinOrder(models.Model):
    """سفارش خرید یا فروش سکه؛ نرخ در لحظهٔ ثبت عکس‌برداری می‌شود.

    - خرید: پس از تأیید ادمین (وصول وجه)، سکه به کیف پول افزوده می‌شود.
    - فروش: در لحظهٔ ثبت، سکه از کیف پول کسر (رزرو) می‌شود تا خرج مضاعف نشود؛
      پس از تأیید ادمین، واریز وجه به شبأ کاربر انجام می‌شود و در صورت ابطال،
      سکه به کاربر بازگردانده می‌شود.
    """

    KIND_BUY = "buy"
    KIND_SELL = "sell"
    KIND_CHOICES = [
        (KIND_BUY, "خرید سکه"),
        (KIND_SELL, "فروش سکه"),
    ]
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "در انتظار بررسی"),
        (STATUS_APPROVED, "تأییدشده"),
        (STATUS_REJECTED, "ابطال‌شده"),
    ]

    code = models.CharField("کد سفارش", max_length=40, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="coin_orders", verbose_name="کاربر",
    )
    kind = models.CharField("نوع", max_length=10, choices=KIND_CHOICES)
    coins = models.DecimalField("تعداد سکه", max_digits=14, decimal_places=2)
    unit_price_rial = models.DecimalField(
        "نرخ هر سکه هنگام ثبت (ریال)", max_digits=14, decimal_places=2,
    )
    total_rial = models.DecimalField("مبلغ کل (ریال)", max_digits=16, decimal_places=2)
    payout_iban = models.CharField(
        "شبأ دریافت وجه (فروش)", max_length=34, blank=True,
        help_text="برای فروش سکه: شماره شبأ بانک ملی که مبلغ به آن واریز می‌شود.",
    )
    payment_receipt = models.FileField(
        "فیش واریز (خرید)", upload_to="wallet_receipts/%Y/%m/", blank=True, null=True,
        help_text="تصویر فیش واریزی که خریدار در صفحهٔ پرداخت بارگذاری می‌کند.",
    )
    receipt_uploaded_at = models.DateTimeField(
        "زمان بارگذاری فیش", null=True, blank=True,
    )
    status = models.CharField(
        "وضعیت", max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING,
        db_index=True,
    )
    admin_note = models.CharField("یادداشت ادمین", max_length=500, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+", verbose_name="بررسی‌کننده",
    )
    processed_at = models.DateTimeField("زمان بررسی", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "سفارش سکه"
        verbose_name_plural = "سفارش‌های سکه"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="order_user_dt"),
            models.Index(fields=["status", "kind", "-created_at"], name="order_status_kind"),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_kind_display()})"


# --------------------------------------------------------------------------- #
# انتقال سکه بین کاربران (P2P)
# --------------------------------------------------------------------------- #
class CoinTransfer(models.Model):
    """انتقال سکه از یک کاربر به کاربر دیگر — به‌محض ثبت نهایی می‌شود."""

    code = models.CharField("کد انتقال", max_length=40, unique=True, editable=False)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="sent_transfers", verbose_name="فرستنده",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="received_transfers", verbose_name="گیرنده",
    )
    coins = models.DecimalField("تعداد سکه", max_digits=14, decimal_places=2)
    note = models.CharField("توضیح", max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "انتقال سکه"
        verbose_name_plural = "انتقال‌های سکه"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sender", "-created_at"], name="trf_sender_dt"),
            models.Index(fields=["receiver", "-created_at"], name="trf_receiver_dt"),
        ]

    def __str__(self):
        return f"{self.code}: {self.sender} → {self.receiver} ({self.coins})"


# --------------------------------------------------------------------------- #
# شمارندهٔ کدهای سفارش/انتقال
# --------------------------------------------------------------------------- #
class WalletCounter(models.Model):
    """شمارندهٔ داخلی برای تولید کد WAL-/TRF- (مشابه شمارندهٔ تیکت)."""

    kind = models.CharField("نوع", max_length=20)
    year = models.PositiveSmallIntegerField("سال")
    seq = models.PositiveBigIntegerField("آخرین شماره", default=0)

    class Meta:
        verbose_name = "شمارندهٔ کیف پول"
        verbose_name_plural = "شمارنده‌های کیف پول"
        constraints = [
            models.UniqueConstraint(fields=["kind", "year"], name="uniq_wallet_counter"),
        ]

    def __str__(self):
        return f"{self.kind}-{self.year}: {self.seq}"