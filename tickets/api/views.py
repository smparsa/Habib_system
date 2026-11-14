from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from tickets import constants as C
from tickets.exceptions import PermissionDenied, TicketError
from tickets.models import Ticket, TicketAttachment
from tickets.permissions import can_manage, can_view, visible_messages_qs  # noqa: F401

from .permissions import StaffOnly, TicketAccess
from .serializers import (
    AssignSerializer, MessageCreateSerializer, RatingApiSerializer, StatusSerializer,
    TicketDetailSerializer, TicketMessageSerializer, TicketSerializer,
)


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [TicketAccess]
    lookup_field = "number"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        from tickets.selectors import my_recipient

        user = self.request.user
        qs = Ticket.objects.select_related("category").prefetch_related("recipients")
        # حذف لیست شدنِ فقط مدیران: فیلتر بر اساس پارامترها
        if self.action in ("list",):
            # لیست بر اساس باکس‌ها
            box = self.request.query_params.get("box", "inbox")
            ids = {r["ticket"] for r in my_ticket_rows(user, box)}
            qs = qs.filter(id__in=ids)
        status_f = self.request.query_params.get("status")
        priority_f = self.request.query_params.get("priority")
        if status_f:
            qs = qs.filter(status=status_f)
        if priority_f:
            qs = qs.filter(priority=priority_f)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(number__icontains=search) | qs.filter(subject__icontains=search)
        return qs

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not can_view(request.user, instance):
            return Response({"detail": "دسترسی مجاز نیست."},
                            status=status.HTTP_403_FORBIDDEN)
        from tickets.services import mark_read

        mark_read(instance, request.user)
        return Response(TicketDetailSerializer(instance, context={"request": request}).data)

    def create(self, request, *args, **kwargs):
        from tickets import services

        subject = request.data.get("subject")
        if not subject:
            return Response({"detail": "موضوع الزامی است."},
                            status=status.HTTP_400_BAD_REQUEST)
        rules = request.data.get("rules")
        specific = request.data.get("specific_user_ids")
        try:
            ticket, count = services.create_ticket(
                author=request.user, subject=subject,
                description=request.data.get("description", ""),
                priority=request.data.get("priority", "normal"),
                category_code=request.data.get("category") or None,
                rules=rules, specific_user_ids=specific,
                due_at=request.data.get("due_at"))
        except TicketError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"number": ticket.number, "recipients": count},
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def reply(self, request, number=None):
        ticket = self.get_object()
        ser = MessageCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            from tickets import services

            msg = services.add_message(
                ticket, request.user, ser.validated_data.get("body", ""),
                kind=C.MSG_INTERNAL_NOTE if ser.validated_data.get("internal") else C.MSG_NORMAL,
                request=request)
        except (TicketError, PermissionDenied) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(TicketMessageSerializer(msg, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def assign(self, request, number=None):
        ticket = self.get_object()
        ser = AssignSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            from django.contrib.auth import get_user_model

            from tickets import services

            agent = None
            if ser.validated_data.get("agent"):
                agent = get_user_model().objects.get(pk=ser.validated_data["agent"])
            services.assign(ticket, request.user, agent=agent,
                            kind=ser.validated_data.get("kind", "manual"), request=request)
        except TicketError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "ارجاع ثبت شد."})

    @action(detail=True, methods=["post"])
    def status(self, request, number=None):
        ticket = self.get_object()
        ser = StatusSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        if not can_manage(request.user, ticket):
            return Response({"detail": "مجاز نیستید."}, status=status.HTTP_403_FORBIDDEN)
        try:
            from tickets import services

            services.change_status(ticket, request.user, ser.validated_data["status"],
                                   note=ser.validated_data.get("note", ""), request=request)
        except TicketError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "وضعیت به‌روزرسانی شد.",
                         "status": ticket.status})

    @action(detail=True, methods=["post"])
    def close(self, request, number=None):
        return self._status_action(request, number, C.STATUS_CLOSED)

    @action(detail=True, methods=["post"])
    def reopen(self, request, number=None):
        ticket = self.get_object()
        try:
            from tickets import services

            services.reopen(ticket, request.user, request=request)
        except TicketError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "تیکت بازگشایی شد."})

    @action(detail=True, methods=["post"])
    def rate(self, request, number=None):
        ticket = self.get_object()
        ser = RatingApiSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            from tickets import services

            services.rate_ticket(ticket, request.user, **ser.validated_data, request=request)
        except TicketError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "امتیاز ثبت شد."})

    def _status_action(self, request, number, target):
        ticket = self.get_object()
        if not can_manage(request.user, ticket):
            return Response({"detail": "مجاز نیستید."}, status=status.HTTP_403_FORBIDDEN)
        try:
            from tickets import services

            services.change_status(ticket, request.user, target, request=request)
        except TicketError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": f"وضعیت: {C.STATUS_LABELS[target]}"})

    @action(detail=True, methods=["get"])
    def messages(self, request, number=None):
        ticket = self.get_object()
        qs = visible_messages_qs(request.user, ticket).select_related("author")
        qs = qs.prefetch_related("attachments")
        return Response(TicketMessageSerializer(qs, many=True,
                                                context={"request": request}).data)


def my_ticket_rows(user, box):
    """کپی سبک از selectors.center_entries برای فیلتر لیست API (فقط id)."""
    from tickets.models import TicketRecipient

    if box in ("assigned", "waiting_me"):
        from tickets.models import TicketAssignment

        qs = TicketAssignment.objects.filter(agent=user, is_active=True)
        if box == "waiting_me":
            qs = qs.filter(ticket__status__in=(C.STATUS_WAITING_USER, C.STATUS_USER_REPLIED))
        return qs.values("ticket")
    return TicketRecipient.objects.filter(user=user, archived=False).values("ticket")


class AttachmentViewSet(viewsets.GenericViewSet):
    """دانلود پیوست با کنترل دسترسی (هیچ فایل خصوصی از MEDIA مستقیم سرو نمی‌شود)."""

    permission_classes = [TicketAccess]
    lookup_field = "pk"
    http_method_names = ["get"]

    def retrieve(self, request, pk=None):
        att = TicketAttachment.objects.select_related(
            "message__ticket", "message__author").get(pk=pk)
        if not can_view(request.user, att.message.ticket):
            return Response({"detail": "دسترسی به پیوست مجاز نیست."},
                            status=status.HTTP_403_FORBIDDEN)
        try:
            resp = FileResponse(att.file.open("rb"),
                                content_type=att.mime or "application/octet-stream")
        except FileNotFoundError:
            return Response({"detail": "فایل یافت نشد."}, status=404)
        resp["Content-Disposition"] = f'attachment; filename="{att.name}"'
        return resp
