"""مدل‌های ماژول «پشتیبان‌گیری و بازیابی» دیتابیس (فقط ادمین).

فایل‌های پشتیبان روی دیسک (BACKUP_DIR / db_backups) نگهداری می‌شوند و این
جدول‌ها فقط ابردادهٔ هر نسخه را ثبت می‌کنند تا در پنل مدیریت فهرست شوند.
"""

from django.conf import settings
from django.db import models

BACKUP_KIND_MANUAL = "manual"
BACKUP_KIND_AUTO = "auto"
BACKUP_KIND_CHOICES = [
    (BACKUP_KIND_MANUAL, "دستی"),
    (BACKUP_KIND_AUTO, "خودکار"),
]

BACKUP_STATUS_OK = "ok"
BACKUP_STATUS_FAILED = "failed"
BACKUP_STATUS_CHOICES = [
    (BACKUP_STATUS_OK, "موفق"),
    (BACKUP_STATUS_FAILED, "ناموفق"),
]


class BackupSetting(models.Model):
    """تنظیمات پشتیبان‌گیری (تک‌رکوردی؛ شبیه WalletSetting)."""

    auto_enabled = models.BooleanField(
        "فعال بودن پشتیبان‌گیری خودکار",
        default=True,
        help_text="در حالی که سرور برنامه روشن است، به‌صورت دوره‌ای پشتیبان خودکار گرفته می‌شود.",
    )
    interval_minutes = models.PositiveIntegerField(
        "بازهٔ پشتیبان‌گیری خودکار (دقیقه)",
        default=1440,
        help_text="مثلاً 1440 = هر ۲۴ ساعت یک نسخه. هرچه کمتر، فایل‌های بیشتری ساخته می‌شود.",
    )
    keep_count = models.PositiveIntegerField(
        "تعداد نسخهٔ خودکارِ نگه‌داری‌شده",
        default=30,
        help_text="قدیمی‌ترین نسخه‌های خودکار فراتر از این تعداد به‌طور خودکار حذف می‌شوند "
        "(نسخه‌های دستی حذف نمی‌شوند).",
    )
    folder = models.CharField(
        "پوشهٔ نگهداری فایل‌های پشتیبان",
        max_length=500,
        blank=True,
        help_text="خالی = پوشهٔ پیش‌فرض کنار پروژه (db_backups). مسیر دلخواه مطلق می‌توانید وارد کنید.",
    )
    sync_folder = models.CharField(
        "کپی خودکار به پوشهٔ درایو/فضای ابری",
        max_length=500,
        blank=True,
        help_text="مسیر یک پوشهٔ دیگر (مثلاً پوشهٔ همگام‌سازی‌شدهٔ گوگل‌درایو یا درایو شبکه) — پس از هر پشتیبان موفق، یک کپی از فایل به اینجا فرستاده می‌شود. خالی = بدون کپی.",
    )
    stale_after_days = models.PositiveIntegerField(
        "هشدار پس از چند روز بدون پشتیبان موفق",
        default=3,
        help_text="اگر آخرین پشتیبان موفقِ این‌قدر روز پیش باشد، داشبورد مدیریت هشدار نشان می‌دهد.",
    )
    last_auto_at = models.DateTimeField(
        "آخرین پشتیبان خودکار", null=True, blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات پشتیبان‌گیری"
        verbose_name_plural = "تنظیمات پشتیبان‌گیری"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class BackupFile(models.Model):
    """ابردادهٔ یک فایل پشتیبان که در پوشهٔ پشتیبان ذخیره شده است."""

    filename = models.CharField("نام فایل", max_length=200, unique=True)
    kind = models.CharField("نوع", max_length=10, choices=BACKUP_KIND_CHOICES, default=BACKUP_KIND_MANUAL)
    status = models.CharField("وضعیت", max_length=10, choices=BACKUP_STATUS_CHOICES, default=BACKUP_STATUS_OK)
    title = models.CharField(
        "نام/برچسب دلخواه", max_length=200, blank=True,
        help_text="مثلاً «پیش از تغییر ساختار جدول‌ها». برای نسخه‌های خودکار خالی است.",
    )
    note = models.TextField(
        "توضیح", blank=True,
        help_text="توضیح دلخواه ادمین دربارهٔ این نسخه (نمایش در فهرست).",
    )
    error = models.TextField("خطا", blank=True)
    size_bytes = models.BigIntegerField("اندازه (بایت)", default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="ایجادکننده (نسخهٔ دستی)",
    )
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)

    class Meta:
        verbose_name = "فایل پشتیبان"
        verbose_name_plural = "فایل‌های پشتیبان"
        ordering = ["-created_at"]

    def __str__(self):
        return self.filename


