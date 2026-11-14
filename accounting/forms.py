"""فرم‌های ماژول حسابداری — همه با استایل bootstrap-like و برچسب فارسی."""

from datetime import date as date_cls

from django import forms

from . import jalali
from .models import Account, AccountingUser, Cheque, FiscalYear


class FiscalYearForm(forms.Form):
    """تعریف سال مالی جدید — فقط سال شمسی؛ مرز سال و پلان خودکار ساخته می‌شود."""

    jalali_year = forms.IntegerField(
        label="سال شمسی (مثلاً ۱۴۰۵)",
        min_value=1300, max_value=1500,
        widget=forms.NumberInput(attrs={"class": "acc-input", "dir": "ltr", "placeholder": "1405"}),
    )
    is_default = forms.BooleanField(label="تنظیم به‌عنوان پیش‌فرض ورود", required=False,
                                    initial=True)

    def clean_jalali_year(self):
        y = self.cleaned_data["jalali_year"]
        if y < 1300 or y > 1500:
            raise forms.ValidationError("سال باید بین ۱۳۰۰ تا ۱۵۰۰ باشد.")
        return y


class AccountingLoginForm(forms.Form):
    """گام دوم ورود: نام کاربری و کلمه عبور مجزای حسابداری (مطابق تصویر ۲)."""

    username = forms.CharField(
        label="نام کاربری", max_length=100,
        widget=forms.TextInput(attrs={"class": "acc-input", "autofocus": "autofocus"}),
    )
    password = forms.CharField(
        label="کلمه عبور", max_length=128,
        widget=forms.PasswordInput(attrs={"class": "acc-input", "autofocus": "autofocus"}),
    )


class AccountForm(forms.ModelForm):
    """ایجاد حساب جدید (گروه/کل/معین/تفصیلی) زیر حساب والد انتخابی."""

    parent = forms.ModelChoiceField(
        label="حساب والد",
        queryset=Account.objects.none(),
        required=True,
        help_text="کد حساب جدید به‌صورت خودکار از والد ساخته می‌شود.",
    )

    class Meta:
        model = Account
        fields = ["name"]
        labels = {"name": "نام حساب"}

    def __init__(self, *args, fiscal_year=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Account.objects.none()
        if fiscal_year:
            qs = Account.objects.filter(fiscal_year=fiscal_year, is_active=True).order_by("code")
        self.fields["parent"].queryset = qs

    def clean(self):
        cleaned = super().clean()
        parent = cleaned.get("parent")
        name = (cleaned.get("name") or "").strip()
        if parent and name:
            if parent.level >= Account.LEVEL_DETAIL:
                raise forms.ValidationError("زیرِ حساب تفصیلی نمی‌توان حساب جدید ایجاد کرد.")
            if parent.fiscal_year.accounts.filter(name=name, parent=parent).exists():
                raise forms.ValidationError("حسابی با همین نام زیر همین والد وجود دارد.")
        return cleaned


class JDateField(forms.CharField):
    """فیلد تاریخ شمسی: ورودی کاربر (فارسی/لاتین) → datetime.date."""

    def to_python(self, value):
        if value in (None, ""):
            return None
        parsed = jalali.parse_jalali_str(value)
        if parsed is None:
            raise forms.ValidationError("تاریخ نامعتبر است. نمونهٔ صحیح: ۱۴۰۵/۰۷/۰۲")
        return parsed


class ChequeForm(forms.ModelForm):
    """ثبت چک دریافتی/پرداختی."""

    due_date = JDateField(label="سررسید")
    issue_date = JDateField(label="تاریخ صدور", required=False)

    class Meta:
        model = Cheque
        fields = ["direction", "number", "sayad_id", "amount", "due_date", "issue_date",
                  "bank_name", "branch", "account_number", "party_name", "description"]
        labels = {
            "direction": "نوع چک",
            "number": "شماره چک",
            "sayad_id": "شناسه صیاد (۱۶ رقمی)",
            "amount": "مبلغ (ریال)",
            "due_date": "سررسید",
            "issue_date": "تاریخ صدور",
            "bank_name": "بانک",
            "branch": "شعبه",
            "account_number": "شماره حساب",
            "party_name": "طرف حساب",
            "description": "شرح",
        }
        widgets = {
            "amount": forms.NumberInput(attrs={"class": "acc-input", "dir": "ltr", "min": "0"}),
            "due_date": forms.TextInput(attrs={"class": "acc-input", "dir": "ltr",
                                               "placeholder": "۱۴۰۵/۰۷/۰۲ یا 1405/07/02"}),
            "issue_date": forms.TextInput(attrs={"class": "acc-input", "dir": "ltr",
                                                 "placeholder": "۱۴۰۵/۰۷/۰۲ یا 1405/07/02"}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= 0:
            raise forms.ValidationError("مبلغ چک باید مثبت باشد.")
        return amount
