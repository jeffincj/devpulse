from django.contrib.auth.models import User
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError

from .models import Feedback
from .serializers import FeedbackSerializer


class SendFeedbackView(generics.CreateAPIView):
    """POST /api/feedback/  body: {recipient_username, team, repository, message}"""
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        recipient_username = request.data.get("recipient_username")
        try:
            recipient = User.objects.get(username=recipient_username)
        except User.DoesNotExist:
            raise ValidationError({"recipient_username": ["No user with that username."]})

        serializer = self.get_serializer(data={
            "recipient": recipient.id,
            "team": request.data.get("team"),
            "repository": request.data.get("repository"),
            "message": request.data.get("message", ""),
        })
        serializer.is_valid(raise_exception=True)
        serializer.save(sender=request.user)
        return self.finalize_response(request, generics.Response(serializer.data, status=201), *args, **kwargs)


class ReceivedFeedbackView(generics.ListAPIView):
    """GET /api/feedback/received/"""
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Feedback.objects.filter(recipient=self.request.user)


class SentFeedbackView(generics.ListAPIView):
    """GET /api/feedback/sent/"""
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Feedback.objects.filter(sender=self.request.user)