class BreakingNews(models.Model):
    """«اخبار فوری» هدر برنامه (فقط ادمین).

    یک جملهٔ خبری (حداکثر ۵۰۰ کاراکتر) که در بازهٔ زمانیِ تعیین‌شده (از تاریخ/ساعت
    تا تاریخ/ساعت) به‌صورت متن متحرکِ خطی (راست‌به‌چپ: حرکت از چپ به راست) در بالای
    هدرِ همهٔ کاربرانِ واردشده — کنار فیلد جستجو — به‌صورت فقط‌خواندنی نمایش داده
    می‌شود. چند خبر می‌تواند هم‌زمان فعال باشد؛ به‌ترتیبِ اولویت (sort_order)،
    پشت‌سرهم و با سرعتِ هر خبر نمایش می‌شوند.
    """

    text = models.CharField(
        "متن خبر", max_length=500,
        help_text="حداکثر ۵۰۰ کاراکتر — یک جملهٔ روان؛ در هدر کاربران به‌صورت فقط‌خواندنی می‌چرخد.",
    )
    show_from = models.DateTimeField(
        "شروع نمایش (تاریخ و ساعت)",
        help_text="از این لحظه خبر در هدر نمایش داده می‌شود.",
    )
    show_until = models.DateTimeField(
        "پایان نمایش (تاریخ و ساعت)",
        help_text="پس از این لحظه خبر خودکار از هدر حذف می‌شود.",
    )
    speed = models.PositiveSmallIntegerField(
        "سرعت نمایش (ثانیه برای هر دور)",
        default=30,
        help_text="مدت‌زمان یک دورِ کامل حرکت متن؛ عدد کمتر = سریع‌تر (مثلاً ۱۵) و بیشتر = آرام‌تر (مثلاً ۶۰).",
    )
    is_active = models.BooleanField("فعال", default=True)
    sort_order = models.PositiveSmallIntegerField(
        "ترتیب پخش", default=0,
        help_text="خبرهای فعالِ هم‌زمان به‌ترتیب این شماره پشت‌سرهم پخش می‌شوند.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="breaking_news",
        verbose_name="ایجادکننده",
    )
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "خبر فوری هدر"
        verbose_name_plural = "اخبار فوری هدر"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.text[:60]

    @property
    def is_live(self):
        from django.utils import timezone

        now = timezone.now()
        return self.is_active and self.show_from <= now <= self.show_until

    @classmethod
    def active_news(cls):
        """خبرهای قابل‌نمایشِ همین لحظه (فعال + داخل بازهٔ زمانی)."""
        from django.utils import timezone

        now = timezone.now()
        return cls.objects.filter(
            is_active=True,
            show_from__lte=now,
            show_until__gte=now,
        )[:20]


# --------------------------------------------------------------------------- #
# ماژول «تبلیغات» — لوگوی تبلیغاتی کاربران که پس از پرداخت هزینهٔ سکه،
# در پایین داشبورد به‌صورت نوار متحرک (مارکی) پخش می‌شود.
# مدیریت نمایش (بازهٔ زمانی، سرعت، ترتیب، توقف) مشابه ماژول «اخبار فوری» است.
# --------------------------------------------------------------------------- #
AD_STATUS_PENDING = "pending"
AD_STATUS_APPROVED = "approved"
AD_STATUS_REJECTED = "rejected"
AD_STATUS_CHOICES = [
    (AD_STATUS_PENDING, "در انتظار تأیید (پرداخت نشده)"),
    (AD_STATUS_APPROVED, "تأییدشده — در حال/آمادهٔ پخش"),
    (AD_STATUS_REJECTED, "ردشده"),
]


