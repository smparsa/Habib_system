from rest_framework import serializers

from tickets import constants as C
from tickets.models import (
    Ticket, TicketAttachment, TicketMessage, TicketRating, TicketRecipient,
)
from tickets.permissions import is_staff_user


class TicketAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = TicketAttachment
        fields = ("id", "name", "size", "mime", "url")

    def get_url(self, obj):
        from django.urls import reverse

        return reverse("api:ticket-attachment", args=[obj.id])


class TicketMessageSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    kind_label = serializers.SerializerMethodField()
    attachments = TicketAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = TicketMessage
        fields = ("id", "author", "kind", "kind_label", "body", "created_at",
                  "edited_at", "attachments")

    def get_author(self, obj):
        return obj.author.mobile_number

    def get_kind_label(self, obj):
        return {
            C.MSG_NORMAL: "پیام", C.MSG_SYSTEM: "سیستمی", C.MSG_INTERNAL_NOTE: "یادداشت داخلی",
            C.MSG_STATUS_UPDATE: "وضعیت", C.MSG_ASSIGNMENT: "ارجاع", C.MSG_AUTO: "خودکار",
        }.get(obj.kind, obj.kind)


class RecipientSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = TicketRecipient
        fields = ("user", "state", "important", "archived", "read_at", "updated_at")

    def get_user(self, obj):
        return obj.user.mobile_number


class TicketSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.code", allow_null=True)
    category_label = serializers.SerializerMethodField()
    priority_label = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    my_state = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ("number", "author", "subject", "description", "category",
                  "category_label", "priority", "priority_label", "status",
                  "status_label", "due_at", "resolved_at", "closed_at",
                  "created_at", "updated_at", "my_state", "url")

    def get_category_label(self, obj):
        return obj.category.name_fa if obj.category else ""

    def get_priority_label(self, obj):
        return C.PRIORITY_LABELS.get(obj.priority, obj.priority)

    def get_status_label(self, obj):
        return C.STATUS_LABELS.get(obj.status, obj.status)

    def get_author(self, obj):
        return obj.author.mobile_number

    def get_my_state(self, obj):
        user = self.context.get("request").user
        r = TicketRecipient.objects.filter(user=user, ticket=obj).first()
        return r.state if r else None

    def get_url(self, obj):
        from django.urls import reverse

        return reverse("api:ticket-detail", args=[obj.number])


class TicketDetailSerializer(TicketSerializer):
    messages = serializers.SerializerMethodField()
    recipients = serializers.SerializerMethodField()
    can_reply = serializers.SerializerMethodField()

    class Meta(TicketSerializer.Meta):
        fields = TicketSerializer.Meta.fields + ("messages", "recipients", "can_reply")

    def get_messages(self, obj):
        from tickets.permissions import visible_messages_qs

        user = self.context["request"].user
        return TicketMessageSerializer(
            visible_messages_qs(user, obj).select_related("author").prefetch_related("attachments"),
            many=True, context=self.context).data

    def get_recipients(self, obj):
        user = self.context["request"].user
        if not is_staff_user(user):
            return None  # حریم خصوصی: کاربر عادی لیست گیرندگان را نمی‌بیند
        return RecipientSerializer(obj.recipients.select_related("user"), many=True).data

    def get_can_reply(self, obj):
        from tickets.permissions import can_reply

        return can_reply(self.context["request"].user, obj)


class MessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(required=False, allow_blank=True)
    internal = serializers.BooleanField(default=False)


class StatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[(s, s) for s in C.STATUSES])
    note = serializers.CharField(required=False, allow_blank=True)


class AssignSerializer(serializers.Serializer):
    agent = serializers.IntegerField(required=False, allow_null=True)
    kind = serializers.ChoiceField(
        choices=[("manual", "دستی"), ("round_robin", "چرخشی"),
                 ("workload", "حجم کار"), ("auto", "خودکار")],
        default="manual")


class RatingApiSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketRating
        fields = ("stars", "response_quality", "resolution_quality", "comment", "created_at")
        read_only_fields = ("created_at",)

    def validate(self, attrs):
        if not 1 <= attrs.get("stars", 0) <= 5:
            raise serializers.ValidationError("ستاره باید بین ۱ تا ۵ باشد.")
        return attrs
