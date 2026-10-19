"""IMAP/SMTP mailboxes: the customer's own mail server instead of SES.

Network is never touched: `imap.connect` is replaced by a fake server,
`socket.getaddrinfo` by a fixed resolver, and SMTP by Django's locmem backend.
"""

from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from cases.inbound import imap
from cases.inbound.hosts import IMAP_PORTS, MailHostError, check_mail_host
from cases.inbound.smtp import connection_for
from cases.models import Case, EmailMessage, InboundMailbox
from cases.tasks import poll_imap_mailboxes, poll_mailbox
from common.credentials import CredentialError, decrypt_secret, encrypt_secret

MAILBOXES_URL = "/api/cases/mailboxes/"
TEST_URL = "/api/cases/mailboxes/test-connection/"


def _raw(message_id: str, subject: str = "Help") -> bytes:
    return (
        "From: Customer <customer@example.com>\r\n"
        "To: soporte@cliente.cl\r\n"
        f"Subject: {subject}\r\n"
        "Date: Mon, 19 Oct 2026 12:00:00 +0000\r\n"
        f"Message-ID: <{message_id}>\r\n"
        'Content-Type: text/plain; charset="utf-8"\r\n\r\n'
        "Necesito ayuda."
    ).encode()


class FakeImap:
    """Just enough of imaplib.IMAP4 for `fetch_new`."""

    def __init__(self, uidvalidity=7, messages=None):
        self.uidvalidity = uidvalidity
        self.messages = dict(messages or {})  # uid -> raw bytes
        self.searches = []
        self.selected_readonly = None

    @property
    def uidnext(self):
        return max(self.messages, default=0) + 1

    def status(self, folder, items):
        line = f"{folder} (UIDVALIDITY {self.uidvalidity} UIDNEXT {self.uidnext})"
        return "OK", [line.encode()]

    def select(self, folder, readonly=False):
        self.selected_readonly = readonly
        return "OK", [str(len(self.messages)).encode()]

    def uid(self, command, *args):
        if command == "SEARCH":
            self.searches.append(args[-1])
            start = int(args[-1].split()[1].split(":")[0])
            hits = [u for u in self.messages if u >= start]
            # Real servers: "N:*" always includes the newest message.
            if not hits and self.messages:
                hits = [max(self.messages)]
            return "OK", [" ".join(str(u) for u in sorted(hits)).encode()]
        if command == "FETCH":
            uid = int(args[0])
            assert args[1] == "(BODY.PEEK[])", "must never mark mail as read"
            if uid not in self.messages:
                return "OK", [None]
            return "OK", [
                (f"1 (UID {uid} BODY[] {{1}}".encode(), self.messages[uid]),
                b")",
            ]
        raise AssertionError(command)

    def logout(self):
        return "BYE", []


@pytest.fixture
def allow_private(settings):
    settings.ALLOW_PRIVATE_MAIL_HOSTS = True


@pytest.fixture
def imap_mailbox(org_a, allow_private):
    mailbox = InboundMailbox(
        org=org_a,
        address="soporte@cliente.cl",
        provider="imap",
        imap_host="mail.cliente.cl",
        imap_username="soporte@cliente.cl",
        smtp_host="mail.cliente.cl",
    )
    mailbox.set_imap_password("s3cret")
    mailbox.save()
    return mailbox


def _public_dns(*_args, **_kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 993))]


def _private_dns(*_args, **_kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 993))]


class TestCredentials:
    def test_roundtrip(self):
        token = encrypt_secret("s3cret")
        assert token != "s3cret"
        assert decrypt_secret(token) == "s3cret"

    def test_tampered_token_is_a_clear_error(self):
        with pytest.raises(CredentialError):
            decrypt_secret(encrypt_secret("s3cret")[:-4] + "AAAA")

    def test_dedicated_key_is_used_when_set(self, settings):
        token = encrypt_secret("s3cret")
        settings.CREDENTIALS_ENCRYPTION_KEY = (
            "cw_0x689RpI-jtRR7oE8h_eQsKImvJapLeSbXpwF4e4="
        )
        with pytest.raises(CredentialError):
            decrypt_secret(token)


class TestHostCheck:
    def test_non_mail_port_is_refused(self):
        with pytest.raises(MailHostError, match="Port 5432"):
            check_mail_host("mail.cliente.cl", 5432, IMAP_PORTS)

    def test_private_address_is_refused(self):
        with patch("socket.getaddrinfo", _private_dns):
            with pytest.raises(MailHostError, match="private"):
                check_mail_host("mail.cliente.cl", 993, IMAP_PORTS)

    def test_public_address_passes(self):
        with patch("socket.getaddrinfo", _public_dns):
            check_mail_host("mail.cliente.cl", 993, IMAP_PORTS)

    def test_private_allowed_for_local_development(self, settings):
        settings.ALLOW_PRIVATE_MAIL_HOSTS = True
        with patch("socket.getaddrinfo", _private_dns):
            check_mail_host("mailserver", 993, IMAP_PORTS)


