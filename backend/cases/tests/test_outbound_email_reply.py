"""A public agent reply becomes a real, threaded email when the case has an
inbound email thread to answer into -- not just a "sign in to read it" notice.

Covers `cases.tasks.send_case_reply_email` directly (the actual send) and the
signal's choice of which of the two notification tasks to enqueue (mocked
`.delay`, same split as `test_portal_notifications.py::TestSignalWiring`).
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core import mail

from cases.models import Case, InboundMailbox
from cases.models import EmailMessage as CaseEmailMessage
from cases.tasks import send_case_reply_email
from common.models import Comment


@pytest.fixture
def mailbox(org_a):
    return InboundMailbox.objects.create(
        org=org_a,
        address="support@acme.com",
        provider="ses",
        topic_arn="arn:aws:sns:us-east-1:123456789012:acme-inbound",
    )


@pytest.fixture
def threaded_case(org_a, mailbox):
    """A case with one inbound email already on record -- a real thread."""
    case = Case.objects.create(
        org=org_a, name="Can't log in", status="New", priority="Normal"
    )
    inbound = CaseEmailMessage.objects.create(
        org=org_a,
        case=case,
        mailbox=mailbox,
        direction="inbound",
        message_id="first@customer.example",
        from_address="customer@example.com",
        to_addresses="support@acme.com",
        subject="Can't log in",
        body_text="I can't log in to my account.",
        received_at=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
    )
    return case, inbound


@pytest.fixture
def bare_case(org_a):
    """A case created by an agent in the UI: no email thread at all."""
    return Case.objects.create(
        org=org_a, name="Internal follow-up", status="New", priority="Normal"
    )


def _make_comment(org, case, **overrides):
    defaults = {
        "org": org,
        "content_type": ContentType.objects.get_for_model(Case),
        "object_id": case.id,
        "comment": "Thanks for reaching out -- try resetting your password.",
        "is_internal": False,
    }
    defaults.update(overrides)
    return Comment.objects.create(**defaults)


@pytest.mark.django_db
class TestSendCaseReplyEmail:
    def test_sends_a_real_threaded_email(self, org_a, threaded_case, admin_profile):
        case, inbound = threaded_case
        comment = _make_comment(org_a, case, commented_by=admin_profile)
        mail.outbox.clear()

        row_id = send_case_reply_email(str(case.id), str(org_a.id), str(comment.id))

        assert row_id is not None
        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.from_email == "support@acme.com"
        assert sent.to == ["customer@example.com"]
        assert sent.body == comment.comment
        assert sent.subject == "Re: Can't log in"
        assert sent.extra_headers["In-Reply-To"] == "<first@customer.example>"
        assert sent.extra_headers["References"] == "<first@customer.example>"
        assert sent.extra_headers["Message-ID"].startswith("<")

    def test_imap_mailbox_replies_through_its_own_smtp(
        self, org_a, threaded_case, mailbox, admin_profile
    ):
        from django.core.mail import get_connection

        case, _inbound = threaded_case
        mailbox.provider = "imap"
        mailbox.smtp_host = "mail.acme.com"
        mailbox.save()
        comment = _make_comment(org_a, case, commented_by=admin_profile)
        mail.outbox.clear()
        own_smtp = get_connection("django.core.mail.backends.locmem.EmailBackend")

        with (
            patch("cases.tasks.smtp.connection_for", return_value=own_smtp) as chosen,
            patch.object(
                own_smtp, "send_messages", wraps=own_smtp.send_messages
            ) as sent_through,
        ):
            send_case_reply_email(str(case.id), str(org_a.id), str(comment.id))

        assert chosen.call_args.args[0].pk == mailbox.pk
        assert sent_through.call_count == 1
        assert len(mail.outbox) == 1

    def test_writes_the_audit_row_threaded_to_the_inbound_message(
        self, org_a, threaded_case, admin_profile
    ):
        case, inbound = threaded_case
        comment = _make_comment(org_a, case, commented_by=admin_profile)

        row_id = send_case_reply_email(str(case.id), str(org_a.id), str(comment.id))

        row = CaseEmailMessage.objects.get(id=row_id)
        assert row.direction == "outbound"
        assert row.case_id == case.id
        assert row.mailbox_id == inbound.mailbox_id
        assert row.comment_id == comment.id
        assert row.in_reply_to == inbound.message_id
        assert inbound.message_id in row.references
        assert row.from_address == "support@acme.com"
        assert row.to_addresses == "customer@example.com"
        # Stored bracket-free, matching every inbound row's convention.
        assert not row.message_id.startswith("<")

    def test_references_accumulate_across_a_longer_thread(
        self, org_a, threaded_case, admin_profile
    ):
        """A second inbound message (the customer replying again) should make
        the next agent reply's References carry both message ids, not just
        the latest."""
        case, first = threaded_case
        second = CaseEmailMessage.objects.create(
            org=org_a,
            case=case,
            mailbox=first.mailbox,
            direction="inbound",
            message_id="second@customer.example",
            in_reply_to=first.message_id,
            references=first.message_id,
            from_address="customer@example.com",
            to_addresses="support@acme.com",
            subject="Re: Can't log in",
            body_text="Still stuck, any update?",
            received_at=datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc),
        )
        comment = _make_comment(org_a, case, commented_by=admin_profile)

        row_id = send_case_reply_email(str(case.id), str(org_a.id), str(comment.id))
        row = CaseEmailMessage.objects.get(id=row_id)

        assert row.in_reply_to == second.message_id
        assert first.message_id in row.references
        assert second.message_id in row.references

    def test_no_thread_is_a_quiet_no_op(self, org_a, bare_case, admin_profile):
        comment = _make_comment(org_a, bare_case, commented_by=admin_profile)
        mail.outbox.clear()

        assert (
            send_case_reply_email(str(bare_case.id), str(org_a.id), str(comment.id))
            is None
        )
        assert mail.outbox == []
        assert not CaseEmailMessage.objects.filter(case=bare_case).exists()

    def test_mailbox_deleted_since_is_also_a_quiet_no_op(
        self, org_a, threaded_case, admin_profile
    ):
        case, inbound = threaded_case
        inbound.mailbox.delete()  # SET_NULL on the EmailMessage row
        inbound.refresh_from_db()
        assert inbound.mailbox_id is None
        comment = _make_comment(org_a, case, commented_by=admin_profile)
        mail.outbox.clear()

        assert (
            send_case_reply_email(str(case.id), str(org_a.id), str(comment.id)) is None
        )
        assert mail.outbox == []

    def test_unknown_case_is_a_no_op(self, org_a, threaded_case, admin_profile):
        import uuid

        case, _ = threaded_case
        comment = _make_comment(org_a, case, commented_by=admin_profile)
        assert (
            send_case_reply_email(str(uuid.uuid4()), str(org_a.id), str(comment.id))
            is None
        )

    def test_cross_org_ids_do_not_resolve(
        self, org_a, org_b, threaded_case, admin_profile
    ):
        """A case from org_a looked up under org_b's id must not resolve."""
        case, _ = threaded_case
        comment = _make_comment(org_a, case, commented_by=admin_profile)
        assert (
            send_case_reply_email(str(case.id), str(org_b.id), str(comment.id)) is None
        )


