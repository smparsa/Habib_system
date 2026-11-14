"""اعتبارسنجی پیوست‌های تیکت — سایز/پسوند/MIME. (ویروس‌یاب در readiness است.)"""

import mimetypes
import os

from django.conf import settings

from .exceptions import AttachmentError

MAX_MB = getattr(settings, "TICKET_UPLOAD_MAX_MB", 10)
ALLOWED_MIME = getattr(settings, "TICKET_ATTACHMENT_ALLOWED", ())
EXT_ALLOWED = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".doc", ".docx",
    ".xls", ".xlsx", ".txt", ".csv", ".zip",
}


def validate_upload(upload):
    if upload is None:
        raise AttachmentError("فایلی انتخاب نشده است.")
    if upload.size <= 0:
        raise AttachmentError("فایل خالی است.")
    if upload.size > MAX_MB * 1024 * 1024:
        raise AttachmentError(f"حجم فایل نباید بیشتر از {MAX_MB} مگابایت باشد.")
    ext = os.path.splitext(upload.name or "")[1].lower()
    if ext and ext not in EXT_ALLOWED:
        raise AttachmentError("این نوع فایل مجاز نیست.")
    mime = (upload.content_type or mimetypes.guess_type(upload.name or "")[0] or "").lower()
    if mime and mime not in ALLOWED_MIME:
        raise AttachmentError("نوع MIME فایل مجاز نیست.")
    return True
