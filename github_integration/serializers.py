from rest_framework import serializers

from .models import Repository, PullRequest, Commit


class RepositorySerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = Repository
        fields = ["id", "team", "team_name", "full_name", "last_synced_at", "created_at"]
        read_only_fields = ["last_synced_at", "created_at"]


class PullRequestSerializer(serializers.ModelSerializer):
    repository_name = serializers.CharField(source="repository.full_name", read_only=True)
    review_turnaround_hours = serializers.ReadOnlyField()

    class Meta:
        model = PullRequest
        fields = [
            "id", "repository", "repository_name", "number", "title", "author_username",
            "state", "additions", "deletions", "changed_files", "created_at", "updated_at",
            "merged_at", "first_review_at", "review_turnaround_hours",
        ]


class CommitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commit
        fields = ["id", "repository", "sha", "author_username", "message", "authored_at"]
