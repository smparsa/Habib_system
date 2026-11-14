"""مدل‌های ماژول «مجله دانستنی‌ها».

کانالی شبیه کانال تلگرامی:
- ادمین مطلب (متن / کلیپ / آهنگ / تصویر / ترکیبی، تا ۵۰ مگابایت) منتشر می‌کند.
- اعضایی که کد ملی ثبت کرده‌اند با ۱۰ ایموجی پرکاربرد به مطلب واکنش نشان می‌دهند.
- ماندن ۳۰ دقیقه‌ای در صفحه یک سکه پاداش می‌دهد (MagazineUserState).
"""

from django.conf import settings
from django.db import models

# ۱۰ ایموجی پرکاربرد (ترتیب نمایش در صفحه)
REACTION_EMOJIS = ["👍", "❤️", "😂", "😮", "😢", "😡", "🔥", "🎉", "👏", "💯"]

# سقف حجم کل پیوست‌های یک مطلب: زیر ۵۰ مگابایت
MAX_TOTAL_BYTES = 50 * 1024 * 1024  # 52428800

# مدت‌زمان لازم برای دریافت سکه (۳۰ دقیقه)
WATCH_SECONDS = 30 * 60  # 1800


def kind_for_file(name, content_type):
    """نوع نمایشی پیوست را از نام/محتوا تشخیص می‌دهد: image/video/audio/other."""
    name_l = (name or "").lower()
    if content_type:
        if content_type.startswith("image/"):
            return "image"
        if content_type.startswith("video/"):
            return "video"
        if content_type.startswith("audio/"):
            return "audio"
    if name_l.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
        return "image"
    if name_l.endswith((".mp4", ".webm", ".mov", ".mkv", ".m4v", ".avi", ".ogv")):
        return "video"
    if name_l.endswith((".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac", ".opus")):
        return "audio"
    return "other"


class MagazinePost(models.Model):
    """یک مطلب منتشرشده در مجله (توسط ادمین)."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="magazine_posts",
        verbose_name="نویسنده",
    )
    text = models.TextField("متن مطلب", blank=True)
    created_at = models.DateTimeField("تاریخ انتشار", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین ویرایش", auto_now=True)

    class Meta:
        verbose_name = "مطلب مجله"
        verbose_name_plural = "مطالب مجله"
        ordering = ["-created_at"]

    def __str__(self):
        return (self.text or "(بدون متن)")[:60]

    @property
    def display_kind(self):
        """برچسب نوع مطلب بر اساس پیوست‌ها."""
        kinds = {a.kind for a in self.attachments.all()}
        if "video" in kinds:
            return "video"
        if "audio" in kinds and len(kinds) == 1:
            return "audio"
        if kinds == {"image"}:
            return "image"
        if not self.attachments.exists():
            return "text"
        return "mixed"

    def emoji_counts(self):
        """دیکشنری ایموجی -> تعداد واکنش (فقط واکنش‌های موجود)."""
        return dict(
            self.reactions.values_list("emoji")
            .annotate(count=models.Count("id"))
            .order_by()
            .values_list("emoji", "count")
        )


class MagazineAttachment(models.Model):
    """پیوست یک مطلب: تصویر، کلیپ ویدئویی یا آهنگ/فایل صوتی."""

    post = models.ForeignKey(
        MagazinePost,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="مطلب",
    )
    file = models.FileField(upload_to="magazine/%Y/%m/", verbose_name="فایل")
    kind = models.CharField("نوع", max_length=10, default="other", editable=False)
    name = models.CharField("نام فایل", max_length=255, blank=True)
    size = models.PositiveBigIntegerField("حجم (بایت)", default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "پیوست مطلب"
        verbose_name_plural = "پیوست‌های مطالب"
        ordering = ["id"]

    def __str__(self):
        return f"{self.name or self.file.name} ({self.kind})"

    @property
    def size_mb(self):
        return round(self.size / (1024 * 1024), 1)


class MagazineReaction(models.Model):
    """واکنش یک کاربر با یک ایموجی روی یک مطلب (تکرار ثبت نمی‌شود)."""

    post = models.ForeignKey(
        MagazinePost,
        on_delete=models.CASCADE,
        related_name="reactions",
        verbose_name="مطلب",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="magazine_reactions",
        verbose_name="کاربر",
    )
    emoji = models.CharField("ایموجی", max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "واکنش"
        verbose_name_plural = "واکنش‌ها"
        constraints = [
            models.UniqueConstraint(
                fields=["post", "user", "emoji"], name="uniq_magazine_reaction"
            )
        ]

    def __str__(self):
        return f"{self.emoji} {self.user} → {self.post_id}"


class MagazineUserState(models.Model):
    """وضعیت سکه و تایمر ۳۰ دقیقه‌ای هر کاربر در مجله."""

    profile = models.OneToOneField(
        "accounts.Profile",
        on_delete=models.CASCADE,
        related_name="mag_state",
        verbose_name="پروفایل",
    )
    coins = models.PositiveIntegerField("سکه‌ها", default=0)
    watch_started_at = models.DateTimeField(
        "آغاز حضور در صفحه", blank=True, null=True
    )
    last_award_at = models.DateTimeField("آخرین پاداش سکه", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "وضعیت مجله کاربر"
        verbose_name_plural = "وضعیت مجله کاربران"

    def __str__(self):
        return f"{self.profile} — {self.coins} سکه"


class MagazineTicket(models.Model):
    """تیکت فوروارد مطلب: وقتی کاربری مطلبی را برای عضو دیگری (با کد ملی)
    فوروارد می‌کند، برای گیرنده تیکتی ساخته می‌شود که لینک همان مطلب را
    دارد و با کلیک روی آن، گیرنده به مجله و همان مطلب فوکوس می‌شود.
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mag_received_tickets",
        verbose_name="گیرنده",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mag_sent_tickets",
        verbose_name="فرستنده",
    )
    post = models.ForeignKey(
        MagazinePost,
        on_delete=models.CASCADE,
        related_name="tickets",
        verbose_name="مطلب",
    )
    is_read = models.BooleanField("خوانده‌شده", default=False)
    created_at = models.DateTimeField("تاریخ ارسال", auto_now_add=True)

    class Meta:
        verbose_name = "تیکت فوروارد مجله"
        verbose_name_plural = "تیکت‌های فوروارد مجله"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sender} → {self.recipient} (مطلب {self.post_id})"
