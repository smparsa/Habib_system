"""موتور اعلان‌ها — رابط کانال + پیاده‌سازی‌ها.

هر رویداد → کانال‌هایی که گیرنده خواسته (UserNotificationPreferences) → ردیف
TicketNotification. ارائه‌دهنده‌ها (provider) سخت‌کد نیستند؛ هر کانال کلاس خودش
را دارد. ایمیل از طریق email backend فعال (پیش‌فرض console) ارسال می‌شود؛
SMS/Push در این محیط stub با لاگ هستند و برای worker آینده آماده‌اند.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from . import constants as C
from .models import TicketNotification, UserNotificationPreferences

logger = logging.getLogger("tickets.notifications")


def prefs_for(user):
    obj, _ = UserNotificationPreferences.objects.get_or_create(user=user)
    return obj


class Channel:
    name = C.CH_INAPP

    def deliver(self, notification):
        raise NotImplementedError


class InAppChannel(Channel):
    name = C.CH_INAPP

    def deliver(self, notification):
        notification.status = "sent"
        notification.sent_at = timezone.now()
        notification.save(update_fields=["status", "sent_at"])


class EmailChannel(Channel):
    name = C.CH_EMAIL

    def deliver(self, notification):
        user = notification.recipient
        email = getattr(user, "email", "") or ""
        if not email and hasattr(user, "profile") and user.profile:
            email = user.profile.email or ""
        if not email:
            notification.status = "failed"
            notification.save(update_fields=["status"])
            return
        try:
            send_mail(
                subject=notification.title,
                message=notification.body,
                from_email=settings.DEFAULT_FROM_EMAIL
                if hasattr(settings, "DEFAULT_FROM_EMAIL") else "no-reply@habibhub.local",
                recipient_list=[email],
                fail_silently=True,
            )
            notification.status = "sent"
            notification.sent_at = timezone.now()
        except Exception as exc:  # noqa: BLE001
            logger.warning("email delivery failed %s: %s", user, exc)
            notification.status = "failed"
        notification.save(update_fields=["status", "sent_at"])


class SmsChannel(Channel):
    name = C.CH_SMS

    def deliver(self, notification):
        # ارائه‌دهندهٔ پیامک هنوز متصل نیست؛ معماری آماده است (task جدا).
        logger.info("SMS stub for %s: %s", notification.recipient, notification.title[:60])
        notification.status = "failed"  # تا اتصال provider
        notification.save(update_fields=["status"])


class PushChannel(Channel):
    name = C.CH_PUSH

    def deliver(self, notification):
        logger.info("Push stub for %s: %s", notification.recipient, notification.title[:60])
        notification.status = "failed"
        notification.save(update_fields=["status"])


CHANNELS = {
    C.CH_INAPP: InAppChannel,
    C.CH_EMAIL: EmailChannel,
    C.CH_SMS: SmsChannel,
    C.CH_PUSH: PushChannel,
}


def enqueue(users, event, title, body="", ticket=None, message=None, actor=None):
    """ساخت ردیف اعلان برای کاربران طبق کانال‌های فعال و ارسال فوری (ایمیل/درون‌برنامه)."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    created = []
    for user in users:
        if isinstance(user, User) is False and hasattr(user, "pk"):
            user = user.user if hasattr(user, "user") else None
        if user is None or not getattr(user, "is_active", False):
            continue
        prefs = prefs_for(user)
        for channel_name in C.CHANNELS:
            if not prefs.wants(event, channel_name):
                continue
            notif = TicketNotification.objects.create(
                recipient=user, ticket=ticket, message=message,
                event=event, channel=channel_name, title=title, body=body,
            )
            created.append(notif)
            CHANNELS[channel_name]().deliver(notif)
    return created


def notify_participants(ticket, event, title, body="", exclude=(), message=None, actor=None):
    """اعلان به همهٔ گیرندگان تیکت (به‌جز exclude) — شامل فرستنده/کارکنانِ شرکت‌کننده."""
    users = ticket.recipients.exclude(user__in=list(exclude) or []).select_related("user")
    return enqueue([r.user for r in users], event, title, body, ticket=ticket,
                   message=message, actor=actor)
