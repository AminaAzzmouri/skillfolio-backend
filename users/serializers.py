"""
serializers.py — DRF serializers for Skillfolio


Purpose
===============================================================================
Convert model instances to/from JSON for the API and enforce API-level
validations that complement model-level checks.

Principles
- Use fields="__all__" for a straightforward MVP, plus explicit serializer fields.
- Protect server-controlled fields by marking them read-only:
  * user: always set from request.user in the ViewSet
  * id: DB PK
  * timestamps: e.g., created_at or date_created
- Keep validations explicit so API consumers receive clear error messages.

NEW
- GoalSerializer: exposes title, checklist integers, derived step metrics, and nested steps.
- ProjectSerializer: prefers calendar dates (start_date, end_date) for duration.
  duration_text is auto-derived; description generation only when blank.

- Keep API behavior/documentation aligned with Admin:
- Field ORDER matches Admin forms/lists.
- Labels/help text mirror model/admin language.
- Project dates/description obey the same STATUS-aware rules as Admin.
- Goal field labels and positivity rules match Admin; steps are optional.

# Notes
- We still rely on model.clean() for final enforcement; serializers add
- friendly API-level messages and normalize data (e.g., clearing end_date when status != completed) so clients see the same behavior as Admin.
"""

from datetime import date, timedelta
from rest_framework import serializers

from .models import Certificate, Project, Goal, GoalStep, Project as ProjectModel


# --------------------------------------------------------------------------- #
# Small helpers                                                               #
# --------------------------------------------------------------------------- #

PHRASES = {
    "deliver_feature": "deliver a functional feature",
    "build_demo": "build a demonstrable prototype",
    "practice_skill": "practice and strengthen key skills",
    "solve_problem": "solve a specific problem",
}

def _today():
    return date.today()

def _yesterday():
    return _today() - timedelta(days=1)


# --------------------------------------------------------------------------- #
# Register payload                                                            #
# --------------------------------------------------------------------------- #

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=4)


# --------------------------------------------------------------------------- #
# Certificate                                                                 #
# --------------------------------------------------------------------------- #

class CertificateSerializer(serializers.ModelSerializer):
    # Compute on the fly so /api/docs works without queryset annotations.
    project_count = serializers.SerializerMethodField(read_only=True)

    def get_project_count(self, obj):
        try:
            return obj.projects.count()
        except Exception:
            return 0

    def validate_date_earned(self, value):
        if value and value > _today():
            raise serializers.ValidationError("date_earned cannot be in the future.")
        return value

    class Meta:
        model = Certificate
        # Order to match Admin: id/user up top, then core fields, then derived.
        fields = [
            "id",
            "user",
            "title",
            "issuer",
            "date_earned",
            "file_upload",
            "project_count",
        ]
        read_only_fields = ("id", "user")
        extra_kwargs = {
            "date_earned": {
                "help_text": "Must be today or a past date. Future dates are not allowed.",
            }
        }


