from django import forms
from .utils import to_english_digits

CALENDAR_CHOICES = (
    ('shamsi', 'شمسی (جلالی)'),
    ('ghamari', 'قمری (هجری)'),
    ('miladi', 'میلادی (گریگوری)'),
)


class DateConvertForm(forms.Form):
    calendar_type = forms.ChoiceField(
        choices=CALENDAR_CHOICES,
        label='نوع تقویم ورودی',
        widget=forms.Select(attrs={'class': 'hh-select', 'id': 'id_calendar_type'})
    )
    year = forms.CharField(widget=forms.HiddenInput(attrs={'id': 'id_year'}))
    month = forms.CharField(widget=forms.HiddenInput(attrs={'id': 'id_month'}))
    day = forms.CharField(widget=forms.HiddenInput(attrs={'id': 'id_day'}))

    def clean_year(self):
        value = to_english_digits(self.cleaned_data['year'])
        try:
            value = int(value)
        except ValueError:
            raise forms.ValidationError('سال نامعتبر است')
        if value < 1:
            raise forms.ValidationError('سال نامعتبر است')
        return value

    def clean_month(self):
        value = to_english_digits(self.cleaned_data['month'])
        try:
            value = int(value)
        except ValueError:
            raise forms.ValidationError('ماه نامعتبر است')
        if not (1 <= value <= 12):
            raise forms.ValidationError('ماه باید بین ۱ تا ۱۲ باشد')
        return value

    def clean_day(self):
        value = to_english_digits(self.cleaned_data['day'])
        try:
            value = int(value)
        except ValueError:
            raise forms.ValidationError('روز نامعتبر است')
        if not (1 <= value <= 31):
            raise forms.ValidationError('روز باید بین ۱ تا ۳۱ باشد')
        return value

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('year') or not cleaned_data.get('month') or not cleaned_data.get('day'):
            raise forms.ValidationError('لطفاً یک تاریخ از تقویم انتخاب کنید')
        return cleaned_data