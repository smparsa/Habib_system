"""فرم‌های پنل مدیریت: کاتالوگ مشاغل + مدیریت کاربران و پروفایل‌ها + پالایش محتوا
+ جوامع هدف تیکت + انواع تیکت + سکه و کیف پول."""

import re
from datetime import datetime, timedelta

from django import forms
from django.conf import settings
from django.utils import timezone
from PIL import Image as PILImage

from accounts.forms import CountrySelect, _country_data, name_choices_with_en
from accounts.models import (
    CityTbl,
    CountryTbl,
    EducationInstitution,
    FameNameTbl,
    StudyField,
    StudyGroup,
    StudySpecialization,
    FamilynameTbl,
    FirstnameTbl,
    LocationSetting,
    Profile,
    ProvinceTbl,
    ReservedNationalCode,
    User,
)
from adminpanel.models import (
    AD_STATUS_APPROVED,
    AD_STATUS_PENDING,
    AD_STATUS_REJECTED,
    AdHeaderPlacement,
    Advertisement,
    BackupSetting,
    BreakingNews,
    STAT_SLIDE_MAX_PER_BOX,
    StatSlide,
    StatSlideBox,
)
from jobs.models import Industry, JobCategory, JobSpecialization, JobTitle, Sector
from tickets import constants as TICKET_C
from tickets.models import SensitiveTerm, TicketAudience, TicketCategory
from wallet.models import FeatureCost, RewardRule, WalletSetting


# ---------------------------------------------------------------------------
# مدیریت کاربران و پروفایل‌ها
# ---------------------------------------------------------------------------

# بخش‌های قابل ویرایشِ پروفایل در پنل ادمین؛ ترتیب بخش‌ها و فیلدها در همین‌جا
# تعریف می‌شود و به‌طور خودکار به فرم (Meta.fields) و قالب (حلقهٔ بخش‌ها) می‌رود.
ADMIN_PROFILE_SECTIONS = [
    {
        "key": "personal",
        "icon": "bi-person",
        "title": "اطلاعات فردی",
        "fields": [
            "first_name", "last_name", "family_suffix", "fame_name",
            "national_id", "date_of_birth", "gender",
            "citizenship", "nationality", "permanent_residence",
            "religion", "sect", "bio",
        ],
    },
    {
        # نام پدر/مادر و وضعیت تأهل از بخش «اطلاعات شخصی» پروفایل به
        # «اطلاعات خانواده» منتقل شده‌اند؛ پنل ادمین هم همان ساختار را دارد.
        "key": "family",
        "icon": "bi-people-fill",
        "title": "اطلاعات خانواده",
        "fields": ["father_name", "mother_name", "marital_status"],
    },
    {
        "key": "contact",
        "icon": "bi-geo-alt",
        "title": "تماس و موقعیت مکانی",
        "fields": [
            "email", "phone", "emergency_contact",
            "country", "province", "city", "address", "postal_code",
        ],
    },
    {
        "key": "org",
        "icon": "bi-briefcase",
        "title": "اطلاعات شغلی و سازمانی",
        "fields": [
            "job_title", "department", "employment_type", "branch",
            "personnel_id", "org_code", "work_group",
        ],
    },
    {
        "key": "education",
        "icon": "bi-mortarboard",
        "title": "تحصیلات",
        "fields": [
            "degree", "education_institution", "study_field", "study_specialization",
            "field_of_study", "university", "graduation_year",
        ],
    },
]

_TEXT_WIDGET = forms.TextInput(attrs={"class": "hb-form-control"})
_SELECT_WIDGET = forms.Select(attrs={"class": "hb-form-control hb-form-select"})
# فیلدهای نام: کلاس hb-name-select → انتخاب‌گرِ جستجویی (نوعی) در app.js
_NAME_SELECT_WIDGET = forms.Select(
    attrs={"class": "hb-form-control hb-form-select hb-name-select"}
)


