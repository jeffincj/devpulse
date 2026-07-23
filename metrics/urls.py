from django.urls import path

from .views import (
    SprintVelocityView, PRTurnaroundView, CodeChurnView, ContributorActivityView,
    CompareContributorsView, CommitTimelineView, MyStatsView, TeamFlagsView,
)

urlpatterns = [
    path("velocity/", SprintVelocityView.as_view(), name="metric-velocity"),
    path("pr-turnaround/", PRTurnaroundView.as_view(), name="metric-pr-turnaround"),
    path("code-churn/", CodeChurnView.as_view(), name="metric-code-churn"),
    path("contributor-activity/", ContributorActivityView.as_view(), name="metric-contributor-activity"),
    path("compare/", CompareContributorsView.as_view(), name="metric-compare"),
    path("timeline/", CommitTimelineView.as_view(), name="metric-timeline"),
    path("my-stats/", MyStatsView.as_view(), name="metric-my-stats"),
    path("flags/", TeamFlagsView.as_view(), name="metric-flags"),
]