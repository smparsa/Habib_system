"""
کاتالوگ سلسله‌مراتبی مشاغل (۵ لایه):

    Sector (حوزه)
      └── Industry (صنعت)  ← می‌تواند زیرشاخهٔ تو در تو داشته باشد (parent)
            └── JobCategory (دسته‌بندی)
                  └── JobTitle (عنوان شغلی) — skill_tags (JSON)
                        └── JobSpecialization (تخصص‌های مرتبط)

هر کاربر این سلسله‌مراتب را با «شغل»های خودش در accounts.Job پیوند می‌دهد؛
accounts.Job همان نقش جدول واسطِ user_job_selections را دارد و تمام پنج لایه +
زمان ثبت + شغلِ اصلی (is_current) را نگه می‌دارد تا داده تکراری ساخته نشود.

حذف ردیف‌های بالادستی که زیرمجموعه دارند با on_delete=PROTECT مسدود است
(معادل ON DELETE RESTRICT) و غیرفعال‌سازی موقت بدون حذف با is_active انجام می‌شود.
"""

from django.db import models


class Sector(models.Model):
    """لایهٔ ۱: حوزه‌های کلی (خدمات، صنعت، کشاورزی، فناوری اطلاعات و ...)"""

    name = models.CharField("نام حوزه", max_length=100)
    code = models.CharField("کد", max_length=20, unique=True)
    description = models.TextField("توضیحات", blank=True)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "حوزه شغلی"
        verbose_name_plural = "حوزه‌های شغلی"
        ordering = ["code"]
        indexes = [models.Index(fields=["is_active"], name="jb_sector_active_idx")]

    def __str__(self):
        return self.name


class Industry(models.Model):
    """لایهٔ ۲: صنایع هر حوزه؛ پشتیبانی از زیرشاخه‌های تو در تو با parent"""

    sector = models.ForeignKey(
        Sector,
        on_delete=models.PROTECT,
        related_name="industries",
        verbose_name="حوزه",
    )
    name = models.CharField("نام صنعت", max_length=150)
    code = models.CharField("کد", max_length=20, unique=True)
    description = models.TextField("توضیحات", blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="زیرمجموعهٔ صنعت",
    )
    level = models.PositiveSmallIntegerField("سطح سلسله‌مراتب", default=2)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "صنعت"
        verbose_name_plural = "صنایع"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["sector", "is_active"], name="jb_industry_sec_idx")
        ]

    def save(self, *args, **kwargs):
        # سطح هر صنعت: اگر زیرمجموعه باشد یک سطح عمیق‌تر از والد خودش است
        if self.parent_id:
            self.level = (self.parent.level if self.parent_id else 2) + 1
        else:
            self.level = 2
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class JobCategory(models.Model):
    """لایهٔ ۳: دسته‌بندی مشاغل زیر هر صنعت (توسعه‌دهنده، مدرس، حسابدار و ...)"""

    industry = models.ForeignKey(
        Industry,
        on_delete=models.PROTECT,
        related_name="categories",
        verbose_name="صنعت",
    )
    name = models.CharField("نام دسته", max_length=150)
    code = models.CharField("کد", max_length=20, unique=True)
    description = models.TextField("توضیحات", blank=True)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "دسته شغلی"
        verbose_name_plural = "دسته‌های شغلی"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["industry", "is_active"], name="jb_category_ind_idx")
        ]

    def __str__(self):
        return self.name


class JobTitle(models.Model):
    """لایهٔ ۴: عنوان شغلی زیر هر دسته (برنامه‌نویس وب، حسابدار و ...)"""

    category = models.ForeignKey(
        JobCategory,
        on_delete=models.PROTECT,
        related_name="titles",
        verbose_name="دسته شغلی",
    )
    name = models.CharField("نام عنوان", max_length=150)
    code = models.CharField("کد", max_length=20, unique=True)
    description = models.TextField("توضیحات", blank=True)
    skill_tags = models.JSONField("مهارت‌های مرتبط", default=list, blank=True)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "عنوان شغلی"
        verbose_name_plural = "عناوین شغلی"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["category", "is_active"], name="jb_title_cat_idx"),
            models.Index(fields=["name"], name="jb_title_name_idx"),
        ]

    def __str__(self):
        return self.name


class JobSpecialization(models.Model):
    """لایهٔ ۵: تخصص‌های مرتبط زیر هر عنوان (کلیدواژه‌های مرتبط با آن شغل)"""

    title = models.ForeignKey(
        JobTitle,
        on_delete=models.PROTECT,
        related_name="specializations",
        verbose_name="عنوان شغلی",
    )
    name = models.CharField("نام تخصص مرتبط", max_length=150)
    code = models.CharField("کد", max_length=20, unique=True)
    description = models.TextField("توضیحات", blank=True)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "تخصص مرتبط"
        verbose_name_plural = "تخصص‌های مرتبط"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["title", "is_active"], name="jb_spec_title_idx"),
            models.Index(fields=["name"], name="jb_spec_name_idx"),
        ]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# ابزار انتخاب/اعتبارسنجی زنجیره (پنج لایه) — سمت سرور