class AdHeaderPlacement(models.Model):
    """نوار «تبلیغات» قابل‌انتخاب در هدرِ هر ماژول — توسط ادمین فعال/غیرفعال می‌شود.

    هر رکورد = یک «محل» (placement) که نوار تبلیغات در آن پخش می‌شود:
      داشبورد  (code=dashboard)    → نوار پایین داشبورد اصلی
      کیف پول  (code=wallet)       → نوار پایین هدر کیف پول و سکه
      حسابداری (code=accounting)   → نوار پایین هدر حسابداری
      تیکت     (code=tickets)      → نوار پایین هدر مرکز تیکت
    ادمین تعیین می‌کند کدام محل‌ها نبار بگیرند؛ کاربر هنگام ثبت تبلیغ با چک‌باکس,
    محل(های) دلخواه را انتخاب می‌کند و هزینه = روزها × تعداد هدرهای انتخابی.
    """

    code = models.CharField("کد", max_length=30, unique=True)
    title = models.CharField("عنوان", max_length=120,
        help_text="مثل: «نوار پایین داشبورد» — در چک‌باکس‌های ثبت تبلیغ نمایش داده می‌شود.")
    description = models.CharField("توضیح", max_length=300, blank=True,
        help_text="توضیح کوتاه دربارهٔ محل پخش (حداکثر ۳۰۰ کاراکتر).")
    is_active = models.BooleanField("پذیرش تبلیغ", default=True,
        help_text="غیرفعال = کاربران هنگام ثبت تبلیغ، این محل را نمی‌بینند.")
    sort_order = models.PositiveSmallIntegerField(
        "ترتیب نمایش", default=0,
        help_text="ترتیب نمایش چک‌باکس‌ها در فرم کاربر.",
    )
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین تغییر", auto_now=True)

    class Meta:
        verbose_name = "محل تبلیغ هدرها"
        verbose_name_plural = "محل‌های تبلیغ فوترها"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.title} ({self.code}) — {'فعال' if self.is_active else 'غیرفعال'}"

    @classmethod
    def active_placements(cls):
        """محل‌های فعال (قابل‌تبلیغ) به‌ترتیب نمایش — برای چک‌باکس‌های فرم."""
        return cls.objects.filter(is_active=True).order_by("sort_order", "id")



class AdTickerSetting(models.Model):
    """تنظیمات نوار متحرک تبلیغات پایین داشبورد (تک‌رکوردی؛ شبیه WalletSetting).

    «حداکثر تبلیغ در ردیف نمایش» چرخهٔ ردیف را می‌سازد: با توجه به حجم زیاد
    تبلیغ‌ها، فقط حداکثر این تعداد به‌ترتیبِ اولویت ادمین (sort_order و سپس
    زمان تأیید) در نوار قرار می‌گیرند؛ وقتی یکی از آن‌ها منقضی/توقف شود،
    تبلیغ بعدیِ صف اولویت جای آن را می‌گیرد.
    """

    max_visible = models.PositiveSmallIntegerField(
        "حداکثر تبلیغ در ردیف نمایش",
        default=10,
        help_text="مثلاً ۱۰ = فقط ۱۰ تبلیغ نخستِ صف اولویت در نوار پخش می‌شوند؛ "
        "با منقضی/توقف شدن یکی، تبلیغ بعدیِ صف جای آن را می‌گیرد. (۰ = بدون سقف)",
    )
    updated_at = models.DateTimeField("آخرین تغییر", auto_now=True)

    class Meta:
        verbose_name = "تنظیمات نوار تبلیغات"
        verbose_name_plural = "تنظیمات نوار تبلیغات"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


def advertisement_logo_path(instance, filename):
    import datetime

    return f"ads/{datetime.datetime.now():%Y/%m}/{instance.pk or 'new'}_{filename}"


