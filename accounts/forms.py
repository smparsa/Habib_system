from datetime import date
import os
import re

from django import forms
from .models import (
    EducationInstitution,
    FameNameTbl,
    FamilynameTbl,
    FirstnameTbl,
    Job,
    JobStatus,
    Profile,
    StudyField,
    StudyGroup,
    StudySpecialization,
    UserDocument,
)


def name_choices_with_en(queryset, fa_attr, en_attr):
    """گزینه‌های یک فهرستِ نام به‌صورت «فارسی (لاتین)» برای نمایش و جستجوی دوزبانه.

    با این برچسب، کاربر می‌تواند در انتخاب‌گرِ جستجویی هم با فارسی و هم با لاتین
    (مثلاً typing «ali») نام را پیدا کند. گزینهٔ خالیِ ابتدای فهرست حفظ می‌شود.
    """
    choices = [("", "---------")]
    for obj in queryset:
        fa = getattr(obj, fa_attr)
        en = (getattr(obj, en_attr) or "").strip()
        label = f"{fa} ({en})" if en else fa
        choices.append((obj.pk, label))
    return choices


def _country_data():
    """داده‌های «کشور» (تابعیت/ملیت/اقامت دائم) از جدول مرجع کشورها.

    برمی‌گرداند (گزینه‌ها، نقشهٔ نام انگلیسی): گزینه‌ها مقدار و برچسبِ فارسی‌اند
    (نام فارسی در Profile ذخیره می‌شود) و نقشه country_fa → country_en برای
    برچسب دو زبانه (data-en روی هر گزینه) استفاده می‌شود. «ایران» همیشه حاضر است
    — حتی اگر جدول مرجع هنوز seed نشده باشد — تا مقدار پیش‌فرضِ هر سه فیلد همیشه
    قابل انتخاب/ذخیره باشد.
    """
    from .models import CountryTbl

    choices = [("", "---------")]
    qs = list(CountryTbl.objects.all().order_by("country_fa"))
    if not any(c.country_fa == "ایران" for c in qs):
        qs.append(CountryTbl(country_fa="ایران", country_en="Iran"))
    en_map = {}
    for obj in qs:
        en_map[obj.country_fa] = (obj.country_en or "").strip()
        choices.append((obj.country_fa, obj.country_fa))
    return choices, en_map


def _country_choices():
    """(سازگاری) فقط گزینه‌های «کشور» — به‌جایش از _country_data استفاده کنید."""
    choices, _ = _country_data()
    return choices


class BilingualSelect(forms.Select):
    """منوی کشویی با برچسب دو زبانه (فارسی + انگلیسی) برای فهرست‌های مرجع مکان.

    مقدارِ ذخیره‌شده همچنان فارسی است (برای هدف‌گیری تیکت‌ها و مقایسه‌های متنی)؛
    روی هر گزینه data-fa (فارسی) و data-en (انگلیسی) و روی هر <optgroup> (گروه
    شهرستان‌های یک استان) هم data-fa/data-en می‌نشیند تا app.js هنگام تغییر زبان
    برچسب‌ها را عوض کند. نامِ فارسیِ گروه در data-fa می‌ماند تا آبشارِ استان
    (initLocationCascade) بدون وابستگی به برچسبِ نمایشیِ ترجمه‌شده کار کند.
    نقشهٔ نام انگلیسیِ گزینه‌ها: self.en_map؛ نقشهٔ نام انگلیسیِ گروه‌ها:
    self.group_en_map (هر دو «فارسی → انگلیسی»).
    """

    def __init__(self, attrs=None, choices=()):
        super().__init__(attrs, choices)
        self.en_map = {}
        self.group_en_map = {}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex, attrs
        )
        if value:
            option["attrs"]["data-fa"] = label
            en = (self.en_map.get(str(value)) or "").strip()
            if en:
                option["attrs"]["data-en"] = en
        return option

    def optgroup_attrs(self, name):
        attrs = super().optgroup_attrs(name)
        fa = str(name)
        attrs["data-fa"] = fa
        en = (self.group_en_map.get(fa) or "").strip()
        if en:
            attrs["data-en"] = en
        return attrs


class CountrySelect(forms.Select):
    """منوی کشویی کشور با برچسب دو زبانه و جستجوی تایپی.

    مقدار ذخیره‌شده نام فارسی کشور است (مثل Profile.country). برچسب اولیه فارسی
    است و روی هر گزینه data-fa (فارسی) و data-en (انگلیسی) می‌نشیند تا app.js
    هنگام تغییر زبان برچسب‌ها را عوض کند و جستجوی تایپی هم با هر دو زبان کار کند.
    """

    def __init__(self, attrs=None, choices=()):
        super().__init__(attrs, choices)
        self.country_en = {}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex, attrs
        )
        if value:
            option["attrs"]["data-fa"] = label
            en = (self.country_en.get(str(value)) or "").strip()
            if en:
                option["attrs"]["data-en"] = en
        return option


def _reference_location_choices():
    """گزینه‌های «استان» و «شهر/شهرستان» از جدول مرجع اطلاعات مکانی (ایران).

    برمی‌گرداند (استان‌ها، گروه‌های شهرستان، نقشهٔ نام انگلیسیِ استان‌ها، نقشهٔ
    نام انگلیسیِ شهرستان‌ها). شهرستان‌ها به‌صورت گروه‌های <optgroup label="استان">
    ساخته می‌شوند تا آبشارِ مشترکِ app.js فقط گروهِ استانِ انتخابی را نشان دهد
    (گزینه‌ها حذف نمی‌شوند؛ بنابراین مقدارِ قبلیِ شهرستان هنگام کپی از محل سکونت
    یا بارگذاری شغل برای ویرایش حفظ می‌شود). نقشه‌های انگلیسی برای برچسب دو زبانهٔ
    گزینه‌ها (data-fa/data-en) استفاده می‌شوند؛ ترجمهٔ برچسبِ <optgroup> (نامِ
    استان) در JS با جستجوی همان نام در فهرستِ «استان» انجام می‌شود.
    """
    from .models import CityTbl, CountryTbl, ProvinceTbl

    iran = CountryTbl.objects.filter(country_fa="ایران").first()
    provinces = (
        ProvinceTbl.objects.filter(country=iran).order_by("province_fa")
        if iran is not None
        else ProvinceTbl.objects.none()
    )
    province_choices = [("", "— انتخاب کنید —")]
    province_choices += [(p.province_fa, p.province_fa) for p in provinces]
    province_en = {p.province_fa: (p.province_en or "").strip() for p in provinces}
    city_groups = []
    city_en = {}
    for prov in provinces:
        cities = list(CityTbl.objects.filter(province=prov).order_by("city_fa"))
        city_groups.append((prov.province_fa, [(c.city_fa, c.city_fa) for c in cities]))
        for c in cities:
            city_en[c.city_fa] = (c.city_en or "").strip()
    return province_choices, city_groups, province_en, city_en


def _store_country_en(profile):
    """نام‌های انگلیسیِ هم‌ارز فیلدهای کشور (تابعیت/ملیت/اقامت دائم) را می‌نویسد.

    مقدارِ رسمیِ فارسیِ خودِ فیلدها (که هدف‌گیری تیکت‌ها و مقایسه‌های متنی روی آن‌هاست)
    دست‌نخورده می‌ماند و نسخهٔ انگلیسیِ هم‌ارز در extra_data («*_en») ذخیره می‌شود تا
    بج‌های خلاصه و انتخاب‌گرها با زبانِ فعالِ رابط نمایش داده شوند. اگر نامی در جدول
    مرجع نباشد، کلیدِ *_en پاک می‌شود (fallback همان مقدار فارسی).
    خروجی: دیکشنریِ تازهٔ extra_data — فراخواننده باید آن را روی پروفایل بنویسد.
    """
    from .location_ref import country_en_for

    extra = dict(profile.extra_data or {})
    for f in ("citizenship", "nationality", "permanent_residence"):
        en = country_en_for(getattr(profile, f) or "")
        if en:
            extra[f"{f}_en"] = en
        else:
            extra.pop(f"{f}_en", None)
    return extra


