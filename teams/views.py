from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Team, Membership, Sprint, JoinRequest
from .serializers import (
    TeamSerializer, MembershipSerializer, AddMemberSerializer, SprintSerializer,
    JoinRequestSerializer, PublicTeamSerializer,
)
from .permissions import IsTeamManagerOrReadOnly


class TeamViewSet(viewsets.ModelViewSet):
    """
    /api/teams/                     -> list, create
    /api/teams/{id}/                -> retrieve, update, delete
    /api/teams/{id}/add-member/     -> POST add a member to the team
    /api/teams/{id}/remove-member/  -> POST remove a member from the team
    /api/teams/{id}/members/        -> GET list members
    """
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeamManagerOrReadOnly]

    def get_queryset(self):
        # Only show teams the logged-in user actually belongs to
        return Team.objects.filter(memberships__user=self.request.user).distinct().order_by("name")

    def perform_create(self, serializer):
        team = serializer.save(manager=self.request.user)
        Membership.objects.get_or_create(
            team=team, user=self.request.user, defaults={"role": Membership.Role.MANAGER}
        )

    @action(detail=True, methods=["post"], url_path="add-member")
    def add_member(self, request, pk=None):
        team = self.get_object()
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get(username=serializer.validated_data["username"])
        membership, created = Membership.objects.update_or_create(
            team=team, user=user,
            defaults={"role": serializer.validated_data["role"]},
        )
        return Response(
            MembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="remove-member")
    def remove_member(self, request, pk=None):
        team = self.get_object()
        username = request.data.get("username")
        deleted, _ = Membership.objects.filter(team=team, user__username=username).delete()
        if not deleted:
            return Response({"detail": "Membership not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        team = self.get_object()
        memberships = team.memberships.select_related("user")
        return Response(MembershipSerializer(memberships, many=True).data)


class SprintViewSet(viewsets.ModelViewSet):
    queryset = Sprint.objects.all()
    serializer_class = SprintSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["team"]


class PublicTeamListView(generics.ListAPIView):
    """GET /api/public-teams/ -> browse ALL teams (to find one to request joining)."""
    queryset = Team.objects.all().order_by("name")
    serializer_class = PublicTeamSerializer
    permission_classes = [permissions.IsAuthenticated]


class RequestJoinView(APIView):
    """POST /api/teams/{id}/request-join/ -> developer asks to join this team."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if Membership.objects.filter(team=team, user=request.user).exists():
            return Response({"detail": "You're already a member of this team."}, status=status.HTTP_400_BAD_REQUEST)
        existing = JoinRequest.objects.filter(team=team, user=request.user, status=JoinRequest.Status.PENDING).first()
        if existing:
            return Response({"detail": "You already have a pending request for this team."}, status=status.HTTP_400_BAD_REQUEST)
        join_request = JoinRequest.objects.create(team=team, user=request.user)
        return Response(JoinRequestSerializer(join_request).data, status=status.HTTP_201_CREATED)


class MyJoinRequestsView(generics.ListAPIView):
    """GET /api/join-requests/mine/ -> a developer's own requests and their status."""
    serializer_class = JoinRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return JoinRequest.objects.filter(user=self.request.user)


class PendingJoinRequestsView(generics.ListAPIView):
    """GET /api/join-requests/pending/ -> requests waiting on teams THIS manager owns."""
    serializer_class = JoinRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return JoinRequest.objects.filter(team__manager=self.request.user, status=JoinRequest.Status.PENDING)


class DecideJoinRequestView(APIView):
    """POST /api/join-requests/{id}/decide/  body: {"decision": "accept" | "reject"}"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        join_request = get_object_or_404(JoinRequest, pk=pk)
        if join_request.team.manager_id != request.user.id:
            return Response({"detail": "Only this team's manager can decide this request."}, status=status.HTTP_403_FORBIDDEN)
        decision = request.data.get("decision")
        if decision not in ("accept", "reject"):
            return Response({"detail": "decision must be 'accept' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)

        join_request.status = JoinRequest.Status.ACCEPTED if decision == "accept" else JoinRequest.Status.REJECTED
        join_request.decided_at = timezone.now()
        join_request.save()

        if decision == "accept":
            Membership.objects.get_or_create(
                team=join_request.team, user=join_request.user, defaults={"role": Membership.Role.DEVELOPER}
            )
        return Response(JoinRequestSerializer(join_request).data)