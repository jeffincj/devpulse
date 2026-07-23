from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    """
    Extends Django's built-in User with a role used for
    role-based permissions (Manager vs Developer).
    """

    class Role(models.TextChoices):
        MANAGER = "manager", "Manager"
        DEVELOPER = "developer", "Developer"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.DEVELOPER)
    github_username = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"