@pytest.mark.django_db
class TestSignalChoosesTheRightChannel:
    """Exactly one of the two tasks fires per public, agent-authored comment."""

    def test_agent_reply_on_a_threaded_case_sends_real_email(
        self, org_a, threaded_case, admin_profile
    ):
        case, _ = threaded_case
        with (
            patch("cases.tasks.send_case_reply_email.delay") as real_email,
            patch("cases.tasks.notify_portal_contacts.delay") as portal_notice,
        ):
            comment = _make_comment(org_a, case, commented_by=admin_profile)

        real_email.assert_called_once_with(str(case.id), str(org_a.id), str(comment.id))
        portal_notice.assert_not_called()

    def test_agent_reply_on_a_bare_case_falls_back_to_the_notice(
        self, org_a, bare_case, admin_profile
    ):
        with (
            patch("cases.tasks.send_case_reply_email.delay") as real_email,
            patch("cases.tasks.notify_portal_contacts.delay") as portal_notice,
        ):
            _make_comment(org_a, bare_case, commented_by=admin_profile)

        real_email.assert_not_called()
        portal_notice.assert_called_once_with(
            str(bare_case.id), str(org_a.id), "reply", actor_contact_id=None
        )

    def test_customer_portal_reply_never_sends_a_real_email(self, org_a, threaded_case):
        """Even on a threaded case: a customer's own reply must not be
        re-mailed to them as a fresh outbound message."""
        case, _ = threaded_case
        from contacts.models import Contact

        pat = Contact.objects.create(
            org=org_a, first_name="Pat", email="pat@example.com"
        )
        case.contacts.add(pat)
        with (
            patch("cases.tasks.send_case_reply_email.delay") as real_email,
            patch("cases.tasks.notify_portal_contacts.delay") as portal_notice,
        ):
            _make_comment(org_a, case, commented_by_contact=pat)

        real_email.assert_not_called()
        portal_notice.assert_called_once_with(
            str(case.id), str(org_a.id), "reply", actor_contact_id=str(pat.id)
        )

    def test_internal_note_on_a_threaded_case_sends_nothing(
        self, org_a, threaded_case, admin_profile
    ):
        case, _ = threaded_case
        with (
            patch("cases.tasks.send_case_reply_email.delay") as real_email,
            patch("cases.tasks.notify_portal_contacts.delay") as portal_notice,
        ):
            _make_comment(org_a, case, commented_by=admin_profile, is_internal=True)

        real_email.assert_not_called()
        portal_notice.assert_not_called()
