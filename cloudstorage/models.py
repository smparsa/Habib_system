"""مدل‌های ماژول «فضای ذخیره‌سازی ابری (Cloud Object Storage)».

اصول:
- مالکیت همه چیز در DB چک می‌شود؛ نام/کد ملی هرگز مجوز نیست.
- مسیر فیزیکی: DOCS_ROOT/cloud/{storage_key}/{folder.uid}/{rel_path}
- شناسهٔ پایدار پوشه = uid (uuid4 hex) مستقل از نام پوشه یا مسیر محلی.
- تشخیص تغییر/تکرار بر پایهٔ مسیر نسبی + اندازه + SHA-256 محتوا.
- پول روی دفتر کل wallet.CoinLedger می‌گذرد؛ کسر/بازپرداخت اتمی و تا حد امکان
  idempotent: پرداخت فقط یک‌بار (گذار وضعیت قفل‌شدهٔ سشن) و تفاوتِ پرداختِ
  بیش از حقیقت در تسویه بازگردانده می‌شود.
"""
import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from .storage import cloud_storage, cloud_upload_path


# --------------------------------------------------------------------------- #
# تنظیمات ماژول (تک‌رکوردی، ادمین‌پذیر)
# --------------------------------------------------------------------------- #
class StorageSettings(models.Model):
    """تنظیمات سراسری فضای ابری که ادمین در پنل مدیریت ویرایش می‌کند."""

    module_enabled = models.BooleanField("", default=True)
    folder_upload_enabled = models.BooleanField("", default=True)
    gallery_enabled = models.BooleanField("", default=True)
    sync_enabled = models.BooleanField("", default=True, help_text="")
    archive_enabled = models.BooleanField("", default=True)

    # سقف‌ها
    max_folder_files = models.PositiveIntegerField("حداکثر فایل در هر عملیات/پوشه", default=2000)
    max_subfolders = models.PositiveIntegerField("حداکثر زیرپوشه در هر عملیات", default=500)
    max_file_size_mb = models.PositiveIntegerField("حداکثر حجم هر فایل (MB)", default=200)
    max_operation_size_mb = models.PositiveIntegerField("حداکثر حجم هر عملیات (MB)", default=2000)
    max_folder_size_gb = models.PositiveIntegerField("حداکثر حجم هر پوشه (GB)", default=10)
    user_quota_gb = models.PositiveIntegerField("سقف فضای هر کاربر (GB)", default=50)
    max_archive_files = models.PositiveIntegerField("حداکثر فایل در هر آرشیو", default=5000)
    max_archive_size_gb = models.PositiveIntegerField("حداکثر حجم هر آرشیو (GB)", default=5)
    archive_retention_hours = models.PositiveSmallIntegerField("مدت نگهداری آرشیو موقت (ساعت)", default=24)

    # تعرفه‌ها (سکه به ازای هر GB)
    storage_coin_per_gb = models.DecimalField("تعرفهٔ ذخیره‌سازی (سکه در هر GB)", max_digits=12, decimal_places=2, default=10)
    transfer_coin_per_gb = models.DecimalField("Upload (سکه در هر GB)", max_digits=12, decimal_places=2, default=0)
    archive_coin_per_gb = models.DecimalField("تعرفهٔ آرشیوسازی (سکه در GB) Download", max_digits=12, decimal_places=2, default=2)

    # مالیت/سقف هزینه
    daily_cost_limit = models.DecimalField("سقف هزینهٔ روزانه (سکه؛ ۰ = نامحدود)", max_digits=12, decimal_places=2, default=0)
    monthly_cost_limit = models.DecimalField("سقف هزینهٔ ماهانه (سکه؛ ۰ = نامحدود)", max_digits=12, decimal_places=2, default=0)

    # سیاست نسخه‌بندی و حذف
    version_keep_count = models.PositiveSmallIntegerField(
        "سیاست نسخه‌بندی: تعداد نسخه‌های قدیمی نگهداری‌شده (۰ = جایگزینی کامل)",
        default=3,
    )
    keep_deleted_files = models.BooleanField(
        "عدم حذف ابری در صورت حذف locale",
        default=True,
        help_text="حذف در دستگاه موبایل/کامپیوتر به‎_mo_tober خودکار فایل ابری را حذف نمی‎_mo_کند؛ "
                  "حذف دوطرفه فقط با سیاست صریح و پذیرش	user فعال می‎_mo_شود.",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات فضای ابری"
        verbose_name_plural = "تنظیمات فضای ابری"

    def __str__(self):
        return "تنظیمات فضای ابری"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def snapshot(cls):
        """لغتنامهٔ مقادیر مؤثر برای ثبت در تعرفه/سشن."""
        obj = cls.get()
        return {f.name: getattr(obj, f.name) for f in obj._meta.get_fields() if f.concrete and not f.many_to_many}


# --------------------------------------------------------------------------- #
# تعرفهٔ ثبت‌شده (تاریخچهٔ تغییرات تعرفه)
# --------------------------------------------------------------------------- #
class StoragePricing(models.Model):
    """سطر تعرفهٔ فعال/تاریخی — هنگام ذخیرهٔ تنظیمات ادمین عکس‌برداری می‌شود."""

    effective_from = models.DateTimeField(auto_now_add=True, verbose_name="مؤثر از")
    storage_coin_per_gb = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="ذخیره‌سازی (سکه/GB)")
    transfer_coin_per_gb = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="انتقال (سکه/GB)")
    archive_coin_per_gb = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="آرشیوسازی (سکه/GB)")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="ثبت‌کننده")

    class Meta:
        verbose_name = "تعرفهٔ ذخیره‌سازی"
        verbose_name_plural = "تعرفه‌های ذخیره‌سازی"
        ordering = ["-effective_from"]

    def __str__(self):
        return f"تعرفهٔ {self.effective_from:%Y-%m-%d %H:%M}"


