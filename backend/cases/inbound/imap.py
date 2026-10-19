"""Read new mail from a customer's own IMAP server.

Only ever opens the folder read-only and fetches with BODY.PEEK, so the
customer's own mail client sees exactly the read/unread state it would have
without the CRM. New mail is tracked by UID instead (see the cursor fields on
`InboundMailbox`), which is also why a mailbox's first poll imports nothing:
it only records where "new" starts.
"""

from __future__ import annotations

import imaplib
import re
import ssl
from dataclasses import dataclass, field

from cases.inbound.hosts import IMAP_PORTS, check_mail_host

DEFAULT_PORTS = {"ssl": 993, "starttls": 143}
TIMEOUT_SECONDS = 30
BATCH_SIZE = 50


class ImapError(Exception):
    pass


@dataclass
class FetchResult:
    uidvalidity: int
    # (uid, raw RFC 5322 bytes); raw is None if the message vanished between
    # SEARCH and FETCH (deleted by the customer meanwhile).
    messages: list[tuple[int, bytes | None]] = field(default_factory=list)
    # Set instead of `messages` when the cursor had to be (re)started.
    baseline_uid: int | None = None


def _describe(exc: BaseException) -> str:
    arg = exc.args[0] if exc.args else exc
    if isinstance(arg, bytes):
        arg = arg.decode("utf-8", errors="replace")
    return str(arg) or exc.__class__.__name__


def _quote(folder: str) -> str:
    return '"' + folder.replace("\\", "\\\\").replace('"', '\\"') + '"'


def connect(
    host: str, port: int | None, security: str, username: str, password: str
) -> imaplib.IMAP4:
    port = port or DEFAULT_PORTS[security]
    check_mail_host(host, port, IMAP_PORTS)
    context = ssl.create_default_context()
    conn = None
    try:
        if security == "ssl":
            conn = imaplib.IMAP4_SSL(
                host, port, ssl_context=context, timeout=TIMEOUT_SECONDS
            )
        else:
            conn = imaplib.IMAP4(host, port, timeout=TIMEOUT_SECONDS)
            conn.starttls(ssl_context=context)
        conn.login(username, password)
    except (imaplib.IMAP4.error, OSError) as exc:
        if conn is not None:
            try:
                conn.shutdown()
            except OSError:
                pass
        raise ImapError(_describe(exc)) from exc
    return conn


def _open_folder(conn: imaplib.IMAP4, folder: str) -> tuple[int, int]:
    """Select `folder` read-only; return (UIDVALIDITY, UIDNEXT)."""
    try:
        typ, data = conn.status(_quote(folder), "(UIDVALIDITY UIDNEXT)")
        text = (data[0] or b"").decode("utf-8", errors="replace") if data else ""
        validity = re.search(r"UIDVALIDITY (\d+)", text)
        uidnext = re.search(r"UIDNEXT (\d+)", text)
        if typ != "OK" or not validity or not uidnext:
            raise ImapError(f"Folder {folder!r} not found on the server.")
        typ, _data = conn.select(_quote(folder), readonly=True)
        if typ != "OK":
            raise ImapError(f"Folder {folder!r} can't be opened.")
    except imaplib.IMAP4.error as exc:
        raise ImapError(_describe(exc)) from exc
    return int(validity.group(1)), int(uidnext.group(1))


def _logout(conn: imaplib.IMAP4) -> None:
    try:
        conn.logout()
    except (imaplib.IMAP4.error, OSError):
        pass


def check_connection(
    host: str,
    port: int | None,
    security: str,
    username: str,
    password: str,
    folder: str,
) -> None:
    conn = connect(host, port, security, username, password)
    try:
        _open_folder(conn, folder or "INBOX")
    finally:
        _logout(conn)


def fetch_new(mailbox, batch_size: int = BATCH_SIZE) -> FetchResult:
    conn = connect(
        mailbox.imap_host,
        mailbox.imap_port,
        mailbox.imap_security,
        mailbox.imap_username,
        mailbox.imap_password(),
    )
    try:
        uidvalidity, uidnext = _open_folder(conn, mailbox.imap_folder or "INBOX")
        last = mailbox.imap_last_uid
        if last is None or mailbox.imap_uidvalidity != uidvalidity:
            return FetchResult(uidvalidity=uidvalidity, baseline_uid=uidnext - 1)
        if uidnext <= last + 1:
            return FetchResult(uidvalidity=uidvalidity)

        try:
            _typ, data = conn.uid("SEARCH", None, f"UID {last + 1}:*")
            # "N:*" always matches the newest message even when its UID is
            # below N, so filter rather than trust the range.
            uids = sorted(
                uid for uid in (int(u) for u in (data[0] or b"").split()) if uid > last
            )[:batch_size]
            messages = []
            for uid in uids:
                _typ, parts = conn.uid("FETCH", str(uid), "(BODY.PEEK[])")
                raw = next(
                    (p[1] for p in parts or [] if isinstance(p, tuple) and len(p) > 1),
                    None,
                )
                messages.append((uid, raw))
        except (imaplib.IMAP4.error, OSError) as exc:
            raise ImapError(_describe(exc)) from exc
        return FetchResult(uidvalidity=uidvalidity, messages=messages)
    finally:
        _logout(conn)
