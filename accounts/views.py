from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .serializers import RegisterSerializer, UserSerializer, PublicProfileSerializer
from .models import Profile


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET /api/auth/me/   -> current user's full profile
    PATCH /api/auth/me/ -> update profile fields: github_username, role, full_name, date_of_birth
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
                        {"profile": {"github_username": ["This GitHub username is already linked to another account."]}}
                    )
                from github_integration.services import GitHubClient, GitHubAPIError
                try:
                    GitHubClient()._get(f"/users/{new_username}")
                except GitHubAPIError as e:
                    if "NOT_FOUND" in str(e):
                        raise ValidationError(
                            {"profile": {"github_username": ["This GitHub username doesn't exist. Double-check the spelling."]}}
                        )
                    else:
                        raise ValidationError(
                            {"profile": {"github_username": [f"Could not verify this username right now — try again in a minute. ({e})"]}}
                        )
            request.user.profile.github_username = new_username

        if "role" in profile_data and profile_data["role"] in ("manager", "developer"):
            request.user.profile.role = profile_data["role"]

        if "full_name" in profile_data:
            request.user.profile.full_name = profile_data["full_name"].strip()

        if "date_of_birth" in profile_data:
            request.user.profile.date_of_birth = profile_data["date_of_birth"] or None

        request.user.profile.save()
        return self.retrieve(request, *args, **kwargs)


class ChangePasswordView(APIView):
    """POST /api/auth/change-password/  body: {old_password, new_password}"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        old_password = request.data.get("old_password", "")
        new_password = request.data.get("new_password", "")

        if not request.user.check_password(old_password):
            return Response({"detail": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user=request.user)
        except DjangoValidationError as e:
            return Response({"detail": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new_password)
        request.user.save()
        return Response({"detail": "Password updated successfully."})


class PublicProfileByGithubView(APIView):
    """GET /api/users/by-github/<github_username>/ -> find a registered app user by their linked GitHub username."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, github_username):
        try:
            profile = Profile.objects.select_related("user").get(github_username__iexact=github_username)
        except Profile.DoesNotExist:
            return Response({"detail": "No registered user found with that GitHub username."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PublicProfileSerializer(profile.user).data)