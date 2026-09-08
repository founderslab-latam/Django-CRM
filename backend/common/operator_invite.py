"""Invite the first ADMIN of an operator-provisioned tenant.

The operator creates an org shell and hands it to a customer by email. This
pre-creates the ADMIN membership and sends a magic link, so the invitee lands
straight in *their* org rather than the "create your first org" onboarding.
"""

import secrets
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.utils import timezone

from common.models import MagicLinkToken, Profile, User


def invite_org_admin(org, email):
    """Create (or reuse) the ADMIN profile for ``email`` in ``org`` and email a
    magic link. Returns True when a link was sent.

    A blank/absent email is a no-op (returns False). An existing user is added
    as an ADMIN of the new org without touching their other memberships.
    """
    email = (email or "").strip().lower()
    if not email:
        return False

    user, _ = User.objects.get_or_create(
        email=email,
        defaults={
            "password": make_password(secrets.token_urlsafe(32)),
            "is_active": True,
        },
    )

    Profile.objects.get_or_create(
        user=user,
        org=org,
        defaults={"role": "ADMIN", "is_organization_admin": True, "is_active": True},
    )

    # Same shape as MagicLinkRequestView: invalidate old unused tokens, mint one.
    MagicLinkToken.objects.filter(email=email, is_used=False).update(is_used=True)
    token_obj = MagicLinkToken.objects.create(
        email=email,
        token=secrets.token_hex(32),
        delivery=MagicLinkToken.DELIVERY_LINK,
        expires_at=timezone.now() + timedelta(days=7),
    )

    from common.tasks import send_magic_link_email

    send_magic_link_email.delay(str(token_obj.id))
    return True
