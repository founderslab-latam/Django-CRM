from django.urls import reverse
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import ChatwootAccount, ChatwootConversation, ChatwootMessage


class ChatwootMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatwootMessage
        fields = ["id", "message_type", "content", "sender_name", "occurred_at"]
        read_only_fields = fields


class ChatwootConversationSerializer(serializers.ModelSerializer):
    """What the CRM UI needs to list and open a mirrored conversation.

    `embed_url` is built here, not in the frontend, so Chatwoot's dashboard
    URL scheme is something only this one method needs to know about. It
    points at the Chatwoot *agent* dashboard, not the public chat widget --
    opening it still requires the agent to be signed in to Chatwoot in that
    browser. There is no SSO between the two yet (see the module notes in
    `conversations/views.py`), so this is a convenience link today, not a
    guarantee of a logged-in view.
    """

    embed_url = serializers.SerializerMethodField()
    channel_display = serializers.CharField(
        source="get_channel_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    messages = ChatwootMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatwootConversation
        fields = [
            "id",
            "channel",
            "channel_display",
            "status",
            "status_display",
            "chatwoot_conversation_id",
            "embed_url",
            "created_at",
            "resolved_at",
            "messages",
        ]
        read_only_fields = fields

    @extend_schema_field(str)
    def get_embed_url(self, obj):
        account = obj.chatwoot_account
        base = account.base_url.rstrip("/")
        return (
            f"{base}/app/accounts/{account.account_id}"
            f"/conversations/{obj.chatwoot_conversation_id}"
        )


class ChatwootAccountSerializer(serializers.ModelSerializer):
    """The org-settings form: one ChatwootAccount per org (admin-only, see
    `conversations.views.ChatwootAccountView`).

    `api_access_token` is write-only and never read back, same posture as
    `InboundMailbox.webhook_secret` -- `has_api_access_token` tells the UI
    whether one is set without ever exposing its value. `webhook_token`
    itself is not a field here at all: it is the entire authentication for
    the public webhook (see `webhook_views.py`), so the only thing this
    serializer exposes about it is the *constructed URL* an admin pastes
    into Chatwoot, never the bare token.
    """

    api_access_token = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    has_api_access_token = serializers.SerializerMethodField()
    webhook_url = serializers.SerializerMethodField()

    class Meta:
        model = ChatwootAccount
        fields = [
            "id",
            "base_url",
            "account_id",
            "api_access_token",
            "has_api_access_token",
            "webhook_url",
            "seat_limit",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    @extend_schema_field(bool)
    def get_has_api_access_token(self, obj):
        return bool(obj.api_access_token)

    @extend_schema_field(str)
    def get_webhook_url(self, obj):
        request = self.context.get("request")
        path = reverse(
            "public_conversations:chatwoot_webhook",
            kwargs={"webhook_token": obj.webhook_token},
        )
        if request is None:
            return path
        return request.build_absolute_uri(path)

    def update(self, instance, validated_data):
        # A blank api_access_token means "leave it alone" (the field it is
        # masking on the form has nothing typed into it), not "clear it" --
        # the admin clears it by typing nothing on purpose has no way to
        # express that intent differently from "I didn't touch this field",
        # so leaving it alone is the safer reading of the ambiguity.
        if validated_data.get("api_access_token") == "":
            validated_data.pop("api_access_token")
        return super().update(instance, validated_data)
