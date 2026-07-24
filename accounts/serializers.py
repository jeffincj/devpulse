from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    age = serializers.ReadOnlyField()

    class Meta:
        model = Profile
        fields = ["role", "github_username", "full_name", "date_of_birth", "age"]


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "profile"]


class PublicProfileSerializer(serializers.ModelSerializer):
    """Safe, limited info shown when one user views another's profile."""
    role = serializers.CharField(source="profile.role", read_only=True)
    github_username = serializers.CharField(source="profile.github_username", read_only=True)
    full_name = serializers.CharField(source="profile.full_name", read_only=True)

    class Meta:
        model = User
        fields = ["username", "full_name", "role", "github_username", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=Profile.Role.choices, write_only=True, default=Profile.Role.DEVELOPER)
    github_username = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "role", "github_username"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        role = validated_data.pop("role", Profile.Role.DEVELOPER)
        github_username = validated_data.pop("github_username", "")
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        user.profile.role = role
        user.profile.github_username = github_username
        user.profile.save()
        return user