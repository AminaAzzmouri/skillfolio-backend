"""
serializers.py — DRF serializers for Skillfolio

Purpose
===============================================================================
Serializers define how our Django models (Certificate, Project, Goal) are
converted to/from JSON for the API. They also enforce field-level constraints
and protect server-controlled fields.

Key principles used here:
- We expose all model fields via fields="__all__" for now (simple MVP).
- We mark server-owned fields as read-only so the client cannot set them:
  * user:     always set from request.user in the ViewSet (perform_create)
  * id:       auto-generated PK
  * timestamps: created_at / date_created are server set

If custom validation is needed (e.g., disallow past deadlines), we can add
`validate_*` methods or an overall `validate()` method in the serializer classes.
"""

from rest_framework import serializers
from .models import Certificate, Project, Goal


class CertificateSerializer(serializers.ModelSerializer):
    """
    CertificateSerializer
    =============================================================================
    Converts Certificate model instances <-> JSON payloads.

    Read-only fields:
      - id:   DB-generated
      - user: injected in the ViewSet (serializer.save(user=request.user))

    Notes:
      - To restrict future dates for `date_earned`, we might add a validator
        (example provided below, commented out).
      - File uploads (file_upload) are supported via multipart/form-data.
    """

    # Example: enable later if you want to forbid future-earned dates
    # def validate_date_earned(self, value):
    #     from datetime import date
    #     if value > date.today():
    #         raise serializers.ValidationError("date_earned cannot be in the future.")
    #     return value

    class Meta:
        model = Certificate
        fields = "__all__"
        read_only_fields = ("id", "user",)


class ProjectSerializer(serializers.ModelSerializer):
    """
    ProjectSerializer
    =============================================================================
    Handles serialization for Project objects.

    Read-only fields:
      - id:           DB-generated
      - user:         injected in the ViewSet (serializer.save(user=request.user))
      - date_created: set automatically by the model (auto_now_add)

    Notes:
      - `certificate` is optional and may be null (project not linked).
      - Add additional validations later (e.g., min/max length of description).
    """

    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = ("id", "user", "date_created",)


class GoalSerializer(serializers.ModelSerializer):
    """
    GoalSerializer
    =============================================================================
    Manages serialization for Goal objects.

    Read-only fields:
      - id:         DB-generated
      - user:       injected in the ViewSet (serializer.save(user=request.user))
      - created_at: set automatically by the model (auto_now_add)

    Suggested validations (optional):
      - target_projects should be a positive integer
      - deadline should not be in the past
    """

    # Example: enable later in case we want to enforce positive targets
    # def validate_target_projects(self, value):
    #     if value <= 0:
    #         raise serializers.ValidationError("target_projects must be > 0.")
    #     return value

    # Example: enable later in case we want to forbid past deadlines
    # def validate_deadline(self, value):
    #     from datetime import date
    #     if value < date.today():
    #         raise serializers.ValidationError("deadline cannot be in the past.")
    #     return value

    class Meta:
        model = Goal
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at",)
