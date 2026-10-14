"""Who is this? Resolve a channel sender to a Contact or a Lead, creating one
only when nobody already represents them.

Matches `contacts.models.Contact.first_name` being required (blank, not
null) by falling back to a placeholder name -- an anonymous WhatsApp number
or Live Chat visitor often gives us nothing else to go on.
"""

from __future__ import annotations

from dataclasses import dataclass

from common.duplicate_detection import DuplicateDetector
from contacts.models import Contact
from leads.models import Lead

CHANNEL_LABELS = {
    "live_chat": "Live Chat",
    "whatsapp": "WhatsApp",
}


@dataclass
class ResolvedProspect:
    """At most one of `contact`/`lead` is set on a match; both are set only
    when `created` is True (this call is what made them)."""

    contact: Contact | None
    lead: Lead | None
    created: bool


def _split_name(name: str) -> tuple[str, str]:
    name = (name or "").strip()
    if not name:
        return "", ""
    parts = name.split(None, 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def resolve_prospect(
    org, *, email: str = "", phone: str = "", name: str = "", channel: str = ""
) -> ResolvedProspect:
    """Find or create whoever is on the other end of a channel message.

    Priority, same as the rest of this codebase's dedup logic
    (`common.duplicate_detection.DuplicateDetector`, already used by the CSV
    importer and webforms):

    1. An existing Contact with this email or phone -- a known customer.
       Nothing is created; this conversation attaches to them.
    2. Failing that, an existing Lead with this email or phone -- a prospect
       already in the pipeline from some other channel. Nothing is created
       either, to avoid the exact duplicate-lead problem webforms already
       solved once (`webforms/service.py::_existing_lead`).
    3. Neither: a genuinely new prospect. Create both a Contact and a Lead,
       linked via `Lead.contacts`, and leave the Lead unassigned -- `source`
       names the channel so it is easy to find in a sales queue later.

    Returns `(None, None, False)` when there is nothing to identify anyone
    by at all (an anonymous Live Chat visitor who typed no email/phone):
    there is nobody, known or new, to attach the conversation to yet.
    """
    email = (email or "").strip()
    phone = (phone or "").strip()

    contacts = DuplicateDetector.find_duplicate_contacts(
        org, email=email or None, phone=phone or None
    )
    if contacts:
        return ResolvedProspect(contact=contacts[0], lead=None, created=False)

    leads = DuplicateDetector.find_duplicate_leads(
        org, email=email or None, phone=phone or None
    )
    if leads:
        return ResolvedProspect(contact=None, lead=leads[0], created=False)

    if not email and not phone:
        return ResolvedProspect(contact=None, lead=None, created=False)

    first_name, last_name = _split_name(name)
    first_name = first_name or "Unknown"

    contact = Contact.objects.create(
        org=org,
        first_name=first_name,
        last_name=last_name,
        email=email or None,
        phone=phone or "",
    )
    label = CHANNEL_LABELS.get(channel, channel or "Chat")
    lead = Lead.objects.create(
        org=org,
        title=f"{label} inquiry",
        first_name=first_name,
        last_name=last_name,
        email=email or None,
        phone=phone or None,
        status="assigned",  # the pipeline-state label webforms also uses for
        # a freshly-created, not-yet-triaged lead -- "sin asignar" is the
        # empty `assigned_to`, set below by never touching it.
        source=channel or None,
    )
    lead.contacts.add(contact)
    return ResolvedProspect(contact=contact, lead=lead, created=True)