class AdminUserForm(forms.ModelForm):
    """فرم حساب کاربری برای ادمین: شماره موبایل + وضعیت فعال/ادمین/سوپریوزر.

    when editing خودِ ادمینِ واردشده (for_self=True) امکان تغییر دسترسی‌ها وجود ندارد
    تا کسی ناخواسته دسترسی ادمین خودش را از دست ندهد؛ فیلدها غیرفعال می‌شوند.
    """

    def __init__(self, *args, for_self=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.for_self = for_self
        if for_self:
            for name in ("is_active", "is_staff", "is_superuser"):
                self.fields[name].disabled = True
                self.fields[name].help_text = "تغییر دسترسی حساب خودتان در پنل ممکن نیست."

    def clean_mobile_number(self):
        mobile = (self.cleaned_data.get("mobile_number") or "").strip()
        if not re.fullmatch(r"09\d{9}", mobile):
            raise forms.ValidationError(
                "شماره موبایل باید ۱۱ رقم و با ۰۹ شروع شود (مثلاً ۰۹۱۲۰۰۰۰۰۱۱)."
            )
        exists = (
            User.objects.filter(mobile_number=mobile)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise forms.ValidationError(
                "این شماره موبایل قبلاً برای کاربر دیگری ثبت شده است."
            )
        return mobile

    class Meta:
        model = User
        fields = ["mobile_number", "is_active", "is_staff", "is_superuser"]
        widgets = {
            "mobile_number": forms.TextInput(
                attrs={"class": "hb-form-control", "dir": "ltr", "placeholder": "مثال: 09120000011"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
            "is_superuser": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }
        labels = {
            "mobile_number": "شماره موبایل",
            "is_active": "حساب فعال است",
            "is_staff": "دسترسی ادمین (پنل مدیریت)",
            "is_superuser": "سوپریوزر (Django Admin)",
        }
        help_texts = {
            "mobile_number": "شماره موبایل شناسهٔ ورود کاربر است؛ با تغییر آن، ورود بعدی با شمارهٔ جدید انجام می‌شود.",
            "is_active": "کاربر غیرفعال دیگر نمی‌تواند وارد برنامه شود.",
        }


class AdminProfileForm(forms.ModelForm):
    """ویرایش پروفایل کاربر توسط ادمین؛ همهٔ فیلدها اختیاری‌اند تا ذخیرهٔ پروفایلِ ناقص ممکن باشد.

    فیلدهای مالی/حساس (شماره حساب، شبا، حقوق و ...) و «مدیر مستقیم» عمداً در پنل ادمین
    قابل ویرایش نیستند و از طریق Django Admin در دسترس‌اند.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # «نام» همهٔ نام‌ها؛ «نام پدر/مادر» بر اساس جنسیتِ جدول نام‌ها؛
        # «شهرت» از جدول مرجع شهرت‌ها (FameNameTbl).
        self.fields["first_name"].queryset = FirstnameTbl.objects.all()
        self.fields["last_name"].queryset = FamilynameTbl.objects.all()
        self.fields["fame_name"].queryset = FameNameTbl.objects.all()
        self.fields["father_name"].queryset = FirstnameTbl.objects.filter(
            gender__in=["male", ""]
        )
        self.fields["mother_name"].queryset = FirstnameTbl.objects.filter(
            gender__in=["female", ""]
        )
        # تابعیت/ملیت/اقامت دائم: منوی کشویی نام کشورها از جدول مرجع CountryTbl
        # (مثل فرم «اطلاعات شخصی» کاربر؛ پیش‌فرض «ایران» از روی مدل می‌آید) با
        # برچسب دو زبانه و جستجوی تایپی (hb-country-select).
        country_choices, country_en_map = _country_data()
        for name in ("citizenship", "nationality", "permanent_residence"):
            self.fields[name].widget = CountrySelect(
                choices=country_choices,
                attrs={"class": "hb-form-control hb-form-select hb-country-select"},
            )
            self.fields[name].widget.country_en = country_en_map
        # نمایش دو زبانهٔ «فارسی (لاتین)» + راهنمای جستجو برای فیلدهای نام.
        # data-hb-kind: first|family|fame و data-hb-gender: محدودیت جنسیت برای پدر/مادر
        for name, fa_attr, en_attr, kind, gender in (
            ("first_name", "first_name_fa", "first_name_en", "first", ""),
            ("last_name", "familyname_fa", "familyname_en", "family", ""),
            ("fame_name", "fame_name_fa", "fame_name_en", "fame", ""),
            ("father_name", "first_name_fa", "first_name_en", "first", "male"),
            ("mother_name", "first_name_fa", "first_name_en", "first", "female"),
        ):
            self.fields[name].widget.attrs["data-hb-filter-hint"] = (
                "تایپ کنید و از فهرست انتخاب کنید…"
            )
            self.fields[name].widget.attrs["data-hb-kind"] = kind
            self.fields[name].widget.attrs["data-hb-gender"] = gender
            self.fields[name].choices = name_choices_with_en(
                self.fields[name].queryset, fa_attr, en_attr
            )
        # انتخاب‌های مرجع تحصیلی؛ فقط مراکز/رشته‌ها/گرایش‌های فعال برای پروفایل
        # کاربر در دسترس‌اند. متن‌های قدیمی نیز عمداً حفظ شده‌اند.
        self.fields["education_institution"].queryset = EducationInstitution.objects.filter(
            is_active=True
        ).order_by("institution_type", "name")
        self.fields["study_field"].queryset = StudyField.objects.filter(
            is_active=True
        ).select_related("study_group").order_by("study_group__name", "name")
        self.fields["study_specialization"].queryset = StudySpecialization.objects.filter(
            is_active=True, field__is_active=True
        ).select_related("field").order_by("field__name", "name")

        # فیلدهای «اطلاعات فردی» همانند فرم «اطلاعات شخصی» کاربر الزامی‌اند (بجز
        # بیوگرافی) تا پروفایلی که از پنل ذخیره می‌شود هم کامل باشد.
        for field_name, message in (
            ("first_name", "لطفاً نام را از فهرست انتخاب کنید."),
            ("last_name", "لطفاً نام خانوادگی را از فهرست انتخاب کنید."),
            ("father_name", "لطفاً نام پدر را از فهرست انتخاب کنید."),
            ("mother_name", "لطفاً نام مادر را از فهرست انتخاب کنید."),
            ("national_id", "کد ملی الزامی است."),
            ("date_of_birth", "لطفاً تاریخ تولد را انتخاب کنید."),
            ("gender", "لطفاً جنسیت را انتخاب کنید."),
            ("marital_status", "لطفاً وضعیت تأهل را انتخاب کنید."),
            ("citizenship", "لطفاً تابعیت را انتخاب کنید."),
            ("nationality", "لطفاً ملیت را انتخاب کنید."),
            ("permanent_residence", "لطفاً اقامت دائم را انتخاب کنید."),
            ("religion", "لطفاً دین را انتخاب کنید."),
            ("sect", "لطفاً مذهب را انتخاب کنید."),
        ):
            self.fields[field_name].required = True
            self.fields[field_name].error_messages["required"] = message

    class Meta:
        model = Profile
        fields = [
            field
            for section in ADMIN_PROFILE_SECTIONS
            for field in section["fields"]
        ]
        widgets = {
            "first_name": _NAME_SELECT_WIDGET,
            "last_name": _NAME_SELECT_WIDGET,
            "fame_name": _NAME_SELECT_WIDGET,
            "family_suffix": forms.TextInput(attrs={
                "class": "hb-form-control", "placeholder": "مثال: رود، نژاد، زاده، پور… (اختیاری)"}),
            "father_name": _NAME_SELECT_WIDGET,
            "mother_name": _NAME_SELECT_WIDGET,
            "national_id": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "date_of_birth": forms.DateInput(
                attrs={"class": "hb-form-control", "type": "date"}
            ),
            "gender": _SELECT_WIDGET,
            "marital_status": _SELECT_WIDGET,
            "religion": _SELECT_WIDGET,
            "sect": _SELECT_WIDGET,
            "bio": forms.Textarea(attrs={"class": "hb-form-control hb-form-textarea", "rows": 4}),
            "email": forms.EmailInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "phone": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "emergency_contact": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            # کشور/استان/شهر: با تایپ از جدول مرجع (دیتابیسِ ادمین) انتخاب می‌شود
            "country": forms.TextInput(attrs={
                "class": "hb-form-control hb-loc-autocomplete",
                "data-hb-loc-kind": "country", "autocomplete": "off",
            }),
            "province": forms.TextInput(attrs={
                "class": "hb-form-control hb-loc-autocomplete",
                "data-hb-loc-kind": "province", "autocomplete": "off",
            }),
            "city": forms.TextInput(attrs={
                "class": "hb-form-control hb-loc-autocomplete",
                "data-hb-loc-kind": "city", "autocomplete": "off",
            }),
            "address": forms.TextInput(attrs={"class": "hb-form-control", "placeholder": "خیابان، کوچه، پلاک"}),
            "postal_code": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "job_title": _TEXT_WIDGET,
            "department": _TEXT_WIDGET,
            "employment_type": _TEXT_WIDGET,
            "branch": _TEXT_WIDGET,
            "personnel_id": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "org_code": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "work_group": _TEXT_WIDGET,
            "degree": _TEXT_WIDGET,
            "education_institution": forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
            "study_field": forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
            "study_specialization": forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
            "field_of_study": _TEXT_WIDGET,
            "university": _TEXT_WIDGET,
            "graduation_year": forms.NumberInput(
                attrs={"class": "hb-form-control", "dir": "ltr"}
            ),
        }

_CODE_HELP = "کد یکتا (لطفاً فارسی/فضای خالی نداشته باشد)؛ باید در کل جدول یکتا باشد."


# ---------------------------------------------------------------------------
# پالایش محتوا: واژه‌ها و عبارت‌های حساس تیکت‌ها
# ---------------------------------------------------------------------------


class EducationInstitutionForm(forms.ModelForm):
    """فرم مدیریت مرکز دانشگاهی/آموزش عالی."""

    class Meta:
        model = EducationInstitution
        fields = [
            "name", "name_en", "code", "institution_type", "province", "city",
            "source", "source_year", "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "hb-form-control"}),
            "name_en": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "code": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "institution_type": forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
            "province": forms.TextInput(attrs={"class": "hb-form-control"}),
            "city": forms.TextInput(attrs={"class": "hb-form-control"}),
            "source": forms.TextInput(attrs={"class": "hb-form-control"}),
            "source_year": forms.NumberInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }
        labels = {
            "name": "نام مرکز", "name_en": "نام مرکز (انگلیسی)", "code": "کد مرکز",
            "institution_type": "نوع مرکز", "province": "استان", "city": "شهر",
            "source": "منبع فهرست", "source_year": "سال منبع", "is_active": "فعال",
        }


class StudyGroupForm(forms.ModelForm):
    """فرم مدیریت گروه امتحانی (لایهٔ ۱ اطلاعات تحصیلی)."""

    class Meta:
        model = StudyGroup
        fields = ["name", "name_en", "code", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "hb-form-control"}),
            "name_en": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "code": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "description": forms.Textarea(attrs={"class": "hb-form-control hb-form-textarea", "rows": 3}),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }
        labels = {
            "name": "نام گروه", "name_en": "نام گروه (انگلیسی)", "code": "کد گروه",
            "description": "توضیحات", "is_active": "فعال",
        }


class StudyFieldForm(forms.ModelForm):
    """فرم مدیریت رشتهٔ تحصیلی."""

    class Meta:
        model = StudyField
        fields = ["study_group", "name", "name_en", "code", "source", "source_year", "is_active"]
        widgets = {
            "study_group": forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
            "name": forms.TextInput(attrs={"class": "hb-form-control"}),
            "name_en": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "code": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "source": forms.TextInput(attrs={"class": "hb-form-control"}),
            "source_year": forms.NumberInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }
        labels = {
            "study_group": "گروه امتحانی", "name": "نام رشته", "name_en": "نام رشته (انگلیسی)", "code": "کد رشته",
            "source": "منبع فهرست", "source_year": "سال منبع", "is_active": "فعال",
        }


class StudySpecializationForm(forms.ModelForm):
    """فرم مدیریت گرایش و اتصال آن به رشتهٔ مادر."""

    class Meta:
        model = StudySpecialization
        fields = ["field", "name", "name_en", "code", "source", "source_year", "is_active"]
        widgets = {
            "field": forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
            "name": forms.TextInput(attrs={"class": "hb-form-control"}),
            "name_en": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "code": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "source": forms.TextInput(attrs={"class": "hb-form-control"}),
            "source_year": forms.NumberInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }
        labels = {
            "field": "رشتهٔ مادر", "name": "نام گرایش", "name_en": "نام گرایش (انگلیسی)",
            "code": "کد گرایش", "source": "منبع فهرست", "source_year": "سال منبع",
            "is_active": "فعال",
        }


class SensitiveTermForm(forms.ModelForm):
    """ثبت/ویرایش واژهٔ حساس توسط ادمین؛ اعتبارسنجی حالت‌های تطبیق و regex."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["term"].help_text = (
            "واژه یا عبارت را همان‌طور که کاربران می‌نویسند وارد کنید؛ املای عربی/فارسی و "
            "حرکت/نیم‌فاصله هنگام بررسی خودکار نرمال می‌شوند."
        )

    def clean_term(self):
        term = (self.cleaned_data.get("term") or "").strip()
        if not term:
            raise forms.ValidationError("واژه/الگو را وارد کنید.")
        from tickets.filtering import is_valid_pattern, normalize

        mode = self.data.get("mode") or self.instance.mode or "word"
        if not normalize(term):
            raise forms.ValidationError(
                "الگو فقط از نویسه‌های بی‌صدا ساخته شده و قابل استفاده نیست."
            )
        if mode == "regex" and not is_valid_pattern(term, mode):
            raise forms.ValidationError(
                "الگوی منظم (regex) معتبر نیست؛ برای آزمودن الگو از بخش «آزمون متن» استفاده کنید."
            )
        return term

    class Meta:
        model = SensitiveTerm
        fields = ["term", "mode", "category", "note", "is_active"]
        widgets = {
            "term": forms.TextInput(attrs={"class": "hb-form-control"}),
            "mode": forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
            "category": forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
            "note": forms.TextInput(attrs={
                "class": "hb-form-control",
                "placeholder": "اختیاری: یادداشت برای سایر ادمین‌ها",
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }
        help_texts = {
            "mode": (
                "«واژهٔ کامل» برای کلمات مستقل؛ «ابتدای واژه» برای گرفتن شکل‌های صرف‌شدهٔ "
                "یک کلمه؛ «هر جای متن» برای عبارت‌های چندکلمه‌ای؛ «regex» برای الگوهای پیشرفته."
            ),
            "category": "دسته‌بندی برای تذکر دقیق‌تر به کاربر و گزارش‌گیری.",
            "is_active": "با غیرفعال‌کردن، واژه بدون حذف از چرخهٔ پالایش خارج می‌شود.",
        }


def _code_field(placeholder):
    """فیلد کد با پیام خطای فارسی برای تکرار کد در کل جدول."""
    return forms.CharField(
        label="کد",
        max_length=20,
        error_messages={
            "unique": "این کد قبلاً برای رکورد دیگری ثبت شده است.",
        },
        widget=forms.TextInput(
            attrs={"class": "hb-form-control", "dir": "ltr", "placeholder": placeholder}
        ),
    )


class SectorForm(forms.ModelForm):
    code = _code_field("مثال: S-01")

    class Meta:
        model = Sector
        fields = ["name", "code", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "hb-form-control"}),
            "description": forms.Textarea(
                attrs={"class": "hb-form-control hb-form-textarea", "rows": 5}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }
        help_texts = {"code": _CODE_HELP}


class IndustryForm(forms.ModelForm):
    code = _code_field("مثال: I-05")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # هنگام ویرایش، خودِ رکورد نمی‌تواند زیرمجموعهٔ خودش باشد
        if self.instance.pk:
            self.fields["parent"].queryset = Industry.objects.exclude(pk=self.instance.pk)

    def clean(self):
        cleaned = super().clean()
        parent = cleaned.get("parent")
        sector = cleaned.get("sector")
        if parent and sector and parent.sector_id != sector.pk:
            self.add_error(
                "parent",
                "زیرمجموعهٔ صنعت باید در همان حوزه‌ای باشد که خود صنعت در آن قرار دارد.",
            )
        return cleaned

    class Meta:
        model = Industry
        fields = ["sector", "parent", "name", "code", "description", "is_active"]
        widgets = {
            "sector": forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
            "parent": forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
            "name": forms.TextInput(attrs={"class": "hb-form-control"}),
            "description": forms.Textarea(
                attrs={"class": "hb-form-control hb-form-textarea", "rows": 5}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }
        help_texts = {
            "code": _CODE_HELP,
            "parent": "اختیاری؛ برای زیرشاخه‌های تو در تو (مثلاً «نرم‌افزار» زیرمجموعهٔ «فناوری اطلاعات»).",
        }


class JobCategoryForm(forms.ModelForm):
    code = _code_field("مثال: C-03")

    class Meta:
        model = JobCategory
        fields = ["industry", "name", "code", "description", "is_active"]
        widgets = {
            "industry": forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
            "name": forms.TextInput(attrs={"class": "hb-form-control"}),
            "description": forms.Textarea(
                attrs={"class": "hb-form-control hb-form-textarea", "rows": 5}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }
        help_texts = {"code": _CODE_HELP}


class JobTitleForm(forms.ModelForm):
    """عنوان شغلی + مهارت‌های مرتبط (JSON) به‌صورت ورودیِ کاما-جدا."""

    code = _code_field("مثال: T-12")
    skill_tags = forms.CharField(
        required=False,
        label="مهارت‌های مرتبط (با کاما جدا کنید)",
        widget=forms.TextInput(
            attrs={
                "class": "hb-form-control",
                "placeholder": "مثال: طراحی سازه، ETABS، نقشه‌کشی",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.skill_tags:
            self.fields["skill_tags"].initial = "، ".join(self.instance.skill_tags)

    def clean_skill_tags(self):
        raw = self.cleaned_data.get("skill_tags") or ""
        tags = [t.strip() for t in raw.replace("،", ",").split(",") if t.strip()]
        return tags

    class Meta:
        model = JobTitle
        fields = ["category", "name", "code", "description", "skill_tags", "is_active"]
        widgets = {
            "category": forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
            "name": forms.TextInput(attrs={"class": "hb-form-control"}),
            "description": forms.Textarea(
                attrs={"class": "hb-form-control hb-form-textarea", "rows": 5}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }
        help_texts = {"code": _CODE_HELP}


class JobSpecializationForm(forms.ModelForm):
    code = _code_field("مثال: SP-08")

    class Meta:
        model = JobSpecialization
        fields = ["title", "name", "code", "description", "is_active"]
        widgets = {
            "title": forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
            "name": forms.TextInput(attrs={"class": "hb-form-control"}),
            "description": forms.Textarea(
                attrs={"class": "hb-form-control hb-form-textarea", "rows": 5}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }
        help_texts = {"code": _CODE_HELP}


# ---------------------------------------------------------------------------
# جوامع هدف تیکت (مخاطبین هدف تعریف‌شده توسط ادمین)
# ---------------------------------------------------------------------------

# کد لایه ← نوع مخاطب در موتور هدف‌گیری
_JOB_LAYER_TO_KIND = {
    "sector": TICKET_C.AUD_JOB_SECTOR,
    "industry": TICKET_C.AUD_JOB_INDUSTRY,
    "category": TICKET_C.AUD_JOB_CATEGORY,
    "title": TICKET_C.AUD_JOB_TITLE,
    "specialization": TICKET_C.AUD_JOB_SPEC,
}

_JOB_LAYER_CHOICES = [
    ("sector", "حوزه (لایهٔ ۱)"),
    ("industry", "صنعت (لایهٔ ۲)"),
    ("category", "دسته (لایهٔ ۳)"),
    ("title", "عنوان (لایهٔ ۴)"),
    ("specialization", "تخصص (لایهٔ ۵)"),
]


class TicketAudienceForm(forms.ModelForm):
    """تعریف جامعهٔ هدف توسط ادمین؛ قواعد نهایی به ساختار موتور هدف‌گیری تبدیل می‌شود.

    فیلدهای وابسته به «نوع مخاطب» با پیشوند aud_* تعریف شده‌اند تا فقط همان‌ها
    هنگام انتخاب نوع، نمایش داده و در clean() اعتبارسنجی شوند.
    """

    kind = forms.ChoiceField(
        label="نوع مخاطب",
        choices=[(k, TICKET_C.AUD_LABELS.get(k, k)) for k in TICKET_C.AUD_KINDS],
        widget=forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
    )
    aud_geo = forms.CharField(
        required=False, label="کشور/استان/شهر",
        widget=forms.Textarea(attrs={
            "class": "hb-form-control hb-form-textarea", "rows": 2,
            "placeholder": "نام‌ها را با کاما جدا کنید؛ مثال: تهران، کرج",
        }),
    )
    aud_lat = forms.FloatField(required=False, label="عرض جغرافیایی (lat)",
                               widget=forms.NumberInput(attrs={"class": "hb-form-control", "dir": "ltr"}))
    aud_lng = forms.FloatField(required=False, label="طول جغرافیایی (lng)",
                               widget=forms.NumberInput(attrs={"class": "hb-form-control", "dir": "ltr"}))
    aud_radius = forms.FloatField(required=False, label="شعاع", min_value=0.001,
                                  widget=forms.NumberInput(attrs={"class": "hb-form-control", "dir": "ltr"}))
    aud_radius_unit = forms.ChoiceField(
        required=False, label="واحد شعاع",
        choices=[("m", "متر"), ("km", "کیلومتر")],
        widget=forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
    )
    aud_job_layer = forms.ChoiceField(
        required=False, label="لایهٔ شغلی",
        choices=[("", "— انتخاب کنید —")] + _JOB_LAYER_CHOICES,
        widget=forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
    )
    aud_job_names = forms.CharField(
        required=False, label="نام رده‌های شغلی",
        widget=forms.Textarea(attrs={
            "class": "hb-form-control hb-form-textarea", "rows": 2,
            "placeholder": "نام‌ها را با کاما جدا کنید؛ مثال: سازه، معماری\n(نام‌ها از کاتالوگ مشاغل پنل مدیریت قابل کپی‌کردن‌اند)",
        }),
    )
    aud_nids = forms.CharField(
        required=False, label="کد ملی کاربران",
        widget=forms.Textarea(attrs={
            "class": "hb-form-control hb-form-textarea", "rows": 3,
            "placeholder": "هر کد ملی را در یک خط وارد کنید", "dir": "ltr",
        }),
    )
    aud_mobile_prefixes = forms.CharField(
        required=False, label="شروع شماره موبایل",
        widget=forms.TextInput(attrs={
            "class": "hb-form-control", "dir": "ltr",
            "placeholder": "مثال: 0912, 0935",
        }),
    )
    aud_age_min = forms.IntegerField(required=False, label="حداقل سن", min_value=0,
                                     widget=forms.NumberInput(attrs={"class": "hb-form-control", "dir": "ltr"}))
    aud_age_max = forms.IntegerField(required=False, label="حداکثر سن", min_value=0,
                                     widget=forms.NumberInput(attrs={"class": "hb-form-control", "dir": "ltr"}))

    class Meta:
        model = TicketAudience
        fields = ["name", "kind", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "hb-form-control",
                "placeholder": "مثال: کاربران تهران",
            }),
            "description": forms.TextInput(attrs={
                "class": "hb-form-control",
                "placeholder": "توضیح کوتاه برای کاربر هنگام انتخاب (اختیاری)",
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kind"].help_text = (
            "کاربر هنگام ارسال تیکت، این جامعهٔ هدف را از فهرست انتخاب و تیکتش را "
            "به‌صورت انبوه برای همهٔ واجدین شرایط می‌فرستد."
        )
        # بازگرداندن مقادیر فیلدهای وابسته هنگام ویرایش
        if self.instance.pk and self.instance.rules:
            leaf = self._first_leaf(self.instance.rules)
            if leaf:
                kind = leaf.get("kind")
                values = leaf.get("values") or leaf.get("value") or []
                if kind in (TICKET_C.AUD_COUNTRY, TICKET_C.AUD_PROVINCE, TICKET_C.AUD_CITY):
                    self.fields["aud_geo"].initial = "، ".join(str(v) for v in values)
                elif kind == TICKET_C.AUD_RADIUS:
                    km = float(leaf.get("km", 1))
                    if km >= 1:
                        self.fields["aud_radius"].initial = km
                        self.fields["aud_radius_unit"].initial = "km"
                    else:
                        self.fields["aud_radius"].initial = round(km * 1000, 2)
                        self.fields["aud_radius_unit"].initial = "m"
                    self.fields["aud_lat"].initial = leaf.get("lat")
                    self.fields["aud_lng"].initial = leaf.get("lng")
                elif kind in _JOB_LAYER_TO_KIND.values():
                    for code, aud_kind in _JOB_LAYER_TO_KIND.items():
                        if aud_kind == kind:
                            self.fields["aud_job_layer"].initial = code
                    self.fields["aud_job_names"].initial = "، ".join(str(v) for v in values)
                elif kind == TICKET_C.AUD_USERS:
                    self.fields["aud_nids"].initial = "\n".join(
                        str(v) for v in (leaf.get("nids") or values))
                elif kind == TICKET_C.AUD_MOBILE_PREFIX:
                    self.fields["aud_mobile_prefixes"].initial = ", ".join(
                        str(v) for v in values)
                elif kind == TICKET_C.AUD_AGE:
                    self.fields["aud_age_min"].initial = leaf.get("age_min")
                    self.fields["aud_age_max"].initial = leaf.get("age_max")

    def _first_leaf(self, rules):
        items = (rules or {}).get("items") or []
        for item in items:
            if isinstance(item, dict) and "kind" in item:
                return item
        return None

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")

        def split(v):
            return [x.strip() for x in (v or "").replace("،", ",").split(",") if x.strip()]

        def leaf(**kw):
            return {"logic": "and", "items": [kw]}

        rules = None
        if kind == TICKET_C.AUD_ALL:
            rules = leaf(kind=kind)
        elif kind in (TICKET_C.AUD_COUNTRY, TICKET_C.AUD_PROVINCE, TICKET_C.AUD_CITY):
            values = split(cleaned.get("aud_geo"))
            if not values:
                self.add_error("aud_geo", "نام کشور/استان/شهر را وارد کنید.")
            else:
                rules = leaf(kind=kind, values=values)
        elif kind == TICKET_C.AUD_RADIUS:
            lat, lng = cleaned.get("aud_lat"), cleaned.get("aud_lng")
            radius = cleaned.get("aud_radius")
            if lat is None or lng is None:
                self.add_error("aud_lat", "مختصات مرکز (lat/lng) لازم است.")
            elif radius is None:
                self.add_error("aud_radius", "شعاع را وارد کنید.")
            else:
                km = radius if cleaned.get("aud_radius_unit") == "km" else radius / 1000.0
                rules = leaf(kind=kind, lat=lat, lng=lng, km=round(km, 4))
        elif kind in _JOB_LAYER_TO_KIND.values():
            layer_code = cleaned.get("aud_job_layer")
            if layer_code not in _JOB_LAYER_TO_KIND:
                self.add_error("aud_job_layer", "لایهٔ شغلی را انتخاب کنید.")
            else:
                values = split(cleaned.get("aud_job_names"))
                if not values:
                    self.add_error("aud_job_names", "نام رده‌های شغلی را وارد کنید.")
                else:
                    rules = leaf(kind=_JOB_LAYER_TO_KIND[layer_code], values=values)
        elif kind == TICKET_C.AUD_USERS:
            nids = [ln.strip() for ln in (cleaned.get("aud_nids") or "").splitlines()
                    if ln.strip()]
            if not nids:
                self.add_error("aud_nids", "دست‌کم یک کد ملی وارد کنید.")
            else:
                from accounts.models import Profile

                found = list(Profile.objects.filter(national_id__in=nids)
                             .values_list("user_id", flat=True))
                if not found:
                    self.add_error("aud_nids", "هیچ کاربری با این کد ملی‌ها یافت نشد.")
                else:
                    rules = leaf(kind=kind, values=found, nids=nids)
        elif kind == TICKET_C.AUD_MOBILE_PREFIX:
            values = split(cleaned.get("aud_mobile_prefixes"))
            if not values:
                self.add_error("aud_mobile_prefixes", "شروع شماره موبایل را وارد کنید.")
            else:
                rules = leaf(kind=kind, values=values)
        elif kind == TICKET_C.AUD_AGE:
            age_min = cleaned.get("aud_age_min")
            age_max = cleaned.get("aud_age_max")
            if age_min is None and age_max is None:
                self.add_error("aud_age_min", "حداقل یا حداکثر سن را وارد کنید.")
            elif age_min is not None and age_max is not None and age_min > age_max:
                self.add_error("aud_age_max", "حداکثر سن باید بزرگ‌تر از حداقل سن باشد.")
            else:
                rules = leaf(kind=kind, age_min=age_min, age_max=age_max)
        else:
            self.add_error("kind", "نوع مخاطب انتخاب‌شده پشتیبانی نمی‌شود.")

        if rules is not None:
            self.cleaned_data["rules"] = rules
        return cleaned

    def save(self, *args, **kwargs):
        rules = self.cleaned_data.get("rules")
        if rules is not None:
            self.instance.rules = rules
        return super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# انواع تیکت (قابل تعریف توسط ادمین)
# ---------------------------------------------------------------------------


class TicketCategoryForm(forms.ModelForm):
    """افزودن/ویرایش نوع تیکت: کد یکتا + نام چندزبانه + آیکون + ترتیب + فعال بودن."""

    code = forms.CharField(
        label="کد", max_length=30,
        error_messages={"unique": "این کد قبلاً برای نوع تیکت دیگری ثبت شده است."},
        widget=forms.TextInput(attrs={
            "class": "hb-form-control", "dir": "ltr", "placeholder": "مثال: product",
        }),
    )

    class Meta:
        model = TicketCategory
        fields = ["code", "name_fa", "name_en", "name_zh", "icon", "order", "is_active"]
        widgets = {
            "name_fa": forms.TextInput(attrs={
                "class": "hb-form-control", "placeholder": "مثال: درخواست کالا/خدمات",
            }),
            "name_en": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "name_zh": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "icon": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "مثال: bi-box-seam (آیکون‌های Bootstrap Icons)",
            }),
            "order": forms.NumberInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }
        help_texts = {
            "code": "کد یکتا؛ هنگام ارسال تیکت به‌عنوان «نوع تیکت» نمایش داده می‌شود.",
            "icon": "نام آیکون از مجموعهٔ Bootstrap Icons (بدون پیشوند bi).",
            "order": "ترتیب نمایش در فهرست انتخاب نوع تیکت.",
        }


# ---------------------------------------------------------------------------
# سکه و کیف پول: تنظیمات سراسری + هزینهٔ سکهٔ ماژول‌ها
# ---------------------------------------------------------------------------


class WalletSettingsForm(forms.ModelForm):
    """تنظیمات سراسری سکه/کیف پول که فقط ادمین ویرایش می‌کند."""

    class Meta:
        model = WalletSetting
        fields = [
            "coin_value_rial", "coin_value_point", "buy_enabled", "sell_enabled",
            "transfer_enabled", "min_buy_coins", "max_buy_coins", "min_sell_coins",
            "max_sell_coins", "bank_name", "receiving_iban", "receiving_card_number",
            "coin_image",
        ]
        widgets = {
            "coin_value_rial": forms.NumberInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "step": "0.01",
            }),
            "coin_value_point": forms.NumberInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "min": "0", "step": "1",
            }),
            "buy_enabled": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
            "sell_enabled": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
            "transfer_enabled": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
            "min_buy_coins": forms.NumberInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "step": "1",
                "min": "1", "inputmode": "numeric", "placeholder": "مثال: 10",
            }),
            "max_buy_coins": forms.NumberInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "step": "1",
                "min": "1", "inputmode": "numeric", "placeholder": "مثال: 100000",
            }),
            "min_sell_coins": forms.NumberInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "step": "1",
                "min": "1", "inputmode": "numeric", "placeholder": "مثال: 10",
            }),
            "max_sell_coins": forms.NumberInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "step": "1",
                "min": "1", "inputmode": "numeric", "placeholder": "مثال: 100000",
            }),
            "bank_name": forms.TextInput(attrs={"class": "hb-form-control"}),
            "receiving_iban": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "IR123456789012345678901234",
            }),
            "receiving_card_number": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "6037997512345678",
                "inputmode": "numeric", "maxlength": "19",
            }),
            "coin_image": forms.ClearableFileInput(attrs={
                "accept": "image/jpeg,image/png,image/webp",
            }),
        }
        labels = {
            "coin_value_rial": "ارزش هر سکه (ریال)",
            "coin_value_point": "ارزش هر سکه (امتیاز)",
            "buy_enabled": "فعال بودن خرید سکه",
            "sell_enabled": "فعال بودن فروش سکه",
            "transfer_enabled": "فعال بودن انتقال سکه به دیگران",
            "min_buy_coins": "حداقل سکهٔ خرید",
            "max_buy_coins": "حداکثر سکهٔ خرید",
            "min_sell_coins": "حداقل سکهٔ فروش",
            "max_sell_coins": "حداکثر سکهٔ فروش",
            "bank_name": "نام بانک مبادلات",
            "receiving_iban": "شبأ دریافت وجه (خرید سکه)",
            "receiving_card_number": "شماره کارت دریافت وجه (خرید سکه)",
            "coin_image": "تصویر/لوگوی سکه",
        }
        help_texts = {
            "coin_value_rial": "نرخ هر سکه به ریال؛ با ذخیره، تاریخچهٔ تغییر نرخ ثبت می‌شود.",
            "coin_value_point": "هر یک سکه معادل چند امتیازِ کاربری است؛ امتیازهای کسب‌شدهٔ "
                                "کاربر (طبق تعرفه امتیازها) بر همین اساس به سکه تبدیل و با "
                                "موجودی کیف پول او تجمیع می‌شوند. مقدار صفر = تبدیل خودکار غیرفعال.",
            "receiving_iban": "شماره شبأ بانکی که خریداران مبلغ سکه را به آن واریز می‌کنند.",
            "receiving_card_number": "شماره کارت بانکی دریافت وجه خرید سکه؛ در کنار شبا به خریدار نمایش داده می‌شود.",
            "coin_image": "تصویر سکهٔ هاب که در صفحهٔ پرداخت خرید سکه (کارت به کارت) به خریدار نمایش داده می‌شود.",
        }