class Advertisement(models.Model):
    """تبلیغ لوگویی کاربر — نمایش در نوار متحرک پایین داشبورد.

    گردش کار:
      ۱. کاربر لوگو + عنوان/توضیح/لینک را بارگذاری می‌کند؛ رکورد با وضعیت
         «در انتظار پرداخت» ثبت می‌شود.
      ۲. در همان لحظهٔ ثبت، هزینهٔ طبق «تعرفهٔ هزینه‌های سکهٔ ماژول‌ها»
         (کد feature: ``ad_submission``) از کیف پول کاربر کسر می‌شود؛ با
         موفقیتِ پرداخت، وضعیت به «تأییدشده» تغییر می‌کند.
      ۳. ادمین در پنل مدیریت (مشابه «اخبار فوری») بازهٔ نمایش/سرعت/ترتیب را
         تنظیم و پخش را متوقف/ادامه می‌دهد؛ تبلیغِ تأییدشده فقط در بازهٔ
         زمانی تعیین‌شده در نوار متحرک پایین داشبورد پخش می‌شود.
    """

    advertiser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="advertisements",
        verbose_name="تبلیغ‌کننده",
    )
    logo = models.FileField(
        "لوگوی تبلیغاتی", upload_to=advertisement_logo_path,
        help_text="تصویر لوگو (PNG/JPG/SVG) — در نوار متحرک پایین داشبورد نمایش داده می‌شود.",
    )
    title = models.CharField(
        "عنوان تبلیغ", max_length=120,
        help_text="عنوان کوتاه کنار لوگو در نوار متحرک.",
    )
    description = models.CharField(
        "توضیح تبلیغ", max_length=300, blank=True,
        help_text="توضیح کوتاه زیر عنوان (اختیاری).",
    )
    link_url = models.CharField(
        "لینک (اختیاری)", max_length=500, blank=True,
        help_text="با کلیک روی تبلیغ باز می‌شود؛ خالی = بدون لینک.",
    )
    coins_paid = models.DecimalField(
        "هزینهٔ پرداخت‌شده (سکه)", max_digits=14, decimal_places=2, default=0,
        help_text="مبلغ سکه‌ای که هنگام ثبت طبق تعرفه از تبلیغ‌کننده کسر شد.",
    )
    status = models.CharField(
        "وضعیت", max_length=20, choices=AD_STATUS_CHOICES, default=AD_STATUS_PENDING,
    )
    show_from = models.DateTimeField(
        "شروع نمایش (تاریخ و ساعت)",
        help_text="از این لحظه تبلیغ در نوار پایین داشبورد پخش می‌شود.",
    )
    show_until = models.DateTimeField(
        "پایان نمایش (تاریخ و ساعت)",
        help_text="پس از این لحظه تبلیغ خودکار از نوار حذف می‌شود.",
    )
    speed = models.PositiveSmallIntegerField(
        "سرعت نمایش (ثانیه برای هر دور)", default=30,
        help_text="مدت‌زمان یک دور کامل حرکت نوار؛ عدد کمتر = سریع‌تر (۵ تا ۱۲۰).",
    )
    is_active = models.BooleanField("فعال", default=True)
    sort_order = models.PositiveSmallIntegerField(
        "ترتیب پخش", default=0,
        help_text="تبلیغ‌های فعالِ هم‌زمان به‌ترتیب این شماره پشت‌سرهم پخش می‌شوند.",
    )
    header_modules = models.ManyToManyField(
        AdHeaderPlacement,
        blank=True,
        related_name="advertisements",
        verbose_name="هدرهای انتخابی",
        help_text="محل(های) پخش تبلیغ؛ هزینهٔ ثبت = روزها × تعداد این هدرها.",
    )
    views = models.PositiveBigIntegerField(
        "شمارندهٔ نمایش (views)", default=0,
        help_text="تنظیم خودکار از نمایش تبلیغ (هر بار رندر در نوارهای فعال).",
    )
    views_updated_at = models.DateTimeField("آخرین ثبت نمایش", null=True, blank=True)
    expiry_notified_at = models.DateTimeField(
        "زمان اطلاع‌رسانی پایان دوره", null=True, blank=True,
        help_text="یک‌بار که تیکت اطلاع‌رسانی پایان دوره به تبلیغ‌کننده ارسال شد.",
    )
    expiry_warning_notified_at = models.DateTimeField(
        "زمان هشدار دو روز پایانی", null=True, blank=True,
        help_text="یک‌بار که تیکت هشدار «۲ روز پایانی» به تبلیغ‌کننده ارسال شد.",
    )
    # --- تأیید ادمین (تیکت) و بازگشت وجه در صورت رد ---
    approval_ticket_id = models.PositiveIntegerField(
        "شناسهٔ تیکت درخواست تأیید", null=True, blank=True,
        help_text="تیکتی که پس از ثبت و کسر هزینه برای تأیید مدیر ساخته شد.",
    )
    refunded_coins = models.DecimalField(
        "سکهٔ بازگشتی به کاربر", max_digits=14, decimal_places=2, default=0,
        help_text="در صورت رد توسط مدیر: مبلغ بازگردانده‌شده به کیف پول (پس از کسر کارمزد).",
    )
    refund_fee_coins = models.DecimalField(
        "کارمزد کسرشده هنگام رد (سکه)", max_digits=14, decimal_places=2, default=0,
        help_text="سهم کسرشده (پیش‌فرض ۱۰٪) از هزینهٔ پرداختی هنگام رد.",
    )
    refunded_at = models.DateTimeField(
        "زمان بازگشت وجه", null=True, blank=True,
        help_text="خالی = وجهی بازگردانده نشده؛ برای جلوگیری از بازگشت مضاعف استفاده می‌شود.",
    )
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "تبلیغ"
        verbose_name_plural = "تبلیغات"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.title} — {self.get_status_display()}"

    @property
    def is_live(self):
        from django.utils import timezone

        now = timezone.now()
        return (
            self.is_active
            and self.status == AD_STATUS_APPROVED
            and self.show_from <= now <= self.show_until
        )

    @property
    def user_can_delete(self):
        """کاربر فقط تبلیغِ «تمام‌شده (منقضی)» یا «ردشده» را می‌تواند حذف کند.

        «در انتظار تأیید» (هزینه کسر شده و تیکت تأیید باز) و تبلیغِ تأییدشدهٔ جاری/زمان‌بندی‌شده
        حذف‌شدنی نیست؛ همان قاعدهٔ اسلایدشو (StatSlide.user_can_delete).
        """
        return self.status == AD_STATUS_REJECTED or self.is_expired


    @property
    def is_expired(self):
        """تمام شدن بازهٔ نمایش (تأییدشده و گذشتهٔ پایان) — قابل تمدید از ماژول تبلیغات.

        کاربر از «تبلیغ‌های من» دکمهٔ «تمدید» را می‌بیند و می‌تواند همان تبلیغ را
        با بازهٔ جدید (و پرداخت هزینهٔ جدید) مجدداً ثبت/فعال کند.
        """
        from django.utils import timezone

        return (
            self.status == AD_STATUS_APPROVED
            and self.show_until is not None
            and self.show_until <= timezone.now()
        )

    @property
    def is_near_expiry(self):
        """در «۲ روز پایانی» دوره (تأییدشده و فعال، کمتر از ۴۸ ساعت تا پایان)."""
        from datetime import timedelta
        from django.utils import timezone

        now = timezone.now()
        return (
            self.status == AD_STATUS_APPROVED
            and self.show_until is not None
            and now < self.show_until <= now + timedelta(hours=48)
        )

    @classmethod
    def active_ads(cls, placement="dashboard"):
        """تبلیغ‌های زنده (تأییدشده) در «محل» (placement) داده‌شده.

        ترتیب پخش = ``sort_order`` (کوچک‌تر = بالاتر) و سپس ``updated_at``
        (لحظهٔ تأیید/آخرین تنظیم ادمین؛ قدیمی‌تر جلوتر). تعداد آیتم‌ها به سقف
        ``AdTickerSetting.max_visible`` محدود می‌شود؛ اگر تبلیغ زندهٔ بیشتری
        وجود داشته باشد، فقط «صفِ اولویت» (همان سقف اول) در نوار قرار می‌گیرد
        و با منقضی/توقف شدن یکی، تبلیغ بعدیِ صف خودکار جای آن را می‌گیرد
        (حق تقدم بر اساس ترتیب و زمانِ تعیین‌شده توسط ادمین محفوظ است).
        ``placement`` = کد ``AdHeaderPlacement`` (dashboard/wallet/accounting/tickets)
        — فیلتر بر اساس هدر(های) انتخابیِ تبلیغ‌کننده.
        """
        from django.utils import timezone

        now = timezone.now()
        limit = AdTickerSetting.get().max_visible or 20
        return cls.objects.filter(
            is_active=True,
            status=AD_STATUS_APPROVED,
            show_from__lte=now,
            show_until__gte=now,
            header_modules__code=placement, header_modules__is_active=True,
        ).order_by("sort_order", "updated_at", "id").distinct()[:limit]

    def increment_views(self, save=True):
        """ثبت یک نمایش (render) در نوار — شمارندهٔ آمار ادمین.

        از کوئری UPDATE اتمی (F expression) استفاده می‌کنیم تا شمارش در رقابتِ
        هم‌زمان صحیح بماند؛ فقط‌آمار (بدون اطلاع‌رسانی).
        """
        from django.db.models import F
        from django.utils import timezone

        if not self.pk:
            return self.views
        type(self).objects.filter(pk=self.pk).update(
            views=F("views") + 1,
            views_updated_at=timezone.now(),
        )
        self.views += 1