# ---------------------------------------------------------------------------


def resolve_selection(
    sector_id=None,
    industry_id=None,
    category_id=None,
    occupation_title_id=None,
    specialization_id=None,
):
    """
    از «عمیق‌ترین» انتخابِ کاربر یک زنجیرهٔ کامل و سازگار می‌سازد:

    - اگر فقط «تخصص مرتبط» انتخاب شده باشد، والدهایش (عنوان/دسته/صنعت/حوزه) خودکار
      از روی خودِ تخصص پیدا می‌شوند؛ بنابراین فرم می‌تواند حتی یک شناسه ارسال کند.
    - هر شناسهٔ صریحِ بالادستی که ارسال شده باید با زنجیره سازگار باشد وگرنه خطا می‌دهد.

    خروجی: دیکشنری {"sector": obj|None, "industry": ..., "category": ...,
                     "occupation_title": ..., "specialization": ...}
    در صورت بی‌مقدار بودن همه: دیکشنری با مقدارهای None برمی‌گردد.
    """

    def _active(model, pk, label):
        if not pk:
            return None
        obj = model.objects.filter(pk=pk, is_active=True).first()
        if obj is None:
            raise ValueError(f"آیتم «{label}» انتخاب‌شده در فهرست فعال وجود ندارد. لطفاً دوباره انتخاب کنید.")
        return obj

    spec = _active(JobSpecialization, specialization_id, "تخصص‌های مرتبط")
    title = _active(JobTitle, occupation_title_id, "عنوان شغلی")
    cat = _active(JobCategory, category_id, "دسته شغلی")
    ind = _active(Industry, industry_id, "صنعت")
    sec = _active(Sector, sector_id, "حوزه")

    # اگر سطح پایین‌تری انتخاب شده، والدهایش از خودِ رکورد استخراج می‌شود
    if spec is not None:
        title = spec.title
        cat = title.category
        ind = cat.industry
        sec = ind.sector
    elif title is not None:
        cat = title.category
        ind = cat.industry
        sec = ind.sector
    elif cat is not None:
        ind = cat.industry
        sec = ind.sector
    elif ind is not None:
        sec = ind.sector

    # سازگاری شناسه‌های صریحِ ارسال‌شده با زنجیرهٔ نهایی
    checks = (
        (sec, sector_id, "حوزه"),
        (ind, industry_id, "صنعت"),
        (cat, category_id, "دسته شغلی"),
        (title, occupation_title_id, "عنوان شغلی"),
        (spec, specialization_id, "تخصص‌های مرتبط"),
    )
    for obj, given_id, label in checks:
        if given_id and obj is not None and obj.pk != given_id:
            raise ValueError(
                f"«{label}» انتخاب‌شده با سایر سطوح سازگار نیست. لطفاً از فهرست انتخاب کنید."
            )

    return {
        "sector": sec,
        "industry": ind,
        "category": cat,
        "occupation_title": title,
        "specialization": spec,
    }


def build_catalog_code(
    sector_id=None,
    industry_id=None,
    category_id=None,
    occupation_title_id=None,
    specialization_id=None,
):
    """
    کد اختصاصی شغل از روی شناسهٔ رکوردهای دیتابیسِ پنج لایهٔ کاتالوگ ساخته می‌شود
    (نه شمارهٔ شغل کاربر): شناسهٔ هر رکوردِ انتخاب‌شده پشت سر هم می‌چسبد، مثلاً
    حوزه=۳، صنعت=۷، دسته=۱۱، عنوان=۲۰ و تخصص‌های مرتبط=۲۶  ←  «37112026».

    چون کد فقط به رکوردهای کاتالوگ وابسته است، برای همهٔ کاربرانی که همین شغل را
    انتخاب کنند یکسان خواهد بود و می‌تواند بین کاربران تکرار شود.
    """
    return "".join(
        str(pk)
        for pk in (
            sector_id,
            industry_id,
            category_id,
            occupation_title_id,
            specialization_id,
        )
        if pk is not None
    )


def leaf_label(chain):
    """نام عمیق‌ترین سطح زنجیره برای نمایش/عنوان پیش‌فرض."""
    for key in ("specialization", "occupation_title", "category", "industry", "sector"):
        obj = chain.get(key)
        if obj is not None:
            return obj.name
    return ""


def breadcrumb(chain):
    """مسیر کامل نمایشی: حوزه › صنعت › دسته › عنوان › تخصص‌های مرتبط"""
    parts = [
        obj.name
        for key in ("sector", "industry", "category", "occupation_title", "specialization")
        for obj in [chain.get(key)]
        if obj is not None
    ]
    return " › ".join(parts)