class RewardRuleForm(forms.ModelForm):
    """ثبت/ویرایش «سرفصل امتیاز» (فهرست امتیازها) — عنوان و میزان امتیاز هر فعالیت را ادمین تعیین می‌کند.

    طبق دستورالعمل، میزانِ هر سرفصل «به امتیاز» است (نه سکه)؛ فیلد coins همان
    میزان امتیاز را نگه می‌دارد و برچسب آن همین‌جا به «امتیاز» بازنویسی می‌شود.
    """

    class Meta:
        model = RewardRule
        fields = [
            "code", "title", "unit_label", "description", "coins",
            "max_per_user", "is_active",
        ]
        labels = {
            "coins": "میزان امتیاز",
        }
        widgets = {
            "code": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "مثال: referral / magazine_watch",
            }),
            "title": forms.TextInput(attrs={
                "class": "hb-form-control",
                "placeholder": "مثال: معرفی کاربر جدید / مطالعه در مجله دانستنی‌ها",
            }),
            "unit_label": forms.TextInput(attrs={
                "class": "hb-form-control",
                "placeholder": "مثال: هر نفر معرفی‌شده / هر ۳۰ دقیقه مطالعه",
            }),
            "description": forms.TextInput(attrs={
                "class": "hb-form-control",
                "placeholder": "اختیاری: توضیح کوتاه برای ادمین",
            }),
            "coins": forms.NumberInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "step": "0.01",
            }),
            "max_per_user": forms.NumberInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "min": "1",
                "placeholder": "خالی = بدون محدودیت",
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }
        help_texts = {
            "code": "کد یکتا؛ بخش مربوطه هنگام امتیازدهی از همین کد استفاده می‌کند "
                    "(referral = معرفی، magazine_watch = مطالعه در مجله، "
                    "profile_completion = تکمیل اطلاعات شخصی).",
            "unit_label": "واحد پاداش برای نمایش؛ مثل «هر نفر معرفی‌شده» یا «هر ۳۰ دقیقه مطالعه».",
            "coins": "میزان امتیازی که به‌ازای هر واحد به امتیاز کاربری افزوده می‌شود؛ "
                     "معادل سکهٔ این امتیازها نیز بر اساس «ارزش هر سکه (امتیاز)» به‌صورت "
                     "خودکار به کیف پول کاربر تجمیع می‌گردد.",
            "max_per_user": "سقف دریافت این امتیاز برای هر کاربر؛ مثلاً حداکثر چند بار. "
                            "خالی = نامحدود.",
            "is_active": "با غیرفعال‌کردن، امتیازدهی بدون حذف متوقف می‌شود.",
        }


