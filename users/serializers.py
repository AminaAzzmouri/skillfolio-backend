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


Week 4 Enhancements
-------------------------------------------------------------------------------
- CertificateSerializer: validate date_earned not in the future (so API surfaces
  a clear error); file types/size are also checked by model validators.
- ProjectSerializer: includes new fields (status, problem_solved, tools_used,
  impact) and **guided question fields** (work_type, duration_text, primary_goal,
  challenges_short, skills_used, outcome_short, skills_to_improve). The model
  auto-generates `description` on save if it’s blank.
 
- GoalSerializer: exposes a computed read-only field `progress_percent`, which
  reflects completed projects vs target_projects for the current user.

Week 5 Notes (feature/analytics-endpoints)
-------------------------------------------------------------------------------
- Analytics goals endpoint reuses GoalSerializer; `progress_percent` requires
  `context={"request": request}` so it can compute based on the current user.
"""

from rest_framework import serializers
from datetime import date

from .models import Certificate, Project, Goal, Project as ProjectModel


class CertificateSerializer(serializers.ModelSerializer):
    """
    CertificateSerializer
    =============================================================================
    Converts Certificate model instances <-> JSON payloads.

    Read-only fields:
      - id:   DB-generated
      - user: injected in the ViewSet (serializer.save(user=request.user))

    Notes:
      - Validates that `date_earned` is not in the future (API-level UX).
      - File uploads (file_upload) are supported via multipart/form-data.
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
    Handles serialization for Project objects.

    Read-only fields:
      - id:           DB-generated
      - user:         injected in the ViewSet (serializer.save(user=request.user))
      - date_created: set automatically by the model (auto_now_add)

    Notes:
      - `certificate` is optional and may be null (project not linked).
      - New fields: status, problem_solved, tools_used, impact,
        work_type, duration_text, primary_goal, challenges_short,
        skills_used, outcome_short, skills_to_improve.
      - If `description` is blank, the model will auto-generate it from the guided fields.
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
      - id:               DB-generated
      - user:             injected in the ViewSet (serializer.save(user=request.user))
      - created_at:       set automatically by the model (auto_now_add)
      - progress_percent: computed (read-only) — ratio of completed projects to target.

    Suggested validations (optional):
      - target_projects should be a positive integer
      - deadline should not be in the past
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
        Compute % progress = (# of completed projects) / target_projects * 100
        based on the current authenticated user.
        If target_projects == 0, return 0 to avoid division-by-zero.
        """
        request = self.context.get("request")
        if not request or not getattr(request, "user", None) or not request.user.is_authenticated:
            return 0

        target = obj.target_projects or 0
        if target <= 0:
            return 0

        # Count completed projects for this user
        from .models import Project as ProjectModel
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


