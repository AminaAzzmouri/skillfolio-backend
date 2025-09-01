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
"""

from rest_framework import serializers
from datetime import date

from .models import Certificate, Project, Goal, GoalStep, Project as ProjectModel


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=4)


class CertificateSerializer(serializers.ModelSerializer):
    project_count = serializers.IntegerField(read_only=True)

    def validate_date_earned(self, value):
        if value and value > date.today():
            raise serializers.ValidationError("date_earned cannot be in the future.")
        return value

    class Meta:
        model = Certificate
        fields = "__all__"
        read_only_fields = ("id", "user",)


PHRASES = {
    "deliver_feature": "deliver a functional feature",
    "build_demo": "build a demonstrable prototype",
    "practice_skill": "practice a specific skill",
    "solve_problem": "solve a specific problem",
}


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = ("id", "user", "date_created",)

    # ---------- validators ----------
    def validate(self, attrs):
        sd = attrs.get("start_date")
        ed = attrs.get("end_date")
        if sd and ed and ed < sd:
            raise serializers.ValidationError({"end_date": "End date cannot be before start date."})
        return attrs

    # ---------- helpers ----------
    @staticmethod
    def _plural(n: int, word: str) -> str:
        return f"{n} {word if n == 1 else word + 's'}"

    def _duration_from_dates(self, data) -> str | None:
        sd = data.get("start_date")
        ed = data.get("end_date")
        if not sd or not ed:
            return None
        delta_days = (ed - sd).days
        if delta_days < 0:
            return None
        d = max(1, delta_days)
        if d < 14:
            return self._plural(d, "day")
        if d < 60:
            weeks = round(d / 7.0) or 1
            return self._plural(weeks, "week")
        if d < 365:
            months = round(d / 30.0) or 1
            return self._plural(months, "month")
        years = round(d / 365.0) or 1
        return self._plural(years, "year")

    def _duration_phrase(self, data) -> str:
        by_dates = self._duration_from_dates(data)
        if by_dates:
            return by_dates
        txt = (data.get("duration_text") or "").strip()
        return txt or "some time"

    def _derive_duration_text_if_needed(self, validated_data):
        """
        Compute duration_text from start/end dates (if available).
        """
        by_dates = self._duration_from_dates(validated_data)
        if by_dates:
            validated_data["duration_text"] = by_dates

    def _build_description(self, data):
        title = (data.get("title") or "This").strip()
        work = (data.get("work_type") or "individual").strip()
        dur = self._duration_phrase(data)
        goal_key = (data.get("primary_goal") or "").strip()
        goal = PHRASES.get(goal_key, "achieve a goal")
        problem = (data.get("problem_solved") or "").strip()
        challenges = (data.get("challenges_short") or "").strip()
        tools = ", ".join([t.strip() for t in (data.get("tools_used") or "").split(",") if t.strip()])
        skills = ", ".join([s.strip() for s in (data.get("skills_used") or "").split(",") if s.strip()])
        improve = (data.get("skills_to_improve") or "").strip()

        parts = [
            f"{title} was a {work} project completed in {dur}.",
            f"The main goal was to {goal}."
        ]
        if problem:
            parts.append(f"It addressed: {problem}.")
        if challenges:
            parts.append(f"Challenges encountered: {challenges}.")
        if tools or skills:
            parts.append(f"Key tools/skills: {', '.join(filter(None, [tools, skills]))}.")
        if improve:
            parts.append(f"Next, I plan to improve: {improve}.")
        return " ".join(parts)

    # ---------- behavior ----------
    def create(self, validated_data):
        self._derive_duration_text_if_needed(validated_data)
        desc = str(validated_data.get("description") or "").strip()
        if not desc:
            validated_data["description"] = self._build_description(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "description" in validated_data:
            if not str(validated_data["description"]).strip():
                validated_data.pop("description")
            self._derive_duration_text_if_needed(validated_data)
            return super().update(instance, validated_data)

        driver_fields = {
            "title", "work_type",
            "start_date", "end_date",
            "primary_goal", "problem_solved", "tools_used", "skills_used",
            "challenges_short", "skills_to_improve"
        }
        changed_driver = any(f in validated_data for f in driver_fields)

        self._derive_duration_text_if_needed(validated_data)

        if changed_driver:
            current = {f: getattr(instance, f, None) for f in driver_fields | {"title"}}
            merged = {**current, **validated_data}
            validated_data["description"] = self._build_description(merged)

        return super().update(instance, validated_data)


class GoalStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalStep
        fields = ["id", "goal", "title", "is_done", "order", "created_at"]
        read_only_fields = ["id", "created_at"]


class GoalSerializer(serializers.ModelSerializer):
    progress_percent = serializers.SerializerMethodField(read_only=True)
    steps_progress_percent = serializers.ReadOnlyField()
    steps_total = serializers.ReadOnlyField()
    steps_completed = serializers.ReadOnlyField()
    steps = GoalStepSerializer(many=True, read_only=True)

    def validate_target_projects(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("target_projects must be > 0.")
        return value

    def validate_deadline(self, value):
        from datetime import date as _date
        if value and value < _date.today():
            raise serializers.ValidationError("deadline cannot be in the past.")
        return value

    def get_progress_percent(self, obj):
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
        read_only_fields = (
            "id",
            "user",
            "created_at",
            "progress_percent",
            "steps_progress_percent",
            "steps_total",
            "steps_completed",
        )


