from django.apps import AppConfig


class CommonConfig(AppConfig):
    name = "common"

    def ready(self):
        from corsheaders.signals import check_request_enabled

        import common.signals  # noqa: F401  # pylint: disable=unused-import
        from common.cors import allow_custom_domain_origin

        check_request_enabled.connect(allow_custom_domain_origin)
