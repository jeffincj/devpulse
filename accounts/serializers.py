from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["role", "github_username"]


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "profile"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=Profile.Role.choices, write_only=True, default=Profile.Role.DEVELOPER)
    github_username = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "role", "github_username"]

    def create(self, validated_data):
        role = validated_data.pop("role", Profile.Role.DEVELOPER)
        github_username = validated_data.pop("github_username", "")
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        # profile already auto-created by the signal; update it with role/github info
        user.profile.role = role
        user.profile.github_username = github_username
        user.profile.save()
        return user