@pytest.mark.django_db
class TestFetchNew:
    def test_first_poll_only_records_where_new_mail_starts(self, imap_mailbox):
        server = FakeImap(messages={1: _raw("old1"), 2: _raw("old2")})
        with patch.object(imap, "connect", return_value=server):
            result = imap.fetch_new(imap_mailbox)
        assert result.baseline_uid == 2
        assert result.messages == []
        assert server.searches == []
        assert server.selected_readonly is True

    def test_new_uidvalidity_restarts_the_cursor(self, imap_mailbox):
        imap_mailbox.imap_uidvalidity = 6
        imap_mailbox.imap_last_uid = 2
        server = FakeImap(uidvalidity=7, messages={5: _raw("x")})
        with patch.object(imap, "connect", return_value=server):
            result = imap.fetch_new(imap_mailbox)
        assert result.baseline_uid == 5

    def test_fetches_only_uids_after_the_cursor(self, imap_mailbox):
        imap_mailbox.imap_uidvalidity = 7
        imap_mailbox.imap_last_uid = 2
        server = FakeImap(
            messages={1: _raw("a"), 2: _raw("b"), 3: _raw("c"), 4: _raw("d")}
        )
        with patch.object(imap, "connect", return_value=server):
            result = imap.fetch_new(imap_mailbox)
        assert [uid for uid, _raw_bytes in result.messages] == [3, 4]
        assert result.messages[0][1] == _raw("c")

    def test_star_range_quirk_does_not_refetch_the_last_message(self, imap_mailbox):
        imap_mailbox.imap_uidvalidity = 7
        imap_mailbox.imap_last_uid = 3
        server = FakeImap(messages={3: _raw("c")})
        server.messages[4] = _raw("d")
        del server.messages[4]  # uidnext stays 4: nothing new
        with patch.object(imap, "connect", return_value=server):
            result = imap.fetch_new(imap_mailbox)
        assert result.messages == []

    def test_batch_size_caps_one_poll(self, imap_mailbox):
        imap_mailbox.imap_uidvalidity = 7
        imap_mailbox.imap_last_uid = 0
        server = FakeImap(messages={u: _raw(f"m{u}") for u in range(1, 6)})
        with patch.object(imap, "connect", return_value=server):
            result = imap.fetch_new(imap_mailbox, batch_size=2)
        assert [uid for uid, _raw_bytes in result.messages] == [1, 2]


