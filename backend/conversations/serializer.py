from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import ChatwootConversation


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
