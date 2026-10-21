import socket

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail.utils import DNS_NAME


def test_message_id_uses_the_configured_domain_not_the_hostname():
    msg = EmailMessage("s", "b", to=["someone@example.com"]).message()

    assert msg["Message-ID"].endswith(f"@{settings.EMAIL_MESSAGE_ID_DOMAIN}>")
    assert not msg["Message-ID"].endswith(f"@{socket.gethostname()}>")


def test_smtp_ehlo_name_follows_the_same_domain():
    # The SMTP backend says EHLO with DNS_NAME.get_fqdn(); same seed.
    assert DNS_NAME.get_fqdn() == settings.EMAIL_MESSAGE_ID_DOMAIN
