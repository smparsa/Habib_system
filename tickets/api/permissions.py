from rest_framework.permissions import BasePermission, SAFE_METHODS

from tickets.permissions import can_manage, can_view


class TicketAccess(BasePermission):
    """خواندن: شرکت‌کننده یا کارکنِ دارای مجوز. تغییر: نقش/شیء بررسی می‌شود."""

    message = "دسترسی به این تیکت مجاز نیست."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in SAFE_METHODS:
            return can_view(user, obj)
        if getattr(view, "action", None) in ("reply",):
            from tickets.permissions import can_reply

            return can_reply(user, obj)
        return can_manage(user, obj)


class StaffOnly(BasePermission):
    message = "فقط کارکنان مجاز هستند."

    def has_permission(self, request, view):
        from tickets.permissions import is_staff_user

        return bool(request.user and request.user.is_authenticated and is_staff_user(request.user))
