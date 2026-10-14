from django.urls import path

from .views import ChatwootConversationListView

app_name = "conversations"

urlpatterns = [
    path(
        "chatwoot/",
        ChatwootConversationListView.as_view(),
        name="chatwoot_conversation_list",
    ),
]
