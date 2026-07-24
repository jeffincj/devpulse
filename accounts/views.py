from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
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

        if "gender" in profile_data:
            request.user.profile.gender = profile_data["gender"]

        request.user.profile.save()
        return self.retrieve(request, *args, **kwargs)


class UploadPhotoView(APIView):
    """POST /api/auth/upload-photo/  multipart form with field 'photo'"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        photo = request.FILES.get("photo")
        if not photo:
            return Response({"detail": "No photo file provided."}, status=status.HTTP_400_BAD_REQUEST)

        import cloudinary.uploader
        try:
            result = cloudinary.uploader.upload(
                photo,
                folder="devpulse_profile_photos",
                public_id=f"user_{request.user.id}",
                overwrite=True,
                resource_type="image",
            )
        except Exception as e:
            return Response({"detail": f"Upload failed: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        request.user.profile.photo_url = result["secure_url"]
        request.user.profile.save()
        return Response({"photo_url": result["secure_url"]})


class ChangePasswordView(APIView):
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
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, github_username):
        try:
            profile = Profile.objects.select_related("user").get(github_username__iexact=github_username)
        except Profile.DoesNotExist:
            return Response({"detail": "No registered user found with that GitHub username."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PublicProfileSerializer(profile.user).data)