# --------------------------------------------------------------------------- #
# ماژول «اسلایدشوی آمار داشبورد» — اسلاید تبلیغاتی در ۴ باکس آمارِ بالای
# «ماژول‌های کسب‌وکار» (اسلایدشو A / اسلایدشو B / اسلایدشو C / اسلایدشو D).
# هر باکس مستقلاً اسلایدشوی خودش را دارد و اسلایدها بدون حرکت
# روان، درجا و پس از زمانِ مشخصی به اسلاید بعد عوض می‌شوند.
# مدیریت (آپلود تصویر، بازهٔ نمایش، ترتیب، توقف، هزینهٔ سکهٔ دریافتی)
# مشابه ماژول «تبلیغات» در پنل مدیریت انجام می‌شود.
# --------------------------------------------------------------------------- #

STAT_SLIDE_BOX_USERS = "stat_users"
STAT_SLIDE_BOX_PROJECTS = "stat_projects"
STAT_SLIDE_BOX_REVENUE = "stat_revenue"
STAT_SLIDE_BOX_TASKS = "stat_tasks"
STAT_SLIDE_BOX_CODES = [
    (STAT_SLIDE_BOX_USERS, "اسلایدشو D"),
    (STAT_SLIDE_BOX_PROJECTS, "اسلایدشو C"),
    (STAT_SLIDE_BOX_REVENUE, "اسلایدشو B"),
    (STAT_SLIDE_BOX_TASKS, "اسلایدشو A"),
]


