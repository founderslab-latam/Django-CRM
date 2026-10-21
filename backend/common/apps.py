from django.apps import AppConfig


class CommonConfig(AppConfig):
    name = "common"

    def ready(self):
        from django.conf import settings
        from django.core.mail.utils import DNS_NAME
        from django.utils.encoding import punycode

        import common.signals  # noqa: F401  # pylint: disable=unused-import

        # Django names the Message-ID of every mail it builds, and the SMTP
        # EHLO, after socket.getfqdn() -- inside a container that's its random
        # hostname (`<...@3ff0ce5802c8>`), which spam filters score against.
        # DNS_NAME is the one cached instance both read, so seeding it here
        # covers the web process and the Celery worker alike.
        if settings.EMAIL_MESSAGE_ID_DOMAIN:
            DNS_NAME._fqdn = punycode(settings.EMAIL_MESSAGE_ID_DOMAIN)
