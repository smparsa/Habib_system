# -*- coding: utf-8 -*-
"""ساخت خودکار پروفایل برای هر کاربر تازه.

`Profile` با `User` رابطهٔ یک‌به‌یک دارد (user_id NOT NULL UNIQUE) و ویوها
بلافاصله بعد از ساخت کاربر `user.profile` را می‌خوانند؛ بدون این سیگنال،
هر ثبت‌نام تازه با `User has no profile` کرش می‌کند.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="accounts.User")  # noqa: unused-argument
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return
    from accounts.models import Profile

    Profile.objects.get_or_create(user=instance)
