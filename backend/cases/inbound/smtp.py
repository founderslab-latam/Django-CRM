"""Send replies through a customer's own SMTP server.

Sending as `soporte@cliente.cl` through this deployment's global mail backend
fails the customer domain's SPF/DKIM and lands in spam; sending through the
customer's own server doesn't, with no DNS changes on their side.
"""

from __future__ import annotations

import smtplib
import ssl

from django.core.mail.backends.smtp import EmailBackend

from cases.inbound.hosts import SMTP_PORTS, check_mail_host

DEFAULT_PORTS = {"ssl": 465, "starttls": 587}
TIMEOUT_SECONDS = 30


class SmtpError(Exception):
    pass


def _backend(
    host: str, port: int | None, security: str, username: str, password: str
) -> EmailBackend:
    port = port or DEFAULT_PORTS[security]
    check_mail_host(host, port, SMTP_PORTS)
    return EmailBackend(
        host=host,
        port=port,
        username=username,
        password=password,
        use_ssl=security == "ssl",
        use_tls=security == "starttls",
        timeout=TIMEOUT_SECONDS,
        fail_silently=False,
    )


def connection_for(mailbox) -> EmailBackend | None:
    """The connection replies from `mailbox` must go out on, or None for the
    deployment's default backend (mailboxes not on IMAP/SMTP)."""
    if mailbox.provider != "imap" or not mailbox.smtp_host:
        return None
    username, password = mailbox.smtp_login()
    return _backend(
        mailbox.smtp_host, mailbox.smtp_port, mailbox.smtp_security, username, password
    )


def _describe(exc: Exception) -> str:
    if isinstance(exc, smtplib.SMTPResponseException):
        text = exc.smtp_error
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")
        return f"{exc.smtp_code} {' '.join(str(text).split())}"
    return str(exc) or exc.__class__.__name__


def check_connection(
    host: str, port: int | None, security: str, username: str, password: str
) -> None:
    """Connect and log in, sending nothing.

    Not `EmailBackend.open()`: its `smtplib.login` retries every AUTH
    mechanism the server offers after a rejection, and Gmail drops the
    connection on the second try -- so a wrong password surfaced as
    "Connection unexpectedly closed" instead of the server's own 535. One
    mechanism, one answer.
    """
    port = port or DEFAULT_PORTS[security]
    check_mail_host(host, port, SMTP_PORTS)
    context = ssl.create_default_context()
    conn = None
    try:
        if security == "ssl":
            conn = smtplib.SMTP_SSL(
                host, port, timeout=TIMEOUT_SECONDS, context=context
            )
        else:
            conn = smtplib.SMTP(host, port, timeout=TIMEOUT_SECONDS)
            conn.starttls(context=context)
        conn.ehlo_or_helo_if_needed()
        conn.user, conn.password = username, password
        offered = conn.esmtp_features.get("auth", "").upper().split()
        if "PLAIN" in offered:
            conn.auth("PLAIN", conn.auth_plain)
        else:
            conn.login(username, password)
    except (smtplib.SMTPException, OSError) as exc:
        raise SmtpError(_describe(exc)) from exc
    finally:
        if conn is not None:
            try:
                conn.quit()
            except (smtplib.SMTPException, OSError):
                pass