class BackupSettingsForm(forms.ModelForm):
    """تنظیمات ماژول پشتیبان‌گیری: خودکار/دستی، بازهٔ زمانی، تعداد نگه‌داری و پوشه."""

    class Meta:
        model = BackupSetting
        fields = ["auto_enabled", "interval_minutes", "keep_count", "folder", "sync_folder", "stale_after_days"]
        widgets = {
            "auto_enabled": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
            "interval_minutes": forms.NumberInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "min": "1",
            }),
            "keep_count": forms.NumberInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "min": "1",
            }),
            "folder": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "خالی = پوشهٔ پیش‌فرض db_backups کنار پروژه",
            }),
            "sync_folder": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "مثلاً D:\\BackupDrive یا پوشهٔ همگام‌سازی‌شدهٔ Google Drive",
            }),
            "stale_after_days": forms.NumberInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "min": "1",
            }),
        }
        labels = {
            "auto_enabled": "فعال بودن پشتیبان‌گیری خودکار",
            "interval_minutes": "بازهٔ پشتیبان خودکار (دقیقه)",
            "keep_count": "تعداد نسخهٔ خودکارِ نگه‌داری‌شده",
            "folder": "پوشهٔ فایل‌های پشتیبان",
            "sync_folder": "کپی خودکار به پوشهٔ درایو/فضای ابری",
            "stale_after_days": "هشدار پس از چند روز بدون پشتیبان موفق",
        }
        help_texts = {
            "interval_minutes": "مثلاً 1440 = هر ۲۴ ساعت یک نسخهٔ خودکار.",
            "keep_count": "قدیمی‌ترین نسخه‌های خودکارِ بیشتر از این تعداد حذف می‌شوند؛ نسخهٔ دستی هرگز خودکار حذف نمی‌شود.",
            "folder": "مسیر کامل یک پوشهٔ دلخواه؛ خالی باشد یعنی پوشهٔ پیش‌فرض کنار پروژه (db_backups).",
            "sync_folder": "پس از هر پشتیبان موفق، یک کپی از فایل به این پوشه فرستاده می‌شود — مثلاً پوشهٔ همگام‌سازی‌شدهٔ Google Drive یا درایو شبکه. خالی = فقط پوشهٔ اصلی.",
            "stale_after_days": "اگر آخرین پشتیبان موفق بیشتر از این‌قدر روز پیش باشد، داشبورد مدیریت هشدار نشان می‌دهد.",
        }


class FeatureCostForm(forms.ModelForm):
    """ثبت/ویرایش هزینهٔ سکهٔ یک بخش از برنامه توسط ادمین."""

    class Meta:
        model = FeatureCost
        fields = ["code", "title", "description", "coins", "is_active"]
        widgets = {
            "code": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "مثال: bulk_ticket",
            }),
            "title": forms.TextInput(attrs={
                "class": "hb-form-control",
                "placeholder": "مثال: ارسال تیکت انبوه",
            }),
            "description": forms.TextInput(attrs={
                "class": "hb-form-control",
                "placeholder": "اختیاری: توضیح کوتاه برای کاربر",
            }),
            "coins": forms.NumberInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "step": "0.01",
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }
        help_texts = {
            "code": "کد یکتا؛ هر ماژول هنگام استفاده از این کد برای کسر سکه استفاده می‌کند.",
            "coins": "تعداد سکه‌ای که هنگام استفادهٔ کاربر از این بخش کسر می‌شود.",
            "is_active": "با غیرفعال‌کردن، هزینه بدون حذف از چرخه خارج می‌شود.",
        }


# ---------------------------------------------------------------------------
# اسامی مرجع (نام‌ها و نام خانوادگی) — جدول‌هایی که فیلدهای نام پروفایل از آن‌ها
# خوانده می‌شود (نام/نام پدر/نام مادر از FirstnameTbl و نام خانوادگی از
# FamilynameTbl). ادمین از این ماژول دیتابیسِ نام‌ها را تکمیل می‌کند.
# ---------------------------------------------------------------------------


class FirstNameForm(forms.ModelForm):
    """افزودن/ویرایش یک «نام» در جدول نام‌ها (برای نام، نام پدر و نام مادر)."""

    def clean_first_name_fa(self):
        value = (self.cleaned_data.get("first_name_fa") or "").strip()
        if not value:
            raise forms.ValidationError("نام را وارد کنید.")
        return value

    def clean_first_name_en(self):
        return (self.cleaned_data.get("first_name_en") or "").strip()

    class Meta:
        model = FirstnameTbl
        fields = ["first_name_fa", "first_name_en", "gender"]
        labels = {
            "first_name_fa": "نام (فارسی)",
            "first_name_en": "نام (انگلیسی)",
            "gender": "جنسیت نام",
        }
        widgets = {
            "first_name_fa": forms.TextInput(attrs={
                "class": "hb-form-control", "placeholder": "مثال: علی",
            }),
            "first_name_en": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "مثال: Ali (اختیاری)",
            }),
            "gender": forms.Select(attrs={
                "class": "hb-form-control hb-form-select",
            }),
        }
        help_texts = {
            "first_name_fa": "این نام در پروفایل کاربر برای «نام»، «نام پدر» و «نام مادر» قابل انتخاب می‌شود.",
            "first_name_en": "اختیاری؛ معادل انگلیسی برای نمایش چندزبانه.",
            "gender": "«مردانه» نام را در فهرستِ «نام پدر» و «زنانه» در فهرستِ «نام مادر» نشان می‌دهد؛ «نامشخص» در هر دو فهرست می‌آید.",
        }


