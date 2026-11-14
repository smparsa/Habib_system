"""استوریج فایل‌های فضای ابری — ریشهٔ پویا و خارج از MEDIA_ROOT.

مسیر فیزیکی: DOCS_ROOT/cloud/{storage_key}/{folder_uid}/{مسیر نسبی فایل}
- ریشه همیشه از تنظیمات لحظه‌ای خوانده می‌شود (مثل UserDocsStorage في accounts).
- هیچ URL عمومی وجود ندارد؛ سرو کردن فقط از ویوهای کنترل‌شده انجام می‌شود.
"""
import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from pathlib import Path
from django.utils.functional import cached_property


def cloud_storage_root():
    """ریشهٔ ذخیرهٔ فضای ابری: {DOCS_ROOT}/cloud به‌صورت pathlib.Path."""
    docs_root = Path(getattr(settings, "DOCS_ROOT", Path(settings.BASE_DIR) / "Docs"))
    return docs_root / "cloud"


def cloud_upload_path(instance, filename):
    """مسیر نسبی فایل زیر ریشه: {storage_key}/{folder_uid}/{rel_path}."""
    rel = getattr(instance, "rel_path", "") or instance.name
    return f"{instance.folder.account.storage_key}/{instance.folder.uid}/{rel}"


class CloudStorageFilesStorage(FileSystemStorage):
    """استوریج فایل‌های فضای ابری با ریشهٔ پویا (مثل UserDocsStorage پروژه)."""

    @property
    def base_location(self):
        return str(cloud_storage_root())

    @property
    def location(self):
        return os.path.abspath(self.base_location)


def cloud_storage():
    return CloudStorageFilesStorage()


def archives_root():
    """ریشهٔ آرشیوهای موقت ZIP (خارج از MEDIA_ROOT)."""
    return cloud_storage_root() / "_archives"


def archive_path_for(token):
    """مسیر فیزیکی آرشیو یک ArchiveJob بر اساس توکن امن."""
    return archives_root() / f"{token}.zip"
