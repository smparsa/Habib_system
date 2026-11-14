"""فرم‌های سادهٔ تیکت — اعتبارسنجی ورودیِ کاربر در لایهٔ فرم/ویو پیش از سرویس."""

from django import forms

from . import constants as C
from .models import TicketCategory


class CreateTicketForm(forms.Form):
    subject = forms.CharField(max_length=200, required=True,
                              error_messages={"required": "موضوع الزامی است."})
    description = forms.CharField(widget=forms.Textarea, required=False)
    priority = forms.ChoiceField(choices=[(p, C.PRIORITY_LABELS[p]) for p in C.PRIORITIES],
                                 initial="normal")
    category = forms.ChoiceField(required=False, choices=[])
    due_date = forms.DateField(required=False)

    def __init__(self, *args, **kwargs):
        # فهرست «انواع تیکت» هنگام ساخت فرم خوانده می‌شود (نه هنگام import ماژول)
        # تا سیستم‌چک‌ها و اجرای تست روی دیتابیسِ خالی/تازه‌ساخته نشکند.
        super().__init__(*args, **kwargs)
        self.fields["category"].choices = [("", "بدون دسته")] + [
            (c.code, c.name_fa)
            for c in TicketCategory.objects.filter(is_active=True)
        ]

    def clean_category(self):
        val = self.cleaned_data.get("category") or ""
        return val if val != "بدون دسته" else ""


class RatingForm(forms.Form):
    stars = forms.IntegerField(min_value=1, max_value=5)
    response_quality = forms.IntegerField(min_value=1, max_value=5, required=False)
    resolution_quality = forms.IntegerField(min_value=1, max_value=5, required=False)
    comment = forms.CharField(widget=forms.Textarea, required=False)
