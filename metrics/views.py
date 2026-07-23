from datetime import date

from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from teams.models import Team
from github_integration.models import Repository
from . import services


def _get_team_or_404(team_id):
    try:
        return Team.objects.get(pk=team_id)
    except Team.DoesNotExist:
        raise NotFound("Team not found.")


def _get_repo_or_404(repo_id):
    try:
        return Repository.objects.get(pk=repo_id)
    except Repository.DoesNotExist:
        raise NotFound("Repository not found.")


class SprintVelocityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        team_id = request.query_params.get("team_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not (team_id and start_date and end_date):
            raise ValidationError("team_id, start_date and end_date are required query params.")

        team = _get_team_or_404(team_id)
        try:
            start_date = date.fromisoformat(start_date)
            end_date = date.fromisoformat(end_date)
        except ValueError:
            raise ValidationError("start_date/end_date must be in YYYY-MM-DD format.")

        return Response(services.sprint_velocity(team, start_date, end_date))


class PRTurnaroundView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        repo_id = request.query_params.get("repository_id")
        if not repo_id:
            raise ValidationError("repository_id is a required query param.")
        days = int(request.query_params.get("days", 30))
        repository = _get_repo_or_404(repo_id)
        return Response(services.average_pr_turnaround(repository, days=days))


class CodeChurnView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        repo_id = request.query_params.get("repository_id")
        if not repo_id:
            raise ValidationError("repository_id is a required query param.")
        days = int(request.query_params.get("days", 30))
        repository = _get_repo_or_404(repo_id)
        return Response(services.code_churn(repository, days=days))


class ContributorActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        team_id = request.query_params.get("team_id")
        if not team_id:
            raise ValidationError("team_id is a required query param.")
        days = int(request.query_params.get("days", 30))
        team = _get_team_or_404(team_id)
        return Response(services.contributor_activity(team, days=days))


class CompareContributorsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        team_id = request.query_params.get("team_id")
        usernames_param = request.query_params.get("usernames")
        if not (team_id and usernames_param):
            raise ValidationError("team_id and usernames (comma-separated) are required.")
        usernames = [u.strip() for u in usernames_param.split(",") if u.strip()]
        days = int(request.query_params.get("days", 3650))
        team = _get_team_or_404(team_id)
        return Response(services.compare_contributors(team, usernames, days=days))


class CommitTimelineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        repo_id = request.query_params.get("repository_id")
        if not repo_id:
            raise ValidationError("repository_id is a required query param.")
        days = int(request.query_params.get("days", 180))
        repository = _get_repo_or_404(repo_id)
        return Response(services.commit_timeline(repository, days=days))


class MyStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 3650))
        return Response(services.my_stats(request.user, days=days))


class TeamFlagsView(APIView):
    """GET /api/metrics/flags/?team_id=1 -> auto-generated warnings for a manager."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        team_id = request.query_params.get("team_id")
        if not team_id:
            raise ValidationError("team_id is a required query param.")
        team = _get_team_or_404(team_id)
        return Response(services.team_flags(team))