# --------------------------------------------------------------------------- #
# حساب فضایی کاربر
# --------------------------------------------------------------------------- #
class StorageAccount(models.Model):
    """حساب فضای کاربر؛ مصرف تجمعی + رزرو مصرف مالی روز/ماه (قوانین سقف)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="storage_account")
    storage_key = models.CharField("کلید نام‌گذاری فیزیکی", max_length=64, unique=False, blank=True, default="")
    used_bytes = models.BigIntegerField("مصرف فعلی (بایت)", default=0)
    files_count = models.PositiveIntegerField("تعداد فایل فعال", default=0)
    folders_count = models.PositiveIntegerField("تعداد پوشه", default=0)
    quota_override_gb = models.PositiveIntegerField(null=True, blank=True, verbose_name="سقف اختصاصی (GB)")
    daily_spent_at = models.DateField(null=True, blank=True, verbose_name="تاریخ شمارندهٔ روز")
    daily_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="هزینهٔ امروز (سکه)")
    monthly_spent_month = models.CharField(max_length=7, blank=True, default="", verbose_name="ماه شمارنده")
    monthly_spent = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="هزینهٔ این ماه (سکه)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "حساب فضای کاربر"
        verbose_name_plural = "حساب‌های فضای کاربر"

    def __str__(self):
        return f"فضای ابری {self.user}"

    @classmethod
    def ensure_for(cls, user):
        """ایجاد حساب در صورت نیاز؛ کلید نام‌گذاری = کد ملی (فقط نام‌گذاری) یا u<pk>."""
        from accounts.models import Profile

        acc, _created = cls.objects.get_or_create(user=user)
        if not acc.storage_key:
            nid = None
            profile = Profile.objects.filter(user=user).only("national_id").first()
            if profile and profile.national_id:
                nid = str(profile.national_id).strip()
            acc.storage_key = nid or f"u{user.pk}"
            acc.save(update_fields=["storage_key"])
        return acc

    FREE_CLOUD_MB = 25  # فضای پیش‌فرض رایگان هر کاربر (مگابایت)

    def active_purchases(self):
        """خریدهای فضای ابری که هنوز فعال‌اند (منقضی‌شده‌ها دیده نمی‌شوند)."""
        return CloudSpacePurchase.objects.filter(
            user=self.user, active_until__gt=timezone.now(),
        ).order_by("-active_until")

    def active_space_gb(self):
        """مجموع فضای خریداری‌شدهٔ فعال (GB) کاربر — تعرفهٔ당 دوره‌ای جمع می‌شود."""
        from django.db.models import Sum

        agg = self.active_purchases().aggregate(total=Sum("storage_gb"))
        return float(agg["total"] or 0)

    @property
    def quota_bytes(self):
        """سقف مؤثر فضای کاربر:
        - اگر ادمین «سقف اختصاصی» گذاشته باشد، همان ملاک است؛
        - در حالت کلی: پیش‌فرض رایگان 25MB + مجموع فضای خریداری‌شدهٔ فعال.
          (فضای ابری فقط تا اندازه‌ای فعال است که خرید فعال داشته باشد.)
        """
        if self.quota_override_gb:
            return self.quota_override_gb * 1024 ** 3
        return (self.FREE_CLOUD_MB * 1024 ** 2) + self.active_space_gb() * 1024 ** 3

    @property
    def quota_gb_display(self):
        """سقف مؤثر به GB (برای پیام‌های خطا/نمایش)."""
        return self.quota_bytes / 1024 ** 3


class CloudSpacePurchase(models.Model):
    """خرید فضای ابری توسط کاربر — تعرفهٔ api «cloud_storage» × حجم (GB) × روزها.

    خرید فعال یعنی active_untilpathname هنوز نرسیده؛ مجموع خریدهای فعال،
    سقف مؤثر کاربر را می‌سازد (رفتار «فضای ابری فعال به اندازهٔ خرید»).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="cloud_space_purchases",
        on_delete=models.CASCADE, verbose_name="کاربر",
    )
    storage_gb = models.DecimalField("فضای خریداری‌شده (GB)", max_digits=8, decimal_places=2)
    days = models.PositiveIntegerField("مدت (روز)")
    coins_charged = models.DecimalField("سکهٔ کسرشده", max_digits=12, decimal_places=2, default=0)
    active_from = models.DateTimeField("فعال از", default=timezone.now)
    active_until = models.DateTimeField("فعال تا", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "خرید فضای ابری"
        verbose_name_plural = "خریدهای فضای ابری"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user} — خرید {self.storage_gb} GB برای {self.days} روز"