class FamilyNameForm(forms.ModelForm):
    """افزودن/ویرایش یک «نام خانوادگی» در جدول نام‌های خانوادگی."""

    def clean_familyname_fa(self):
        value = (self.cleaned_data.get("familyname_fa") or "").strip()
        if not value:
            raise forms.ValidationError("نام خانوادگی را وارد کنید.")
        return value

    def clean_familyname_en(self):
        return (self.cleaned_data.get("familyname_en") or "").strip()

    class Meta:
        model = FamilynameTbl
        fields = ["familyname_fa", "familyname_en"]
        labels = {
            "familyname_fa": "نام خانوادگی (فارسی)",
            "familyname_en": "نام خانوادگی (انگلیسی)",
        }
        widgets = {
            "familyname_fa": forms.TextInput(attrs={
                "class": "hb-form-control", "placeholder": "مثال: رضایی",
            }),
            "familyname_en": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "مثال: Rezaei (اختیاری)",
            }),
        }
        help_texts = {
            "familyname_fa": "این نام خانوادگی در پروفایل کاربر برای فیلد «نام خانوادگی» قابل انتخاب می‌شود.",
            "familyname_en": "اختیاری؛ معادل انگلیسی برای نمایش چندزبانه.",
        }


class FameNameForm(forms.ModelForm):
    """افزودن/ویرایش یک «شهرت» در جدول مرجع شهرت‌ها.

    شهرت: نام و عنوانی که نام‌برده در جامعه با آن شناخته می‌شود (مانند
    لقب‌های فرهنگی، ورزشی، علمی و ...). فهرست انتخابیِ فیلد اختیاریِ «شهرت»
    بخش اطلاعات شخصی پروفایل از همین جدول خوانده می‌شود.
    """

    def clean_fame_name_fa(self):
        value = (self.cleaned_data.get("fame_name_fa") or "").strip()
        if not value:
            raise forms.ValidationError("شهرت را وارد کنید.")
        return value

    def clean_fame_name_en(self):
        return (self.cleaned_data.get("fame_name_en") or "").strip()

    def clean_description(self):
        return (self.cleaned_data.get("description") or "").strip()

    class Meta:
        model = FameNameTbl
        fields = ["fame_name_fa", "fame_name_en", "description"]
        labels = {
            "fame_name_fa": "شهرت (فارسی)",
            "fame_name_en": "شهرت (انگلیسی)",
        }
        widgets = {
            "fame_name_fa": forms.TextInput(attrs={
                "class": "hb-form-control", "placeholder": "مثال: پدر فلسفه",
            }),
            "fame_name_en": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "مثال: Father of Philosophy (اختیاری)",
            }),
            "description": forms.Textarea(attrs={
                "class": "hb-form-control", "rows": 3,
                "placeholder": "مثال: لقبی که در محافل فرهنگی به حکیمان بزرگ داده می‌شود…",
            }),
        }
        help_texts = {
            "fame_name_fa": "این شهرت در پروفایل کاربر برای فیلد اختیاریِ «شهرت» قابل انتخاب می‌شود.",
            "fame_name_en": "اختیاری؛ معادل انگلیسی برای نمایش چندزبانه.",
            "description": "اختیاری؛ توضیح دربارهٔ منشأ یا کاربرد این شهرت.",
        }


# ---------------------------------------------------------------------------
# اطلاعات مکانی مرجع (کشور/استان/شهرستان) — جدول‌هایی که فیلدهای «اطلاعات
# مکانی» پروفایل (محل سکونت) از آن‌ها خوانده می‌شود. هم‌اکنون دیتابیس مربوط به
# کشور ایران است و ادمین از این ماژول آن را تکمیل/اصلاح می‌کند.
# ---------------------------------------------------------------------------


class CountryForm(forms.ModelForm):
    """افزودن/ویرایش یک «کشور» در جدول کشورها."""

    def clean_country_fa(self):
        value = (self.cleaned_data.get("country_fa") or "").strip()
        if not value:
            raise forms.ValidationError("نام کشور را وارد کنید.")
        return value

    def clean_country_en(self):
        return (self.cleaned_data.get("country_en") or "").strip()

    class Meta:
        model = CountryTbl
        fields = ["country_fa", "country_en"]
        labels = {
            "country_fa": "نام کشور (فارسی)",
            "country_en": "نام کشور (انگلیسی)",
        }
        widgets = {
            "country_fa": forms.TextInput(attrs={
                "class": "hb-form-control", "placeholder": "مثال: ایران",
            }),
            "country_en": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "مثال: Iran (اختیاری)",
            }),
        }
        help_texts = {
            "country_fa": "این کشور در فهرستِ «کشور» بخش اطلاعات مکانی پروفایل قابل انتخاب می‌شود (فعلاً: ایران).",
            "country_en": "اختیاری؛ معادل انگلیسی برای نمایش چندزبانه.",
        }


class ProvinceForm(forms.ModelForm):
    """افزودن/ویرایش یک «استان» (متعلق به یک کشور)."""

    def clean_province_fa(self):
        value = (self.cleaned_data.get("province_fa") or "").strip()
        if not value:
            raise forms.ValidationError("نام استان را وارد کنید.")
        return value

    def clean_province_en(self):
        return (self.cleaned_data.get("province_en") or "").strip()

    class Meta:
        model = ProvinceTbl
        fields = ["country", "province_fa", "province_en"]
        labels = {
            "country": "کشور",
            "province_fa": "نام استان (فارسی)",
            "province_en": "نام استان (انگلیسی)",
        }
        widgets = {
            "country": forms.Select(attrs={
                "class": "hb-form-control hb-form-select",
            }),
            "province_fa": forms.TextInput(attrs={
                "class": "hb-form-control", "placeholder": "مثال: تهران",
            }),
            "province_en": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "مثال: Tehran (اختیاری)",
            }),
        }
        help_texts = {
            "country": "استان به همین کشور پیوند داده می‌شود.",
            "province_fa": "این استان در فهرستِ «استان» بخش اطلاعات مکانی پروفایل قابل انتخاب می‌شود.",
        }


