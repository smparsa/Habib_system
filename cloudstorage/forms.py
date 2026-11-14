"""فرم ادمین تنظیمات فضای ذخیره‌سازی ابری."""
from django import forms

from .models import StorageSettings


class StorageSettingsForm(forms.ModelForm):
    """ویرایش سقف‌ها، تعرفه‌ها و سیاست‌های ماژول از پنل مدیریت."""

    class Meta:
        model = StorageSettings
        fields = "__all__"
        widgets = {
            "module_enabled": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
            "folder_upload_enabled": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
            "gallery_enabled": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
            "sync_enabled": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
            "archive_enabled": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
            "keep_deleted_files": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
            "two_way_delete_enabled": forms.CheckboxInput(attrs={"class": "hb-form-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, (forms.NumberInput, forms.TextInput)) and "class" not in field.widget.attrs:
                field.widget.attrs.setdefault("class", "hb-form-control")
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("class", "hb-form-control")