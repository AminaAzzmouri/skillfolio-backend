"""
models.py — Core domain models for Skillfolio


Purpose
===============================================================================
Capture learning artifacts and progress for each user:
- Certificate: proof of learning (metadata + optional uploaded file)
- Project: practical work (optionally linked to a Certificate)
- Goal: a lightweight target (e.g., “finish 5 projects by a date”)
  NEW:
    • optional checklist-style progress via total_steps/completed_steps
      + computed steps_progress_percent (fallback)
    • named checklist items via GoalStep (preferred)
    • Goal now has a title


Auth model
- Uses Django's built-in User for simplicity. If profile fields are needed later,
  add a Profile model (OneToOne to User) or switch to a custom user model.


Design notes
- All models are user-scoped (FK to User) which makes per-user filtering simple
  and safely enforces ownership in the API layer.
- Timestamps use auto_now_add where helpful to audit creation time.
- Certificate uploads are stored under MEDIA_ROOT/certificates/.


Migrations
- Adding Goal.title and GoalStep requires new migrations.
- Existing total_steps/completed_steps remain for compatibility; when Goal.steps
  exist, progress is derived from them; otherwise we fall back to the integers.


NEW
===============================================================================
- Project duration is **calendar-based**:
    • start_date + end_date are the source of truth for duration
    • duration_text is auto-filled from dates (humanized) and kept for UI
- Removed structured duration fields (duration_amount, duration_unit).
- Field labels:
    • skills_used → “Skills practiced” (verbose_name)
    • challenges_short → “Challenges encountered” (verbose_name)
- Description auto-generation still only runs when description is blank; it now
  prefers date-based duration (falling back to any existing duration_text).


(status-aware rules & text)
===============================================================================
- Validation:
    • start_date is **required** for all statuses.
    • Planned:     start_date must be **today or future**.
    • In Progress: start_date must be **today or past**.
    • Completed:   start_date must be **yesterday or earlier** (strictly before today),
                   end_date is **required**, must be **strictly after** start_date,
                   and **cannot be in the future**.
    • Non-completed: end_date must be empty (we also clear it in save()).
- Description: opening sentence adapts to status:
    • Completed  → “... was a … completed in <duration>.”
    • In Progress → **present tense** (“... is a … project started since <start_date>.”)
    • Planned    → **present/future tense** (“... is a planned … starting on <start_date>.”)
  Duration is only mentioned for completed projects.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from datetime import date, timedelta


def validate_file_size_5mb(f):
    max_bytes = 5 * 1024 * 1024
    if f and getattr(f, "size", 0) > max_bytes:
        raise ValidationError("File too large (max 5 MB).")


class Certificate(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="certificates",
        help_text="Owner of this certificate."
    )
    title = models.CharField(max_length=255, help_text="Certificate title.")
    issuer = models.CharField(max_length=255, help_text="Issuing organization/platform.")
    date_earned = models.DateField(help_text="Date when the certificate was earned.")
    file_upload = models.FileField(
        upload_to="certificates/", blank=True, null=True,
        help_text="Optional proof file (PDF/image).",
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "png", "jpg", "jpeg", "webp"]), validate_file_size_5mb],
    )

    class Meta:
        ordering = ["-date_earned"]
        verbose_name = "Certificate"
        verbose_name_plural = "Certificates"

    def clean(self):
        if self.date_earned and self.date_earned > date.today():
            raise ValidationError({"date_earned": "date_earned cannot be in the future."})

    def __str__(self):
        return f"{self.title} - {self.issuer}"


class Project(models.Model):
    STATUS_PLANNED = "planned"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_PLANNED, "Planned"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects", help_text="Owner of this project.")
    title = models.CharField(max_length=255, help_text="Project title.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED, help_text="Current status of the project.")

    WORK_INDIVIDUAL = "individual"
    WORK_TEAM = "team"
    WORK_TYPE_CHOICES = [(WORK_INDIVIDUAL, "Individual"), (WORK_TEAM, "Team")]
    work_type = models.CharField(max_length=20, choices=WORK_TYPE_CHOICES, blank=True, null=True, help_text="Was this an individual or team project?")

    # Dates
    start_date = models.DateField(
        null=True, blank=True, verbose_name="Start date",
        help_text="Required. Planned: today or future; In progress: today or past; Completed: yesterday or earlier."
    )
    end_date   = models.DateField(
        null=True, blank=True, verbose_name="End date",
        help_text="Required when status is Completed; must be after Start date."
    )

    # Human-friendly duration string (derived from dates; displayed in Admin/UI)
    duration_text = models.CharField(max_length=100, blank=True, null=True, verbose_name="Duration", help_text="Auto-filled from start/end dates.")

    GOAL_PRACTICE = "practice_skill"
    GOAL_DELIVER = "deliver_feature"
    GOAL_DEMO = "build_demo"
    GOAL_SOLVE = "solve_problem"
    PRIMARY_GOAL_CHOICES = [
        (GOAL_PRACTICE, "Practice a skill"),
        (GOAL_DELIVER, "Deliver a feature"),
        (GOAL_DEMO, "Build a demo"),
        (GOAL_SOLVE, "Solve a problem"),
    ]
    primary_goal = models.CharField(max_length=30, choices=PRIMARY_GOAL_CHOICES, blank=True, null=True, help_text="The main intent behind this project.")

    certificate = models.ForeignKey("Certificate", on_delete=models.SET_NULL, null=True, blank=True, related_name="projects", help_text="Optionally link this project to a certificate.")

    tools_used = models.TextField(blank=True, help_text="(Optional) Which tools/technologies did you use?")
    skills_used = models.TextField(blank=True, null=True, verbose_name="Skills practiced", help_text="Skills practiced (CSV or short text).")
    problem_solved = models.TextField(blank=True, help_text="(Optional) What problem did this project solve?")
    challenges_short = models.TextField(blank=True, null=True, verbose_name="Challenges encountered", help_text="Key challenges faced (short).")
    skills_to_improve = models.TextField(blank=True, null=True, help_text="What to practice more next time.")
    description = models.TextField(help_text="What you built, how, tools used, and impact.", blank=True)

    date_created = models.DateTimeField(auto_now_add=True, help_text="When this project was created.")

    class Meta:
        ordering = ["-date_created"]
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def __str__(self):
        return self.title

    # ----------------------------- Duration helpers -----------------------------
    @staticmethod
    def _plural(n: int, word: str) -> str:
        return f"{n} {word if n == 1 else word + 's'}"

    def _duration_from_dates(self) -> str | None:
        if not self.start_date or not self.end_date:
            return None
        delta_days = (self.end_date - self.start_date).days
        if delta_days <= 0:
            return None
        d = delta_days
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

    @property
    def duration_human(self) -> str:
        if self.status == self.STATUS_COMPLETED:
            by_dates = self._duration_from_dates()
            if by_dates:
                return by_dates
        return ""

    def _sync_duration_text(self):
        if self.status == self.STATUS_COMPLETED:
            self.duration_text = self._duration_from_dates() or None
        else:
            self.duration_text = None

    # -------------------- Validation & description generation -------------------
    def clean(self):
        """
        Validate status-aware rules:

        - start_date is required for all statuses.
        - Planned:     start_date >= today.
        - In Progress: start_date <= today.
        - Completed:   start_date <= yesterday (strictly before today), end_date is required,
                       end_date > start_date, end_date <= today.
        - Non-completed: end_date must be empty.
        """
        errors = {}
        today = date.today()
        yesterday = today - timedelta(days=1)

        # start_date required always
        if not self.start_date:
            # single friendly message to avoid duplicate form+model errors
            errors["start_date"] = "The project must have a start date"

        # Status-based start rules (only if a date is provided)
        if self.start_date:
            if self.status == self.STATUS_PLANNED and self.start_date < today:
                errors["start_date"] = "For planned projects, Start date must be today or in the future."
            elif self.status == self.STATUS_IN_PROGRESS and self.start_date > today:
                errors["start_date"] = "Start date cannot be in the future for in-progress projects."
            elif self.status == self.STATUS_COMPLETED and self.start_date > yesterday:
                # i.e., today or future is invalid for completed
                errors["start_date"] = "For completed projects, Start date must be before today."

        # End date rules
        if self.status == self.STATUS_COMPLETED:
            if not self.end_date:
                errors["end_date"] = "Completed projects must have an end date."
            else:
                if self.start_date and self.end_date <= self.start_date:
                    errors["end_date"] = "End date must be after Start date (at least one day)."
                if self.end_date > today:
                    errors["end_date"] = "End date cannot be in the future for a completed project."
        else:
            if self.end_date:
                errors["end_date"] = "Set status to Completed to provide an end date."

        if errors:
            raise ValidationError(errors)

    def _generated_description(self) -> str:
        """
        Build a status-aware description.
        - COMPLETED  : past tense (“was … completed in …”); goal phrased as “was to …”
        - IN PROGRESS: present tense & “so far” language
        - PLANNED    : present/future tense & “will use” language
        Only include clauses for fields that are actually filled.
        """
        opening = f"{self.title}".strip() if self.title else "This project"
        # role words geared for natural phrasing
        role_word = "individual" if self.work_type == self.WORK_INDIVIDUAL else ("team" if self.work_type == self.WORK_TEAM else None)

        bits = []

        # COMPLETED → past tense
        if self.status == self.STATUS_COMPLETED:
            dur = self.duration_human.strip() if self.duration_human else None
            if role_word and dur:
                bits.append(f"{opening} was a {role_word} project completed in {dur}.")
            elif role_word:
                bits.append(f"{opening} was a {role_word} project.")
            elif dur:
                bits.append(f"{opening} was completed in {dur}.")
            else:
                bits.append(f"{opening} was completed.")
            # goal (past)
            goal_map = {
                self.GOAL_PRACTICE: "practice and strengthen key skills",
                self.GOAL_DELIVER: "deliver a functional feature",
                self.GOAL_DEMO: "build a demonstrable prototype",
                self.GOAL_SOLVE: "solve a specific problem",
            }
            if self.primary_goal in goal_map:
                bits.append(f"The main goal was to {goal_map[self.primary_goal]}.")
            # problem/challenges/tools/skills (past-neutral)
            if self.problem_solved:
                bits.append(f"It addressed: {self.problem_solved.strip()}.")
            if self.challenges_short:
                bits.append(f"Challenges encountered: {self.challenges_short.strip()}.")
            used = []
            if self.tools_used:
                used.append(self.tools_used.strip())
            if self.skills_used and self.skills_used.strip() != (self.tools_used or "").strip():
                used.append(self.skills_used.strip())
            if used:
                bits.append(f"Key tools/skills: {', '.join(used)}.")
            if self.skills_to_improve:
                bits.append(f"Next, I plan to improve: {self.skills_to_improve.strip()}.")

            return " ".join(bits).strip()

        # IN PROGRESS → present tense with “so far”
        if self.status == self.STATUS_IN_PROGRESS:
            since = f" started since {self.start_date.isoformat()}" if self.start_date else ""
            if role_word:
                bits.append(f"{opening} is a {role_word} project{since}.")
            else:
                bits.append(f"{opening} is a project{since}.")
            # goal (present)
            goal_map = {
                self.GOAL_PRACTICE: "practice and strengthen key skills",
                self.GOAL_DELIVER: "deliver a functional feature",
                self.GOAL_DEMO: "build a demonstrable prototype",
                self.GOAL_SOLVE: "solve a specific problem",
            }
            if self.primary_goal in goal_map:
                bits.append(f"The main goal is to {goal_map[self.primary_goal]}.")
            # so-far clauses
            if self.problem_solved:
                bits.append(f"So far it addresses: {self.problem_solved.strip()}.")
            if self.challenges_short:
                bits.append(f"Challenges encountered so far are: {self.challenges_short.strip()}.")
            sofar = []
            if self.tools_used:
                sofar.append(self.tools_used.strip())
            if self.skills_used and self.skills_used.strip() != (self.tools_used or "").strip():
                sofar.append(self.skills_used.strip())
            if sofar:
                bits.append(f"Key skills/tools practiced so far: {', '.join(sofar)}.")
            if self.skills_to_improve:
                bits.append(f"Next I’ll improve: {self.skills_to_improve.strip()}.")
            return " ".join(bits).strip()

        # PLANNED → present/future tense
        if role_word and self.start_date:
            bits.append(f"{opening} is a planned {role_word} project starting on {self.start_date.isoformat()}.")
        elif role_word:
            bits.append(f"{opening} is a planned {role_word} project.")
        elif self.start_date:
            bits.append(f"{opening} is planned to start on {self.start_date.isoformat()}.")
        else:
            bits.append(f"{opening} is a planned project.")

        goal_map = {
            self.GOAL_PRACTICE: "practice and strengthen key skills",
            self.GOAL_DELIVER: "deliver a functional feature",
            self.GOAL_DEMO: "build a demonstrable prototype",
            self.GOAL_SOLVE: "solve a specific problem",
        }
        if self.primary_goal in goal_map:
            bits.append(f"The main goal is to {goal_map[self.primary_goal]}.")

        if self.tools_used:
            bits.append(f"The tools I’m willing to use are: {self.tools_used.strip()}.")
        if self.skills_to_improve:
            bits.append(f"I plan to improve: {self.skills_to_improve.strip()}.")

        return " ".join(bits).strip()

    def save(self, *args, **kwargs):
        # Immediately drop end_date if status is not Completed (pre-save safety)
        if self.status != self.STATUS_COMPLETED:
            self.end_date = None
        self._sync_duration_text()
        if not self.description or not self.description.strip():
            self.description = self._generated_description()
        super().save(*args, **kwargs)


class Goal(models.Model):
    """
    A user-scoped target with optional checklist support.

    Label updates (model-level):
      - target_projects   -> "Target number of projects to build"
      - total_steps       -> "Overall required steps"
      - completed_steps   -> "Accomplished steps"
    These names now propagate to admin, forms, and serializers by default.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="goals",
        help_text="Owner of this goal.",
    )
    title = models.CharField(max_length=255, help_text="Short label for this goal.")

    # Keep IntegerField (positivity still enforced by clean()) to avoid risky data migration.
    # If you want a stricter field type later, we can switch to PositiveIntegerField in a follow-up.
    target_projects = models.IntegerField(
        verbose_name="Target number of projects to build",
        help_text="Number of projects to complete (must be ≥ 1).",
    )

    deadline = models.DateField(
        help_text="Target deadline."
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Creation timestamp.",
    )

    total_steps = models.PositiveIntegerField(
        default=0,
        verbose_name="Overall required steps",
        help_text="Total checklist steps (optional).",
    )

    completed_steps = models.PositiveIntegerField(
        default=0,
        verbose_name="Accomplished steps",
        help_text="Completed checklist steps (optional).",
    )

    class Meta:
        ordering = ["deadline"]
        verbose_name = "Goal"
        verbose_name_plural = "Goals"

    def clean(self):
        from datetime import date as _date
        errors = {}

        # Must be positive
        if self.target_projects is None or self.target_projects <= 0:
            errors["target_projects"] = "target_projects must be a positive integer."

        # Future-only deadline
        if self.deadline and self.deadline < _date.today():
            errors["deadline"] = "deadline cannot be in the past."

        # Normalize step counters and keep consistency
        if self.total_steps is None or self.total_steps < 0:
            self.total_steps = 0
        if self.completed_steps is None or self.completed_steps < 0:
            self.completed_steps = 0
        if self.completed_steps > self.total_steps:
            self.completed_steps = self.total_steps

        if errors:
            raise ValidationError(errors)

    @property
    def steps_total(self) -> int:
        return getattr(self, "steps", None).count() if hasattr(self, "steps") else 0

    @property
    def steps_completed(self) -> int:
        rel = getattr(self, "steps", None)
        return rel.filter(is_done=True).count() if rel is not None else 0

    @property
    def steps_progress_percent(self):
        total = self.steps_total
        if total > 0:
            done = self.steps_completed
            return round(100 * (done / float(total)))
        if self.total_steps:
            return round(100 * (self.completed_steps / float(self.total_steps)))
        return 0

    def __str__(self):
        return f"{self.user.username} - {self.title or ''} ({self.target_projects} by {self.deadline})"


