"""Where a tenant's mailbox settings are allowed to make this server connect.

IMAP/SMTP hosts and ports are typed in by an org admin -- in a hosted
deployment, a customer. Unchecked, that turns the poller and the "test
connection" button into a way to reach this deployment's own private network
(the database, Redis, cloud metadata endpoints). So: standard mail ports only,
and the host must resolve to public addresses only.
`ALLOW_PRIVATE_MAIL_HOSTS` exists for local development against a mail server
container; never set it in production.
"""

from __future__ import annotations

import ipaddress
import socket

from django.conf import settings

IMAP_PORTS = frozenset({143, 993})
SMTP_PORTS = frozenset({25, 465, 587, 2525})


class MailHostError(ValueError):
    pass


def check_mail_host(host: str, port: int, allowed_ports: frozenset[int]) -> None:
    if port not in allowed_ports:
        allowed = ", ".join(str(p) for p in sorted(allowed_ports))
        raise MailHostError(f"Port {port} is not allowed (use one of: {allowed}).")
    if getattr(settings, "ALLOW_PRIVATE_MAIL_HOSTS", False):
        return
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError) as exc:
        raise MailHostError(f"Can't resolve host {host!r}.") from exc
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise MailHostError(
                f"Host {host!r} resolves to a private or reserved address."
            )
