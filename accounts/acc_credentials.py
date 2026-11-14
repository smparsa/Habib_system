"""اعتبارنامهٔ مجزای ماژول حسابداری: تعریف از «پروفایل من ← اطلاعات امنیتی».

این اعتبارنامه فقط و فقط برای ورود به ماژول حسابداری استفاده می‌شود و هیچ
تأثیری روی ورود اصلی سایت (شماره موبایل) ندارد. رمز با هش استاندارد جنگو
(PBKDF2-SHA256 + salt) ذخیره می‌شود و با همان اعتبارسنج‌های رسمی جنگو
(AUTH_PASSWORD_VALIDATORS) سنجیده می‌شود.
"""

import re

from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.db.models.functions import Lower
from django.utils import timezone

from .models import User

# نام کاربری حسابداری: فقط ترکیب حروف لاتین و اعداد (بدون فاصله/نقطه/خط تیره و ...).
ACC_USERNAME_RE = re.compile(r"^[A-Za-z0-9]+$")


def normalize_acc_username(raw):
    """نرمال‌سازی نام کاربری حسابداری: ارقام فارسی/عربی → لاتین + تبدیل به حروف کوچک.

    تطبیق نام کاربری در سراسر سیستم به بزرگی/کوچکی حروف حساس نیست؛ بنابراین
    مقدار ذخیره‌شده همیشه به شکل حروف کوچک است (مثلاً «Ali1284» → «ali1284»)،
    ولی کاربر می‌تواند هر ترکیبی از بزرگ/کوچک را تایپ کند.
    """
    text = (raw or "").strip()
    # ارقام فارسی ۰-۹ و عربی ٠-٩ → 0-9
    text = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    return text.lower()