class CityForm(forms.ModelForm):
    """افزودن/ویرایش یک «شهرستان» (متعلق به یک استان)."""

    def clean_city_fa(self):
        value = (self.cleaned_data.get("city_fa") or "").strip()
        if not value:
            raise forms.ValidationError("نام شهرستان را وارد کنید.")
        return value

    def clean_city_en(self):
        return (self.cleaned_data.get("city_en") or "").strip()

    class Meta:
        model = CityTbl
        fields = ["province", "city_fa", "city_en"]
        labels = {
            "province": "استان",
            "city_fa": "نام شهرستان (فارسی)",
            "city_en": "نام شهرستان (انگلیسی)",
        }
        widgets = {
            "province": forms.Select(attrs={
                "class": "hb-form-control hb-form-select",
            }),
            "city_fa": forms.TextInput(attrs={
                "class": "hb-form-control", "placeholder": "مثال: تهران",
            }),
            "city_en": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "مثال: Tehran (اختیاری)",
            }),
        }
        help_texts = {
            "province": "شهرستان به همین استان پیوند داده می‌شود.",
            "city_fa": "این شهرستان در فهرستِ «شهر» بخش اطلاعات مکانی پروفایل (محل سکونت) قابل انتخاب می‌شود.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # برچسب استان‌ها «استان (کشور)» باشد تا هنگام افزودن، جایگاه درست مشخص باشد
        self.fields["province"].label_from_instance = (
            lambda obj: f"{obj.province_fa} ({obj.country.country_fa})"
            if obj.country_id else obj.province_fa
        )
        self.fields["province"].queryset = (
            ProvinceTbl.objects.select_related("country").all()
        )


# ---------------------------------------------------------------------------
# تنظیمات «سرویس موقعیت» (نقشه و GPS)
# ---------------------------------------------------------------------------


class LocationSettingsForm(forms.ModelForm):
    """انتخاب «ارائه‌دهندهٔ نقشه» و «منبع موقعیت (GPS)» توسط ادمین.

    دو رادیوگروه مستقل که در صفحهٔ «سرویس موقعیت مکانی» پنل مدیریت به‌صورت
    کارت‌های انتخابی نمایش داده می‌شوند و روی همهٔ صفحاتِ دارای نقشه/GPS اثر
    می‌گذارند.
    """

    class Meta:
        model = LocationSetting
        fields = ["map_provider", "location_provider"]
        widgets = {
            "map_provider": forms.RadioSelect,
            "location_provider": forms.RadioSelect,
        }
        labels = {
            "map_provider": "ارائه‌دهندهٔ نقشه (Map Provider)",
            "location_provider": "منبع موقعیت (Location Provider)",
        }
        help_texts = {
            "map_provider": (
                "فقط تعیین می‌کند کدام نقشهٔ تعاملی به کاربران نمایش داده شود؛ "
                "جستجوی آدرس و تبدیل مختصات به آدرس از زنجیرهٔ سرور پیروی می‌کند."
            ),
            "location_provider": (
                "از کدام منبع، مختصاتِ «دریافت خودکار موقعیت» استخراج شود."
            ),
        }


# ---------------------------------------------------------------------------
# ماژول «کنترل کد ملی» — کدهای ملیِ رزروشده که کاربران عادی نمی‌توانند ثبت کنند
# ---------------------------------------------------------------------------


class ReservedNationalCodeForm(forms.ModelForm):
    """ثبت/ویرایش یک «کد ملی رزروشده» توسط ادمین.

    فقط کد ۱۰ رقمی پذیرفته می‌شود و در صورت ثبتِ مجدد، پیام یکتایی نمایش داده
    می‌شود. با «فعال/غیرفعال» می‌توان محدودیت را بدون حذف رکورد برداشت.
    """

    def clean_national_id(self):
        nid = (self.cleaned_data.get("national_id") or "").strip()
        if not nid:
            raise forms.ValidationError("کد ملی را وارد کنید.")
        if not re.fullmatch(r"\d{10}", nid):
            raise forms.ValidationError(
                "کد ملی باید دقیقاً ۱۰ رقم (۰-۹) باشد."
            )
        exists = (
            ReservedNationalCode.objects.filter(national_id=nid)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise forms.ValidationError(
                "این کد ملی قبلاً در فهرست کدهای رزروشده ثبت شده است."
            )
        return nid

    def clean_title(self):
        return (self.cleaned_data.get("title") or "").strip()

    class Meta:
        model = ReservedNationalCode
        fields = ["national_id", "access_level", "title", "is_active"]
        labels = {
            "national_id": "کد ملی رزروشده",
            "access_level": "سطح دسترسی",
            "title": "عنوان / توضیح",
            "is_active": "فعال",
        }
        widgets = {
            "national_id": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "maxlength": "10",
                "inputmode": "numeric", "placeholder": "مثال: 9999999999",
            }),
            "access_level": forms.Select(attrs={
                "class": "hb-form-control hb-form-select",
            }),
            "title": forms.TextInput(attrs={
                "class": "hb-form-control",
                "placeholder": "اختیاری؛ مثلاً «کد اختصاصی مدیر ارشد»",
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }
        help_texts = {
            "national_id": "کد ملی ۱۰ رقمی که می‌خواهید از دسترس کاربران عادی خارج شود.",
            "access_level": "«فقط ادمین»: فقط کاربران با دسترسی ادمین می‌توانند ثبت کنند؛ «ممنوع برای همه»: هیچ‌کس نمی‌تواند.",
            "title": "اختیاری؛ برای شناسایی راحت‌تر در فهرست.",
            "is_active": "با برداشتن تیک، محدودیت بدون حذف رکورد برداشته می‌شود.",
        }

class AdHeaderPlacementForm(forms.ModelForm):
    """فرم مدیریت «محل تبلیغ هدر»: کد یکتا + عنوان + توضیح + فعال/غیرفعال + ترتیب.

    کد فارسی/مرکبی؛ باید در کل جدول یکتا باشد (پیام خطای منحصر‌به‌فرد).
    """

    code = _code_field("مثال: dashboard")

    class Meta:
        model = AdHeaderPlacement
        fields = ["code", "title", "description", "is_active", "sort_order"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "hb-form-control"}),
            "description": forms.TextInput(attrs={
                "class": "hb-form-control",
                "placeholder": "مثال: نوار پایین داشبورد — فقط وقتی تبلیغ برای این هدر پذیرفته شود، در آن پخش می‌شود",
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
            "sort_order": forms.NumberInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "min": 0,
            }),
        }
        help_texts = {
            "code": "کد یکتا؛ کدهای آماده: dashboard (داشبورد)، wallet (کیف پول)، accounting (حسابداری)، tickets (تیکت).",
            "title": "عنوان محل برای نمایش در چک‌باکس‌های ثبت تبلیغ و پنل مدیریت.",
            "description": "توضیح کوتاه برای ادمین و کاربر.",
            "sort_order": "ترتیب نمایش چک‌باکس‌ها در فرم کاربر (کوچک‌تر = بالاتر).",
        }

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip()
        if not code:
            raise forms.ValidationError("کد را وارد کنید.")
        if self.instance and self.instance.code and self.instance.code != code:
            self.add_error("code", "کد یکتایی که تغییر دادید قبلاً ثبت شده است.")
            return code
        exists = (
            AdHeaderPlacement.objects.filter(code__iexact=code)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise forms.ValidationError("این کد قبلاً ثبت شده است.")
        return code


class BreakingNewsForm(forms.ModelForm):
    """ثبت/ویرایش «خبر فوری» هدر توسط ادمین.

    متن حداکثر ۵۰۰ کاراکتر + بازهٔ زمانی نمایش (از تاریخ/ساعت تا تاریخ/ساعت)
    + سرعت حرکت متن. تاریخ‌ها با «تقویم شمسی» (همان انتخابگرِ «تاریخ تولد»
    پروفایل) انتخاب می‌شوند: اسکریپتِ تقویم، روزِ میلادی را در فیلدهای پنهانِ
    show_from_date/show_until_date می‌نویسد و clean() آن‌ها را با «ساعت»
    ترکیب و در show_from/show_until ذخیره می‌کند. اعتبارسنجی: پایانِ بازه باید
    بعد از شروع باشد و سرعت در بازهٔ منطقی (۵ تا ۱۲۰ ثانیه برای هر دور) بماند.
    """

    # فیلدهای کمکیِ تقویم شمسی: تاریخِ میلادی (توسط JS تقویم پر می‌شود) + ساعت؛
    # در clean() به show_from/show_until تبدیل می‌شوند. قالبِ breaking_news_form.html
    # بلوک سفارشیِ تقویم را برایشان رندر می‌کند.
    show_from_date = forms.CharField(required=False, widget=forms.HiddenInput)
    show_until_date = forms.CharField(required=False, widget=forms.HiddenInput)
    show_from_time = forms.TimeField(
        label="ساعت شروع نمایش",
        required=False,
        widget=forms.TimeInput(
            attrs={"type": "time", "class": "hb-form-control", "dir": "ltr"},
            format="%H:%M",
        ),
    )
    show_until_time = forms.TimeField(
        label="ساعت پایان نمایش",
        required=False,
        widget=forms.TimeInput(
            attrs={"type": "time", "class": "hb-form-control", "dir": "ltr"},
            format="%H:%M",
        ),
    )

    class Meta:
        model = BreakingNews
        fields = ["text", "show_from", "show_until", "speed", "is_active", "sort_order"]
        widgets = {
            # در قالب سفارشی، show_from/show_until با تقویم شمسی رندر می‌شوند؛
            # این widget فقط برای رندر پیش‌فرض (بدون قالب سفارشی) است.
            "show_from": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "hb-form-control", "dir": "ltr"},
                format="%Y-%m-%dT%H:%M",
            ),
            "show_until": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "hb-form-control", "dir": "ltr"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["text"].widget.attrs.update({
            "class": "hb-form-control", "rows": 2, "maxlength": "500",
        })
        for name in ("speed", "sort_order"):
            self.fields[name].widget.attrs.update({"class": "hb-form-control", "min": 0})
        # show_from/show_until از تقویم شمسی + ساعت پر می‌شوند؛ الزامشان را در
        # clean() با پیام فارسی بررسی می‌کنیم (کلیدهایشان در POST وجود ندارد).
        for name in ("show_from", "show_until"):
            self.fields[name].required = False
        # مقدار اولیهٔ تاریخ/ساعت هنگام ویرایش (به وقت محلی تهران)
        if self.instance and self.instance.pk:
            for field_name, moment in (
                ("show_from", self.instance.show_from),
                ("show_until", self.instance.show_until),
            ):
                if not moment:
                    continue
                local = timezone.localtime(moment) if timezone.is_aware(moment) else moment
                self.fields[f"{field_name}_date"].initial = local.strftime("%Y-%m-%d")
                self.fields[f"{field_name}_time"].initial = local.strftime("%H:%M")

    def clean_text(self):
        text = (self.cleaned_data.get("text") or "").strip()
        if not text:
            raise forms.ValidationError("متن خبر را وارد کنید.")
        if len(text) > 500:
            raise forms.ValidationError("متن خبر حداکثر ۵۰۰ کاراکتر است.")
        return text

    def clean(self):
        cleaned = super().clean()

        def combine(date_name, time_name, label):
            """تاریخِ میلادیِ تقویم شمسی + ساعت ← datetime آگاه."""
            date_raw = (cleaned.get(date_name) or "").strip()
            time_val = cleaned.get(time_name)
            if not date_raw and not time_val:
                return None
            if not date_raw:
                self.add_error(date_name, f"تاریخ «{label}» را از تقویم شمسی انتخاب کنید.")
                return None
            if not time_val:
                self.add_error(time_name, f"ساعت «{label}» را انتخاب کنید.")
                return None
            try:
                day = datetime.strptime(date_raw, "%Y-%m-%d").date()
            except ValueError:
                self.add_error(date_name, f"تاریخ «{label}» معتبر نیست.")
                return None
            naive = datetime.combine(day, time_val)
            return timezone.make_aware(naive) if settings.USE_TZ else naive

        start = combine("show_from_date", "show_from_time", "شروع نمایش")
        end = combine("show_until_date", "show_until_time", "پایان نمایش")
        if start is not None:
            cleaned["show_from"] = start
        if end is not None:
            cleaned["show_until"] = end
        # الزام بازهٔ نمایش (اگر برای همان فیلد خطای بالاتری اضافه نشده باشد)
        if start is None and not (self.errors.get("show_from_date") or self.errors.get("show_from_time")):
            self.add_error("show_from_date", "تاریخ و ساعت «شروع نمایش» را انتخاب کنید.")
        if end is None and not (self.errors.get("show_until_date") or self.errors.get("show_until_time")):
            self.add_error("show_until_date", "تاریخ و ساعت «پایان نمایش» را انتخاب کنید.")
        if start and end and end <= start:
            self.add_error("show_until_date", "«پایان نمایش» باید بعد از «شروع نمایش» باشد.")
        speed = cleaned.get("speed")
        if speed is not None and not (5 <= speed <= 120):
            self.add_error("speed", "سرعت باید بین ۵ تا ۱۲۰ ثانیه برای هر دور باشد.")
        return cleaned


