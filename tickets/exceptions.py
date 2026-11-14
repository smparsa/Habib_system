class TicketError(Exception):
    """خطای پایهٔ دامنهٔ تیکت."""


class PermissionDenied(TicketError):
    """دسترسی شیء‌محور رد شد."""


class StateError(TicketError):
    """انتقال وضعیت نامعتبر در گردش کار."""


class TargetingError(TicketError):
    """قواعد هدف‌گیری نامعتبر."""


class AttachmentError(TicketError):
    """پیوست نامعتبر/غیرمجاز."""