class AccCredentialsForm(forms.Form):
    """تعریف/تغییر نام کاربری و کلمه عبور حسابداری.

    - username: ۳ تا ۳۰ کاراکتر، فقط ترکیب حروف لاتین و اعداد؛ بدون حساسیت
      به بزرگی/کوچکی حروف (ذخیره همیشه به‌صورت حروف کوچک انجام می‌شود).
    - password: حداقل ۸ کاراکتر + validators رسمی جنگو (شباهت به مشخصات،
      رایج‌بودن، تمام‌عددی‌بودن).
    - confirm: باید با password برابر باشد.
    - هنگام تغییر رمز، رمز فعلی نیز باید تأیید شود.
    """

    username = forms.CharField(
        label="نام کاربری حسابداری",
        min_length=3, max_length=30,
        widget=forms.TextInput(attrs={
            "class": "hb-form-control", "dir": "ltr", "autocomplete": "off",
            "placeholder": "مثلاً ali1284",
        }),
        help_text="۳ تا ۳۰ کاراکتر؛ فقط ترکیب حروف انگلیسی و اعداد "
                  "(بدون فاصله، نقطه و سایر کاراکترهای خاص؛ بزرگ/کوچک یکسان است).",
    )
    current_password = forms.CharField(
        label="کلمه عبور فعلی حسابداری",
        required=False,
        widget=forms.PasswordInput(attrs={
            "class": "hb-form-control", "dir": "ltr", "autocomplete": "current-password",
        }),
        help_text="فقط هنگام تغییرِ اعتبارنامهٔ قبلاً تعریف‌شده الزامی است.",
    )
    password = forms.CharField(
        label="کلمه عبور",
        widget=forms.PasswordInput(attrs={
            "class": "hb-form-control", "dir": "ltr", "autocomplete": "new-password",
        }),
    )
    confirm_password = forms.CharField(
        label="تکرار کلمه عبور",
        widget=forms.PasswordInput(attrs={
            "class": "hb-form-control", "dir": "ltr", "autocomplete": "new-password",
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    # ---------- اعتبارسنجی ----------
    def clean_username(self):
        username = normalize_acc_username(self.cleaned_data.get("username"))
        if not ACC_USERNAME_RE.fullmatch(username or ""):
            raise ValidationError(
                "نام کاربری حسابداری فقط می‌تواند ترکیبی از حروف انگلیسی و اعداد باشد "
                "(بدون فاصله، نقطه و سایر کاراکترهای خاص)."
            )
        # یکتایی به بزرگی/کوچکی حساس نیست (مقایسه روی نسخهٔ حروف‌کوچک)؛
        # مقدار ذخیره‌شده همیشه حروف کوچک است.
        qs = User.objects.annotate(acc_username_lower=Lower("acc_username")).filter(
            acc_username_lower=username
        )
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise ValidationError("این نام کاربری قبلاً توسط کاربر دیگری انتخاب شده است.")
        return username

    def clean(self):
        cleaned = super().clean()
        user = self.user
        if user is None:
            return cleaned

        password = cleaned.get("password") or ""
        confirm = cleaned.get("confirm_password") or ""
        current = cleaned.get("current_password") or ""

        # ۱) تغییر اعتبارنامهٔ موجود → رمز فعلی الزامی است
        if user.has_acc_credentials() and not user.check_acc_password(current):
            self.add_error("current_password",
                           "برای تغییر اعتبارنامه، کلمه عبور فعلی حسابداری را صحیح وارد کنید.")

        # ۲) تأیید رمز
        if password != confirm:
            self.add_error("confirm_password", "کلمه عبور و تکرار آن یکسان نیستند.")

        # ۳) validators رسمی جنگو (طول/رایج/عددی/شباهت به مشخصات کاربر)
        try:
            password_validation.validate_password(password, user=self.user)
        except ValidationError as exc:
            self.add_error("password", list(exc.messages))
        else:
            # حداقل طول بیشتر برای این رمز حساس (۸ کاراکتر)
            if len(password) < 8:
                self.add_error("password", "کلمه عبور باید حداقل ۸ کاراکتر باشد.")

        # نام کاربری نباید شمارهٔ موبایل خود کاربر باشد (جلوگیری از گمراهی)
        username = cleaned.get("username")
        if username and username == normalize_acc_username(user.mobile_number):
            self.add_error("username", "نام کاربری حسابداری نمی‌تواند شمارهٔ موبایل شما باشد.")

        return cleaned

    def apply(self):
        """ذخیرهٔ اعتبارنامه: هش رمز + ثبت زمان تغییر. خروجی: کاربر به‌روزشده."""
        user = self.user
        user.acc_username = self.cleaned_data["username"]
        user.set_acc_password(self.cleaned_data["password"])
        user.acc_password_updated_at = timezone.now()
        user.save(update_fields=["acc_username", "acc_password", "acc_password_updated_at"])
        return user


class AccPasswordResetForm(forms.Form):
    """ریست کلمهٔ عبور حسابداری (فراموش‌شده) — بدون نیاز به کلمهٔ عبور فعلی.

    «به چه درد می‌خورد؟» — کلمهٔ عبور هش‌شده ذخیره می‌شود و بازیابی‌ناپذیر است؛
    برای کاربری که رمزش را فراموش کرده، تنها راه همین بازنشانی است: رمز جدید
    را از خود کاربر می‌گیریم (تکرار + validators رسمی جنگو) و هش قبلی را دور
    می‌ریزیم. نام کاربری دست‌نخورده می‌ماند.
    فقط برای کاربرِ دارای اعتبارنامه کاربرد دارد (دکمهٔ فرم فقط در همین حالت
    رندر می‌شود و ویو هم گارد دارد).
    """

    password = forms.CharField(
        label="کلمه عبور جدید",
        widget=forms.PasswordInput(attrs={
            "class": "hb-form-control", "dir": "ltr", "autocomplete": "new-password",
        }),
    )
    confirm_password = forms.CharField(
        label="تکرار کلمه عبور جدید",
        widget=forms.PasswordInput(attrs={
            "class": "hb-form-control", "dir": "ltr", "autocomplete": "new-password",
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned = super().clean()
        user = self.user
        if user is None:
            return cleaned
        if not user.has_acc_credentials():
            raise ValidationError("شما هنوز اعتبارنامهٔ حسابداری تعریف نکرده‌اید.")
        password = cleaned.get("password") or ""
        confirm = cleaned.get("confirm_password") or ""
        if password != confirm:
            self.add_error("confirm_password", "کلمه عبور و تکرار آن یکسان نیستند.")
        try:
            password_validation.validate_password(password, user=user)
        except ValidationError as exc:
            self.add_error("password", list(exc.messages))
        else:
            if len(password) < 8:
                self.add_error("password", "کلمه عبور باید حداقل ۸ کاراکتر باشد.")
        return cleaned

    def apply(self):
        """بازنشانی: هش جدید + زمان تغییر؛ نام کاربری دست‌نخورده. خروجی: کاربر به‌روزشده."""
        user = self.user
        user.set_acc_password(self.cleaned_data["password"])
        user.acc_password_updated_at = timezone.now()
        user.save(update_fields=["acc_password", "acc_password_updated_at"])
        return user
