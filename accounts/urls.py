from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import RegisterView, MeView, ChangePasswordView, PublicProfileByGithubView, UploadPhotoView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("upload-photo/", UploadPhotoView.as_view(), name="upload-photo"),
    path("users/by-github/<str:github_username>/", PublicProfileByGithubView.as_view(), name="public-profile-by-github"),
]