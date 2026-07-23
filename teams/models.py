from django.contrib.auth.models import User
from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    manager = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="managed_teams"
    )
    members = models.ManyToManyField(User, through="Membership", related_name="teams")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        MANAGER = "manager", "Manager"
        DEVELOPER = "developer", "Developer"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.DEVELOPER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("team", "user")

    def __str__(self):
        return f"{self.user.username} @ {self.team.name} ({self.role})"


class Sprint(models.Model):
    """A time-boxed period used to compute sprint-level velocity metrics."""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="sprints")
    name = models.CharField(max_length=150)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.team.name} - {self.name}"


class JoinRequest(models.Model):
    """A developer's request to join a team, waiting on that team's manager to decide."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="join_requests")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="join_requests")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} -> {self.team.name} ({self.status})"