class PersonalInfoForm(forms.ModelForm):
    """فرم اطلاعات شخصی (فقط فیلدهای قابل ویرایش)"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تابعیت/ملیت/اقامت دائم: منوی کشویی نام کشورها از جدول مرجع CountryTbl،
        # پیش‌فرض هر سه «ایران» (در صورت خالی بودن مقدار ذخیره‌شده) و الزامی؛
        # برچسب‌ها دو زبانه‌اند (data-en) و با JS جستجوی تایپی می‌گیرند.
        country_choices, country_en_map = _country_data()
        for name in ("citizenship", "nationality", "permanent_residence"):
            self.fields[name].widget = CountrySelect(
                choices=country_choices,
                attrs={
                    "class": "hb-form-control hb-form-select hb-country-select",
                    "required": True,
                },
            )
            self.fields[name].widget.country_en = country_en_map
            self.fields[name].required = True
            self.fields[name].error_messages["required"] = (
                "کشور مورد نظر را از فهرست انتخاب کنید."
            )
            self.initial.setdefault(name, "ایران")
        # نام خودِ کاربر: همهٔ نام‌ها. (نام پدر/مادر به بخش «اطلاعات خانواده»
        # منتقل شده‌اند — FamilyInfoForm؛ «شهرت» از جدول مرجع FameNameTbl است.)
        self.fields['first_name'].queryset = FirstnameTbl.objects.all()
        self.fields['last_name'].queryset = FamilynameTbl.objects.all()
        self.fields['fame_name'].queryset = FameNameTbl.objects.all()
        # راهنمای جستجو برای فیلدهای نام (انتخاب‌گر خودکارِ جستجوی زنده در app.js) +
        # نمایش دو زبانهٔ «فارسی (لاتین)» تا جستجو با هر دو زبان ممکن باشد.
        # data-hb-kind: first|family|fame — نوع جدول مرجع برای جستجوی زنده
        for name, fa_attr, en_attr, kind in (
            ('first_name', 'first_name_fa', 'first_name_en', 'first'),
            ('last_name', 'familyname_fa', 'familyname_en', 'family'),
            ('fame_name', 'fame_name_fa', 'fame_name_en', 'fame'),
        ):
            self.fields[name].widget.attrs['data-hb-filter-hint'] = (
                'تایپ کنید و از فهرست انتخاب کنید…')
            self.fields[name].widget.attrs['data-hb-kind'] = kind
            self.fields[name].widget.attrs['data-hb-gender'] = ''
            self.fields[name].choices = name_choices_with_en(
                self.fields[name].queryset, fa_attr, en_attr)
        # فیلدهای ضروری: نام، نام خانوادگی، کد ملی، تاریخ تولد، جنسیت، تابعیت/
        # ملیت/اقامت دائم، دین و مذهب. (نام پدر/مادر و وضعیت تأهل به بخش
        # «اطلاعات خانواده» منتقل شده‌اند؛ پسوند فامیل و شهرت اختیاری‌اند.)
        for field_name, message in (
            ('first_name', 'لطفاً نام را از فهرست انتخاب کنید.'),
            ('last_name', 'لطفاً نام خانوادگی را از فهرست انتخاب کنید.'),
            ('national_id', 'کد ملی الزامی است.'),
            ('date_of_birth', 'لطفاً تاریخ تولد را انتخاب کنید.'),
            ('gender', 'لطفاً جنسیت را انتخاب کنید.'),
            ('religion', 'لطفاً دین را انتخاب کنید.'),
            ('sect', 'لطفاً مذهب را انتخاب کنید.'),
        ):
            self.fields[field_name].required = True
            self.fields[field_name].error_messages['required'] = message
        self.fields['national_id'].label = 'کد ملی *'
        # «کد ملی پس از ثبت نهایی و گرفتن امتیاز، دیگر قابل تغییر نیست»:
        # اگر پاداشِ تکمیل اطلاعات شخصی پرداخت شده باشد، فیلد در فرم غیرفعال
        # می‌شود (سمت کلاینت) و مقدار قدیم در clean هم حفظ می‌شود (سمت سرور).
        if self.national_id_locked:
            self.fields['national_id'].disabled = True
            self.fields['national_id'].help_text = (
                'کد ملی شما ثبت و تأیید نهایی شده است و دیگر قابل تغییر نیست.'
            )

    @property
    def national_id_locked(self):
        """کد ملی قفل است؟ (پس از پاداشِ تکمیل اطلاعات شخصی = ثبت نهایی)"""
        if not self.instance or not self.instance.pk:
            return False
        extra = self.instance.extra_data or {}
        return bool(extra.get("profile_completion_rewarded"))

    def clean_national_id(self):
        nid = (self.cleaned_data.get('national_id') or '').strip()
        # قفلِ کد ملی: اگر پاداش پرداخت شده، مقدار قدیم برمی‌گردد (تغییر ناپذیر)
        if self.national_id_locked:
            return self.instance.national_id or nid
        if not nid:
            raise forms.ValidationError('کد ملی الزامی است.')
        if not re.fullmatch(r'\d{10}', nid):
            raise forms.ValidationError('کد ملی باید دقیقاً ۱۰ رقم (۰-۹) باشد. رقم اول می‌تواند ۰ باشد.')
        # «کنترل کد ملی»: کدهای رزروشدهٔ پنل مدیریت (مثلاً اختصاصیِ ادمین) برای
        # کاربرِ عادی قابل ثبت نیستند؛ کاربر ادمین (is_staff) مجاز است.
        from .models import national_code_denied

        is_staff = self.instance.user.is_staff if self.instance and self.instance.user_id else False
        denied = national_code_denied(nid, is_staff=is_staff)
        if denied:
            raise forms.ValidationError(denied)
        return nid

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get("date_of_birth")
        if not dob:
            return dob
        today = date.today()
        age = today.year - dob.year - (
            (today.month, today.day) < (dob.month, dob.day)
        )
        if age < 7:
            raise forms.ValidationError("سن نمی‌تواند کمتر از ۷ سال باشد.")
        if age > 120:
            raise forms.ValidationError("سن نمی‌تواند بیشتر از ۱۲۰ سال باشد.")
        return dob

    def clean(self):
        cleaned = super().clean()
        # «شماره ملی با نام و نام‌خانوادگی کنترل بشود و در صورت مغایرت ثبت نگردد»:
        # در نخستین ثبتِ کد ملی (و هر تغییرِ آن)، مشخصات متقاضی با سرویس استعلام
        # تطبیق داده می‌شود؛ مغایرت = عدم ثبت. در نبودِ سرویس، کنترل انجام نمی‌شود
        # (هیچ ردی در extra_data ثبت نمی‌شود تا روند همان قبل بماند).
        nid = (cleaned.get("national_id") or "").strip()
        if nid and not self.national_id_locked:
            first = self.cleaned_data.get("first_name")
            last = self.cleaned_data.get("last_name")
            first_fa = getattr(first, "first_name_fa", "") or ""
            last_fa = getattr(last, "familyname_fa", "") or ""
            full_name = f"{first_fa} {last_fa}".strip()
            if full_name:
                from .iban_verify import verify as verify_nid

                result = verify_nid(full_name, nid)
                if result.get("available"):
                    if result.get("match") is False:
                        self.add_error(
                            "national_id",
                            "کد ملی تأیید نمی‌شود: "
                            + (result.get("message") or
                               "مشخصات واردشده با کد ملی هم‌خوانی ندارد."),
                        )
                    else:
                        # نتیجهٔ کنترل (مثبت) در extra_data نگه داشته می‌شود
                        self.national_id_verify_result = result
        return cleaned

    def save(self, commit=True):
        profile = super().save(commit=commit)
        if commit:
            profile.extra_data = _store_country_en(profile)
            # ذخیرهٔ نتیجهٔ موفق کنترل کد ملی (در صورت انجام)
            result = getattr(self, "national_id_verify_result", None)
            if result is not None:
                extra = dict(profile.extra_data or {})
                extra["national_id_verify"] = {
                    "match": result.get("match"),
                    "available": result.get("available"),
                    "checked_at": result.get("checked_at"),
                }
                profile.extra_data = extra
            profile.save(update_fields=["extra_data"])
        return profile

    class Meta:
        model = Profile
        fields = [
            'first_name', 'last_name', 'family_suffix', 'fame_name', 'national_id',
            'date_of_birth', 'gender', 'citizenship', 'nationality',
            'permanent_residence', 'religion', 'sect', 'bio',
        ]
        widgets = {
            'first_name': forms.Select(attrs={'class': 'hb-form-control hb-form-select hb-name-select'}),
            'last_name': forms.Select(attrs={'class': 'hb-form-control hb-form-select hb-name-select'}),
            'family_suffix': forms.TextInput(attrs={
                'class': 'hb-form-control', 'placeholder': 'مثال: رود، نژاد، زاده، پور… (اختیاری)'}),
            'fame_name': forms.Select(attrs={'class': 'hb-form-control hb-form-select hb-name-select'}),
            'national_id': forms.TextInput(attrs={'class': 'hb-form-control', 'dir': 'ltr', 'placeholder': 'کد ملی'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'hb-form-control'}),
            'gender': forms.Select(attrs={'class': 'hb-form-control hb-form-select'}),
            'religion': forms.Select(attrs={'class': 'hb-form-control hb-form-select'}),
            'sect': forms.Select(attrs={'class': 'hb-form-control hb-form-select'}),
            'bio': forms.Textarea(attrs={'class': 'hb-form-control hb-form-textarea'}),
        }


NID_RE = re.compile(r"^\d{10}$")


class FamilyInfoForm(forms.ModelForm):
    """فرم بخش «اطلاعات خانواده» پروفایل — با دکمهٔ ذخیرهٔ مستقل.

    فیلدهای الزامی:
      * «وضعیت تأهل» (مجرد / متاهل / جداشده)، «نام پدر» و «نام مادر» (انتخاب از
        جدول مرجع نام‌ها با فیلتر جنسیت — همان مشخصات قبلیِ منتقل‌شده از اطلاعات
        شخصی).
    «تعداد همسر(های) قانونی»، «تعداد فرزندان پسر» و «تعداد فرزندان دختر»
    اختیاری‌اند:
      * در وضعیت «مجرد» همسر و فرزندان غیرفعال می‌شوند و مقادیر قبلی پاک می‌شوند؛
      * در وضعیت «متاهل» فقط همسر(های) قانونی فعال است؛
      * در وضعیت «جداشده» فقط فرزندان فعال است (همسر پاک می‌شود)؛
      * در وضعیت‌های فعال، تعداد فقط سقفِ ردیف‌های «کد ملی» را مشخص می‌کند؛
        کد ملیِ هر ردیف هم اختیاری است و ردیف‌های خالی ذخیره نمی‌شوند.

    برای هر همسر/فرزند فقط «کد ملی» از کاربر گرفته می‌شود (اختیاری)؛ نام و نام
    خانوادگی از کاربر پرسیده نمی‌شود. کد ملی‌ها **فقط** در پایگاه داده (extra_data)
    ذخیره می‌شوند و نمایش نام همیشه از سیستم فراخوانی می‌شود:
      * اگر فرد قبلاً در سیستم ثبت‌نام کرده باشد، نامش به‌صورت خودکار
        فراخوانی می‌شود (endpoint فراخوانی + رندر مجدد)؛
      * اگر ثبت‌نام نکرده باشد، کاربر فقط کد ملی را وارد می‌کند — مشخصاتش
        بعد از ثبت‌نامِ او به‌طور خودکار در سیستم ظاهر می‌شود.

    ساختار داده در extra_data["family"]:
        {"spouses_count": n,
         "spouses": [{"national_id": "1234567890", "matched": true}, ...],
         "sons_count": n, "daughters_count": n,
         "sons": [{"national_id": .., "matched": bool}, ...],
         "daughters": [...], "dependents_count": n}
    """

    MAX_ROWS = 10

    # تعدادها همه اختیاری‌اند: خالی = «نامشخص/بدون ثبت»؛ اگر مقدار بزرگ‌تر از
    # صفر داده شود، به همان تعداد کد ملی لازم است (ولی خودِ تعداد الزامی نیست).
    spouses_count = forms.IntegerField(
        required=False, label="تعداد همسر(های) قانونی", min_value=1,
        max_value=MAX_ROWS,
        error_messages={
            "min_value": "تعداد همسر(های) قانونی باید حداقل ۱ باشد.",
        },
        widget=forms.NumberInput(attrs={
            "class": "hb-form-control", "min": "1", "max": str(MAX_ROWS),
            "data-family-count": "spouse"}),
    )
    sons_count = forms.IntegerField(
        required=False, label="تعداد فرزندان پسر", min_value=0, max_value=MAX_ROWS,
        error_messages={"min_value": "تعداد نمی‌تواند منفی باشد."},
        widget=forms.NumberInput(attrs={
            "class": "hb-form-control", "min": "0", "max": str(MAX_ROWS),
            "data-family-count": "sons"}),
    )
    daughters_count = forms.IntegerField(
        required=False, label="تعداد فرزندان دختر", min_value=0, max_value=MAX_ROWS,
        error_messages={"min_value": "تعداد نمی‌تواند منفی باشد."},
        widget=forms.NumberInput(attrs={
            "class": "hb-form-control", "min": "0", "max": str(MAX_ROWS),
            "data-family-count": "daughters"}),
    )
    dependents_count = forms.IntegerField(
        required=False, label="افراد تحت تکفل", min_value=0, max_value=30,
        widget=forms.NumberInput(attrs={"class": "hb-form-control", "min": "0"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # نام پدر/مادر: بر اساس جنسیتِ جدول نام‌ها (نام‌های بدون جنسیت هم برای
        # اطمینان نمایش داده می‌شوند) — همان مشخصات قبلی بخش اطلاعات شخصی.
        self.fields['father_name'].queryset = FirstnameTbl.objects.filter(
            gender__in=['male', ''])
        self.fields['mother_name'].queryset = FirstnameTbl.objects.filter(
            gender__in=['female', ''])
        for name, fa_attr, en_attr, kind, gender in (
            ('father_name', 'first_name_fa', 'first_name_en', 'first', 'male'),
            ('mother_name', 'first_name_fa', 'first_name_en', 'first', 'female'),
        ):
            self.fields[name].widget.attrs['data-hb-filter-hint'] = (
                'تایپ کنید و از فهرست انتخاب کنید…')
            self.fields[name].widget.attrs['data-hb-kind'] = kind
            self.fields[name].widget.attrs['data-hb-gender'] = gender
            self.fields[name].choices = name_choices_with_en(
                self.fields[name].queryset, fa_attr, en_attr)
        for field_name, message in (
            ('father_name', 'لطفاً نام پدر را از فهرست انتخاب کنید.'),
            ('mother_name', 'لطفاً نام مادر را از فهرست انتخاب کنید.'),
            ('marital_status', 'لطفاً وضعیت تأهل را انتخاب کنید.'),
        ):
            self.fields[field_name].required = True
            self.fields[field_name].error_messages['required'] = message
        extra = dict(self.instance.extra_data or {})
        family = extra.get("family") or {}
        # پرکردن مقادیر اولیهٔ تعدادها از دادهٔ ذخیره‌شدهٔ قبلی
        for name in ("spouses_count", "sons_count", "daughters_count",
                     "dependents_count"):
            self.initial.setdefault(name, family.get(name, ""))

    # ---- ردیف‌های کد ملی همسر/فرزند --------------------------------------

    def _row_value(self, prefix, idx, field):
        """خواندن مقدار یک فیلد از ردیف؛ idx همان رشتهٔ شمارهٔ ردیف در POST است."""
        raw = self.data.get(f"{prefix}_{idx}_{field}", "")
        return (raw or "").strip() if isinstance(raw, str) else (raw or "")

    def _nid_row_list(self, prefix):
        """ردیف‌های کد ملی یک گروه (همسر/پسر/دختر) را از POST جمع می‌کند.

        شمارهٔ ردیف‌ها از کلیدهای ارسالی خوانده می‌شود (مثل «spouse_00_national_id»)
        تا حذف ردیف‌های میانی در سمت کاربر مشکلی برای شماره‌گذاری ایجاد نکند؛
        رشتهٔ اصلی شماره حفظ می‌شود تا نام کلید دقیقاً مثل POST بازسازی شود.
        برای محدودسازی، حداکثر MAX_ROWS ردیف برای هر گروه پردازش می‌شود.
        """
        idx_re = re.compile(
            r"^" + re.escape(prefix) + r"_(\d+)_national_id$")
        pairs = sorted({
            (int(m.group(1)), m.group(1))
            for key in self.data.keys()
            for m in [idx_re.match(key)] if m
        })[: self.MAX_ROWS]
        return [
            {"national_id": self._row_value(prefix, idx, "national_id")}
            for _num, idx in pairs
        ]

    @staticmethod
    def _resolve_national_record(nid):
        """پروفایل فردِ ثبت‌نام‌شده با این کد ملی را برمی‌گرداند (یا None)."""
        if not nid:
            return None
        return (
            Profile.objects.filter(national_id=nid)
            .only("id", "national_id", "first_name_id", "last_name_id")
            .first()
        )

    def _validate_rows(self, rows, group_label):
        """ردیف‌های کد ملی یک گروه را اعتبارسنجی و نگاشت نهایی برمی‌گرداند.

        کد ملی‌ها **اختیاری**‌اند: ردیف‌های خالی نادیده گرفته می‌شوند و فقط
        کد ملی‌های واردشده ذخیره می‌شوند. «matched» یعنی فرد در سیستم
        ثبت‌نام کرده و نامش از سیستم فراخوانی می‌شود.
        """
        cleaned = []
        for idx, row in enumerate(rows, start=1):
            nid = (row.get("national_id") or "").strip()
            if not nid:
                continue  # اختیاری: ردیف بدون کد ملی نادیده گرفته می‌شود
            if not NID_RE.fullmatch(nid):
                raise forms.ValidationError(
                    f"{group_label} {idx}: کد ملی باید دقیقاً ۱۰ رقم (۰-۹) باشد.")
            rec = self._resolve_national_record(nid)
            entry = {"national_id": nid}
            if rec is not None:
                entry["matched"] = True
            cleaned.append(entry)
        return cleaned

    def _validate_counts(self, group_label, count, rows):
        """کد ملی‌های واردشدهٔ یک گروه را اعتبارسنجی و نگاشت نهایی برمی‌گرداند.

        کد ملی اختیاری است: تعدادِ تعیین‌شده فقط سقفِ ردیف‌ها را مشخص می‌کند و
        خالی‌گذاشتن کد ملیِ هر ردیف مجاز است (ردیف خالی ذخیره نمی‌شود).
        """
        people = self._validate_rows(rows, group_label)
        if len(people) > count:
            raise forms.ValidationError(
                f"برای {group_label} حداکثر به تعداد تعیین‌شده کد ملی می‌توان وارد کرد.")
        ids = [p["national_id"] for p in people]
        if len(ids) != len(set(ids)):
            raise forms.ValidationError(
                f"کد ملی {group_label} نباید تکراری باشد.")
        return people

    @property
    def family_data_json(self):
        """دادهٔ ذخیره‌شدهٔ خانواده به‌صورت JSON امن برای قالب.

        JS همین داده را می‌خواند تا کد ملی‌های ثبت‌شدهٔ قبلی را هنگام ویرایش
        در ردیف‌ها بازسازی کند و نمایش نامشان را فراخوانی کند.
        """
        import json as _json

        family = dict((self.instance.extra_data or {}).get("family") or {})
        return _json.dumps(family, ensure_ascii=False)

    def clean(self):
        cleaned = super().clean()
        marital = cleaned.get("marital_status") or ""

        # --- همسر(های) قانونی: فقط در وضعیت «متاهل» فعال است ---
        if marital == "married":
            count = cleaned.get("spouses_count")
            if count in (None, ""):
                cleaned["spouses"] = []  # اختیاری: بدون همسر هم قابل ذخیره است
            else:
                cleaned["spouses"] = self._validate_counts(
                    "همسر(های) قانونی", count, self._nid_row_list("spouse"))
        else:
            # مجرد/جداشده: همسر(های) قانونی غیرفعال است و با تعدادش پاک می‌شود
            cleaned["spouses"] = []
            cleaned.pop("spouses_count", None)

        # --- فرزندان پسر/دختر: اختیاری؛ فقط برای مجرد غیرفعال می‌شوند ---
        children_active = marital in ("married", "separated")
        for group, group_label, count_key in (
            ("sons", "فرزندان پسر", "sons_count"),
            ("daughters", "فرزندان دختر", "daughters_count"),
        ):
            count = cleaned.get(count_key)
            if not children_active:
                cleaned[group] = []
                cleaned.pop(count_key, None)
            elif count in (None, ""):
                cleaned[group] = []  # اختیاری: بدون ثبتِ تعداد هم قابل ذخیره است
            else:
                cleaned[group] = self._validate_counts(
                    group_label, count, self._nid_row_list(group))

        return cleaned

    def save(self, commit=True):
        profile = super().save(commit=False)
        extra = dict(profile.extra_data or {})
        family = dict(extra.get("family") or {})
        cleaned = self.cleaned_data
        for key in ("spouses", "sons", "daughters"):
            value = cleaned.get(key)
            if value:
                family[key] = value
            else:
                family.pop(key, None)
        for key in ("spouses_count", "sons_count", "daughters_count"):
            value = cleaned.get(key)
            if value in (None, ""):
                family.pop(key, None)
            else:
                family[key] = value
        value = cleaned.get("dependents_count")
        if value in (None, ""):
            family.pop("dependents_count", None)
        else:
            family["dependents_count"] = value
        if family:
            extra["family"] = family
        else:
            extra.pop("family", None)
        profile.extra_data = extra
        if commit:
            profile.save()
        return profile

    class Meta:
        model = Profile
        fields = ['father_name', 'mother_name', 'marital_status', 'emergency_contact']
        widgets = {
            'father_name': forms.Select(attrs={'class': 'hb-form-control hb-form-select hb-name-select'}),
            'mother_name': forms.Select(attrs={'class': 'hb-form-control hb-form-select hb-name-select'}),
            'marital_status': forms.Select(attrs={'class': 'hb-form-control hb-form-select'}),
            'emergency_contact': forms.TextInput(attrs={
                'class': 'hb-form-control', 'dir': 'ltr',
                'placeholder': 'شماره تماس اضطراری (اختیاری)'}),
        }


class EducationInfoForm(forms.ModelForm):
    """فرم اطلاعات تحصیلی با انتخاب از فهرست‌های مرجع قابل مدیریت توسط ادمین.

    فیلدهای آخرین مدرک، مرکز دانشگاهی، رشته تحصیلی و گرایش تحصیلی الزامی و ستاره‌دار
    هستند. اگر مدرک دیپلم انتخاب شود، فیلدهای مرکز دانشگاهی و رشته تحصیلی غیرفعال
    می‌شوند. رشته و گرایش به‌صورت آبشاری و سلسله‌مراتبی (گروه → رشته → گرایش) اعتبارسنجی
    می‌شوند — مشابه کاتالوگ مشاغل (حوزه → صنعت → دسته). همهٔ فیلدهای انتخاب دارای
    جستجوی تایپی با دوزبانهٔ فارسی/انگلیسی هستند.
    """

    degree = forms.ChoiceField(
        required=True,
        label="آخرین مدرک *",
        choices=[
            ("", "— انتخاب کنید —"),
            ("دیپلم", "دیپلم"),
            ("کاردانی", "کاردانی"),
            ("کارشناسی", "کارشناسی"),
            ("کارشناسی ارشد", "کارشناسی ارشد"),
            ("دکتری", "دکتری"),
        ],
        widget=forms.Select(attrs={"class": "hb-form-control hb-form-select", "required": True}),
    )
    education_institution = forms.ModelChoiceField(
        required=True,
        queryset=EducationInstitution.objects.none(),
        label="مرکز دانشگاهی *",
        empty_label="— انتخاب کنید —",
        widget=forms.Select(attrs={"class": "hb-form-control hb-form-select hb-education-autocomplete", "data-hb-kind": "education_institution", "required": True}),
    )
    study_group = forms.ModelChoiceField(
        required=False,
        queryset=StudyGroup.objects.none(),
        label="گروه امتحانی",
        empty_label="— همهٔ گروه‌ها / بدون گروه —",
        help_text="با انتخاب گروه امتحانی، فهرست رشته‌های تحصیلی فقط به همان گروه محدود می‌شود.",
        widget=forms.Select(attrs={"class": "hb-form-control hb-form-select hb-education-autocomplete", "data-hb-kind": "study_group", "data-education-group": "1"}),
    )
    study_field = forms.ModelChoiceField(
        required=True,
        queryset=StudyField.objects.none(),
        label="رشته تحصیلی *",
        empty_label="— انتخاب کنید —",
        widget=forms.Select(attrs={"class": "hb-form-control hb-form-select hb-education-autocomplete", "data-hb-kind": "study_field", "data-education-field": "1", "required": True}),
    )
    study_specialization = forms.ModelChoiceField(
        required=False,
        queryset=StudySpecialization.objects.none(),
        label="گرایش تحصیلی",
        empty_label="— بدون گرایش / انتخاب کنید —",
        widget=forms.Select(attrs={"class": "hb-form-control hb-form-select hb-education-autocomplete", "data-hb-kind": "study_specialization", "data-education-specialization": "1", "required": False}),
    )
    graduation_year = forms.IntegerField(
        required=False,
        min_value=1300,
        max_value=1600,
        label="سال فارغ‌التحصیلی",
        widget=forms.NumberInput(attrs={"class": "hb-form-control", "dir": "ltr", "placeholder": "مثلاً ۱۴۰۲"}),
    )
    gpa = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=20,
        max_digits=4,
        decimal_places=2,
        label="معدل",
        widget=forms.NumberInput(attrs={"class": "hb-form-control", "dir": "ltr", "step": "0.01"}),
    )
    courses = forms.CharField(
        required=False,
        label="دوره‌های آموزشی",
        widget=forms.TextInput(attrs={"class": "hb-form-control"}),
    )
    languages = forms.CharField(
        required=False,
        label="زبان‌های خارجی",
        widget=forms.TextInput(attrs={"class": "hb-form-control"}),
    )
    language_levels = forms.CharField(
        required=False,
        label="سطح هر زبان",
        widget=forms.TextInput(attrs={"class": "hb-form-control"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["education_institution"].queryset = EducationInstitution.objects.filter(
            is_active=True
        ).order_by("institution_type", "name")
        self.fields["study_group"].queryset = StudyGroup.objects.filter(
            is_active=True
        ).order_by("code")
        # اگر پروفایل قبلاً رشته داشته، گروهِ همان رشته به‌صورت پیش‌فرض انتخاب است
        initial_group = None
        if self.instance.pk and self.instance.study_field_id:
            initial_group = self.instance.study_field.study_group_id
        if initial_group:
            self.fields["study_group"].initial = initial_group
        self.fields["study_field"].queryset = StudyField.objects.filter(
            is_active=True
        ).select_related("study_group").order_by("study_group__name", "name")
        self.fields["study_specialization"].queryset = StudySpecialization.objects.filter(
            is_active=True, field__is_active=True
        ).select_related("field").order_by("field__name", "name")
        extra = dict(self.instance.extra_data or {})
        education = extra.get("education") or {}
        for name in ("courses", "languages", "language_levels"):
            self.initial.setdefault(name, education.get(name, ""))
        self._setup_education_bilingual_choices()

    def clean(self):
        cleaned = super().clean()
        degree = cleaned.get("degree")
        field = cleaned.get("study_field")
        specialization = cleaned.get("study_specialization")
        institution = cleaned.get("education_institution")
        if degree == "دیپلم":
            # When diploma, institution and field are optional; remove any required errors
            if institution is None:
                self.errors.pop("education_institution", None)
            if field is None:
                self.errors.pop("study_field", None)
            # If specialization was selected with diploma, remove its error too
            if specialization is None:
                self.errors.pop("study_specialization", None)
        else:
            # Normal validation: specialization must belong to field
            if specialization and field and specialization.field_id != field.pk:
                self.add_error(
                    "study_specialization",
                    "گرایش انتخاب‌شده متعلق به رشتهٔ انتخاب‌شده نیست.",
                )
            elif specialization and not field:
                self.add_error("study_field", "برای انتخاب گرایش، ابتدا رشته را انتخاب کنید.")
            # اعتبارسنجی آبشاری گروه ← رشته: اگر گروه انتخاب شده باشد، رشتهٔ
            # انتخاب‌شده باید به همان گروه تعلق داشته باشد.
            group = cleaned.get("study_group")
            if group and field and field.study_group_id != group.pk:
                self.add_error(
                    "study_field",
                    "رشتهٔ انتخاب‌شده متعلق به گروه امتحانی انتخاب‌شده نیست.",
                )
        return cleaned

    def save(self, commit=True):
        profile = super().save(commit=False)
        institution = self.cleaned_data.get("education_institution")
        field = self.cleaned_data.get("study_field")
        specialization = self.cleaned_data.get("study_specialization")
        degree = self.cleaned_data.get("degree")
        is_diploma = degree == "دیپلم"
        if is_diploma:
            # For diploma, clear FK fields and legacy text fields
            profile.education_institution = None
            profile.study_field = None
            profile.study_specialization = None
            profile.university = ""
            profile.field_of_study = ""
        else:
            if institution:
                profile.university = institution.name
            if field:
                profile.field_of_study = field.name
        extra = dict(profile.extra_data or {})
        education = dict(extra.get("education") or {})
        for key in ("courses", "languages", "language_levels"):
            value = (self.cleaned_data.get(key) or "").strip()
            if value:
                education[key] = value
            else:
                education.pop(key, None)
        education["institution_id"] = institution.pk if institution and not is_diploma else None
        education["field_id"] = field.pk if field and not is_diploma else None
        education["specialization_id"] = specialization.pk if specialization and not is_diploma else None
        education["group_id"] = (
            self.cleaned_data["study_group"].pk
            if self.cleaned_data.get("study_group") and not is_diploma
            else (field.study_group_id if field and not is_diploma else None)
        )
        education["degree"] = degree
        if any(education.values()):
            extra["education"] = education
        else:
            extra.pop("education", None)
        profile.extra_data = extra
        if commit:
            profile.save()
        return profile

    class Meta:
        model = Profile
        fields = [
            "degree", "study_group", "education_institution", "study_field", "study_specialization",
            "graduation_year", "gpa",
        ]

    def _setup_education_bilingual_choices(self):
        """تنظیم گزینه‌های دوزبانه برای فیلدهای انتخابی تحصیلی.

        مانند فیلدهای نام در بخش اطلاعات شخصی، هر گزینه برچسب فارسی و انگلیسی دارد.
        """
        inst_choices = [("", "---------")]
        for obj in self.fields["education_institution"].queryset:
            en = (obj.name_en or "").strip()
            label = f"{obj.name} ({en})" if en else obj.name
            inst_choices.append((obj.pk, label))
        self.fields["education_institution"].choices = inst_choices

        # گروه امتحانی: گزینه‌های سادهٔ دوزبانه
        group_choices = [("", self.fields["study_group"].empty_label)]
        for obj in self.fields["study_group"].queryset:
            en = (obj.name_en or "").strip()
            label = f"{obj.name} ({en})" if en else obj.name
            group_choices.append((obj.pk, label))
        self.fields["study_group"].choices = group_choices

        # رشته تحصیلی: گزینه‌ها داخل <optgroup> هر گروه امتحانی گروه‌بندی می‌شوند
        # تا آبشاری «گروه ← رشته» حتی بدون جاوااسکریپت هم سرراست باشد.
        field_choices = [("", "---------")]
        by_group = {}
        for obj in self.fields["study_field"].queryset:
            by_group.setdefault(obj.study_group, []).append(obj)
        for group in self.fields["study_group"].queryset:
            fields_in_group = by_group.get(group, [])
            if not fields_in_group:
                continue
            en_g = (group.name_en or "").strip()
            glabel = f"{group.name} ({en_g})" if en_g else group.name
            field_choices.append((
                glabel,
                [(obj.pk, f"{obj.name} ({(obj.name_en or '').strip()})" if (obj.name_en or "").strip() else obj.name) for obj in fields_in_group],
            ))
        # رشته‌های بدون گروه (نباید رخ دهد؛ برای اطمینان در انتها)
        orphans = by_group.get(None, [])
        if orphans:
            field_choices.append(("بدون گروه", [obj.pk for obj in []] + [(obj.pk, obj.name) for obj in orphans]))
        self.fields["study_field"].choices = field_choices

        spec_choices = [("", "---------")]
        for obj in self.fields["study_specialization"].queryset:
            en = (obj.name_en or "").strip()
            field_name = obj.field.name if obj.field else ""
            label = f"{obj.name} ({en})" if en else obj.name
            if field_name:
                label = f"{label} [{field_name}]"
            spec_choices.append((obj.pk, label))
        self.fields["study_specialization"].choices = spec_choices


# --------------------------------------------------------------------------- #
# «اطلاعات ارتباطی» — شماره‌های تماس، وب‌سایت و شبکه‌های اجتماعی
# --------------------------------------------------------------------------- #
# شبکه‌های اجتماعیِ پروفایل (بخش «اطلاعات ارتباطی»): هرکدام یک فیلد جداگانه
# دارد که آدرس/شناسهٔ کاربر در همان شبکه در آن وارد می‌شود. گروه «ایرانی»:
# بله، ایتا، روبیکا — گروه «غیرایرانی»: تلگرام، واتساپ و ... . همه اختیاری‌اند
# و در extra_data["social"] (کلید → آدرس) ذخیره می‌شوند.
SOCIAL_NETWORKS = [
    ("bale", "بله (Bale)"),
    ("eitaa", "ایتا (Eitaa)"),
    ("rubika", "روبیکا (Rubika)"),
    ("telegram", "تلگرام (Telegram)"),
    ("whatsapp", "واتساپ (WhatsApp)"),
    ("instagram", "اینستاگرام (Instagram)"),
    ("facebook", "فیس‌بوک (Facebook)"),
    ("x", "ایکس / توییتر (X)"),
    ("youtube", "یوتیوب (YouTube)"),
    ("linkedin", "لینکدین (LinkedIn)"),
]

IRANIAN_SOCIAL_KEYS = ("bale", "eitaa", "rubika")


class ContactInfoForm(forms.ModelForm):
    """فرم «اطلاعات ارتباطی» پروفایل.

    شماره موبایل (شناسهٔ ورود) الزامی است اما فقط نمایشی است و قابل ویرایش
    نیست؛ همهٔ فیلدهای دیگر این بخش اختیاری‌اند. هر شبکهٔ اجتماعی (ایرانی و
    غیرایرانی) یک فیلد جداگانه دارد و آدرس/شناسهٔ آن در extra_data["social"]
    ذخیره می‌شود؛ وب‌سایت شخصی هم در extra_data["website"]. «کد ملی معرف» که در
    بخش اطلاعات شخصی فقط نمایشی است، اینجا تکرار شده و قابل تغییر است و روی
    User.referrer_national_id نوشته می‌شود (با همان اعتبارسنجی صفحهٔ ورود).
    """

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user is None and self.instance and self.instance.user_id:
            self.user = self.instance.user
        extra = dict(self.instance.extra_data or {})
        social = extra.get("social") or {}

        # شماره موبایل: نمایشی و الزامی (شناسهٔ ورود؛ قابل ویرایش نیست)
        mobile = self.user.mobile_number if self.user else ""
        self.fields["mobile_number"] = forms.CharField(
            required=False, disabled=True, label="شماره موبایل *",
            initial=mobile,
            widget=forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "readonly": True,
            }),
        )
        # «کد ملی معرف»: تکرارِ بخش اطلاعات شخصی، اما اینجا قابل تغییر است
        referrer = (self.user.referrer_national_id or "") if self.user else ""
        self.fields["referrer_national_id"] = forms.CharField(
            required=False, label="کد ملی معرف", initial=referrer,
            widget=forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "maxlength": "10",
                "inputmode": "numeric", "placeholder": "کد ملی ۱۰ رقمی معرف",
            }),
        )
        # وب‌سایت و شبکه‌های اجتماعی از extra_data خوانده می‌شوند (همه اختیاری)
        self.fields["website"] = forms.URLField(
            required=False, label="وب‌سایت شخصی",
            initial=str(extra.get("website") or ""),
            widget=forms.URLInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "https://example.com",
            }),
        )
        for key, label in SOCIAL_NETWORKS:
            name = f"social_{key}"
            self.fields[name] = forms.CharField(
                required=False, label=label,
                initial=str(social.get(key) or ""),
                widget=forms.TextInput(attrs={
                    "class": "hb-form-control", "dir": "ltr",
                    "placeholder": "شناسه یا آدرس (اختیاری)",
                }),
            )

    _FA_AR_DIGITS = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )

    def clean_referrer_national_id(self):
        raw = (self.cleaned_data.get("referrer_national_id") or "").strip()
        if not raw:
            return ""  # اختیاری — حذف معرف مجاز است
        nid = raw.translate(self._FA_AR_DIGITS)
        if not (len(nid) == 10 and nid.isdigit()):
            raise forms.ValidationError("کد ملی معرف باید دقیقاً ۱۰ رقم (۰-۹) باشد.")
        # «کنترل کد ملی»: کدهای رزروشده هرگز نمی‌توانند کد ملی معرف باشند
        from .models import reserved_national_code

        if reserved_national_code(nid):
            raise forms.ValidationError(
                "این کد ملی رزرو شده است و نمی‌تواند به‌عنوان «کد ملی معرف» استفاده شود."
            )
        # کد ملی معرف باید متعلق به عضوی باشد که کد ملی‌اش را در پروفایل ثبت کرده است
        from .models import Profile

        ref_profile = (
            Profile.objects.select_related("user").filter(national_id=nid).first()
        )
        if ref_profile is None:
            raise forms.ValidationError(
                "کاربری با این کد ملی در حبیب‌هاب یافت نشد؛ کد ملیِ عضوی را وارد "
                "کنید که قبلاً ثبت‌نام کرده و کد ملی‌اش را ثبت کرده است."
            )
        if self.user is not None and ref_profile.user_id == self.user.id:
            raise forms.ValidationError("نمی‌توانید خودتان را معرفی کنید.")
        return nid

    def save(self, commit=True):
        # خودِ فیلدهای مدل (ایمیل، تلفن ثابت، تلفن شخصی) به‌صورت عادی ذخیره می‌شوند
        profile = super().save(commit=commit)
        # وب‌سایت و شبکه‌های اجتماعی در extra_data ذخیره می‌شوند
        extra = dict(profile.extra_data or {})
        website = (self.cleaned_data.get("website") or "").strip()
        if website:
            extra["website"] = website
        else:
            extra.pop("website", None)
        social = {
            key: (self.cleaned_data.get(f"social_{key}") or "").strip()
            for key, _ in SOCIAL_NETWORKS
        }
        social = {k: v for k, v in social.items() if v}
        if social:
            extra["social"] = social
        else:
            extra.pop("social", None)
        profile.extra_data = extra
        if commit:
            profile.save(update_fields=["extra_data", "updated_at"])
            # «کد ملی معرف» روی User نوشته می‌شود (قابل تغییر در همین بخش)
            if self.user is not None:
                nid = (self.cleaned_data.get("referrer_national_id") or "").strip()
                if (self.user.referrer_national_id or "") != nid:
                    self.user.referrer_national_id = nid or None
                    self.user.save(update_fields=["referrer_national_id"])
        return profile

    class Meta:
        model = Profile
        fields = ["email", "phone", "personal_phone"]
        widgets = {
            "email": forms.EmailInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "example@example.com",
            }),
            "phone": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "مثال: 021 12345678",
            }),
            "personal_phone": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr",
                "placeholder": "مثال: 0935 000 0000",
            }),
        }


class LocationForm(forms.ModelForm):
    """
    فرم موقعیت مکانی پروفایل («محل سکونت»). مختصات فقط با GPS دستگاه (دکمهٔ
    «دریافت GPS») به دست می‌آید؛ کشور همیشه «ایران» است و استان/شهرستان فقط از
    فهرست مرجعِ «اطلاعات مکانی» (جدول‌های ادمین) به‌صورت آبشاری انتخاب می‌شود.
    «استان»، «شهر/شهرستان» و «آدرس» الزامی‌اند؛ «کد پستی» اختیاری است و اگر
    وارد شود باید دقیقاً ۱۰ رقم باشد (ارقام فارسی/عربی خودکار به انگلیسی تبدیل
    می‌شوند). ذخیره با دکمهٔ «تأیید و ذخیره موقعیت» انجام می‌شود.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # «کشور» به‌صورت مخفی همراه فرم ارسال می‌شود؛ مقدارِ ذخیره‌شدهٔ پروفایل
        # (پیش‌فرض: ایران) حفظ می‌شود تا کشورهای غیرایرانیِ ثبت‌شده با GPS/تأیید
        # کاربر در ویرایش‌های بعدی هم‌چنان سر جای خود بمانند.
        self.initial["country"] = (self.instance.country or "").strip() or "ایران"
        # استان و شهر/شهرستان فقط از جدول مرجعِ «اطلاعات مکانی» انتخاب می‌شوند
        # (استان‌های ایران و شهرستان‌های هر استان؛ شهرستان‌ها گروه‌بندی‌شده‌اند تا
        # آبشار app.js گروهِ استانِ انتخابی را نشان دهد). مقدارِ انتخابی همان نام
        # رسمی فارسیِ رکورد مرجع است که در Profile ذخیره می‌شود.
        province_choices, city_groups, province_en, city_en = _reference_location_choices()
        # برچسب گزینه‌ها دوزبانه است (data-fa/data-en) تا با تغییر زبانِ رابط عوض شود
        province_widget = BilingualSelect(
            choices=province_choices,
            attrs={
                "class": "hb-form-control hb-form-select hb-loc-province",
                "data-bilingual": "1",
            },
        )
        province_widget.en_map = province_en
        province_widget.group_en_map = province_en
        self.fields["province"].widget = province_widget
        city_widget = BilingualSelect(
            choices=city_groups,
            attrs={
                "class": "hb-form-control hb-form-select hb-loc-city",
                "data-bilingual": "1",
            },
        )
        city_widget.en_map = city_en
        city_widget.group_en_map = province_en
        self.fields["city"].widget = city_widget
        self.fields["country"].widget = forms.HiddenInput()
        # فیلدهای الزامی: استان، شهر/شهرستان و آدرس (کد پستی اختیاری)
        for name, message in (
            ("province", "استان را از فهرست انتخاب کنید."),
            ("city", "شهر/شهرستان را از فهرست انتخاب کنید."),
            ("address", "آدرس (خیابان، کوچه، پلاک) را وارد کنید."),
        ):
            self.fields[name].required = True
            self.fields[name].error_messages["required"] = message
        self.fields["address"].widget.attrs.setdefault("placeholder", "خیابان، کوچه، پلاک")
        # «کد پستی» اختیاری است و جدا از محدودیت نویسهٔ خامِ مدل اعتبارسنجی می‌شود
        # تا ارقام فارسی/عربی (و جداکنندهٔ احتمالی) را بپذیرد؛ مقدارِ نهایی که
        # ذخیره می‌شود دقیقاً ۱۰ رقم انگلیسی است (clean_postal_code).
        self.fields["postal_code"] = forms.CharField(
            required=False,
            max_length=20,
            strip=True,
            widget=forms.TextInput(attrs={
                "class": "hb-form-control",
                "dir": "ltr",
                "inputmode": "numeric",
                "placeholder": "کد پستی (اختیاری) — فقط رقم",
            }),
        )

    # ارقام فارسی (۰-۹) و عربی (٠-٩) → انگلیسی برای کد پستی
    _FA_AR_DIGITS = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )

    def clean_postal_code(self):
        raw = (self.cleaned_data.get("postal_code") or "").strip()
        if not raw:
            return ""  # اختیاری
        # نرمال‌سازی ارقام فارسی/عربی به انگلیسی و حذف فاصله/خط تیره
        compact = re.sub(r"[\s\-]+", "", raw.translate(self._FA_AR_DIGITS))
        if not compact.isdigit() or len(compact) != 10:
            raise forms.ValidationError(
                "کد پستی باید دقیقاً ۱۰ رقم باشد (میان ۰ تا ۹، فارسی یا انگلیسی)."
            )
        return compact

    class Meta:
        model = Profile
        fields = [
            "address", "city", "province", "country", "postal_code",
            "latitude", "longitude",
        ]
        widgets = {
            "address": forms.TextInput(attrs={
                "class": "hb-form-control",
                "placeholder": "خیابان، کوچه، پلاک",
            }),
            # کشور/استان/شهرستان در __init__ ساخته می‌شوند: «کشور» مخفی با مقدار
            # ایران و استان/شهرستان فهرست‌های انتخابی از جدول مرجع.
            "postal_code": forms.TextInput(attrs={
                "class": "hb-form-control", "dir": "ltr", "maxlength": "10",
            }),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
        }



