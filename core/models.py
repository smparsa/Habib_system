from django.db import models


class InfoPage(models.Model):
    """صفحات اطلاعاتی/قانونی برنامه (درباره ما، حریم خصوصی، قوانین و …).

    محتوا به فارسی و استاندارد است، توسط ادمین از پنل مدیریت ویرایش می‌شود و
    عنوان/لینک هر صفحهٔ فعال به‌صورت خودکار در سایدبار و پانویس برنامه ظاهر می‌گردد.
    """

    # شناسه‌های ثابت صفحه — هر صفحه فقط یک‌بار وجود دارد
    SLUG_CHOICES = (
        ("about", "درباره ما"),
        ("privacy", "حریم خصوصی"),
        ("terms", "قوانین و مقررات"),
        ("support", "پشتیبانی"),
        ("help", "مرکز راهنما"),
        ("contact", "تماس با ما"),
    )

    slug = models.SlugField(
        "شناسهٔ صفحه", max_length=20, unique=True, choices=SLUG_CHOICES,
        help_text="شناسهٔ صفحه را تغییر ندهید؛ لینک‌های برنامه به همین شناسه‌ها متصل‌اند.",
    )
    title = models.CharField("عنوان صفحه", max_length=120)
    subtitle = models.CharField(
        "زیرعنوان", max_length=200, blank=True,
        help_text="توضیح کوتاه زیر عنوان صفحه.",
    )
    icon = models.CharField(
        "آیکن", max_length=40, default="bi-info-circle",
        help_text="کلاس آیکن بوت‌استرپ، مثل bi-info-circle",
    )
    content = models.TextField(
        "محتوای صفحه", blank=True,
        help_text="محتوای HTML صفحه (فارسی). با ساختار کارت‌های برنامه هماهنگ است.",
    )
    is_active = models.BooleanField("فعال", default=True)
    show_in_sidebar = models.BooleanField("نمایش در منوی کنار", default=True)
    show_in_footer = models.BooleanField("نمایش در پانویس", default=True)
    sort_order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)
    updated_at = models.DateTimeField("آخرین به‌روزرسانی", auto_now=True)

    # اطلاعات تماس — فقط برای صفحهٔ «تماس با ما» استفاده می‌شود
    contact_phone = models.CharField("تلفن پشتیبانی", max_length=30, blank=True)
    contact_email = models.EmailField("ایمیل پشتیبانی", blank=True)
    contact_address = models.CharField("نشانی", max_length=300, blank=True)
    contact_hours = models.CharField("ساعات پاسخگویی", max_length=200, blank=True)

    class Meta:
        verbose_name = "صفحهٔ اطلاعاتی"
        verbose_name_plural = "صفحات اطلاعاتی"
        ordering = ("sort_order", "id")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("core:info_page", args=[self.slug])

    @classmethod
    def sidebar_pages(cls):
        return cls.objects.filter(is_active=True, show_in_sidebar=True)

    @classmethod
    def footer_pages(cls):
        return cls.objects.filter(is_active=True, show_in_footer=True)


class SiteFeedback(models.Model):
    """نظرسنجی رضایت کاربران (بومی‌سازی‌شدهٔ فرم بازخورد اولیه برای حبیب‌هاب)."""

    SATISFACTION_CHOICES = [(i, str(i)) for i in range(1, 6)]
    QUALITY_CHOICES = (
        ("excellent", "عالی"),
        ("good", "خوب"),
        ("average", "متوسط"),
        ("poor", "ضعیف"),
    )
    RECOMMEND_CHOICES = (
        ("yes", "بله"),
        ("maybe", "شاید"),
        ("no", "خیر"),
    )

    user = models.ForeignKey(
        "accounts.User", verbose_name="کاربر", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="site_feedbacks",
    )
    satisfaction = models.PositiveSmallIntegerField(
        "رضایت کلی (۱ تا ۵)", choices=SATISFACTION_CHOICES,
    )
    quality = models.CharField(
        "کیفیت امکانات", max_length=20, choices=QUALITY_CHOICES, blank=True,
    )
    support_speed = models.CharField(
        "سرعت پاسخ‌گویی پشتیبانی", max_length=20, choices=QUALITY_CHOICES, blank=True,
    )
    recommend = models.CharField(
        "توصیه به دیگران", max_length=10, choices=RECOMMEND_CHOICES, blank=True,
    )
    sources = models.CharField("نحوهٔ آشنایی", max_length=200, blank=True)
    improvements = models.TextField("پیشنهادها و انتقادها", blank=True)
    created_at = models.DateTimeField("تاریخ ثبت", auto_now_add=True)

    class Meta:
        verbose_name = "نظرسنجی رضایت"
        verbose_name_plural = "نظرسنجی‌های رضایت"
        ordering = ("-created_at",)

    def __str__(self):
        return f"نظرسنجی #{self.pk} — امتیاز {self.satisfaction}/۵"