# حداکثر تعداد اسلایدهای قابل ثبت در اسلایدشو (فقط «اسلایدشو A»).
# برای هم در گردش‌کار ادمین و گردش‌کار کاربر (ماژول «اسلایدشوی آمار داشبورد»)
# با فرم/نمای ثبت اعمال می‌شود.
STAT_SLIDE_MAX_PER_BOX = 10

class StatSlideBox(models.Model):
    """یکی از ۴ باکس آمار داشبورد که اسلایدشو در آن پخش می‌شود.

    مشابه ``AdHeaderPlacement``؛ ادمین می‌تواند پذیرش اسلاید در هر باکس را
    فعال/غیرفعال کند؛ با غیرفعال شدن، اسلایدهای آن باکس در داشبورد پخش نمی‌شوند.
    """

    code = models.CharField("کد", max_length=30, unique=True)
    title = models.CharField("عنوان", max_length=120,
        help_text="مثل: «اسلایدشو A» — در فرم اسلاید و پنل مدیریت نمایش داده می‌شود.")
    description = models.CharField("توضیح", max_length=300, blank=True,
        help_text="توضیح کوتاه دربارهٔ محل نمایش (حداکثر ۳۰۰ کاراکتر).")
    is_active = models.BooleanField("پذیرش اسلاید", default=True,
        help_text="غیرفعال = اسلایدهای این باکس در داشبورد پخش نمی‌شوند و باکس، آمار معمولی خود را نشان می‌دهد.")
    switch_seconds = models.PositiveSmallIntegerField(
        "زمان هر اسلاید (ثانیه)", default=6,
        help_text="هر اسلایدِ این باکس چند ثانیه بماند و بعد درجا عوض شود (۳ تا ۱۲۰). ۰ = مقادیر تنظیمات سراسری.",
    )
    sort_order = models.PositiveSmallIntegerField(
        "ترتیب نمایش", default=0,
        help_text="ترتیب نمایش چک‌باکس‌ها در فرم اسلاید.",
    )
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین تغییر", auto_now=True)

    class Meta:
        verbose_name = "باکس اسلایدشوی آمار"
        verbose_name_plural = "باکس‌های اسلایدشوی آمار"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.title} ({self.code}) — {'فعال' if self.is_active else 'غیرفعال'}"

    @classmethod
    def active_boxes(cls):
        """باکس‌های فعال (قابل‌اسلاید) به‌ترتیب نمایش."""
        return cls.objects.filter(is_active=True).order_by("sort_order", "id")

    @classmethod
    def the_box(cls):
        """تنها باکس اسلایدشو («اسلایدشو A»، کد ``stat_tasks``)؛ در نبودِ آن None.

        از این پس همهٔ اسلایدها فقط در همین یک باکس پخش می‌شوند (باکس‌های B/C/D حذف شدند).
        """
        return cls.objects.filter(code=STAT_SLIDE_BOX_TASKS).first()

    def effective_switch_seconds(self, default_seconds):
        """زمانِ نمایش هر اسلایدِ این باکس؛ ۰ = استفاده از مقدار سراسری."""
        if self.switch_seconds and 3 <= self.switch_seconds <= 120:
            return self.switch_seconds
        return default_seconds


class StatSlideSetting(models.Model):
    """تنظیمات سراسری اسلایدشوی آمار (تک‌رکوردی؛ شبیه AdTickerSetting)."""

    switch_seconds = models.PositiveSmallIntegerField(
        "زمان پیش‌فرض هر اسلاید (ثانیه)",
        default=6,
        help_text="هر اسلاید در هر باکس این‌قدر ثانیه می‌ماند و سپس درجا (بدون حرکت روان) عوض می‌شود (۳ تا ۱۲۰). "
        "باکس‌ها با «زمان هر اسلاید» اختصاصی خود می‌توانند این مقدار را بازنویسی کنند.",
    )
    updated_at = models.DateTimeField("آخرین تغییر", auto_now=True)

    class Meta:
        verbose_name = "تنظیمات اسلایدشوی آمار"
        verbose_name_plural = "تنظیمات اسلایدشوی آمار"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


def stat_slide_image_path(instance, filename):
    import datetime

    return f"stat_slides/{datetime.datetime.now():%Y/%m}/{instance.pk or 'new'}_{filename}"