class FinancialInfoForm(forms.ModelForm):
    """فرم «اطلاعات مالی» پروفایل: فقط اعلام یک شماره شبا از بانک‌های ایرانی.

    کاربر فقط یک «شماره شبا» وارد می‌کند؛ نام بانک به‌صورت خودکار از کد سه‌رقمی
    داخل همان شبا تشخیص داده می‌شود (iban_bank_name) و بانک پیش‌فرض «بانک ملی
    ایران» است. شبا با همان موتور اعتبارسنجی کیف پول (normalize_iban) بررسی
    می‌شود تا مقداری که این‌جا ثبت می‌شود دقیقاً همانی باشد که هنگام فروش سکه
    برای واریز وجه استفاده می‌شود.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["iban"].widget.attrs.update({"dir": "ltr"})
        self.fields["iban"].help_text = (
            "فقط یک شماره شبا (۲۶ نویسه، با IR شروع می‌شود) کافی است؛ نام بانک "
            "به‌صورت خودکار از شبا تشخیص داده می‌شود (پیش‌فرض: بانک ملی ایران). "
            "کیف پول برای واریز وجه فروش سکه همین شبا را می‌خواند."
        )

    def clean_iban(self):
        value = (self.cleaned_data.get("iban") or "").strip()
        if not value:
            return ""
        # همان موتور اعتبارسنجی کیف پول؛ تا ثبت و مصرف کاملاً همراستا باشند
        from wallet.services import WalletError, normalize_iban

        try:
            return normalize_iban(value)
        except WalletError as exc:
            raise forms.ValidationError(str(exc))

    class Meta:
        model = Profile
        fields = ["iban"]
        widgets = {
            "iban": forms.TextInput(attrs={
                "class": "hb-form-control",
                "placeholder": "IR820170000000000000000017",
            }),
        }


class AvatarUploadForm(forms.ModelForm):
    """فرم آپلود عکس پروفایل"""

    class Meta:
        model = Profile
        fields = ['avatar']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'hb-form-control',
                'accept': 'image/*',
            }),
        }


class JobForm(forms.ModelForm):
    """
    فرم ثبت شغل: عنوان فقط از فهرست سلسله‌مراتبی ۵ لایه (jobs؛ لایهٔ ۵ = تخصص‌های مرتبط) انتخاب می‌شود؛
    «ورود دستی» حذف شده و در صورت نبودن شغل، کاربر از طریق تیکت به مدیر درخواست می‌دهد.
    شناسهٔ هر سطح در فیلدهای پنهان ارسال و در clean به یک زنجیرهٔ سازگار تبدیل می‌شود.
    عکس پروفایل شغل (فقط یکی) و مختصات GPS محل کار نیز در همین فرم ارسال می‌شوند؛
    GPS سمت ویو از مقادیر POST ست می‌شود (دکمهٔ «دریافت GPS» سمت کلاینت).
    """

    photo = forms.FileField(
        required=False,
        label="عکس پروفایل شغل",
        help_text="برای هر شغل فقط یک عکس پروفایل قابل ثبت است؛ بارگذاری مجدد، عکس قبلی را جایگزین می‌کند.",
        widget=forms.ClearableFileInput(attrs={
            "accept": "image/jpeg,image/png,image/gif,image/webp,image/bmp",
            "class": "hb-form-control hb-job-photo-input",
        }),
    )
    sector_id = forms.IntegerField(
        required=False, widget=forms.HiddenInput(attrs={"class": "hb-chain-field"})
    )
    industry_id = forms.IntegerField(
        required=False, widget=forms.HiddenInput(attrs={"class": "hb-chain-field"})
    )
    category_id = forms.IntegerField(
        required=False, widget=forms.HiddenInput(attrs={"class": "hb-chain-field"})
    )
    occupation_title_id = forms.IntegerField(
        required=False, widget=forms.HiddenInput(attrs={"class": "hb-chain-field"})
    )
    specialization_id = forms.IntegerField(
        required=False, widget=forms.HiddenInput(attrs={"class": "hb-chain-field"})
    )
    # عکس پروفایل این شغل (فقط یکی) که برای هر شغل تعریف‌شده‌ی کاربر مستقل است:
    # بارگذاریش تنها در بخش «ب) شغل آزاد» (مشغول بودن به مشخصاتِ وارون) است و به
    # صورت جداگانه از فایل‌های مدرک پروفایل ذخیره می‌شود در پوشهٔ DOCS/<کد ملی>/jobs/<order>/photo.
    job_photo = forms.FileField(
        required=False,
        label="عکس پروفایل شغلی (فقط یکی، مخصوص شغل این بخش)",
        help_text="برای هر شغل یک عکس پروفایل قابل ثبت است؛ بارگذاری مجدد، عکس قبلی را جایگزین می‌کند.",
        widget=forms.ClearableFileInput(attrs={
            "accept": "image/jpeg,image/png,image/gif,image/webp,image/bmp",
            "class": "hb-form-control hb-job-photo-input",
            "data-job-photo": "1",
        }),
    )
    # موقعیت مکلی شغلی (برای همین شغل): با تایپ از جدول مرجع انتخاب می‌شود و
    # مختصات GPS جدا ذخیره می‌گردد. پیش‌فرض «همان محل سکونت» است (Current Location)
    # — در آن حالت مقادیر از روی پروفایل کپی می‌شوند (سمت ویو).
    work_same_as_residence = forms.BooleanField(
        required=False,
        label="موقعیت مکانی شغلی همان محل سکونت من است (Current Location)",
        widget=forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
    )
    # موقعیت مکانیِ بخش «ب» (شغل آزاد): کاملاً مجزا از بخش «ج» (کارمندی). آدرس کامل
    # در بخش ب هم الزامی است (بررسی سمت ویو) ولی هیچ ارتباطی با آدرسِ بخش ج ندارد.
    free_address = forms.CharField(
        required=False,
        label="آدرس کامل محل کار (شغل آزاد)",
        widget=forms.TextInput(attrs={
            "class": "hb-form-control",
            "placeholder": "خیابان، کوچه، پلاک — محل فعالیت شغل آزاد",
        }),
    )
    free_country = forms.CharField(
        required=False,
        label="کشور محل کار (شغل آزاد)",
        widget=forms.HiddenInput(),
    )
    free_province = forms.CharField(
        required=False,
        label="استان محل کار (شغل آزاد)",
        widget=forms.Select(attrs={
            "class": "hb-form-control hb-form-select hb-loc-province",
            "data-bilingual": "1",
            "data-free-loc": "1",
        }),
    )
    free_city = forms.CharField(
        required=False,
        label="شهر / شهرستان محل کار (شغل آزاد)",
        widget=forms.Select(attrs={
            "class": "hb-form-control hb-form-select hb-loc-city",
            "data-bilingual": "1",
            "data-free-loc": "1",
        }),
    )
    # «بدون شغل / بیکار»: کاربر اعلام می‌کند فعلاً شغلی ندارد؛ در این حالت انتخاب
    # از فهرست سلسله‌مراتبی (و سایر جزئیات شغل) لازم نیست و غیرفعال می‌شود.
    is_unemployed = forms.BooleanField(
        required=False,
        label="بدون شغل / بیکار",
        widget=forms.CheckboxInput(attrs={"class": "hb-form-checkbox", "data-job-unemployed": "1"}),
    )
    # «نوع ثبت شغل»: فرم پروفایل به سه زیربخش الف/ب/ج تفکیک شده است. این فیلد
    # پنهان صرفاً اعلام می‌کند کاربر کدام مسیر را رفته تا سرور با آن هماهنگ باشد؛
    # الزامات اعتبارسنجی همچنان از خود فیلدها استخراج می‌شود.
    EMPLOYMENT_MODE_CHOICES = (
        ("", "—"),
        ("unemployed", "الف) بدون شغل / بیکار"),
        ("free", "ب) شغل آزاد (فهرست سلسله‌مراتبی)"),
        ("employee", "ج) شغل وابسته (کارمندی)"),
        ("both", "ب + ج — هم‌زمان"),
    )
    employment_mode = forms.ChoiceField(
        required=False,
        choices=EMPLOYMENT_MODE_CHOICES,
        widget=forms.HiddenInput(attrs={"class": "hb-chain-field"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        title_field = self.fields.get("title")
        if title_field:
            title_field.required = False
            title_field.widget.attrs["placeholder"] = (
                "در صورت انتخاب از فهرست، عنوان به‌صورت خودکار ثبت می‌شود"
            )
            # Django برای فیلدهای اجباری مدل، ویژگی required را مستقیم روی ویجت
            # می‌گذارد؛ آن را برمی‌داریم تا اعتبارسنجی مرورگر ارسال فرم را در حالت
            # «انتخاب از فهرست» مسدود نکند (عنوان هنگام انتخاب از کاتالوگ خالی است).
            # اعتبارسنجی نهایی همان‌طور که هست سمت سرور انجام می‌شود.
            title_field.widget.attrs.pop("required", None)
        # «تاریخ استخدام» با تقویم شمسی (مانند تاریخ تولد) انتخاب می‌شود:
        # فیلد واقعی مدل به ورودی پنهانِ میلادی تبدیل می‌شود و JS تقویم شمسیِ
        # مشترک مقدارش را پر می‌کند؛ اعتبارسنجی DateField سرور دست‌نخورده است.
        hire = self.fields.get("hire_date")
        if hire is not None:
            hire.widget = forms.HiddenInput(attrs={
                "class": "hb-chain-field", "data-hire-date-gregorian": "1",
            })
        # موقعیت مکانی شغلی: مثل «اطلاعات مکانی» پروفایل — کشور ایران ثابت است و
        # استان/شهرستان از فهرست مرجع (ادمین) به‌صورت آبشاری انتخاب می‌شود.
        province_choices, city_groups, province_en, city_en = _reference_location_choices()
        self.fields["work_country"].widget = forms.HiddenInput()
        self.initial.setdefault("work_country", "ایران")
        # استان و شهر/شهرستان در هر صورت (پیش‌فرض «همان محل سکونت» یا آدرس مجزا)
        # برای ذخیرهٔ شغل الزامی‌اند؛ required فقط جنبهٔ راهنمای مرورگر است — وقتی
        # فیلدها از محل سکونت کپی و غیرفعال می‌شوند ارسال نمی‌شوند و اعتبارسنجی نهایی
        # سمت ویو (پس از کپی از پروفایل) انجام می‌شود. برچسب گزینه‌ها دوزبانه است
        # (data-fa/data-en) تا با تغییر زبانِ رابط عوض شود.
        work_province_widget = BilingualSelect(
            choices=province_choices,
            attrs={
                "class": "hb-form-control hb-form-select hb-loc-province",
                "required": True,
                "data-bilingual": "1",
            },
        )
        work_province_widget.en_map = province_en
        work_province_widget.group_en_map = province_en
        self.fields["work_province"].widget = work_province_widget
        work_city_widget = BilingualSelect(
            choices=city_groups,
            attrs={
                "class": "hb-form-control hb-form-select hb-loc-city",
                "required": True,
                "data-bilingual": "1",
            },
        )
        work_city_widget.en_map = city_en
        work_city_widget.group_en_map = province_en
        self.fields["work_city"].widget = work_city_widget
        # بخش «ب» (شغل آزاد): همان آبشار استان ← شهر/شهرستان با کلاس‌های
        # hb-loc-province/hb-loc-city؛ «data-free-loc» این جفت را از جفتِ بخش «ج»
        # جدا می‌کند تا آبشار JS و پیش‌فرضِ «همان محل سکونت» فقط جفتِ خودش را
        # تنظیم کند. کشورِ شغل آزاد هم فعلاً ایران است (فیلد پنهان).
        self.fields["free_country"].initial = "ایران"
        free_province_widget = BilingualSelect(
            choices=province_choices,
            attrs={
                "class": "hb-form-control hb-form-select hb-loc-province",
                "data-bilingual": "1",
                "data-free-loc": "1",
            },
        )
        free_province_widget.en_map = province_en
        free_province_widget.group_en_map = province_en
        self.fields["free_province"].widget = free_province_widget
        free_city_widget = BilingualSelect(
            choices=city_groups,
            attrs={
                "class": "hb-form-control hb-form-select hb-loc-city",
                "data-bilingual": "1",
                "data-free-loc": "1",
            },
        )
        free_city_widget.en_map = city_en
        free_city_widget.group_en_map = province_en
        self.fields["free_city"].widget = free_city_widget

    # «در حالت ویرایش، زنجیرهٔ ذخیره‌شدهٔ شغل حفظ شود»: وقتی کاربر در حالت ویرایش
    # بدون تغییر فهرست، فقط فیلدهای دیگر را ویرایش می‌کند، JS مقادیر فیلدهای پنهان
    # زنجیره را از شغل ذخیره‌شده پر می‌کند و این نشانه را می‌فرستد؛ در این حالت
    # انتخاب قبلیِ شغل (حتی ناقص، مثلاً فقط حوزه) باطل نشود.
    keep_chain = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput(attrs={"class": "hb-chain-field"}),
    )

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned

        from jobs.models import leaf_label, resolve_selection

        # انتخاب فقط از فهرست سلسله‌مراتبی؛ «ورود دستی عنوان» حذف شده است و در صورت
        # نبودن شغل مورد نظر، کاربر با دکمهٔ «ارسال تیکت به مدیر» درخواستش را ثبت می‌کند.
        try:
            chain = resolve_selection(
                sector_id=cleaned.get("sector_id"),
                industry_id=cleaned.get("industry_id"),
                category_id=cleaned.get("category_id"),
                occupation_title_id=cleaned.get("occupation_title_id"),
                specialization_id=cleaned.get("specialization_id"),
            )
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc

        manual_title = str(cleaned.get("title") or "").strip()

        # «بدون شغل / بیکار» (زیربخش الف): زنجیرهٔ کاتالوگ لازم نیست؛ عنوان ثابت
        # ثبت می‌شود. اگر فیلد پنهان «نوع ثبت شغل» از قالب نیامده باشد (مثلاً
        # در جاهای دیگر که همین فرم رندر می‌شود) رفتار همان حالت قبلی است.
        mode = cleaned.get("employment_mode") or ""
        unemployed = bool(cleaned.get("is_unemployed")) or mode == "unemployed"
        # «حفظ زنجیرهٔ ذخیره‌شده» (فقط ویرایش): اگر کاربر در فهرست دست نزده باشد،
        # انتخاب قبلی شغل — حتی ناقص (مثلاً فقط حوزه) — حفظ می‌شود و حذف نمی‌گردد.
        keep = bool(cleaned.get("keep_chain")) and bool(self.instance and self.instance.pk)
        if keep and not any(chain.values()) and (self.instance.sector_id or self.instance.occupation_title_id):
            cleaned["_chain"] = {
                "sector": self.instance.sector,
                "industry": self.instance.industry,
                "category": self.instance.category,
                "occupation_title": self.instance.occupation_title,
                "specialization": self.instance.specialization,
            }
            if not manual_title:
                cleaned["title"] = self.instance.title
            return cleaned
        # انتخاب شغل از فهرست سلسله‌مراتبی (حوزه ← صنعت ← دسته ← عنوان ← تخصص‌های مرتبط)
        # همیشه بر «بدون شغل / بیکار» اولویت دارد: اگر کاربر هم‌زمان شغلی انتخاب
        # کرده و تیک «بدون شغل» را زده باشد، تیکِ آن خودکار برداشته می‌شود تا
        # شغل انتخابی به‌درستی ثبت شود (اولویت با انتخاب واقعی شغل است).
        if unemployed and any(chain.values()):
            unemployed = False
            cleaned["is_unemployed"] = False
            cleaned["employment_mode"] = "free"
        if unemployed:
            cleaned["is_unemployed"] = True
            cleaned["_chain"] = {k: None for k in chain}
            cleaned["title"] = "بدون شغل"
            return cleaned

        # حالت «ج» (شغل وابسته/کارمندی) بدون انتخاب از فهرست کاتالوگ مجاز است:
        # عنوان شغلی از «سازمان / شرکت» گرفته می‌شود (بدون پیام خطا). اگر کاربر
        # خودش از فهرست انتخاب کرده باشد، همان انتخاب (زنجیرهٔ کامل) برتری دارد.
        if mode == "employee" and not any(chain.values()):
            org = str(cleaned.get("organization") or "").strip()
            cleaned["_chain"] = {k: None for k in chain}
            cleaned["title"] = manual_title or ((org + " — کارمند") if org else "کارمند")
            return cleaned

        # وجود دست‌کم یک سطح الزامی است
        if not any(chain.values()):
            # ویرایش شغل قدیمیِ «ورود دستی» (بدون زنجیره): عنوان قبلی حفظ می‌شود
            if self.instance and self.instance.pk:
                if not manual_title:
                    cleaned["title"] = self.instance.title
                return cleaned
            self.add_error(
                None,
                "شغل را از فهرست سلسله‌مراتبی انتخاب کنید. اگر شغل مورد نظر شما در فهرست نیست، "
                "با دکمهٔ «ارسال تیکت به مدیر» درخواست خود را ثبت کنید.",
            )
            return cleaned

        cleaned["_chain"] = chain
        if not manual_title:
            cleaned["title"] = leaf_label(chain)
        return cleaned

    class Meta:
        model = Job
        fields = [
            "title",
            "organization",
            "department",
            "employment_type",
            "hire_date",
            "is_current",
            "is_unemployed",
            "field_of_activity",
            "skills",
            "free_address",
            "free_country",
            "free_province",
            "free_city",
            "work_same_as_residence",
            "work_country",
            "work_province",
            "work_city",
            "work_address",
            "photo",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "hb-form-control", "placeholder": "مثال: مدیر عامل", "required": True,
            }),
            "organization": forms.TextInput(attrs={
                "class": "hb-form-control", "placeholder": "نام سازمان / شرکت",
            }),
            "department": forms.TextInput(attrs={
                "class": "hb-form-control", "placeholder": "واحد سازمانی",
            }),
            "employment_type": forms.Select(attrs={
                "class": "hb-form-control hb-form-select",
            }),
            "hire_date": forms.DateInput(attrs={
                "class": "hb-form-control", "type": "date",
            }),
            "is_current": forms.CheckboxInput(attrs={
                "class": "hb-form-checkbox",
            }),
            "is_unemployed": forms.CheckboxInput(attrs={
                "class": "hb-form-checkbox", "data-job-unemployed": "1",
            }),
            "field_of_activity": forms.TextInput(attrs={
                "class": "hb-form-control", "placeholder": "حوزه فعالیت",
            }),
            "skills": forms.TextInput(attrs={
                "class": "hb-form-control", "placeholder": "با کاما جدا کنید",
            }),
            # کشور/استان/شهر محل کار: انتخاب‌گر جستجویی از جدول مرجع (مثل پروفایل)
            "work_country": forms.TextInput(attrs={
                "class": "hb-form-control hb-loc-autocomplete",
                "data-hb-loc-kind": "country", "autocomplete": "off",
            }),
            "work_province": forms.TextInput(attrs={
                "class": "hb-form-control hb-loc-autocomplete",
                "data-hb-loc-kind": "province", "autocomplete": "off",
            }),
            "work_city": forms.TextInput(attrs={
                "class": "hb-form-control hb-loc-autocomplete",
                "data-hb-loc-kind": "city", "autocomplete": "off",
            }),
            "work_address": forms.TextInput(attrs={
                "class": "hb-form-control",
                "placeholder": "خیابان، کوچه، پلاک (محل کار)",
            }),
        }



class JobStatusForm(forms.ModelForm):
    """فرم انتشار «استتوس» ۲۴ ساعته برای یک شغل (شبیه استتوس واتساپ).

    هر استتوس یک عکس (الزامی) + توضیح اختیاری است؛ انقضای ۲۴ ساعته سمت مدل
    (JobStatus.save) با «الان + ۲۴ ساعت» محاسبه می‌شود. فیلد expires_at از فرم
    حذف شده تا هنگام اعتبارسنجی، مقدارِ خودکارِ مدل بازنویسی نشود.
    """

    expires_at = forms.DateTimeField(required=False, widget=forms.HiddenInput)

    image = forms.FileField(
        label="عکس استتوس",
        required=True,
        error_messages={"required": "برای انتشار استتوس، انتخاب عکس الزامی است."},
        widget=forms.ClearableFileInput(attrs={
            "accept": "image/jpeg,image/png,image/gif,image/webp,image/bmp",
            "class": "hb-form-control",
        }),
    )

    class Meta:
        model = JobStatus
        fields = ["image", "caption"]
        widgets = {
            "caption": forms.TextInput(attrs={
                "class": "hb-form-control",
                "placeholder": "توضیح استتوس (اختیاری)",
                "maxlength": 200,
            }),
        }


class DocsSectionForm(forms.Form):
    """فرم بخش «مدارک و فایل‌ها»ی پروفایل — آپلود مستقل با دکمهٔ ذخیرهٔ خودش.

    برای هر نوع مدرک یک FileField اختیاری دارد (شناسه‌ها hok-doc_*) و فرمت
    مجاز هر فیلد را مطابق نوع مدرک کنترل می‌کند:
    - تصویر پرسنلی/امضا/کارت ملی/گذرنامه/مدارک تحصیلی: فرمت عکس
    - رزومه/قراردادها: Word یا PDF
    - فایل‌های ضمیمه: هر فرمتی
    """

    IMAGE_ACCEPT = "image/jpeg,image/png,image/gif,image/webp,image/bmp"
    DOC_ACCEPT = ("application/pdf," 
                  "application/msword," 
                  "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    personal_photo = forms.FileField(
        label="تصویر پرسنلی", required=False,
        help_text=UserDocument.TYPE_HINTS["personal_photo"],
        widget=forms.ClearableFileInput(attrs={"accept": IMAGE_ACCEPT, "class": "hb-doc-input"}),
    )
    signature = forms.FileField(
        label="امضا", required=False,
        help_text=UserDocument.TYPE_HINTS["signature"],
        widget=forms.ClearableFileInput(attrs={"accept": IMAGE_ACCEPT, "class": "hb-doc-input"}),
    )
    national_card = forms.FileField(
        label="کارت ملی", required=False,
        help_text=UserDocument.TYPE_HINTS["national_card"],
        widget=forms.ClearableFileInput(attrs={"accept": IMAGE_ACCEPT, "class": "hb-doc-input"}),
    )
    passport = forms.FileField(
        label="گذرنامه", required=False,
        help_text=UserDocument.TYPE_HINTS["passport"],
        widget=forms.ClearableFileInput(attrs={"accept": IMAGE_ACCEPT, "class": "hb-doc-input"}),
    )
    education_doc = forms.FileField(
        label="مدارک تحصیلی", required=False,
        help_text=UserDocument.TYPE_HINTS["education_doc"],
        widget=forms.ClearableFileInput(attrs={"accept": IMAGE_ACCEPT, "class": "hb-doc-input"}),
    )
    resume = forms.FileField(
        label="رزومه", required=False,
        help_text=UserDocument.TYPE_HINTS["resume"],
        widget=forms.ClearableFileInput(attrs={"accept": DOC_ACCEPT, "class": "hb-doc-input"}),
    )
    contract = forms.FileField(
        label="قراردادها", required=False,
        help_text=UserDocument.TYPE_HINTS["contract"],
        widget=forms.ClearableFileInput(attrs={"accept": DOC_ACCEPT, "class": "hb-doc-input"}),
    )
    attachment = forms.FileField(
        label="فایل‌های ضمیمه", required=False,
        help_text=UserDocument.TYPE_HINTS["attachment"],
        widget=forms.ClearableFileInput(attrs={"class": "hb-doc-input"}),
    )

    def __init__(self, *args, profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = profile

    def clean(self):
        cleaned = super().clean()
        profile = self.profile
        # ۱) تنها برای کاربرانی که کد ملی ثبت‌شده دارند فعال است
        if not profile or not (profile.national_id or "").strip():
            raise forms.ValidationError(
                "برای بارگذاری مدارک، ابتدا کد ملی را در بخش اطلاعات شخصی ثبت کنید."
            )
        # ۲) حداقل یک فایل انتخاب شده باشد
        if not any(cleaned.get(f) for f in cleaned):
            raise forms.ValidationError("هیچ فایلی برای بارگذاری انتخاب نشده است.")
        return cleaned

    def _check_extension(self, field_name, f):
        allowed = UserDocument.TYPE_EXTENSIONS.get(field_name)
        if not allowed:
            return
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in allowed:
            hint = UserDocument.TYPE_HINTS.get(field_name, "")
            raise forms.ValidationError(
                f"فرمت «{ext}» برای این مدرک مجاز نیست. {hint}"
            )

    def iter_files(self):
        """فایل‌های انتخاب‌شدهٔ معتبر به‌صورت (نام‌فیلد/نوع‌مدرک، فایل)."""
        for field_name in (
            "personal_photo", "signature", "national_card", "passport",
            "education_doc", "resume", "contract", "attachment",
        ):
            f = self.cleaned_data.get(field_name)
            if f:
                yield field_name, f

    def clean_personal_photo(self):
        f = self.cleaned_data["personal_photo"]
        if f:
            self._check_extension("personal_photo", f)
        return f

    def clean_signature(self):
        f = self.cleaned_data["signature"]
        if f:
            self._check_extension("signature", f)
        return f

    def clean_national_card(self):
        f = self.cleaned_data["national_card"]
        if f:
            self._check_extension("national_card", f)
        return f

    def clean_passport(self):
        f = self.cleaned_data["passport"]
        if f:
            self._check_extension("passport", f)
        return f

    def clean_education_doc(self):
        f = self.cleaned_data["education_doc"]
        if f:
            self._check_extension("education_doc", f)
        return f

    def clean_resume(self):
        f = self.cleaned_data["resume"]
        if f:
            self._check_extension("resume", f)
        return f

    def clean_contract(self):
        f = self.cleaned_data["contract"]
        if f:
            self._check_extension("contract", f)
        return f


# --------------------------------------------------------------------------- #
# بخش‌های آزاد/اختیاری پروفایل: اطلاعات سازمانی، مهارت‌ها، سوابق آموزشی
# همهٔ فیلدها اختیاری‌اند؛ مقادیر فاقد فیلد مدل در extra_data ذخیره می‌شوند.
# --------------------------------------------------------------------------- #
class _ProfileSectionForm(forms.Form):
    """پایهٔ بخش‌های اختیاری پروفایل — هر بخش با دکمهٔ ذخیرهٔ مستقل خودش.

    فیلدهای فاقد ستون در مدل، داخل extra_data زیرِ کلیدِ section_key ذخیره
    می‌شوند (بدون آلوده‌کردن کلیدهای سایر بخش‌ها) و مقدار خالی، کلید را حذف
    می‌کند تا extra_data شلوغ نشود.
    """

    section_key = ""  # کلید زیرِ extra_data — در زیرکلاس‌ها مقدار می‌گیرد

    def __init__(self, *args, profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = profile
        self._set_initial()

    def _set_initial(self):
        """مقادیر اولیه: فیلدهای مدل در زیرکلاس؛ بقیه از extra_data[section_key]."""
        if self.profile is None:
            return
        extra = (self.profile.extra_data or {}).get(self.section_key) or {}
        for name in self.fields:
            if name in extra and extra[name] not in (None, ""):
                self.initial[name] = extra[name]

    def extra_section_data(self, fields):
        """زیرِ‌دیکشنری تازهٔ extra_data برای این بخش (خالی‌ها حذف می‌شوند)."""
        sub = {}
        for name in fields:
            value = self.cleaned_data.get(name)
            if value in (None, ""):
                continue
            sub[name] = value
        return sub

    def apply(self):
        """مقادیر تأییدشده را روی پروفایل می‌نویسد — در زیرکلاس‌ها پیاده‌سازی می‌شود."""
        raise NotImplementedError


class OrganizationSectionForm(_ProfileSectionForm):
    """بخش «اطلاعات سازمانی» — همهٔ فیلدها آزاد و اختیاری.

    شماره پرسنلی، کد سازمانی، وضعیت همکاری و تاریخ شروع همکاری ستونِ مدل دارند؛
    مدیر مستقیم، محل خدمت، شعبه و گروه کاری در extra_data["organization"]
    ذخیره می‌شوند.
    """

    section_key = "organization"

    COOP_STATUS_CHOICES = [
        ("", "— اختیاری —"),
        ("در حال همکاری", "در حال همکاری"),
        ("مرخصی", "مرخصی"),
        ("اتمام همکاری", "اتمام همکاری"),
    ]

    personnel_id = forms.CharField(
        required=False, label="شماره پرسنلی",
        widget=forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
    )
    org_code = forms.CharField(
        required=False, label="کد سازمانی",
        widget=forms.TextInput(attrs={"class": "hb-form-control", "dir": "ltr"}),
    )
    manager_name = forms.CharField(
        required=False, label="مدیر مستقیم",
        widget=forms.TextInput(attrs={"class": "hb-form-control"}),
    )
    workplace = forms.CharField(
        required=False, label="محل خدمت",
        widget=forms.TextInput(attrs={"class": "hb-form-control"}),
    )
    branch = forms.CharField(
        required=False, label="شعبه",
        widget=forms.TextInput(attrs={"class": "hb-form-control"}),
    )
    work_group = forms.CharField(
        required=False, label="گروه کاری",
        widget=forms.TextInput(attrs={"class": "hb-form-control"}),
    )
    cooperation_status = forms.ChoiceField(
        required=False, label="وضعیت همکاری",
        choices=COOP_STATUS_CHOICES,
        widget=forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
    )
    hire_date = forms.DateField(
        required=False, label="تاریخ شروع همکاری",
        widget=forms.DateInput(attrs={"class": "hb-form-control", "type": "date"}),
    )

    EXTRA_FIELDS = ("manager_name", "workplace", "branch", "work_group", "cooperation_status")

    def _set_initial(self):
        super()._set_initial()
        p = self.profile
        if p is None:
            return
        for name in ("personnel_id", "org_code", "hire_date"):
            value = getattr(p, name, None)
            if value not in (None, ""):
                self.initial[name] = value
        if (p.employment_type or "") in ("در حال همکاری", "مرخصی", "اتمام همکاری"):
            self.initial["cooperation_status"] = p.employment_type

    def apply(self):
        """ستون‌های مدل + extra_data["organization"] را به‌روز می‌کند (بدون save)."""
        p = self.profile
        p.personnel_id = self.cleaned_data.get("personnel_id") or ""
        p.org_code = self.cleaned_data.get("org_code") or ""
        p.employment_type = self.cleaned_data.get("cooperation_status") or ""
        p.hire_date = self.cleaned_data.get("hire_date") or None
        extra = dict(p.extra_data or {})
        sub = self.extra_section_data(self.EXTRA_FIELDS)
        if sub:
            extra[self.section_key] = sub
        else:
            extra.pop(self.section_key, None)
        p.extra_data = extra


class SkillsSectionForm(_ProfileSectionForm):
    """بخش «مهارت‌ها» — همهٔ فیلدها آزاد و اختیاری (ذخیره در extra_data["skills"])."""

    section_key = "skills"

    SKILL_LEVEL_CHOICES = [
        ("", "— اختیاری —"),
        ("مبتدی", "مبتدی"),
        ("متوسط", "متوسط"),
        ("پیشرفته", "پیشرفته"),
        ("خبره", "خبره"),
    ]

    technical_skills = forms.CharField(
        required=False, label="مهارت‌های فنی",
        widget=forms.Textarea(attrs={
            "class": "hb-form-control hb-form-textarea",
            "placeholder": "Python, Django, MySQL, React, Linux...",
        }),
    )
    soft_skills = forms.CharField(
        required=False, label="مهارت‌های نرم",
        widget=forms.Textarea(attrs={
            "class": "hb-form-control hb-form-textarea",
            "placeholder": "رهبری، مذاکره، مدیریت زمان...",
        }),
    )
    software = forms.CharField(
        required=False, label="نرم‌افزارهای مسلط",
        widget=forms.TextInput(attrs={"class": "hb-form-control"}),
    )
    programming_languages = forms.CharField(
        required=False, label="زبان‌های برنامه‌نویسی",
        widget=forms.TextInput(attrs={"class": "hb-form-control"}),
    )
    skill_level = forms.ChoiceField(
        required=False, label="سطح مهارت",
        choices=SKILL_LEVEL_CHOICES,
        widget=forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
    )
    career_interests = forms.CharField(
        required=False, label="علایق شغلی",
        widget=forms.TextInput(attrs={"class": "hb-form-control"}),
    )

    EXTRA_FIELDS = tuple()  # همهٔ فیلدها در extra_data می‌روند

    def extra_section_data(self, fields=None):
        return super().extra_section_data(self.fields)

    def apply(self):
        extra = dict(self.profile.extra_data or {})
        sub = self.extra_section_data()
        if sub:
            extra[self.section_key] = sub
        else:
            extra.pop(self.section_key, None)
        self.profile.extra_data = extra


class TrainingSectionForm(_ProfileSectionForm):
    """بخش «سوابق آموزشی» — همهٔ فیلدها آزاد و اختیاری (extra_data["training"])."""

    section_key = "training"

    classes = forms.CharField(
        required=False, label="کلاس‌ها",
        widget=forms.Textarea(attrs={"class": "hb-form-control hb-form-textarea"}),
    )
    webinars = forms.CharField(
        required=False, label="وبینارها",
        widget=forms.Textarea(attrs={"class": "hb-form-control hb-form-textarea"}),
    )
    certificates = forms.CharField(
        required=False, label="گواهینامه‌ها",
        widget=forms.TextInput(attrs={"class": "hb-form-control"}),
    )
    training_score = forms.IntegerField(
        required=False, label="امتیازات آموزشی",
        widget=forms.NumberInput(attrs={"class": "hb-form-control"}),
    )
    exams = forms.CharField(
        required=False, label="آزمون‌ها",
        widget=forms.TextInput(attrs={"class": "hb-form-control"}),
    )

    EXTRA_FIELDS = tuple()  # همهٔ فیلدها در extra_data می‌روند

    def extra_section_data(self, fields=None):
        return super().extra_section_data(self.fields)

    def apply(self):
        extra = dict(self.profile.extra_data or {})
        sub = self.extra_section_data()
        if sub:
            extra[self.section_key] = sub
        else:
            extra.pop(self.section_key, None)
        self.profile.extra_data = extra


class HealthSectionForm(_ProfileSectionForm):
    """بخش «اطلاعات سلامت» — فقط گروه خونی اجباری، بقیهٔ فیلدها آزاد و اختیاری.

    هیچ‌کدام از فیلدهای این بخش ستون مدل ندارند؛ همه در extra_data["health"]
    ذخیره می‌شوند و پاک‌کردن مقدارها کلید مربوطه را حذف می‌کند.
    """

    section_key = "health"

    BLOOD_GROUP_CHOICES = [
        ("", "— انتخاب کنید —"),
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
        ("O+", "O+"),
        ("O-", "O-"),
    ]
    INSURANCE_STATUS_CHOICES = [
        ("", "— اختیاری —"),
        ("دارد", "دارد"),
        ("ندارد", "ندارد"),
    ]

    blood_group = forms.ChoiceField(
        required=True, label="گروه خونی",
        choices=BLOOD_GROUP_CHOICES,
        widget=forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
        error_messages={"required": "انتخاب گروه خونی الزامی است."},
    )
    allergies = forms.CharField(
        required=False, label="حساسیت‌ها",
        widget=forms.TextInput(attrs={"class": "hb-form-control"}),
    )
    insurance_status = forms.ChoiceField(
        required=False, label="وضعیت بیمه درمان",
        choices=INSURANCE_STATUS_CHOICES,
        widget=forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
    )
    trusted_doctor = forms.CharField(
        required=False, label="پزشک معتمد",
        widget=forms.TextInput(attrs={"class": "hb-form-control"}),
    )
    emergency_conditions = forms.CharField(
        required=False, label="شرایط اضطراری",
        widget=forms.Textarea(attrs={"class": "hb-form-control hb-form-textarea"}),
    )

    EXTRA_FIELDS = (
        "allergies", "insurance_status", "trusted_doctor", "emergency_conditions",
    )

    def apply(self):
        """گروه خونی + سایر فیلدها را در extra_data["health"] می‌نویسد (بدون save)."""
        extra = dict(self.profile.extra_data or {})
        sub = self.extra_section_data(("blood_group",) + self.EXTRA_FIELDS)
        if sub:
            extra[self.section_key] = sub
        else:
            extra.pop(self.section_key, None)
        self.profile.extra_data = extra


class UiSettingsForm(_ProfileSectionForm):
    """بخش «تنظیمات شخصی سیستم» — فقط دو مورد قابل‌تغییر است:

    1) «تم نرم‌افزار»: تاریک (پیش‌فرض) / روشن
    2) «رنگ رابط کاربری»: رنگ تأکیدی (اکسنت) به‌جای طلاییِ پیش‌فرض

    سایر موارد (زبان، تقویم، منطقه زمانی، فونت، اعلان‌ها) پیش‌فرض و ثابت‌اند و
    اصلاً رندر نمی‌شوند. داده در extra_data["ui_settings"] ذخیره می‌شود.
    """

    section_key = "ui_settings"

    THEME_CHOICES = [
        ("dark", "تاریک"),
        ("light", "روشن"),
    ]

    DEFAULT_ACCENT = "#c9a227"

    ui_theme = forms.ChoiceField(
        required=False, choices=THEME_CHOICES, initial="dark", label="تم نرم‌افزار",
        widget=forms.Select(attrs={"class": "hb-form-control hb-form-select"}),
    )
    ui_accent = forms.CharField(
        required=False, initial=DEFAULT_ACCENT, label="رنگ رابط کاربری",
        widget=forms.TextInput(attrs={"type": "color", "class": "hb-form-control",
                                     "style": "height:48px;padding:4px;"}),
    )

    def clean_ui_accent(self):
        value = (self.cleaned_data.get("ui_accent") or "").strip()
        if value and not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise forms.ValidationError("فرمت رنگ معتبر نیست.")
        return value.lower() if value else value

    def apply(self):
        """تم و رنگ را در extra_data["ui_settings"] می‌نویسد (بدون save)."""
        extra = dict(self.profile.extra_data or {})
        sub = {}
        theme = self.cleaned_data.get("ui_theme") or "dark"
        if theme != "dark":  # پیش‌فرض (تاریک) ذخیره نمی‌شود
            sub["ui_theme"] = theme
        accent = self.cleaned_data.get("ui_accent") or self.DEFAULT_ACCENT
        if accent.lower() != self.DEFAULT_ACCENT:  # پیش‌فرض ذخیره نمی‌شود
            sub["ui_accent"] = accent.lower()
        if sub:
            extra[self.section_key] = sub
        else:
            extra.pop(self.section_key, None)  # برگشت به پیش‌فرض = حذف کلید
        self.profile.extra_data = extra


def profile_ui_appearance(profile):
    """(theme, accent) فعالِ کاربر برای تزریق به قالب‌ها (متای hb-appearance).

    پیش‌فرض: تم تاریک + طلایی برند — بدون هیچ تنظیم ذخیره‌شده.
    """
    sub = (profile.extra_data or {}).get("ui_settings") or {}
    theme = sub.get("ui_theme") if sub.get("ui_theme") in ("dark", "light") else "dark"
    accent = sub.get("ui_accent") or UiSettingsForm.DEFAULT_ACCENT
    return theme, accent
