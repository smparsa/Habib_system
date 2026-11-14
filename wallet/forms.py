"""فرم‌های کاربری کیف پول: خرید، فروش، انتقال سکه (با کد ملی گیرنده).

شبأ واریز وجهِ فروش در فرم پرسیده نمی‌شود؛ از «اطلاعات مالی» پروفایل کاربر
خوانده می‌شود (بخش مالی پروفایل تنها منبع اطلاعات بانکی است).

خطاهای اعتبارسنجی (مثل «حداقل خرید 10.00 سکه است.») روی خودِ فیلد نگه داشته
می‌شوند تا در همان فریم خرید/فروش/انتقال و زیر فیلدِ مربوطه نمایش داده شوند و
فوکوس مرورگر هم روی همان فیلد برود.
"""

from decimal import Decimal

from django import forms

from .models import WalletSetting
from .services import WalletError, normalize_national_id


class WalletFormMixin:
    """کلاس پایهٔ فرم‌های کیف پول.

    - حداقل/حداکثر مجاز را از تنظیمات ادمین روی «فیلد» اعمال می‌کند تا
      مرورگر (min/max بومی) و اعتبارسنجی Django با پیام فارسی همان خطا را
      بدهند و کاربر پیش از ارسال هم محدودیت را ببیند.
    - خطاها را از سطح فرم به سطح فیلد منتقل می‌کند تا قالب بتواند هر خطا را
      درست زیر فیلدِ همان فریم نمایش دهد و JS فوکوس را روی فیلد بگذارد.
    """

    amount_label = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._inject_amount_bounds()

    def _inject_amount_bounds(self):
        setting = WalletSetting.get()
        minimum = getattr(self, "min_setting_field", None)
        maximum = getattr(self, "max_setting_field", None)
        field = self.fields.get("coins")
        if field is None:
            return
        if minimum:
            min_coins = Decimal(str(getattr(setting, minimum)))
            field.min_value = min_coins
            field.error_messages["min_value"] = (
                f"حداقل {self.amount_label} {min_coins} سکه است."
            )
        if maximum:
            max_coins = Decimal(str(getattr(setting, maximum)))
            field.max_value = max_coins
            field.error_messages["max_value"] = (
                f"حداکثر {self.amount_label} {max_coins} سکه است."
            )

    def add_error(self, field, error):
        """هر خطای سطح فرم (non-field) را به فیلد «coins» منتقل می‌کند.

        چون تمام فرم‌های کیف پول یک فیلد مالی دارند، پیام‌هایی که در
        سرویس‌ها (مثل «حداقل خرید 10.00 سکه است.») به‌صورت WalletError بالا
        می‌آیند و ویو آن‌ها را به فرم می‌دهد، درست زیر فیلد تعداد سکه رندر
        می‌شوند و کاربر بدون جست‌وجو آن را می‌بیند.
        """
        if field is None and "coins" in self.fields:
            field = "coins"
        super().add_error(field, error)


class BuyForm(WalletFormMixin, forms.Form):
    amount_label = "خرید"
    min_setting_field = "min_buy_coins"
    max_setting_field = "max_buy_coins"

    coins = forms.DecimalField(
        label="تعداد سکه",
        min_value=Decimal("0.01"),
        max_digits=14,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "hb-form-control", "dir": "ltr", "step": "0.01",
                "placeholder": "مثال: 50", "id": "id_buy_coins",
                "autocomplete": "off",
            }
        ),
    )


class SellForm(WalletFormMixin, forms.Form):
    amount_label = "فروش"
    min_setting_field = "min_sell_coins"
    max_setting_field = "max_sell_coins"

    coins = forms.DecimalField(
        label="تعداد سکه",
        min_value=Decimal("0.01"),
        max_digits=14,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "hb-form-control", "dir": "ltr", "step": "0.01",
                "placeholder": "مثال: 20", "id": "id_sell_coins",
                "autocomplete": "off",
            }
        ),
    )


class TransferForm(WalletFormMixin, forms.Form):
    receiver_national_id = forms.CharField(
        label="کد ملی گیرنده",
        max_length=10,
        widget=forms.TextInput(
            attrs={
                "class": "hb-form-control", "dir": "ltr", "inputmode": "numeric",
                "placeholder": "مثال: 0013542419",
                "maxlength": "10", "id": "id_receiver_national_id",
                "autocomplete": "off",
            }
        ),
        help_text="کد ملی گیرنده را وارد کنید؛ نام او به‌صورت زنده نمایش داده می‌شود.",
    )
    coins = forms.DecimalField(
        label="تعداد سکه",
        min_value=Decimal("0.01"),
        max_digits=14,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "hb-form-control", "dir": "ltr", "step": "0.01",
                "placeholder": "مثال: 10", "id": "id_transfer_coins",
                "autocomplete": "off",
            }
        ),
    )
    note = forms.CharField(
        label="توضیح (اختیاری)",
        required=False,
        max_length=300,
        widget=forms.TextInput(
            attrs={
                "class": "hb-form-control",
                "placeholder": "مثال: تسویه حساب پروژه",
                "id": "id_transfer_note",
            }
        ),
    )

    def clean_receiver_national_id(self):
        value = self.cleaned_data.get("receiver_national_id") or ""
        try:
            return normalize_national_id(value)
        except WalletError as exc:
            raise forms.ValidationError(str(exc))
