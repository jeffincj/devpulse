from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError
from django.contrib.auth.models import User

from .serializers import RegisterSerializer, UserSerializer
from .models import Profile


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/  -> create a new user (manager or developer)."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET /api/auth/me/   -> return the currently authenticated user's profile.
    PATCH /api/auth/me/ -> update profile fields (e.g. github_username).
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        profile_data = request.data.get("profile", {})

        if "github_username" in profile_data:
            new_username = profile_data["github_username"].strip()
            if new_username:
                already_taken = (
                    Profile.objects.filter(github_username=new_username)
                    .exclude(user=request.user)
                    .exists()
                )
                if already_taken:
                    raise ValidationError(
                        {"profile": {"github_username": [
                            "This GitHub username is already linked to another account."
                        ]}}
                    )

                from github_integration.services import GitHubClient, GitHubAPIError
                try:
                    GitHubClient()._get(f"/users/{new_username}")
                except GitHubAPIError as e:
                    if "NOT_FOUND" in str(e):
                        raise ValidationError(
                            {"profile": {"github_username": [
                                "This GitHub username doesn't exist. Double-check the spelling."
                            ]}}
                        )
                    else:
                        raise ValidationError(
                            {"profile": {"github_username": [
                                f"Could not verify this username right now — GitHub may be rate-limiting requests. Try again in a minute. ({e})"
                            ]}}
                        )

            request.user.profile.github_username = new_username

        if "role" in profile_data and profile_data["role"] in ("manager", "developer"):
            request.user.profile.role = profile_data["role"]

        request.user.profile.save()
        return self.retrieve(request, *args, **kwargs)