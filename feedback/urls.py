from django.urls import path

from .views import SendFeedbackView, ReceivedFeedbackView, SentFeedbackView

urlpatterns = [
    path("", SendFeedbackView.as_view(), name="send-feedback"),
    path("received/", ReceivedFeedbackView.as_view(), name="received-feedback"),
    path("sent/", SentFeedbackView.as_view(), name="sent-feedback"),
]