class AdvertisementForm(forms.ModelForm):
    """ثبت «تبلیغ» توسط کاربر در ماژول «تبلیغات» داشبورد.

    کاربر لوگو + عنوان/توضیح/لینک را وارد می‌کند؛ هزینهٔ طبق تعرفهٔ «هزینه‌های
    سکهٔ ماژول‌ها» (کد ``ad_submission``) در ویو (نه فرم) از کیف پول کسر می‌شود.
    بازهٔ نمایش و سرعت توسط ادمین (مشابه اخبار فوری) در پنل مدیریت تنظیم می‌شود؛
    این فیلدها فقط برای پیش‌نمایش/ویرایش ادمین در این فرم اختیاری‌اند.
    تاریخ‌ها با «تقویم شمسی» (همان انتخابگر پروفایل/اخبار فوری) انتخاب می‌شوند.
    """

    # فیلدهای تاریخ/ساعتِ کاربر (تقویم شمسی، مشابه اخبار فوری):
    # تاریخ شروع + تاریخ پایان + «یک ساعت واحد» که هم شروع و هم پایان هر روز
    # است (ساعت شروع = ساعت پایان). تعداد روزها = پایان − شروع و
    # هزینه = روزها × تعرفهٔ ۲۴ ساعتهٔ «هزینه‌های سکهٔ ماژول‌ها».
    start_date = forms.CharField(
        required=True, widget=forms.HiddenInput,
        help_text="تاریخ شروع نمایش (تقویم شمسی).",
    )
    end_date = forms.CharField(
        required=True, widget=forms.HiddenInput,
        help_text="تاریخ پایان نمایش (تقویم شمسی).",
    )
    ad_time = forms.TimeField(
        required=True,
        label="ساعت شروع و پایان (یکسان)",
        help_text="یک ساعت واحد که هم شروع و هم پایان تبلیغ است (مثلاً ۰۸:۰۰).",
        widget=forms.TimeInput(
            attrs={"type": "time", "class": "hb-form-control", "dir": "ltr"},
            format="%H:%M",
        ),
    )
    # چک‌باکس‌های «هدرهای انتخابی» — کاربر محل(های) پخش تبلیغ را انتخاب می‌کند؛
    # هزینه = روزها × تعداد هدرهای انتخاب‌شده (در ویو با تعرفه از کیف پول کسر می‌شود).
    header_modules = forms.ModelMultipleChoiceField(
        required=True,
        queryset=AdHeaderPlacement.active_placements(),
        widget=forms.CheckboxSelectMultiple(attrs={'dir': 'rtl'}),
        label="هدر(های) نوار تبلیغ — محل(های) پخش",
        help_text="تبلیغ در نوار متحرک هدر(های) انتخاب‌شده پخش می‌شود؛ "
        "برای هر هدر، هزینهٔ روزانه به‌صورت مجزا محاسبه می‌شود.",
    )

    class Meta:
        model = Advertisement
        fields = [
            "logo", "title", "description", "link_url",
            "show_from", "show_until", "speed", "sort_order", "header_modules",
        ]
        widgets = {
            "logo": forms.ClearableFileInput(attrs={"class": "hb-form-control", "accept": "image/*"}),
            "title": forms.TextInput(attrs={"class": "hb-form-control", "maxlength": "120"}),
            "description": forms.TextInput(attrs={"class": "hb-form-control", "maxlength": "300"}),
            "link_url": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr", "placeholder": "https://example.com"}),
            "show_from": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "hb-form-control", "dir": "ltr"},
                format="%Y-%m-%dT%H:%M",
            ),
            "show_until": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "hb-form-control", "dir": "ltr"},
                format="%Y-%m-%dT%H:%M",
            ),
        }
        labels = {
            "logo": "لوگوی تبلیغاتی",
            "title": "عنوان تبلیغ",
            "description": "توضیح تبلیغ",
            "link_url": "لینک (اختیاری)",
            "speed": "سرعت نمایش (ثانیه برای هر دور)",
            "sort_order": "ترتیب پخش",
        }
        help_texts = {
            "logo": "تصویر لوگو (PNG/JPG) — پس از پرداخت هزینه در نوار متحرک پایین داشبورد پخش می‌شود.",
            "title": "عنوان کوتاه کنار لوگو؛ حداکثر ۱۲۰ کاراکتر.",
            "description": "توضیح کوتاه زیر عنوان (اختیاری)؛ حداکثر ۳۰۰ کاراکتر.",
            "link_url": "با کلیک روی تبلیغ باز می‌شود؛ خالی = بدون لینک.",
            "speed": "۵ تا ۱۲۰ ثانیه — عدد کمتر = سریع‌تر.",
        }

    def __init__(self, *args, renew_ad=None, **kwargs):
        super().__init__(*args, **kwargs)
        # حالت «تمدید» (Advertisement.is_expired): ثبت رکوردِ جدید از
        # روی تبلیغ منقضی‌شده. لوگو پیش‌فرض از تبلیغ قبلی برگردانده می‌شود
        # (آپلود مجدد اختیاری است) و متن/لینک/هدرها در ویو با initial
        # پیش‌پُر می‌شوند؛ تاریخ جدید باید به‌طور کامل انتخاب شود.
        self.renew_ad = renew_ad
        if renew_ad is not None and renew_ad.logo:
            self.fields["logo"].required = False
        # بازهٔ نمایش توسط ادمین تعیین می‌شود؛ برای کاربر عادی لازم نیست،
        # اما مقدار پیش‌فرض منطقی پیشنهاد می‌شود (در clean بررسی می‌شود).
        self.fields["show_from"].required = False
        self.fields["show_until"].required = False
        self.fields["speed"].required = False
        self.fields["sort_order"].required = False
        self.fields["sort_order"].widget.attrs.update({"class": "hb-form-control", "min": 0})
        self.fields["title"].widget.attrs.update({"class": "hb-form-control"})
        self.fields["description"].widget.attrs.update({"class": "hb-form-control"})
        self.fields["link_url"].widget.attrs.update({"class": "hb-form-control"})
        # مقدار اولیهٔ تاریخ/ساعت هنگام ویرایش (به وقت محلی تهران)؛
        # تاریخ‌ها و ساعتِ واحدِ انتخاب‌شدهٔ کاربر برای ویرایش پر می‌شود.
        if self.instance and self.instance.pk:
            start = self.instance.show_from
            end = self.instance.show_until
            if start:
                local = timezone.localtime(start) if timezone.is_aware(start) else start
                self.fields["start_date"].initial = local.strftime("%Y-%m-%d")
                self.fields["ad_time"].initial = local.strftime("%H:%M")
            if end:
                local_end = timezone.localtime(end) if timezone.is_aware(end) else end
                self.fields["end_date"].initial = local_end.strftime("%Y-%m-%d")

    def clean(self):
        cleaned = super().clean()

        # تاریخ شروع + تاریخ پایان + یک ساعتِ واحد (ساعت شروع = ساعت پایان)
        # از کاربر گرفته می‌شود؛ بازهٔ نمایش و تعداد روزها از همین‌ها ساخته می‌شود.
        start_raw = (cleaned.get("start_date") or "").strip()
        end_raw = (cleaned.get("end_date") or "").strip()
        ad_time = cleaned.get("ad_time")
        if not start_raw and "start_date" not in self.errors:
            self.add_error("start_date", "تاریخ شروع نمایش را از تقویم شمسی انتخاب کنید.")
        if not end_raw and "end_date" not in self.errors:
            self.add_error("end_date", "تاریخ پایان نمایش را از تقویم شمسی انتخاب کنید.")
        if not ad_time and "ad_time" not in self.errors:
            self.add_error("ad_time", "ساعت شروع/پایان (یکسان) را انتخاب کنید.")
        if not (start_raw and end_raw and ad_time):
            return cleaned
        try:
            start_day = datetime.strptime(start_raw, "%Y-%m-%d").date()
        except ValueError:
            self.add_error("start_date", "تاریخ شروع نمایش نامعتبر است.")
            return cleaned
        try:
            end_day = datetime.strptime(end_raw, "%Y-%m-%d").date()
        except ValueError:
            self.add_error("end_date", "تاریخ پایان نمایش نامعتبر است.")
            return cleaned
        if end_day <= start_day:
            self.add_error("end_date", "تاریخ پایان باید بعد از تاریخ شروع باشد.")
            return cleaned
        start_dt = datetime.combine(start_day, ad_time)
        end_dt = datetime.combine(end_day, ad_time)
        if settings.USE_TZ:
            start_dt = timezone.make_aware(start_dt)
            end_dt = timezone.make_aware(end_dt)
        cleaned["show_from"] = start_dt
        cleaned["show_until"] = end_dt
        # تعداد روزها = اختلاف تاریخ‌ها؛ هزینه = روزها × تعرفهٔ ۲۴ ساعته
        cleaned["days"] = (end_day - start_day).days

        # «سرعت نمایش» اختیاری است: با فرمِ خالی، مقدار فعلی (یا پیش‌فرض ۳۰)
        # حفظ شود — اگر None در cleaned بماند، construct_instance آن را روی
        # اینستا می‌نویسد و save با NOT NULL خطا می‌دهد؛ بازهٔ مجاز ۵ تا ۱۲۰
        # ثانیه برای هر دور (مطابق «اخبار فوری» و محدودهٔ نوار متحرک).
        speed = cleaned.get("speed")
        if speed in (None, ""):
            cleaned["speed"] = int(getattr(self.instance, "speed", 0) or 0) or 30
        elif not (5 <= speed <= 120):
            self.add_error("speed", "سرعت باید بین ۵ تا ۱۲۰ ثانیه برای هر دور باشد.")
        return cleaned

    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()
        if not title:
            raise forms.ValidationError("عنوان تبلیغ را وارد کنید.")
        return title

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if logo in (None, ""):
            renew_ad = getattr(self, "renew_ad", None)
            if renew_ad is not None and renew_ad.logo:
                # حالت «تمدید»: بدون آپلود جدید، همان لوگوی تبلیغ قبلی استفاده می‌شود.
                return renew_ad.logo
            raise forms.ValidationError("لوگوی تبلیغاتی را بارگذاری کنید.")
        # بررسی سادهٔ نوع فایل تصویری
        content_type = getattr(logo, "content_type", "") or ""
        if content_type and not content_type.startswith("image/"):
            raise forms.ValidationError("فایل بارگذاری‌شده باید تصویر (PNG/JPG/SVG) باشد.")
        return logo

    def clean_link_url(self):
        link = (self.cleaned_data.get("link_url") or "").strip()
        if link and not link.lower().startswith(("http://", "https://")):
            raise forms.ValidationError("لینک باید با http:// یا https:// شروع شود.")
        return link


# ---------------------------------------------------------------------
# مشخصات مجاز تصویر «اسلاید آمار داشبورد» — اعمال در ثبت/ویرایش (ادمین و کاربر).
# باکس‌های آمار با «عرض واکنشگرا (حداقل ۲۲۰px)» و ارتفاع ۱۷۰px رندر می‌شوند؛
# پس نسبت ابعاد (عرض/ارتفاع) بین ۳٫۵ تا ۴٫۵ پذیرفته می‌شود و حالت توصیه‌شده
# ۲۴۰۰×۶۰۰ (نسبت ۴:۱ — بنر) است. اعتبارسنجی با Pillow انجام می‌شود تا فایلِ فریب‌دهنده
# (پسوند قلابی یا زبان‌آلود) بلاک شود.
# ---------------------------------------------------------------------
STAT_SLIDE_ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}
STAT_SLIDE_ALLOWED_EXT = (".png", ".jpg", ".jpeg", ".webp")
STAT_SLIDE_ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}
STAT_SLIDE_IMAGE_MAX_MB = 2
STAT_SLIDE_IMAGE_MAX_BYTES = STAT_SLIDE_IMAGE_MAX_MB * 1024 * 1024
STAT_SLIDE_MIN_W, STAT_SLIDE_MIN_H = 1200, 300
STAT_SLIDE_MAX_W, STAT_SLIDE_MAX_H = 4800, 1200
STAT_SLIDE_RATIO_MIN, STAT_SLIDE_RATIO_MAX = 3.5, 4.5
STAT_SLIDE_IMAGE_SPEC_TEXT = (
    "مشخصات مجاز: PNG/JPG/WEBP • حداکثر ۲ مگابایت • ابعاد ۱۲۰۰×۳۰۰ تا ۴۸۰۰×۱۲۰۰ پیکسل • "
    "نسبت ابعاد ۳٫۵ تا ۴٫۵ (توصیه‌شده ۲۴۰۰×۶۰۰، یعنی ۴:۱). مهم‌ترین بخش تصویر را در "
    "«ناحیهٔ امن» مرکزی (۱۲۰۰×۶۰۰) بگذارید؛ در موبایل فقط همین بخش دیده می‌شود."
)


def validate_stat_slide_image(image):
    """اعتبارسنجی کامل تصویر اسلاید — در صورت ناسازگار بودن، آپلود بلاک می‌شود.

    کنترل‌ها: پسوند، MIME، حجم فایل، فرم واقعی با Pillow، ابعاد و نسبت ابعاد.
    فراخوانی با «None» فقط در ویرایش (حفظ تصویر قبلی) رخ می‌دهد؛ اینجا None
    یعنی تصویری انتخاب نشده و خطا ثبت می‌شود.
    """
    if image in (None, ""):
        raise forms.ValidationError("تصویر اسلاید را بارگذاری کنید.")
    name = (getattr(image, "name", "") or "").lower()
    if name and not name.endswith(STAT_SLIDE_ALLOWED_EXT):
        raise forms.ValidationError(
            "فرمت فایل مجاز نیست؛ فقط PNG/JPG/WEBP پذیرفته می‌شود."
        )
    mime = (getattr(image, "content_type", "") or "").lower()
    if mime and mime not in STAT_SLIDE_ALLOWED_MIME:
        raise forms.ValidationError(
            "فرمت فایل مجاز نیست؛ فقط تصاویر PNG/JPG/WEBP پذیرفته می‌شود."
        )
    if image.size > STAT_SLIDE_IMAGE_MAX_BYTES:
        raise forms.ValidationError(
            f"حجم تصویر {image.size / 1048576:.2f} مگابایت است؛ حداکثر مجاز "
            f"{STAT_SLIDE_IMAGE_MAX_MB} مگابایت."
        )
    try:
        probe_ctx = PILImage.open(image)  # تصویر خراب/فریب‌دهنده اینجا خطا می‌دهد
    except forms.ValidationError:
        raise
    except Exception:
        raise forms.ValidationError(
            "فایل بارگذاری‌شده یک تصویر معتبر PNG/JPG/WEBP نیست (فایل خراب یا فریب‌دهنده)."
        )
    with probe_ctx as probe:
        loaded_format = (probe.format or "").upper()
        loaded_w, loaded_h = probe.size
        if loaded_format not in STAT_SLIDE_ALLOWED_FORMATS:
            raise forms.ValidationError(
                "فرمت واقعی فایل مجاز نیست؛ فقط تصاویر PNG/JPG/WEBP پذیرفته می‌شود."
            )
        if loaded_w < STAT_SLIDE_MIN_W or loaded_h < STAT_SLIDE_MIN_H:
            raise forms.ValidationError(
                f"ابعاد تصویر {loaded_w}×{loaded_h} پیکسل است؛ "
                f"حداقل مجاز {STAT_SLIDE_MIN_W}×{STAT_SLIDE_MIN_H} پیکسل."
            )
        if loaded_w > STAT_SLIDE_MAX_W or loaded_h > STAT_SLIDE_MAX_H:
            raise forms.ValidationError(
                f"ابعاد تصویر {loaded_w}×{loaded_h} پیکسل است؛ "
                f"حداکثر مجاز {STAT_SLIDE_MAX_W}×{STAT_SLIDE_MAX_H} پیکسل."
            )
        ratio = loaded_w / loaded_h
        if ratio < STAT_SLIDE_RATIO_MIN or ratio > STAT_SLIDE_RATIO_MAX:
            raise forms.ValidationError(
                f"نسبت ابعاد تصویر {ratio:.2f} است؛ نسبت مجاز ۳٫۵ تا ۴٫۵ "
                "(توصیه‌شده ۲۴۰۰×۶۰۰ — بنر ۴:۱)."
            )


