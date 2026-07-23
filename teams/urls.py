from rest_framework.routers import DefaultRouter

from .views import (
    TeamViewSet, SprintViewSet, PublicTeamListView, RequestJoinView,
    MyJoinRequestsView, PendingJoinRequestsView, DecideJoinRequestView,
)
from django.urls import path

router = DefaultRouter()
router.register("teams", TeamViewSet, basename="team")
router.register("sprints", SprintViewSet, basename="sprint")

urlpatterns = router.urls + [
    path("public-teams/", PublicTeamListView.as_view(), name="public-teams"),
    path("teams/<int:pk>/request-join/", RequestJoinView.as_view(), name="request-join"),
    path("join-requests/mine/", MyJoinRequestsView.as_view(), name="my-join-requests"),
    path("join-requests/pending/", PendingJoinRequestsView.as_view(), name="pending-join-requests"),
    path("join-requests/<int:pk>/decide/", DecideJoinRequestView.as_view(), name="decide-join-request"),
]