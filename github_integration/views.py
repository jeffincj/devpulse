from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Repository, PullRequest, Commit
from .serializers import RepositorySerializer, PullRequestSerializer, CommitSerializer
from .services import sync_repository, GitHubAPIError, GitHubClient
from teams.permissions import IsTeamManagerOrReadOnly


class RepositoryViewSet(viewsets.ModelViewSet):
    """
    /api/repositories/            -> list, create
    /api/repositories/{id}/       -> retrieve, update, delete
    /api/repositories/{id}/sync/  -> POST triggers a live GitHub pull
    """
    queryset = Repository.objects.select_related("team").all()
    serializer_class = RepositorySerializer
    permission_classes = [permissions.IsAuthenticated, IsTeamManagerOrReadOnly]
    filterset_fields = ["team"]
    
    def create(self, request, *args, **kwargs):
        full_name = request.data.get("full_name", "").strip()
        try:
            client = GitHubClient()
            client.get_repository(full_name)  # this raises GitHubAPIError if it doesn't exist
        except GitHubAPIError as e:
            return Response(
                {"full_name": [f"This repository doesn't exist on GitHub, or the name is wrong: {e}"]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)
    
    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        repository = self.get_object()
        try:
            summary = sync_repository(repository)
        except GitHubAPIError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(summary, status=status.HTTP_200_OK)
    @action(detail=True, methods=["get"])
    def details(self, request, pk=None):
        repository = self.get_object()
        try:
            client = GitHubClient()
            data = client.get_repository(repository.full_name)
        except GitHubAPIError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({
            "full_name": data["full_name"],
            "description": data.get("description"),
            "owner": data["owner"]["login"],
            "owner_avatar": data["owner"]["avatar_url"],
            "stars": data.get("stargazers_count"),
            "forks": data.get("forks_count"),
            "open_issues": data.get("open_issues_count"),
            "created_on_github": data.get("created_at"),
            "default_branch": data.get("default_branch"),
        })

class PullRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    /api/pull-requests/                 -> list (filter by repository, state, author_username)
    /api/pull-requests/pending-review/   -> GET open PRs with no review yet
    """
    queryset = PullRequest.objects.select_related("repository").all()
    serializer_class = PullRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["repository", "state", "author_username"]
    search_fields = ["title", "author_username"]
    ordering_fields = ["created_at", "updated_at", "merged_at"]

    @action(detail=False, methods=["get"], url_path="pending-review")
    def pending_review(self, request):
        qs = self.get_queryset().filter(state="open", first_review_at__isnull=True)
        repo_id = request.query_params.get("repository")
        if repo_id:
            qs = qs.filter(repository_id=repo_id)
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page or qs, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)


class CommitViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Commit.objects.select_related("repository").all()
    serializer_class = CommitSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["repository", "author_username"]
    ordering_fields = ["authored_at"]
