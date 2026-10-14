"""Keeps `common.PortalAccessToken`'s unscoped lookup current for the
Chatwoot webhook, which needs it to resolve the org *before* RLS context is
set (a genuinely anonymous Chatwoot delivery carries no Authorization
header, so nothing else sets it) -- see the module docstring on
`conversations/webhook_views.py`.

`webhook_token` never changes after creation in practice (there is no
rotation UI), so this fires once per account; wired as `post_save` rather
than only on create so an existing row missing its registration heals the
next time it's touched too.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from common.models import PortalAccessToken
from common.portal_tokens import portal_token_hash, register_portal_token_hash

from .models import ChatwootAccount


@receiver(post_save, sender=ChatwootAccount)
def chatwoot_account_post_save_register_portal_token(sender, instance, **kwargs):
    register_portal_token_hash(
        portal_token_hash(instance.webhook_token),
        instance.org_id,
        PortalAccessToken.CHATWOOT_WEBHOOK,
        instance.pk,
    )
