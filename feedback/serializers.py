from rest_framework import serializers

from .models import Feedback


class FeedbackSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)
    recipient_username = serializers.CharField(source="recipient.username", read_only=True)
    repository_name = serializers.CharField(source="repository.full_name", read_only=True)

    class Meta:
        model = Feedback
        fields = [
            "id", "sender", "sender_username", "recipient", "recipient_username",
            "team", "repository", "repository_name", "message", "created_at",
        ]
        read_only_fields = ["sender", "created_at"]