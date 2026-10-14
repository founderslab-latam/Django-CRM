from django.apps import AppConfig


class ConversationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "conversations"
    verbose_name = "Conversations"

    def ready(self):
        import conversations.signals  # noqa: F401  # pylint: disable=unused-import