# --------------------------------------------------------------------------- #
# پوشهٔ ابری
# --------------------------------------------------------------------------- #
def _gen_uid():
    return uuid.uuid4().hex


def _gen_token():
    """توکن امن ۴۳ کاراکتری (قابل سریال‌سازی در migration)."""
    return secrets.token_urlsafe(32)


class StorageFolder(models.Model):
    """پوشهٔ منطقی ابری با شناسهٔ پایدار؛ درخت با parent ساخته می‌شود."""

    STATUS_ACTIVE = "active"
    STATUS_ARCHIVED = "archived"
    STATUS_DELETED = "deleted"
    STATUS_CHOICES = [(STATUS_ACTIVE, "فعال"), (STATUS_ARCHIVED, "بایگانی"), (STATUS_DELETED, "حذف‌شده")]

    account = models.ForeignKey(StorageAccount, on_delete=models.CASCADE, related_name="folders")
    uid = models.CharField("شناسهٔ پایدار پوشه", max_length=32, unique=True, default=_gen_uid)
    name = models.CharField("نام نمایشی", max_length=255)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    path_display = models.CharField("مسیر منطقی", max_length=1024, blank=True, default="/")
    subtree_dirs = models.JSONField(
        "ساختار زیرپوشه‌ها", default=list, blank=True,
        help_text="مسیر نسبی همهٔ زیرپوشه‌ها (شامل پوشه‌های خالی که فقط ساختارند).",
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    size_bytes = models.BigIntegerField("حجم (بایت)", default=0)
    files_count = models.PositiveIntegerField("تعداد فایل", default=0)
    subfolders_count = models.PositiveIntegerField("تعداد زیرپوشه", default=0)
    version_policy_override = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="سیاست نسخه اختصاصی")
    # تنظیمات Sync
    auto_sync_enabled = models.BooleanField(null=True, default=None, verbose_name="Sync خودکار (None=پیش‌فرض ماژول)")
    sync_interval_minutes = models.PositiveIntegerField(null=True, blank=True, verbose_name="فاصلهٔ Sync خودکار (دقیقه)")
    sync_on_login = models.BooleanField(default=False, verbose_name="Sync هنگام ورود")
    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name="آخرین Sync موفق")
    last_sync_status = models.CharField(max_length=10, blank=True, default="", verbose_name="وضعیت آخرین Sync")
    last_sync_note = models.CharField(max_length=300, blank=True, default="", verbose_name="یادداشت آخرین Sync")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "پوشهٔ ابری"
        verbose_name_plural = "پوشه‌های ابری"
        indexes = [models.Index(fields=["account", "status"], name="cstorage_animpa21t")]

    def __str__(self):
        return f"{self.path_display} ({self.uid[:8]})"

    @property
    def version_policy(self):
        if self.version_policy_override is not None:
            return self.version_policy_override
        return StorageSettings.get().version_keep_count


