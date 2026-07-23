from rest_framework.routers import DefaultRouter

from .views import RepositoryViewSet, PullRequestViewSet, CommitViewSet

router = DefaultRouter()
router.register("repositories", RepositoryViewSet, basename="repository")
router.register("pull-requests", PullRequestViewSet, basename="pull-request")
router.register("commits", CommitViewSet, basename="commit")

urlpatterns = router.urls
