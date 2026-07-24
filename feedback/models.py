from django.contrib.auth.models import User
from django.db import models

from teams.models import Team
from github_integration.models import Repository


class Feedback(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_feedback")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_feedback")
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    repository = models.ForeignKey(Repository, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sender.username} -> {self.recipient.username}"