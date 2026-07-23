from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Team, Membership, Sprint, JoinRequest


class MembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "team", "user", "username", "role", "joined_at"]
        read_only_fields = ["joined_at"]


class TeamSerializer(serializers.ModelSerializer):
    manager_username = serializers.CharField(source="manager.username", read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            "id", "name", "description", "manager", "manager_username",
            "member_count", "created_at",
        ]
        read_only_fields = ["created_at"]

    def get_member_count(self, obj):
        return obj.memberships.count()


class AddMemberSerializer(serializers.Serializer):
    username = serializers.CharField()
    role = serializers.ChoiceField(choices=Membership.Role.choices, default=Membership.Role.DEVELOPER)

    def validate_username(self, value):
        if not User.objects.filter(username=value).exists():
            raise serializers.ValidationError("No user with that username exists.")
        return value


class SprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sprint
        fields = ["id", "team", "name", "start_date", "end_date"]


class JoinRequestSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    manager_username = serializers.CharField(source="team.manager.username", read_only=True)

    class Meta:
        model = JoinRequest
        fields = ["id", "team", "team_name", "manager_username", "user", "username", "status", "created_at", "decided_at"]
        read_only_fields = ["status", "created_at", "decided_at", "user"]


class PublicTeamSerializer(serializers.ModelSerializer):
    manager_username = serializers.CharField(source="manager.username", read_only=True)

    class Meta:
        model = Team
        fields = ["id", "name", "description", "manager_username"]