class StatSlideForm(forms.ModelForm):
    """ثبت/ویرایش «اسلاید آمار داشبورد» توسط ادمین — مشابه AdvertisementForm.

    ادمین تصویر + عنوان/توضیح/لینک و «هزینهٔ دریافتی (سکه)» را ثبت می‌کند؛
    بازهٔ نمایش با «تقویم شمسی» (تاریخ شروع + تاریخ پایان + یک ساعت واحد)
    انتخاب می‌شود. اسلایدشو فقط یک باکس دارد («اسلایدشو A» بالای «ماژول‌های
    کسب‌وکار»)؛ اسلاید همیشه به همان متصل می‌شود و انتخاب باکس وجود ندارد.
    """

    # فیلدهای کمکیِ تقویم شمسی (مثل AdvertisementForm): تاریخ میلادیِ پنهان
    # توسط JS تقویم پر می‌شود و clean() آن‌ها را با «ساعت واحد» ترکیب می‌کند.
    start_date = forms.CharField(
        required=True, widget=forms.HiddenInput,
        help_text="تاریخ شروع نمایش (تقویم شمسی).",
    )
    end_date = forms.CharField(
        required=True, widget=forms.HiddenInput,
        help_text="تاریخ پایان نمایش (تقویم شمسی).",
    )
    ad_time = forms.TimeField(
        required=True,
        label="ساعت شروع و پایان (یکسان)",
        help_text="یک ساعت واحد که هم شروع و هم پایان اسلاید است (مثلاً ۰۸:۰۰).",
        widget=forms.TimeInput(
            attrs={"type": "time", "class": "hb-form-control", "dir": "ltr"},
            format="%H:%M",
        ),
    )
    class Meta:
        model = StatSlide
        fields = [
            "image", "title", "description", "link_url", "coins_paid",
            "show_from", "show_until", "sort_order",
        ]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"class": "hb-form-control", "accept": ".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"}),
            "title": forms.TextInput(attrs={"class": "hb-form-control", "maxlength": "120"}),
            "description": forms.TextInput(attrs={"class": "hb-form-control", "maxlength": "300"}),
            "link_url": forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr", "placeholder": "https://example.com"}),
            "show_from": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "hb-form-control", "dir": "ltr"},
                format="%Y-%m-%dT%H:%M",
            ),
            "show_until": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "hb-form-control", "dir": "ltr"},
                format="%Y-%m-%dT%H:%M",
            ),
        }
        labels = {
            "image": "تصویر اسلاید",
            "title": "عنوان اسلاید",
            "description": "توضیح اسلاید (اختیاری)",
            "link_url": "لینک (اختیاری)",
            "coins_paid": "هزینهٔ دریافتی (سکه)",
            "sort_order": "ترتیب پخش",
        }
        help_texts = {
            "image": STAT_SLIDE_IMAGE_SPEC_TEXT,
            "title": "عنوان کوتاه روی/زیر تصویر؛ حداکثر ۱۲۰ کاراکتر.",
            "description": "توضیح کوتاه (اختیاری)؛ حداکثر ۳۰۰ کاراکتر.",
            "link_url": "با کلیک روی اسلاید باز می‌شود؛ خالی = بدون لینک.",
            "coins_paid": "میانگین/کل هزینهٔ دریافتی بابت پخش این اسلاید بر حسب سکه.",
            "sort_order": "ترتیب اسلایدهای هم‌زمان در هر باکس (کوچک‌تر = جلوتر).",
        }
        # «is_active» در فرم نیست؛ اسلاید تازه همیشه فعال ثبت می‌شود و
        # توقف/ادامهٔ پخش از فهرست با دکمهٔ toggle انجام می‌شود (مثل تبلیغات).

    def __init__(self, *args, renew_slide=None, **kwargs):
        super().__init__(*args, **kwargs)
        # حالت «تمدید» (StatSlide.is_expired): ثبت رکوردِ جدید از روی اسلاید
        # منقضی‌شده — تصویر پیش‌فرض از اسلاید قبلی برگردانده می‌شود (آپلود
        # مجدد اختیاری است) و در clean_image اعمال می‌شود.
        self.renew_slide = renew_slide
        if renew_slide is not None and renew_slide.image:
            self.fields["image"].required = False
        # بازهٔ نمایش از تاریخ/ساعتِ تقویم شمسی ساخته می‌شود؛ فیلد اصلی رندر نمی‌شود.
        self.fields["show_from"].required = False
        self.fields["show_until"].required = False
        # «coins_paid» و «sort_order» در فرم کاربر حذف می‌شوند — شرطی بنویسیم.
        if "sort_order" in self.fields:
            self.fields["sort_order"].required = False
            self.fields["sort_order"].widget.attrs.update({"class": "hb-form-control", "min": 0})
        if "coins_paid" in self.fields:
            self.fields["coins_paid"].widget.attrs.update({"class": "hb-form-control", "min": 0, "step": "0.01"})
        self.fields["title"].widget.attrs.update({"class": "hb-form-control"})
        self.fields["description"].widget.attrs.update({"class": "hb-form-control"})
        self.fields["link_url"].widget.attrs.update({"class": "hb-form-control"})
        # مقدار اولیهٔ تاریخ/ساعت هنگام ویرایش (به وقت محلی تهران)
        if self.instance and self.instance.pk:
            start = self.instance.show_from
            end = self.instance.show_until
            if start:
                local = timezone.localtime(start) if timezone.is_aware(start) else start
                self.fields["start_date"].initial = local.strftime("%Y-%m-%d")
                self.fields["ad_time"].initial = local.strftime("%H:%M")
            if end:
                local_end = timezone.localtime(end) if timezone.is_aware(end) else end
                self.fields["end_date"].initial = local_end.strftime("%Y-%m-%d")

    def clean(self):
        cleaned = super().clean()

        # اسلایدشو فقط یک باکس دارد («اسلایدشو A»)؛ نمای‌ها از ``cleaned_data["stat_boxes"]``
        # برای اتصال اسلاید استفاده می‌کنند (همیشه همان باکس یگانه).
        the_box = StatSlideBox.the_box()
        cleaned["stat_boxes"] = (
            StatSlideBox.objects.filter(pk=the_box.pk) if the_box else StatSlideBox.objects.none()
        )
        if the_box is None or not the_box.is_active:
            self.add_error(None, "پذیرش اسلایدشو در حال حاضر غیرفعال است.")
            return cleaned

        # تاریخ شروع + تاریخ پایان + یک ساعتِ واحد (مثل AdvertisementForm)
        start_raw = (cleaned.get("start_date") or "").strip()
        end_raw = (cleaned.get("end_date") or "").strip()
        ad_time = cleaned.get("ad_time")
        if not start_raw and "start_date" not in self.errors:
            self.add_error("start_date", "تاریخ شروع نمایش را از تقویم شمسی انتخاب کنید.")
        if not end_raw and "end_date" not in self.errors:
            self.add_error("end_date", "تاریخ پایان نمایش را از تقویم شمسی انتخاب کنید.")
        if not ad_time and "ad_time" not in self.errors:
            self.add_error("ad_time", "ساعت شروع/پایان (یکسان) را انتخاب کنید.")
        if not (start_raw and end_raw and ad_time):
            return cleaned
        try:
            start_day = datetime.strptime(start_raw, "%Y-%m-%d").date()
        except ValueError:
            self.add_error("start_date", "تاریخ شروع نمایش نامعتبر است.")
            return cleaned
        try:
            end_day = datetime.strptime(end_raw, "%Y-%m-%d").date()
        except ValueError:
            self.add_error("end_date", "تاریخ پایان نمایش نامعتبر است.")
            return cleaned
        if end_day <= start_day:
            self.add_error("end_date", "تاریخ پایان باید بعد از تاریخ شروع باشد.")
            return cleaned
        start_dt = datetime.combine(start_day, ad_time)
        end_dt = datetime.combine(end_day, ad_time)
        if settings.USE_TZ:
            start_dt = timezone.make_aware(start_dt)
            end_dt = timezone.make_aware(end_dt)
        cleaned["show_from"] = start_dt
        cleaned["show_until"] = end_dt

        # ظرفیت اسلایدشو: حداکثر ۱۰ اسلاید (تأییدشده + در انتظار تأیید؛ ردشده‌ها
        # جای را اشغال نمی‌کنند). در ویرایش، خودِ همین اسلاید از شمارش خارج شود.
        self_pk = self.instance.pk if self.instance and self.instance.pk else None
        in_box = StatSlide.slides_in_box(the_box.code).exclude(pk=self_pk)
        if in_box.count() >= STAT_SLIDE_MAX_PER_BOX:
            self.add_error(
                None,
                forms.ValidationError(
                    f"ظرفیت «{the_box.title}» پر است؛ "
                    f"حداکثر {STAT_SLIDE_MAX_PER_BOX} اسلاید ذخیره می‌شود."
                ),
            )
        return cleaned

    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()
        if not title:
            raise forms.ValidationError("عنوان اسلاید را وارد کنید.")
        return title

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if self.instance and self.instance.pk and self.instance.image and image in (None, ""):
            # در ویرایش، تصویر قبلی بدون انتخاب فایل جدید حفظ شود.
            return self.instance.image
        if image in (None, ""):
            renew_slide = getattr(self, "renew_slide", None)
            if renew_slide is not None and renew_slide.image:
                # حالت «تمدید»: بدون آپلود جدید، همان تصویر اسلاید قبلی استفاده می‌شود.
                return renew_slide.image
        # مشخصات مجاز تصویر (فرمت/حجم/ابعاد/نسبت) — پذیرفته نشدن فایلِ ناسازگار.
        validate_stat_slide_image(image)
        return image

    def clean_link_url(self):
        link = (self.cleaned_data.get("link_url") or "").strip()
        if link and not link.lower().startswith(("http://", "https://")):
            raise forms.ValidationError("لینک باید با http:// یا https:// شروع شود.")
        return link


class StatSlideUserForm(StatSlideForm):
    """ثبت اسلاید آمار داشبورد توسط «کاربر» — مشابه AdvertisementForm در ماژول تبلیغات.

    کاربر تصویر/عنوان/توضیح/لینک + بازهٔ نمایش (تقویم شمسی + ساعت واحد) را
    انتخاب می‌کند؛ هزینه به‌ازای هر «روز» در نمای ثبت از کیف پول کسر می‌شود و اسلاید با وضعیت «در انتظار تأیید» ذخیره می‌گردد.
    برخلاف نسخهٔ ادمین، «هزینهٔ دریافتی» و «ترتیب پخش» را کاربر تعیین نمی‌کند.
    سقف «حداکثر ۱۰ اسلاید» از فرم والد اعمال می‌شود.
    """

    class Meta(StatSlideForm.Meta):
        model = StatSlide
        fields = ["image", "title", "description", "link_url", "show_from", "show_until"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("coins_paid", None)
        self.fields.pop("sort_order", None)