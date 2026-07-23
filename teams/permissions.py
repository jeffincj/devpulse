from rest_framework import permissions


class IsManager(permissions.BasePermission):
    """
    Allows access only to users whose account-level profile role is 'manager'.
    Used for endpoints that mutate team-wide data (e.g. creating teams, syncing repos).
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        profile = getattr(request.user, "profile", None)
        return bool(profile and profile.role == "manager")


class IsTeamManagerOrReadOnly(permissions.BasePermission):
    """
    Read access for any authenticated team member.
    Write access only for the team's manager (or Django superusers).
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        team = obj if hasattr(obj, "manager") else getattr(obj, "team", None)
        return bool(
            request.user.is_superuser
            or (team and team.manager_id == request.user.id)
        )