# --------------------------------------------------------------------------- #
# Project                                                                     #
# --------------------------------------------------------------------------- #

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        # Order mirrors Admin form layout.
        fields = [
            "id",
            "user",
            "title",
            "status",
            "start_date",
            "end_date",
            "work_type",
            "duration_text",
            "primary_goal",
            "certificate",
            "problem_solved",
            "tools_used",
            "skills_used",
            "challenges_short",
            "skills_to_improve",
            "description",
            "date_created",
        ]
        read_only_fields = ("id", "user", "date_created")
        extra_kwargs = {
            # Admin shows dynamic help; we surface the same rules in the schema.
            "start_date": {
                "help_text": (
                    "Required. Planned: today or future; In progress: today or past; "
                    "Completed: yesterday or earlier (strictly before today)."
                ),
                "required": False,
            },
            "end_date": {
                "help_text": (
                    "Required only when status is Completed; must be strictly after Start date "
                    "and cannot be in the future. Cleared automatically when not Completed."
                ),
                "required": False,
            },
            "description": {"required": False},
            "duration_text": {"read_only": True},
        }

    # ---------- description helpers (match model/admin tone) ----------
    @staticmethod
    def _plural(n: int, word: str) -> str:
        return f"{n} {word if n == 1 else word + 's'}"

    def _duration_from_dates(self, sd, ed) -> str | None:
        if not sd or not ed:
            return None
        d = (ed - sd).days
        if d <= 0:
            return None
        if d < 14:
            return self._plural(d, "day")
        if d < 60:
            return self._plural(round(d / 7.0) or 1, "week")
        if d < 365:
            return self._plural(round(d / 30.0) or 1, "month")
        return self._plural(round(d / 365.0) or 1, "year")

    def _sync_duration_text_if_completed(self, payload: dict):
        status_val = payload.get("status", getattr(self.instance, "status", None))
        if status_val == Project.STATUS_COMPLETED:
            sd = payload.get("start_date", getattr(self.instance, "start_date", None))
            ed = payload.get("end_date", getattr(self.instance, "end_date", None))
            by_dates = self._duration_from_dates(sd, ed)
            payload["duration_text"] = by_dates or None
        else:
            # Keep None when not completed (mirrors model._sync_duration_text)
            payload["duration_text"] = None

    def _build_description(self, merged: dict) -> str:
        title = (merged.get("title") or "This project").strip()
        status_val = (merged.get("status") or Project.STATUS_PLANNED).strip()
        work_type = merged.get("work_type")
        role = "individual" if work_type == Project.WORK_INDIVIDUAL else ("team" if work_type == Project.WORK_TEAM else None)
        sd = merged.get("start_date")
        ed = merged.get("end_date")
        dur = self._duration_from_dates(sd, ed)
        goal_key = (merged.get("primary_goal") or "").strip()
        goal_phrase = PHRASES.get(goal_key)

        bits = []

        if status_val == Project.STATUS_COMPLETED:
            # Past tense; include duration if available
            if role and dur:
                bits.append(f"{title} was a {role} project completed in {dur}.")
            elif role:
                bits.append(f"{title} was a {role} project.")
            elif dur:
                bits.append(f"{title} was completed in {dur}.")
            else:
                bits.append(f"{title} was completed.")
            if goal_phrase:
                bits.append(f"The main goal was to {goal_phrase}.")
        elif status_val == Project.STATUS_IN_PROGRESS:
            since = f" started since {sd.isoformat()}" if sd else ""
            if role:
                bits.append(f"{title} is a {role} project{since}.")
            else:
                bits.append(f"{title} is a project{since}.")
            if goal_phrase:
                bits.append(f"The main goal is to {goal_phrase}.")
        else:  # planned
            if role and sd:
                bits.append(f"{title} is a planned {role} project starting on {sd.isoformat()}.")
            elif role:
                bits.append(f"{title} is a planned {role} project.")
            elif sd:
                bits.append(f"{title} is planned to start on {sd.isoformat()}.")
            else:
                bits.append(f"{title} is a planned project.")
            if goal_phrase:
                bits.append(f"The main goal is to {goal_phrase}.")

        # Shared optional clauses
        problem = (merged.get("problem_solved") or "").strip()
        challenges = (merged.get("challenges_short") or "").strip()
        tools = (merged.get("tools_used") or "").strip()
        skills = (merged.get("skills_used") or "").strip()
        improve = (merged.get("skills_to_improve") or "").strip()

        if status_val == Project.STATUS_IN_PROGRESS and problem:
            bits.append(f"So far it addresses: {problem}.")
        elif problem:
            bits.append(f"It addressed: {problem}.")

        if status_val == Project.STATUS_IN_PROGRESS and challenges:
            bits.append(f"Challenges encountered so far are: {challenges}.")
        elif challenges:
            bits.append(f"Challenges encountered: {challenges}.")

        # Combine tools/skills without duplication
        used = []
        if tools:
            used.append(tools)
        if skills and skills != tools:
            used.append(skills)
        if used:
            if status_val == Project.STATUS_IN_PROGRESS:
                bits.append(f"Key skills/tools practiced so far: {', '.join(used)}.")
            else:
                bits.append(f"Key tools/skills: {', '.join(used)}.")

        if improve:
            next_phrase = "Next I’ll improve" if status_val == Project.STATUS_IN_PROGRESS else "Next, I plan to improve"
            bits.append(f"{next_phrase}: {improve}.")

        return " ".join(bits).strip()

    # ---------- validation (mirror model.clean + admin auto-clear) ----------
    def validate(self, attrs):
        # Determine effective values across create/update
        st = attrs.get("status", getattr(self.instance, "status", Project.STATUS_PLANNED))
        sd = attrs.get("start_date", getattr(self.instance, "start_date", None))
        ed = attrs.get("end_date", getattr(self.instance, "end_date", None))
        today = _today()
        yesterday = _yesterday()

        # Start date must exist (model will enforce too, but be friendly early)
        if sd is None:
            raise serializers.ValidationError({"start_date": "The project must have a start date"})

        # Status-based start date rules
        if st == Project.STATUS_PLANNED and sd < today:
            raise serializers.ValidationError({"start_date": "For planned projects, Start date must be today or in the future."})
        if st == Project.STATUS_IN_PROGRESS and sd > today:
            raise serializers.ValidationError({"start_date": "Start date cannot be in the future for in-progress projects."})
        if st == Project.STATUS_COMPLETED and sd > yesterday:
            raise serializers.ValidationError({"start_date": "For completed projects, Start date must be before today."})

        # End date rules
        if st == Project.STATUS_COMPLETED:
            if ed is None:
                raise serializers.ValidationError({"end_date": "Completed projects must have an end date."})
            if ed <= sd:
                raise serializers.ValidationError({"end_date": "End date must be after Start date (at least one day)."})
            if ed > today:
                raise serializers.ValidationError({"end_date": "End date cannot be in the future for a completed project."})
        else:
            # Mirror Admin: quietly clear end_date when not completed.
            if "end_date" in attrs and attrs["end_date"] is not None:
                attrs["end_date"] = None

        return attrs

    # ---------- create/update ----------
    def create(self, validated_data):
        # Normalize duration_text to match Admin/model
        self._sync_duration_text_if_completed(validated_data)

        # Auto-generate description if missing/blank
        desc = str(validated_data.get("description") or "").strip()
        if not desc:
            # Build from incoming payload only
            validated_data["description"] = self._build_description(validated_data)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Normalize duration_text to match Admin/model
        self._sync_duration_text_if_completed(validated_data)

        # Determine if a “driver” field changed; if yes and description wasn’t
        # explicitly edited in this request, rebuild to stay aligned.
        driver_fields = {
            "title", "status", "work_type",
            "start_date", "end_date",
            "primary_goal",
            "problem_solved", "tools_used", "skills_used",
            "challenges_short", "skills_to_improve",
        }
        description_provided = "description" in validated_data
        driver_changed = any(f in validated_data for f in driver_fields)

        if description_provided:
            # If an empty/whitespace description is sent, drop it (keep/generate below).
            if not str(validated_data.get("description") or "").strip():
                validated_data.pop("description")

        if driver_changed and not description_provided:
            merged = {f: getattr(instance, f, None) for f in driver_fields | {"title", "status", "start_date", "end_date"}}
            merged.update(validated_data)
            validated_data["description"] = self._build_description(merged)

        return super().update(instance, validated_data)


