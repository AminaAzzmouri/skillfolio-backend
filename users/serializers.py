"""
serializers.py — DRF serializers for Skillfolio

Purpose
===============================================================================
Convert model instances to/from JSON for the API and enforce API-level
validations that complement model-level checks.

Principles
- Use fields="__all__" for a straightforward MVP.
- Protect server-controlled fields by marking them read-only:
  * user: always set from request.user in the ViewSet
  * id: DB PK
  * timestamps: e.g., created_at or date_created
- Keep validations explicit so API consumers receive clear error messages.
"""

from rest_framework import serializers
from datetime import date

from .models import Certificate, Project, Goal, Project as ProjectModel


class RegisterSerializer(serializers.Serializer):
    """
    RegisterSerializer
    =============================================================================
    Purpose
    - Document the request body for the public registration endpoint so
      Swagger (drf-yasg) can render a proper form in /api/docs/.

    Fields
    - email: Email address that becomes the username.
    - password: Plain text on input; your view sets it securely via set_password().

    Notes
    - This is NOT a ModelSerializer on purpose; it only describes the input.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=4)  # tweak min length as desired



class CertificateSerializer(serializers.ModelSerializer):
    """
    CertificateSerializer
    =============================================================================
    Fields
    - Maps directly from Certificate model.

    Read-only
    - id: database PK
    - user: assigned automatically from request.user in the ViewSet

    API Validation
    - validate_date_earned(): prevents future dates (explicit API feedback).
    """

    def validate_date_earned(self, value):
        if value and value > date.today():
            raise serializers.ValidationError("date_earned cannot be in the future.")
        return value

    class Meta:
        model = Certificate
        fields = "__all__"
        read_only_fields = ("id", "user",)


class ProjectSerializer(serializers.ModelSerializer):
    """
    ProjectSerializer
    =============================================================================
    Fields
    - Mirrors Project model including guided fields that may help auto-generate
      a description on the server.

    Read-only
    - id: DB PK
    - user: injected from request.user in the ViewSet
    - date_created: timestamp from the model
    """

    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = ("id", "user", "date_created",)


class GoalSerializer(serializers.ModelSerializer):
    """
    GoalSerializer
    =============================================================================
    Adds a computed, read-only `progress_percent` to show progress toward the
    target based on the authenticated user's completed projects.

    Read-only
    - id, user, created_at, progress_percent

    Validation (API-level; complements model.clean())
    - validate_target_projects(): must be > 0
    - validate_deadline(): cannot be in the past
    """

    progress_percent = serializers.SerializerMethodField(read_only=True)

    def validate_target_projects(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("target_projects must be > 0.")
        return value

    def validate_deadline(self, value):
        from datetime import date
        if value and value < date.today():
            raise serializers.ValidationError("deadline cannot be in the past.")
        return value

    def get_progress_percent(self, obj):
        """
        Compute:
            (# of user's completed projects) / target_projects * 100

        Notes
        - Requires the request in serializer context to know which user to count.
        - Returns 0 if target_projects is not positive or user is not available.
        """
        request = self.context.get("request")
        if not request or not getattr(request, "user", None) or not request.user.is_authenticated:
            return 0

        target = obj.target_projects or 0
        if target <= 0:
            return 0

        completed_count = ProjectModel.objects.filter(
            user=request.user,
            status=ProjectModel.STATUS_COMPLETED,
        ).count()

        pct = (completed_count / float(target)) * 100.0
        return round(max(0.0, min(pct, 100.0)), 2)

    class Meta:
        model = Goal
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at", "progress_percent",)