# --------------------------------------------------------------------------- #
# فایل (شیء) ابری
# --------------------------------------------------------------------------- #
class StorageObject(models.Model):
    """فایل داخل یک پوشه؛ path_key = مسیر نسبی نرمال‌شده داخل پوشه."""

    STATUS_ACTIVE = "active"
    STATUS_REPLACED = "replaced"
    STATUS_DELETED = "deleted"
    STATUS_CHOICES = [(STATUS_ACTIVE, "فعال"), (STATUS_REPLACED, "نسخهٔ قدیمی"), (STATUS_DELETED, "حذف‌شده")]

    folder = models.ForeignKey(StorageFolder, on_delete=models.CASCADE, related_name="storage_objects")
    session = models.ForeignKey("cloudstorage.UploadSession", null=True, blank=True, on_delete=models.SET_NULL, related_name="staged_objects")
    rel_path = models.CharField("مسیر نسبی داخل پوشه", max_length=1000)
    name = models.CharField("نام فایل", max_length=255)
    file = models.FileField(upload_to=cloud_upload_path, storage=cloud_storage, max_length=1500, verbose_name="فایل")
    size_bytes = models.BigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, default="")
    mime = models.CharField(max_length=140, blank=True, default="")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    version = models.PositiveIntegerField("نسخه", default=1)
    client_mtime_ms = models.BigIntegerField(null=True, blank=True, verbose_name="زمان اصلاح محلی (ms)")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    replaced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "فایل ابری"
        verbose_name_plural = "فایل‌های ابری"
        indexes = [
            models.Index(fields=["folder", "rel_path", "status"], name="cstorage_fscIdx"),
            models.Index(fields=["folder", "sha256"], name="cstorage_shaIdx"),
        ]

    def __str__(self):
        return f"{self.folder.uid[:8]}:{self.rel_path}"

    def mark_replaced(self):
        self.status = self.STATUS_REPLACED
        self.replaced_at = timezone.now()
        self.save(update_fields=["status", "replaced_at"])