@pytest.mark.django_db
class TestPollMailbox:
    def test_first_poll_sets_the_cursor_and_creates_nothing(self, imap_mailbox):
        server = FakeImap(messages={1: _raw("old")})
        with patch.object(imap, "connect", return_value=server):
            assert poll_mailbox(imap_mailbox) == 0
        imap_mailbox.refresh_from_db()
        assert imap_mailbox.imap_last_uid == 1
        assert imap_mailbox.imap_uidvalidity == 7
        assert imap_mailbox.last_polled_at is not None
        assert Case.objects.count() == 0

    def test_new_mail_becomes_cases_and_advances_the_cursor(self, imap_mailbox):
        server = FakeImap(messages={1: _raw("old")})
        with patch.object(imap, "connect", return_value=server):
            poll_mailbox(imap_mailbox)
            server.messages[2] = _raw("new1", subject="Pedido 1")
            server.messages[3] = _raw("new2", subject="Pedido 2")
            assert poll_mailbox(imap_mailbox) == 2
        imap_mailbox.refresh_from_db()
        assert imap_mailbox.imap_last_uid == 3
        assert imap_mailbox.last_poll_error == ""
        assert sorted(Case.objects.values_list("name", flat=True)) == [
            "Pedido 1",
            "Pedido 2",
        ]
        assert EmailMessage.objects.filter(mailbox=imap_mailbox).count() == 2

    def test_connection_failure_is_recorded_not_raised(self, imap_mailbox):
        imap_mailbox.imap_uidvalidity = 7
        imap_mailbox.imap_last_uid = 4
        imap_mailbox.save()
        with patch.object(
            imap, "connect", side_effect=imap.ImapError("AUTHENTICATIONFAILED")
        ):
            assert poll_mailbox(imap_mailbox) == 0
        imap_mailbox.refresh_from_db()
        assert "AUTHENTICATIONFAILED" in imap_mailbox.last_poll_error
        assert imap_mailbox.imap_last_uid == 4

    def test_a_message_that_fails_is_skipped_not_retried_forever(self, imap_mailbox):
        imap_mailbox.imap_uidvalidity = 7
        imap_mailbox.imap_last_uid = 0
        imap_mailbox.save()
        server = FakeImap(messages={1: _raw("bad"), 2: _raw("good", subject="Ok")})
        real_ingest = __import__("cases.tasks", fromlist=["ingest"]).ingest

        def flaky(parsed, mailbox):
            if parsed.message_id == "bad":
                raise RuntimeError("boom")
            return real_ingest(parsed, mailbox)

        with (
            patch.object(imap, "connect", return_value=server),
            patch("cases.tasks.ingest", side_effect=flaky),
        ):
            assert poll_mailbox(imap_mailbox) == 1
        imap_mailbox.refresh_from_db()
        assert imap_mailbox.imap_last_uid == 2
        assert "UID 1" in imap_mailbox.last_poll_error
        assert list(Case.objects.values_list("name", flat=True)) == ["Ok"]

    def test_scheduler_polls_only_active_imap_mailboxes_of_active_orgs(
        self, imap_mailbox, org_a
    ):
        InboundMailbox.objects.create(
            org=org_a, address="ses@cliente.cl", provider="ses"
        )
        InboundMailbox.objects.create(
            org=org_a,
            address="off@cliente.cl",
            provider="imap",
            is_active=False,
        )
        with patch("cases.tasks.poll_mailbox", return_value=0) as polled:
            poll_imap_mailboxes()
        assert [call.args[0].pk for call in polled.call_args_list] == [imap_mailbox.pk]

    def test_suspended_org_is_not_polled(self, imap_mailbox, org_a):
        org_a.status = "SUSPENDED"
        org_a.save()
        with patch("cases.tasks.poll_mailbox", return_value=0) as polled:
            poll_imap_mailboxes()
        polled.assert_not_called()


@pytest.mark.django_db
class TestSmtpConnection:
    def test_ses_mailbox_uses_the_default_backend(self, org_a):
        mailbox = InboundMailbox(org=org_a, address="a@b.cl", provider="ses")
        assert connection_for(mailbox) is None

    def test_smtp_login_falls_back_to_the_imap_account(self, imap_mailbox):
        backend = connection_for(imap_mailbox)
        assert backend.host == "mail.cliente.cl"
        assert backend.port == 587
        assert backend.use_tls is True
        assert backend.username == "soporte@cliente.cl"
        assert backend.password == "s3cret"

    def test_separate_smtp_account(self, imap_mailbox):
        imap_mailbox.smtp_username = "relay@cliente.cl"
        imap_mailbox.set_smtp_password("other")
        imap_mailbox.smtp_security = "ssl"
        backend = connection_for(imap_mailbox)
        assert (backend.username, backend.password) == ("relay@cliente.cl", "other")
        assert backend.port == 465
        assert backend.use_ssl is True


@pytest.mark.django_db
class TestMailboxApi:
    def _payload(self, **overrides):
        payload = {
            "address": "soporte@cliente.cl",
            "provider": "imap",
            "imap_host": "mail.cliente.cl",
            "imap_username": "soporte@cliente.cl",
            "imap_password": "s3cret",
            "smtp_host": "mail.cliente.cl",
        }
        payload.update(overrides)
        return payload

    def test_creates_an_imap_mailbox_with_the_password_encrypted(self, admin_client):
        with patch("socket.getaddrinfo", _public_dns):
            resp = admin_client.post(MAILBOXES_URL, self._payload(), format="json")
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert "imap_password" not in body
        assert body["has_imap_password"] is True
        stored = InboundMailbox.objects.get(pk=body["id"])
        assert stored.imap_password_enc != "s3cret"
        assert stored.imap_password() == "s3cret"

    def test_required_fields(self, admin_client):
        resp = admin_client.post(
            MAILBOXES_URL,
            {"address": "soporte@cliente.cl", "provider": "imap"},
            format="json",
        )
        assert resp.status_code == 400
        errors = resp.json()["errors"]
        assert {"imap_host", "imap_username", "imap_password", "smtp_host"} <= set(
            errors
        )

    def test_private_host_is_refused(self, admin_client):
        with patch("socket.getaddrinfo", _private_dns):
            resp = admin_client.post(MAILBOXES_URL, self._payload(), format="json")
        assert resp.status_code == 400
        assert "imap_host" in resp.json()["errors"]

    def test_blank_password_on_update_keeps_the_stored_one(
        self, admin_client, imap_mailbox
    ):
        resp = admin_client.put(
            f"{MAILBOXES_URL}{imap_mailbox.id}/",
            {"imap_password": "", "default_priority": "High"},
            format="json",
        )
        assert resp.status_code == 200, resp.json()
        imap_mailbox.refresh_from_db()
        assert imap_mailbox.imap_password() == "s3cret"

    def test_pointing_at_another_mailbox_restarts_the_cursor(
        self, admin_client, imap_mailbox
    ):
        imap_mailbox.imap_uidvalidity = 7
        imap_mailbox.imap_last_uid = 40
        imap_mailbox.save()
        resp = admin_client.put(
            f"{MAILBOXES_URL}{imap_mailbox.id}/",
            {"imap_username": "ventas@cliente.cl"},
            format="json",
        )
        assert resp.status_code == 200, resp.json()
        imap_mailbox.refresh_from_db()
        assert imap_mailbox.imap_last_uid is None

    def test_members_do_not_see_server_settings(self, user_client, imap_mailbox):
        row = user_client.get(MAILBOXES_URL).json()["mailboxes"][0]
        assert "imap_host" not in row
        assert "smtp_username" not in row
        assert "last_poll_error" not in row
        assert "last_polled_at" in row
        assert row["has_poll_error"] is False


