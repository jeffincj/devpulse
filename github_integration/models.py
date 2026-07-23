from django.db import models
from teams.models import Team


class Repository(models.Model):
    """A GitHub repo (e.g. 'octocat/hello-world') linked to one of our teams."""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="repositories")
    full_name = models.CharField(
        max_length=255, help_text="owner/repo, e.g. 'razorpay/checkout'"
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("team", "full_name")

    def __str__(self):
        return self.full_name


class PullRequest(models.Model):
    class State(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        MERGED = "merged", "Merged"

    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name="pull_requests")
    number = models.IntegerField()
    title = models.CharField(max_length=500)
    author_username = models.CharField(max_length=150)
    state = models.CharField(max_length=20, choices=State.choices)

    additions = models.IntegerField(default=0)
    deletions = models.IntegerField(default=0)
    changed_files = models.IntegerField(default=0)

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    merged_at = models.DateTimeField(null=True, blank=True)
    first_review_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp of the first review submitted on this PR"
    )

    class Meta:
        unique_together = ("repository", "number")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.repository.full_name}#{self.number}"

    @property
    def review_turnaround_hours(self):
        """Hours between PR creation and its first review. None if not yet reviewed."""
        if not self.first_review_at:
            return None
        delta = self.first_review_at - self.created_at
        return round(delta.total_seconds() / 3600, 2)


class Commit(models.Model):
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name="commits")
    sha = models.CharField(max_length=40)
    author_username = models.CharField(max_length=150, blank=True)
    message = models.TextField(blank=True)
    authored_at = models.DateTimeField()

    class Meta:
        unique_together = ("repository", "sha")
        ordering = ["-authored_at"]

    def __str__(self):
        return f"{self.repository.full_name}@{self.sha[:7]}"