# --------------------------------------------------------------------------- #
# سشن آپلود (قابلیت: پیش‌فاکتور → پرداخت → آپلود → تسویه)
# --------------------------------------------------------------------------- #
class UploadSession(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PAID = "paid"
    STATUS_UPLOADING = "uploading"
    STATUS_FINISHED = "finished"
    STATUS_CANCELLED = "cancelled"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "در انتظار تأیید و پرداخت"),
        (STATUS_PAID, "پرداخت‌شده — در انتظار آپلود"),
        (STATUS_UPLOADING, "در حال آپلود"),
        (STATUS_FINISHED, "کامل‌شده"),
        (STATUS_CANCELLED, "لغو شده"),
        (STATUS_FAILED, "ناموفق"),
        (STATUS_REFUNDED, "بازپرداخت‌شده"),
    ]

    SOURCE_FOLDER = "folder"
    SOURCE_GALLERY = "gallery"
    SOURCE_SYNC = "sync"
    SOURCE_CHOICES = [(SOURCE_FOLDER, "انتخاب پوشه"), (SOURCE_GALLERY, "گالری موبایل"), (SOURCE_SYNC, "همگام‌سازی")]

    account = models.ForeignKey(StorageAccount, on_delete=models.CASCADE, related_name="upload_sessions")
    token = models.CharField(max_length=43, unique=True, default=_gen_token)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    folder_name = models.CharField(max_length=255)
    target_folder = models.ForeignKey(StorageFolder, null=True, blank=True, on_delete=models.SET_NULL, related_name="sync_sessions")
    manifest = models.JSONField(default=list, blank=True)  # [{relpath, size, sha256, mtime}]
    folders = models.JSONField(default=list, blank=True)   # ["a", "a/b", ...]
    stats = models.JSONField(default=dict, blank=True)     # خروجی برآورد: شمارش‌ها/حجم/هزینه
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    priced_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    uploaded_count = models.PositiveIntegerField(default=0)
    created_note = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        verbose_name = "سشن آپلود"
        verbose_name_plural = "سشن‌های آپلود"
        ordering = ["-priced_at"]

    def __str__(self):
        return f"{self.get_source_display()} {self.token[:12]}"

    @property
    def total_bytes(self):
        return sum(item.get("size", 0) or 0 for item in self.manifest)

    def is_active_for_upload(self):
        return self.status in (self.STATUS_PAID, self.STATUS_UPLOADING)