class GoalStep(models.Model):
    """
    A named checklist item for a Goal.
    - goal: FK to parent Goal (owner-scoped via the goal's user)
    - title: short description of the step
    - is_done: checkmark state
    - order: optional ordering integer
    - created_at: timestamp
    """
    goal = models.ForeignKey(
        Goal,
        on_delete=models.CASCADE,
        related_name="steps",
        help_text="Parent goal for this step.",
    )
    title = models.CharField(max_length=255, help_text="Step title/label.")
    is_done = models.BooleanField(default=False, help_text="Checked/done?")
    order = models.IntegerField(default=0, help_text="Optional manual ordering.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"[{'x' if self.is_done else ' '}] {self.title}"

    # ------- keep parent goal counts in sync on every change -------
    def _sync_parent_counts(self):
        gid = self.goal_id
        # Recompute totals from the DB to avoid drift.
        total = GoalStep.objects.filter(goal_id=gid).count()
        done = GoalStep.objects.filter(goal_id=gid, is_done=True).count()
        # Use update() to avoid triggering Goal.clean() validations while syncing.
        Goal.objects.filter(pk=gid).update(total_steps=total, completed_steps=done)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_parent_counts()

    def delete(self, *args, **kwargs):
        gid = self.goal_id
        super().delete(*args, **kwargs)
        # After delete, recompute using gid (self.goal_id no longer available)
        total = GoalStep.objects.filter(goal_id=gid).count()
        done = GoalStep.objects.filter(goal_id=gid, is_done=True).count()
        Goal.objects.filter(pk=gid).update(total_steps=total, completed_steps=done)