# --------------------------------------------------------------------------- #
# Goal & GoalStep                                                             #
# --------------------------------------------------------------------------- #

class GoalStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalStep
        fields = ["id", "goal", "title", "is_done", "order", "created_at"]
        read_only_fields = ["id", "created_at"]


class GoalSerializer(serializers.ModelSerializer):
    # Derived metrics & nested steps (read-only)
    progress_percent = serializers.SerializerMethodField(read_only=True)
    steps_progress_percent = serializers.ReadOnlyField()
    steps_total = serializers.ReadOnlyField()
    steps_completed = serializers.ReadOnlyField()
    steps = GoalStepSerializer(many=True, read_only=True)

    # Enforce positivity at serializer level to match Admin min=1 UI
    target_projects = serializers.IntegerField(
        min_value=1,
        label="Target number of projects to build",
        help_text="Number of projects to complete (must be ≥ 1).",
    )

    class Meta:
        model = Goal
        # Order to match Admin form (each on its own line there)
        fields = [
            "id",
            "user",
            "title",
            "target_projects",
            "deadline",
            "total_steps",
            "completed_steps",
            "progress_percent",
            "steps_progress_percent",
            "steps_total",
            "steps_completed",
            "created_at",
            "steps",
        ]
        read_only_fields = (
            "id",
            "user",
            "created_at",
            "progress_percent",
            "steps_progress_percent",
            "steps_total",
            "steps_completed",
        )
        extra_kwargs = {
            "total_steps": {
                "required": False,
                "label": "Overall required steps",
                "help_text": "Optional.",
            },
            "completed_steps": {
                "required": False,
                "label": "Accomplished steps",
                "help_text": "Optional.",
            },
            "deadline": {
                "help_text": "Target deadline (must be today or future).",
            },
        }

    # Validators consistent with Admin/model
    def validate_deadline(self, value):
        if value and value < _today():
            raise serializers.ValidationError("deadline cannot be in the past.")
        return value

    def validate(self, attrs):
        # Keep completed_steps within total_steps (mirror model.clean safety)
        total = attrs.get("total_steps", getattr(self.instance, "total_steps", 0)) or 0
        done = attrs.get("completed_steps", getattr(self.instance, "completed_steps", 0)) or 0
        if done > total:
            attrs["completed_steps"] = total
        return attrs

    def get_progress_percent(self, obj):
        # Same semantics as before (user-scoped completed projects)
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