@pytest.mark.django_db
class TestConnectionTest:
    BODY = {
        "imap_host": "mail.cliente.cl",
        "imap_username": "soporte@cliente.cl",
        "imap_password": "typed",
        "smtp_host": "mail.cliente.cl",
    }

    def test_members_cannot_use_it(self, user_client):
        assert user_client.post(TEST_URL, self.BODY, format="json").status_code == 403

    def test_reports_each_half_separately(self, admin_client):
        with (
            patch("cases.inbound_views.imap.check_connection") as imap_check,
            patch(
                "cases.inbound_views.smtp.check_connection",
                side_effect=__import__(
                    "cases.inbound.smtp", fromlist=["SmtpError"]
                ).SmtpError("535 auth failed"),
            ) as smtp_check,
        ):
            resp = admin_client.post(TEST_URL, self.BODY, format="json")
        assert resp.status_code == 200
        assert resp.json() == {
            "imap": {"ok": True, "error": ""},
            "smtp": {"ok": False, "error": "535 auth failed"},
        }
        assert imap_check.call_args.args[4] == "typed"
        # No separate SMTP account typed: the IMAP login is reused.
        assert smtp_check.call_args.args[3:] == ("soporte@cliente.cl", "typed")

    def test_blank_password_uses_the_stored_one(self, admin_client, imap_mailbox):
        body = {**self.BODY, "imap_password": "", "mailbox_id": str(imap_mailbox.id)}
        with (
            patch("cases.inbound_views.imap.check_connection") as imap_check,
            patch("cases.inbound_views.smtp.check_connection"),
        ):
            admin_client.post(TEST_URL, body, format="json")
        assert imap_check.call_args.args[4] == "s3cret"


class FakeSmtp:
    """Rejects the first AUTH and drops the line on any second one, the way
    Gmail does -- the behaviour that used to hide the real 535."""

    def __init__(self, *_args, **_kwargs):
        self.esmtp_features = {"auth": "LOGIN PLAIN XOAUTH2"}
        self.auth_calls = []

    def starttls(self, context=None):
        return (220, b"ready")

    def ehlo_or_helo_if_needed(self):
        return None

    def auth_plain(self, challenge=None):
        return ""

    def auth(self, mechanism, authobject, initial_response_ok=True):
        import smtplib

        self.auth_calls.append(mechanism)
        if len(self.auth_calls) > 1:
            raise smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
        raise smtplib.SMTPAuthenticationError(
            535, b"5.7.8 Username and Password not accepted."
        )

    def login(self, *_args):
        raise AssertionError("must not fall back to trying every mechanism")

    def quit(self):
        return (221, b"bye")


class TestSmtpCheck:
    def test_reports_the_servers_own_rejection(self, allow_private):
        from cases.inbound import smtp

        fake = FakeSmtp()
        with patch("cases.inbound.smtp.smtplib.SMTP", return_value=fake):
            with pytest.raises(smtp.SmtpError) as excinfo:
                smtp.check_connection(
                    "smtp.cliente.cl", 587, "starttls", "soporte", "wrong"
                )
        assert str(excinfo.value) == "535 5.7.8 Username and Password not accepted."
        assert fake.auth_calls == ["PLAIN"]