class StatSlide(models.Model):
    """اسلاید اسلایدشوی آمار داشبورد — آپلود/مدیریت توسط ادمین، مشابه تبلیغ.

    گردش کار:
      ۱. ادمین تصویر + عنوان/لینک را در پنل مدیریت ثبت می‌کند و بازهٔ نمایش
         (تقویم شمسی) و ترتیب و باکس(های) نمایش را تعیین می‌کند؛ اسلایدِ ثبت‌شده
         از پنل مدیریت مستقیماً «تأییدشده» است.
      ۲. کاربر هم می‌تواند از ماژول «اسلایدشوی آمار داشبورد» (مسیر ``/slideshow/``؛
         مشابه ماژول تبلیغات) اسلاید ثبت کند: تصویر/عنوان/لینک + بازهٔ نمایش +
         باکس(های) چهارگانه؛ هزینه = روزها × تعداد باکس‌ها × تعرفهٔ ۲۴ ساعته
         از کیف پول کسر می‌شود و اسلاید با وضعیت «در انتظار تأیید» ذخیره می‌گردد.
      ۳. پس از تأیید ادمین (فهرست اسلایدها در پنل مدیریت) اسلاید در
         باکس(های) انتخابی به‌صورت مستقل و با زمانِ هر باکس درجا عوض می‌شود.
      ۴. فیلد «هزینهٔ دریافتی (سکه)» برای ثبت هزینه‌ای است که بابت پخش این
         اسلاید دریافت شده — در فهرست پنل مدیریت جمع کل نمایش داده می‌شود.
    """

    advertiser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="stat_slides",
        verbose_name="صاحب اسلاید (کاربر)",
        help_text="ادمین = خالی؛ اسلایدِ ثبت‌شده توسط کاربر از ماژول اسلایدشو، صاحبش می‌گیرد.",
    )
    status = models.CharField(
        "وضعیت تأیید",
        max_length=20,
        choices=AD_STATUS_CHOICES,
        default=AD_STATUS_PENDING,
        help_text="در انتظار تأیید / تأییدشده / ردشده — فقط اسلایدهای «تأییدشده» در باکس‌ها پخش می‌شوند.",
    )

    boxes = models.ManyToManyField(
        StatSlideBox,
        blank=True,
        related_name="slides",
        verbose_name="باکس(های) نمایش",
        help_text="اسلاید در اسلایدشوی باکس(های) انتخابی پخش می‌شود؛ هر باکس مستقلاً و با زمانِ خودش اسلاید عوض می‌کند.",
    )
    image = models.FileField(
        "تصویر اسلاید", upload_to=stat_slide_image_path,
        help_text="تصویر اسلاید (PNG/JPG) — هم‌اندازهٔ باکس آمار در داشبورد نمایش داده می‌شود.",
    )
    title = models.CharField(
        "عنوان اسلاید", max_length=120,
        help_text="عنوان کوتاه زیر تصویر در باکس (اختیاری نمایش داده شدن).",
    )
    description = models.CharField(
        "توضیح اسلاید", max_length=300, blank=True,
        help_text="توضیح کوتاه زیر عنوان (اختیاری).",
    )
    link_url = models.CharField(
        "لینک (اختیاری)", max_length=500, blank=True,
        help_text="با کلیک روی اسلاید باز می‌شود؛ خالی = بدون لینک.",
    )
    coins_paid = models.DecimalField(
        "هزینهٔ دریافتی (سکه)", max_digits=14, decimal_places=2, default=0,
        help_text="هزینه‌ای که بابت پخش این اسلاید دریافت شده — در فهرست پنل مدیریت جمع کل دیده می‌شود.",
    )
    show_from = models.DateTimeField(
        "شروع نمایش (تاریخ و ساعت)",
        help_text="از این لحظه اسلاید در باکس(های) انتخابی پخش می‌شود.",
    )
    show_until = models.DateTimeField(
        "پایان نمایش (تاریخ و ساعت)",
        help_text="پس از این لحظه اسلاید خودکار از اسلایدشو حذف می‌شود.",
    )
    is_active = models.BooleanField("فعال", default=True)
    sort_order = models.PositiveSmallIntegerField(
        "ترتیب پخش", default=0,
        help_text="ترتیب اسلایدهای هم‌زمان در هر باکس (کوچک‌تر = جلوتر).",
    )
    views = models.PositiveBigIntegerField(
        "شمارندهٔ نمایش (views)", default=0,
        help_text="تنظیم خودکار از نمایش اسلاید (هر بار رندر در باکس‌های فعال).",
    )
    views_updated_at = models.DateTimeField("آخرین ثبت نمایش", null=True, blank=True)
    expiry_warning_notified_at = models.DateTimeField(
        "زمان هشدار دو روز پایانی", null=True, blank=True,
        help_text="یک‌بار که تیکت هشدار «۲ روز پایانی» به صاحب اسلاید ارسال شد.",
    )
    expiry_notified_at = models.DateTimeField(
        "زمان اطلاع‌رسانی پایان دوره", null=True, blank=True,
        help_text="یک‌بار که تیکت اطلاع‌رسانی پایان دوره به صاحب اسلاید ارسال شد.",
    )
    # --- تأیید ادمین (تیکت) و بازگشت وجه در صورت رد ---
    approval_ticket_id = models.PositiveIntegerField(
        "شناسهٔ تیکت درخواست تأیید", null=True, blank=True,
        help_text="تیکتی که پس از ثبت و کسر هزینه برای تأیید مدیر ساخته شد.",
    )
    refunded_coins = models.DecimalField(
        "سکهٔ بازگشتی به کاربر", max_digits=14, decimal_places=2, default=0,
        help_text="در صورت رد توسط مدیر: مبلغ بازگردانده‌شده به کیف پول (پس از کسر کارمزد).",
    )
    refund_fee_coins = models.DecimalField(
        "کارمزد کسرشده هنگام رد (سکه)", max_digits=14, decimal_places=2, default=0,
        help_text="سهم کسرشده (پیش‌فرض ۱۰٪) از هزینهٔ پرداختی هنگام رد.",
    )
    refunded_at = models.DateTimeField(
        "زمان بازگشت وجه", null=True, blank=True,
        help_text="خالی = وجهی بازگردانده نشده؛ برای جلوگیری از بازگشت مضاعف استفاده می‌شود.",
    )
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "اسلاید آمار داشبورد"
        verbose_name_plural = "اسلایدهای اسلایدشوی آمار"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.title} — {'فعال' if self.is_active else 'متوقف'}"

    @property
    def is_live(self):
        from django.utils import timezone

        now = timezone.now()
        return (
            self.is_active
            and self.status == AD_STATUS_APPROVED
            and self.show_from <= now <= self.show_until
        )

    @property
    def user_can_delete(self):
        """کاربر فقط اسلایدِ «تمام‌شده (منقضی)» یا «ردشده» را می‌تواند حذف کند.

        «در انتظار تأیید» (هزینه کسر شده و تیکت تأیید باز است) و اسلایدِ تأییدشده‌ای که هنوز
        زمان‌بندی/در حال پخش است حذف‌شدنی نیست؛ وگرنه پرداخت و تیکتِ مدیر بی‌صاحب می‌ماند.
        """
        return self.status == AD_STATUS_REJECTED or self.is_expired


    @property
    def is_expired(self):
        """تمام شدن بازهٔ نمایش (تأییدشده و گذشتهٔ پایان) — قابل تمدید از ماژول اسلایدشو.

        کاربر از «اسلایدهای من» دکمهٔ «تمدید» را می‌بیند و می‌تواند همان اسلاید را
        با بازهٔ جدید (و پرداخت هزینهٔ جدید) مجدداً ثبت/فعال کند.
        """
        from django.utils import timezone

        return (
            self.status == AD_STATUS_APPROVED
            and self.show_until is not None
            and self.show_until <= timezone.now()
        )

    @property
    def is_near_expiry(self):
        """در «۲ روز پایانی» دوره (تأییدشده و فعال، کمتر از ۴۸ ساعت تا پایان)."""
        from datetime import timedelta
        from django.utils import timezone

        now = timezone.now()
        return (
            self.status == AD_STATUS_APPROVED
            and self.show_until is not None
            and now < self.show_until <= now + timedelta(hours=48)
        )

    @classmethod
    def active_slides(cls, box="stat_users"):
        """اسلایدهای زنده در باکس داده‌شده (کد ``StatSlideBox``).

        ترتیب پخش = ``sort_order`` (کوچک‌تر = جلوتر) و سپس ``updated_at``.
        """
        from django.utils import timezone

        return cls.objects.filter(
            is_active=True,
            status=AD_STATUS_APPROVED,
            show_from__lte=timezone.now(),
            show_until__gte=timezone.now(),
            boxes__code=box, boxes__is_active=True,
        ).order_by("sort_order", "updated_at", "id").distinct()

    @property
    def is_pending(self):
        return self.status == AD_STATUS_PENDING

    @classmethod
    def slides_in_box(cls, box_code, exclude_rejected=True):
        """اسلایدهای «جای‌گیر» باکس (تأییدشده + در انتظار تأیید) برای شمارش ظرفیت."""
        qs = cls.objects.filter(boxes__code=box_code)
        if exclude_rejected:
            qs = qs.exclude(status=AD_STATUS_REJECTED)
        return qs.distinct()

    def increment_views(self, save=True):
        """ثبت یک نمایش (render) در باکس — شمارندهٔ آمار ادمین (اتمیک)."""
        from django.db.models import F
        from django.utils import timezone

        if not self.pk:
            return self.views
        type(self).objects.filter(pk=self.pk).update(
            views=F("views") + 1,
            views_updated_at=timezone.now(),
        )
        self.views += 1
