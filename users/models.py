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


NEW in this revision
===============================================================================
- Project duration is now **calendar-based**:
    • start_date + end_date are the single source of truth for duration
    • duration_text is auto-filled from dates (humanized) and kept for UI display
- Removed structured duration fields (duration_amount, duration_unit).
- Field labels:
    • skills_used → “Skills practiced” (verbose_name)
    • challenges_short → “Challenges encountered” (verbose_name)
- Description auto-generation still only runs when description is blank; it now
  prefers date-based duration (falling back to any existing duration_text).
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from datetime import date


# -----------------------------------------------------------------------------
# Helpers / Validators
# -----------------------------------------------------------------------------
def validate_file_size_5mb(f):
    """Reject files larger than 5 MB to keep uploads reasonable."""
    max_bytes = 5 * 1024 * 1024
    if f and getattr(f, "size", 0) > max_bytes:
        raise ValidationError("File too large (max 5 MB).")


class Certificate(models.Model):
    """
    Certificate
    =============================================================================
    Represents a course completion or credential.

    Relationships
    - user: owner of the record
    - projects: reverse FK from Project (related_name="projects")

    Fields
    - title: Name of the certificate
    - issuer: Organization/platform that issued it
    - date_earned: When it was achieved
    - file_upload: Optional PDF/image proof

    Validation
    - clean(): disallows future dates for date_earned
    - file type/size enforced via validators

    Tips
    - Consider adding fields like external ID or skill tags if needed later.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="certificates",
        help_text="Owner of this certificate.",
    )
    title = models.CharField(max_length=255, help_text="Certificate title.")
    issuer = models.CharField(max_length=255, help_text="Issuing organization/platform.")
    date_earned = models.DateField(help_text="Date when the certificate was earned.")
    file_upload = models.FileField(
        upload_to="certificates/",
        blank=True,
        null=True,
        help_text="Optional proof file (PDF/image).",
        validators=[
            FileExtensionValidator(allowed_extensions=["pdf", "png", "jpg", "jpeg", "webp"]),
            validate_file_size_5mb,
        ],
    )

    class Meta:
        ordering = ["-date_earned"]  # newest certificates first
        verbose_name = "Certificate"
        verbose_name_plural = "Certificates"

    def clean(self):
        """Prevent future dates for earned certificates."""
        if self.date_earned and self.date_earned > date.today():
            raise ValidationError({"date_earned": "date_earned cannot be in the future."})

    def __str__(self):
        return f"{self.title} - {self.issuer}"


class Project(models.Model):
    """
    Project
    =============================================================================
    Practical work a user completed; may be linked to a Certificate to connect
    learning to outcomes. Supports guided fields to help generate a clear
    description if the author leaves it blank.

    Key Fields
    - title: Name of the project
    - status: planned / in_progress / completed
    - work_type: individual or team
    - start_date + end_date: calendar range (preferred; duration is derived)
    - duration_text: human-readable duration (auto-derived; shown in Admin)
    - primary_goal: practice_skill / deliver_feature / build_demo / solve_problem
    - certificate: optional FK to a related Certificate
    - description: narrative (auto-generated if left blank)
    - date_created: timestamp (auto)

    Guided fields (used for auto-description; all optional)
    - tools_used, skills_used, problem_solved, challenges_short, skills_to_improve
    """

    STATUS_PLANNED = "planned"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_PLANNED, "Planned"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="projects",
        help_text="Owner of this project.",
    )
    title = models.CharField(max_length=255, help_text="Project title.")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PLANNED,
        help_text="Current status of the project.",
    )

    WORK_INDIVIDUAL = "individual"
    WORK_TEAM = "team"
    WORK_TYPE_CHOICES = [
        (WORK_INDIVIDUAL, "Individual"),
        (WORK_TEAM, "Team"),
    ]
    work_type = models.CharField(
        max_length=20,
        choices=WORK_TYPE_CHOICES,
        blank=True,
        null=True,
        help_text="Was this an individual or team project?"
    )

    # Preferred: date range
    start_date = models.DateField(null=True, blank=True, verbose_name="Start date", help_text="Optional start date.")
    end_date   = models.DateField(null=True, blank=True, verbose_name="End date",   help_text="Optional end date.")

    # Human-friendly duration string (derived from dates; displayed in Admin/UI)
    duration_text = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Duration",
        help_text="Auto-filled from start/end dates.",
    )

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
    primary_goal = models.CharField(
        max_length=30,
        choices=PRIMARY_GOAL_CHOICES,
        blank=True,
        null=True,
        help_text="The main intent behind this project."
    )

    certificate = models.ForeignKey(
        Certificate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        help_text="Optionally link this project to a certificate.",
    )

    tools_used = models.TextField(
        blank=True,
        help_text="(Optional) Which tools/technologies did you use?"
    )
    skills_used = models.TextField(
        blank=True,
        null=True,
        verbose_name="Skills practiced",
        help_text="Skills practiced (CSV or short text)."
    )
    problem_solved = models.TextField(
        blank=True,
        help_text="(Optional) What problem did this project solve?"
    )
    challenges_short = models.TextField(
        blank=True,
        null=True,
        verbose_name="Challenges encountered",
        help_text="Key challenges faced (short)."
    )
    skills_to_improve = models.TextField(blank=True, null=True, help_text="What to practice more next time.")
    description = models.TextField(help_text="What you built, how, tools used, and impact.", blank=True)

    date_created = models.DateTimeField(auto_now_add=True, help_text="When this project was created.")

    class Meta:
        ordering = ["-date_created"]  # recent-first
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def __str__(self):
        return self.title

    # ----------------------------- Duration helpers -----------------------------
    @staticmethod
    def _plural(n: int, word: str) -> str:
        return f"{n} {word if n == 1 else word + 's'}"

    def _duration_from_dates(self) -> str | None:
        """
        Humanize start_date → end_date:
        - < 14 days: 'N days'
        - < 60 days: '~N weeks'
        - < 365 days: '~N months'
        - otherwise: '~N years'
        Returns None if dates are incomplete or invalid.
        """
        if not self.start_date or not self.end_date:
            return None
        delta_days = (self.end_date - self.start_date).days
        if delta_days < 0:
            return None
        d = max(1, delta_days)  # treat same-day as 1 day
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
        """
        Human-friendly duration, preferring dates; falls back to stored text.
        """
        by_dates = self._duration_from_dates()
        if by_dates:
            return by_dates
        return self.duration_text or ""

    def _sync_duration_text(self):
        """
        Keep duration_text derived from dates.
        """
        by_dates = self._duration_from_dates()
        if by_dates:
            self.duration_text = by_dates
        # else leave as-is (may be blank)

    # -------------------- Validation & description generation -------------------
    def clean(self):
        """Validate date range if both provided."""
        errors = {}
        if self.start_date and self.end_date and self.end_date < self.start_date:
            errors["end_date"] = "End date cannot be before start date."
        if errors:
            raise ValidationError(errors)

    def _generated_description(self) -> str:
        """
        Build a concise description using any guided fields that are present.
        """
        bits = []

        # Opening line with role and/or duration if available
        opening = f"{self.title}".strip() if self.title else "This project"
        role = None
        if self.work_type == self.WORK_INDIVIDUAL:
            role = "individual project"
        elif self.work_type == self.WORK_TEAM:
            role = "team project"

        dur = self.duration_human.strip() if self.duration_human else None
        if role and dur:
            bits.append(f"{opening} was a {role} completed in {dur}.")
        elif role:
            bits.append(f"{opening} was a {role}.")
        elif dur:
            bits.append(f"{opening} was completed in {dur}.")
        else:
            bits.append(f"{opening}.")

        # Primary goal (human phrasing)
        goal_map = {
            self.GOAL_PRACTICE: "practice and strengthen key skills",
            self.GOAL_DELIVER: "deliver a functional feature",
            self.GOAL_DEMO: "build a demonstrable prototype",
            self.GOAL_SOLVE: "solve a specific problem",
        }
        if self.primary_goal in goal_map:
            bits.append(f"The main goal was to {goal_map[self.primary_goal]}.")

        # Problem solved
        if self.problem_solved:
            bits.append(f"It addressed: {self.problem_solved.strip()}.")
            
        # Challenges encountered
        if self.challenges_short:
            bits.append(f"Challenges encountered: {self.challenges_short.strip()}.")

        # Tools / skills
        tools = []
        if self.tools_used:
            tools.append(self.tools_used.strip())
        if self.skills_used and self.skills_used.strip() != (self.tools_used or "").strip():
            tools.append(self.skills_used.strip())
        if tools:
            bits.append(f"Key tools/skills: {', '.join(tools)}.")

        # Reflection / next steps
        if self.skills_to_improve:
            bits.append(f"Next, I plan to improve: {self.skills_to_improve.strip()}.")

        return " ".join(bits).strip()

    def save(self, *args, **kwargs):
        """
        On save:
        - Keep duration_text in sync (prefer dates).
        - If `description` is blank/whitespace, compose one from the guided fields.
        - If `description` already has content, we respect the author's text.
        """
        self._sync_duration_text()
        if not self.description or not self.description.strip():
            self.description = self._generated_description()
        super().save(*args, **kwargs)


class Goal(models.Model):
    """
    Goal
    =============================================================================
    A simple target like “complete 5 projects by YYYY-MM-DD”, with optional
    checklist steps.

    Fields
    - title: short human-readable name for the goal
    - target_projects: positive integer target
    - deadline: date by which the target should be met
    - created_at: timestamp when the goal was created

    NEW (Checklist-style progress)
    - total_steps: total number of sub-steps (optional, default 0)
    - completed_steps: number of sub-steps completed (optional, default 0)
      The two are clamped in clean() so 0 <= completed_steps <= total_steps.

    Computed Progress
    - steps_progress_percent:
        • If the goal has any GoalStep rows, compute from those (preferred).
        • Otherwise, fall back to total_steps/completed_steps integers.

    Validation
    - clean(): ensures a positive target and non-past deadline; clamps checklist fields

    Notes
    - progress_percent (existing, serializer-computed): based on user's completed
      projects vs target_projects.
    - steps_progress_percent (model property): based on checklist ratio.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="goals",
        help_text="Owner of this goal.",
    )
    title = models.CharField(max_length=255, help_text="Short label for this goal.")
    target_projects = models.IntegerField(help_text="Number of projects to complete.")
    deadline = models.DateField(help_text="Target deadline.")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Creation timestamp.")

    # Existing checklist integers (kept for compatibility / optional use)
    total_steps = models.PositiveIntegerField(default=0, help_text="Total checklist steps (optional).")
    completed_steps = models.PositiveIntegerField(default=0, help_text="Completed checklist steps (optional).")

    class Meta:
        ordering = ["deadline"]
        verbose_name = "Goal"
        verbose_name_plural = "Goals"

    def clean(self):
        """
        Ensure data integrity:
        - target_projects must be a positive integer
        - deadline cannot be in the past
        - clamp checklist fields: 0 <= completed_steps <= total_steps
        """
        from datetime import date as _date
        errors = {}
        if self.target_projects is None or self.target_projects <= 0:
            errors["target_projects"] = "target_projects must be a positive integer."
        if self.deadline and self.deadline < _date.today():
            errors["deadline"] = "deadline cannot be in the past."

        # Clamp checklist fields
        if self.total_steps is None or self.total_steps < 0:
            self.total_steps = 0
        if self.completed_steps is None or self.completed_steps < 0:
            self.completed_steps = 0
        if self.completed_steps > self.total_steps:
            self.completed_steps = self.total_steps

        if errors:
            raise ValidationError(errors)

    # --- Derived counters from named steps (preferred when steps exist) ---
    @property
    def steps_total(self) -> int:
        return getattr(self, "steps", None).count() if hasattr(self, "steps") else 0

    @property
    def steps_completed(self) -> int:
        rel = getattr(self, "steps", None)
        return rel.filter(is_done=True).count() if rel is not None else 0

    @property
    def steps_progress_percent(self):
        """
        Percent complete based on checklist.
        Priority: if there are named steps (GoalStep), compute from those;
        otherwise, fall back to total_steps/completed_steps integers.
        """
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
