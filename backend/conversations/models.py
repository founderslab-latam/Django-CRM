"""Multi-channel conversation history: Chatwoot (Live Chat, WhatsApp) mirror.

Email stays on the existing native SES/SNS pipeline (`cases.inbound`) --
these models cover only the two channels that pipeline doesn't: Live Chat and
WhatsApp, both arriving through a shared Chatwoot installation. One
`ChatwootAccount` per org (Chatwoot's own multi-account support, not a
separate install per tenant). `ChatwootConversation`/`ChatwootMessage` are a
one-way mirror built from Chatwoot's webhooks -- nothing here sends a message
back to Chatwoot; the agent replies from Chatwoot's own UI, embedded inside
the CRM.
"""

from __future__ import annotations

import secrets

from django.db import models

from common.base import BaseOrgModel
from contacts.models import Contact
from leads.models import Lead


def generate_webhook_token() -> str:
    """A URL-safe secret identifying which org a Chatwoot webhook is for.

    Chatwoot does not sign its webhook deliveries (unlike AWS SNS, which this
    codebase already has to verify for inbound email), so the secret in the
    URL path IS the authentication: without it, anyone who learned the plain
    webhook URL could post fabricated conversations into an org's CRM data.
    """
    return secrets.token_hex(24)


class ChatwootAccount(BaseOrgModel):
    """One org's Chatwoot "account" on a shared Chatwoot installation.

    `seat_limit` is a plain config value for now, not enforced against a real
    commercial plan -- there isn't one yet (see the operator console). It's
    here so the field exists when that catches up, rather than a later
    migration.
    """

    base_url = models.URLField(
        help_text="Chatwoot installation base URL, e.g. https://chat.founderslab.cloud"
    )
    account_id = models.PositiveIntegerField(
        help_text="Chatwoot's own numeric account id, from its admin UI."
    )
    api_access_token = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Agent/admin API token. Not used to send messages -- agents "
        "reply from Chatwoot's own embedded UI. Reserved for future "
        "read-side lookups (e.g. fetching a contact's full history on demand).",
    )
    webhook_token = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        default=generate_webhook_token,
    )
    seat_limit = models.PositiveIntegerField(
        default=1,
        help_text="Agent seats this org's plan allows in Chatwoot.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Chatwoot Account"
        verbose_name_plural = "Chatwoot Accounts"
        db_table = "chatwoot_account"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["org"], name="uniq_chatwoot_account_per_org"
            ),
        ]
        indexes = [models.Index(fields=["org", "-created_at"])]

    def __str__(self):
        return f"ChatwootAccount(org={self.org_id}, account_id={self.account_id})"


CHANNEL_CHOICES = (
    ("live_chat", "Live Chat"),
    ("whatsapp", "WhatsApp"),
)

CONVERSATION_STATUS_CHOICES = (
    ("open", "Open"),
    ("pending", "Pending"),
    ("resolved", "Resolved"),
)


class ChatwootConversation(BaseOrgModel):
    """Mirror of one Chatwoot conversation -- a Live Chat session or a
    WhatsApp thread.

    `contact` is set when the sender matched an existing Contact (a known
    customer); `lead` is set when it matched an existing, not-yet-converted
    Lead instead. Both are set when neither matched and this conversation is
    what created them (see `conversations.resolution.resolve_prospect`).
    Both null means the sender gave us nothing to identify them by (an
    anonymous Live Chat visitor who never typed an email or phone) -- there
    is nobody to attach this conversation to yet.
    """

    chatwoot_account = models.ForeignKey(
        ChatwootAccount, on_delete=models.CASCADE, related_name="conversations"
    )
    chatwoot_conversation_id = models.PositiveIntegerField()
    chatwoot_inbox_id = models.PositiveIntegerField()
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES)
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chatwoot_conversations",
    )
    lead = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chatwoot_conversations",
    )
    status = models.CharField(
        max_length=16, choices=CONVERSATION_STATUS_CHOICES, default="open"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Chatwoot Conversation"
        verbose_name_plural = "Chatwoot Conversations"
        db_table = "chatwoot_conversation"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["org", "chatwoot_account", "chatwoot_conversation_id"],
                name="uniq_chatwoot_conversation",
            ),
        ]
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["contact"]),
            models.Index(fields=["lead"]),
        ]

    def __str__(self):
        return (
            f"ChatwootConversation({self.chatwoot_conversation_id}, org={self.org_id})"
        )


MESSAGE_TYPE_CHOICES = (
    ("incoming", "Incoming"),
    ("outgoing", "Outgoing"),
    ("activity", "Activity"),
    ("template", "Template"),
)


class ChatwootMessage(BaseOrgModel):
    """One message within a mirrored Chatwoot conversation."""

    conversation = models.ForeignKey(
        ChatwootConversation, on_delete=models.CASCADE, related_name="messages"
    )
    chatwoot_message_id = models.PositiveIntegerField()
    message_type = models.CharField(max_length=16, choices=MESSAGE_TYPE_CHOICES)
    content = models.TextField(blank=True, default="")
    sender_name = models.CharField(max_length=255, blank=True, default="")
    occurred_at = models.DateTimeField()

    class Meta:
        verbose_name = "Chatwoot Message"
        verbose_name_plural = "Chatwoot Messages"
        db_table = "chatwoot_message"
        ordering = ("occurred_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["org", "conversation", "chatwoot_message_id"],
                name="uniq_chatwoot_message",
            ),
        ]
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["conversation", "occurred_at"]),
        ]

    def __str__(self):
        return f"ChatwootMessage({self.chatwoot_message_id}, conversation={self.conversation_id})"