# --------------------------------------------------------------------------- #
# صورتحساب و تراکنش مالی
# --------------------------------------------------------------------------- #
class StorageInvoice(models.Model):
    STATUS_PAID = "paid"
    STATUS_SETTLED = "settled"
    STATUS_REFUNDED = "refunded"
    STATUS_CHOICES = [(STATUS_PAID, "پرداخت‌شده"), (STATUS_SETTLED, "تسویه‌شده"), (STATUS_REFUNDED, "بازگشت‌شده")]

    number = models.CharField("شماره صورتحساب", max_length=40, blank=True, default="")
    session = models.ForeignKey(UploadSession, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices")
    account = models.ForeignKey(StorageAccount, on_delete=models.CASCADE, related_name="invoices")
    amount_coins = models.DecimalField("مبلغ (سکه)", max_digits=14, decimal_places=2, default=0)
    actual_coins = models.DecimalField("مبلغ واقعی (سکه)", max_digits=14, decimal_places=2, default=0)
    refunded_coins = models.DecimalField("بازپرداخت (سکه)", max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PAID)
    paid_at = models.DateTimeField(null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "صورتحساب فضای ابری"
        verbose_name_plural = "صورتحساب‌های فضای ابری"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.number or self.pk} — {self.amount_coins} سکه"


class StorageTransaction(models.Model):
    """نگاشت پرداخت فضای ابری به دفتر کل کیف پول."""

    KIND_CHARGE = "charge"
    KIND_REFUND = "refund"
    KIND_ARCHIVE = "archive"
    KIND_CHOICES = [(KIND_CHARGE, "کسر هزینه"), (KIND_REFUND, "بازپرداخت"), (KIND_ARCHIVE, "آرشیوسازی")]

    account = models.ForeignKey(StorageAccount, on_delete=models.CASCADE, related_name="transactions")
    session = models.ForeignKey(UploadSession, null=True, blank=True, on_delete=models.CASCADE, related_name="transactions")
    invoice = models.ForeignKey(StorageInvoice, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    kind = models.CharField(max_length=12, choices=KIND_CHOICES)
    amount_coins = models.DecimalField(max_digits=14, decimal_places=2)
    ref_code = models.CharField(max_length=40, blank=True, default="")
    ledger = models.ForeignKey("wallet.CoinLedger", null=True, blank=True, on_delete=models.SET_NULL, related_name="storage_transactions")
    note = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تراکنش فضای ابری"
        verbose_name_plural = "تراکنش‌های فضای ابری"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.kind} {self.amount_coins}"


# --------------------------------------------------------------------------- #
# همگام‌سازی
# --------------------------------------------------------------------------- #
class SyncJob(models.Model):
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [(STATUS_DONE, "انجام شد"), (STATUS_FAILED, "ناموفق"), (STATUS_CANCELLED, "لغو شد")]

    SOURCE_MANUAL = "manual"
    SOURCE_LOGIN = "login"
    SOURCE_SCHEDULED = "scheduled"
    SOURCE_CHOICES = [(SOURCE_MANUAL, "دستی"), (SOURCE_LOGIN, "هنگام ورود"), (SOURCE_SCHEDULED, "زمان‌بندی‌شده")]

    account = models.ForeignKey(StorageAccount, on_delete=models.CASCADE, related_name="sync_jobs")
    folder = models.ForeignKey(StorageFolder, on_delete=models.CASCADE, related_name="sync_jobs")
    source = models.CharField(max_length=12, choices=SOURCE_CHOICES, default=SOURCE_MANUAL)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES)
    session = models.ForeignKey(UploadSession, null=True, blank=True, on_delete=models.SET_NULL, related_name="sync_jobs")
    diff = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True, default="")


# --------------------------------------------------------------------------- #
# آرشیو موقت (دانلود ZIP لینک زمان‌دار)
# --------------------------------------------------------------------------- #
class ArchiveJob(models.Model):
    STATUS_READY = "ready"
    STATUS_BUILDING = "building"
    STATUS_FAILED = "failed"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [(STATUS_READY, "آماده"), (STATUS_BUILDING, "در حال ساخت"), (STATUS_FAILED, "ناموفق"), (STATUS_EXPIRED, "منقضی")]

    account = models.ForeignKey(StorageAccount, on_delete=models.CASCADE, related_name="archive_jobs")
    folder = models.ForeignKey(StorageFolder, on_delete=models.CASCADE, related_name="archive_jobs")
    download_token = models.CharField("توکن دانلود زمان‌دار", max_length=43, unique=True, default=_gen_token)
    selected_paths = models.JSONField(default=list, blank=True)
    client_name = models.CharField("نام پیشنهادی فایل ZIP", max_length=255, blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_BUILDING)
    size_bytes = models.BigIntegerField(default=0)
    files_count = models.PositiveIntegerField(default=0)
    cost_coins = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    note = models.CharField(max_length=300, blank=True, default="")
    ready_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "آرشیو موقت"
        verbose_name_plural = "آرشیوهای موقت"
        ordering = ["-id"]

    def __str__(self):
        return f"آرشیو {self.client_name or self.pk}"

    def is_expired(self):
        return timezone.now() >= self.expires_at


# --------------------------------------------------------------------------- #
# دفتر ممیزی
# --------------------------------------------------------------------------- #
class StorageAuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="storage_audit_logs")
    action = models.CharField("اقدام", max_length=80)
    object_type = models.CharField(max_length=60, blank=True, default="")
    object_id = models.CharField(max_length=60, blank=True, default="")
    meta = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "رویداد ممیزی فضای ابری"
        verbose_name_plural = "رویدادهای ممیزی فضای ابری"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} — {self.actor} در {self.created_at:%Y-%m-%d %H:%M}"
