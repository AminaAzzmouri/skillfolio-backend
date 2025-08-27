"""
models.py — Core domain models for Skillfolio

Purpose
===============================================================================
Capture learning artifacts and progress for each user:
- Certificate: proof of learning (metadata + optional uploaded file)
- Project: practical work (optionally linked to a Certificate)
- Goal: a lightweight target (e.g., “finish 5 projects by a date”)

Auth model
- Uses Django's built-in User for simplicity. If profile fields are needed later,
  add a Profile model (OneToOne to User) or switch to a custom user model.

Design notes
- All models are user-scoped (FK to User) which makes per-user filtering simple
  and safely enforces ownership in the API layer.
- Timestamps use auto_now_add where helpful to audit creation time.
- Certificate uploads are stored under MEDIA_ROOT/certificates/.
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
    - duration_text: short, human-readable duration (“2 weeks”, “weekend”)
    - primary_goal: practice_skill / deliver_feature / build_demo / solve_problem
    - certificate: optional FK to a related Certificate
    - description: narrative (auto-generated if left blank)
    - date_created: timestamp (auto)

    Guided fields (used for auto-description; all optional)
    - tools_used, skills_used, problem_solved, challenges_short,
      outcome_short, skills_to_improve
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

    duration_text = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Rough duration (e.g., '2 weeks', 'a weekend')."
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
    skills_used = models.TextField(blank=True, null=True, help_text="Skills/tools used (CSV or short text).")
    problem_solved = models.TextField(
        blank=True,
        help_text="(Optional) What problem did this project solve?"
    )
    challenges_short = models.TextField(blank=True, null=True, help_text="Key challenges faced (short).")
    outcome_short = models.TextField(blank=True, null=True, help_text="(Optional) What was the outcome or impact?")
    skills_to_improve = models.TextField(blank=True, null=True, help_text="What to practice more next time.")
    description = models.TextField(help_text="What you built, how, tools used, and impact.", blank=True)

    date_created = models.DateTimeField(auto_now_add=True, help_text="When this project was created.")

    class Meta:
        ordering = ["-date_created"]  # recent-first
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def __str__(self):
        return self.title

    # -----------------------------------------------------------------------------
    # Auto-generate description from guided answers when empty
    # -----------------------------------------------------------------------------
    def _generated_description(self) -> str:
        """
        Build a concise description using any guided fields that are present.
        This makes the record readable even when the author leaves description blank.
        """
        bits = []

        # Opening line with role and/or duration if available
        opening = f"{self.title}".strip() if self.title else "This project"
        role = None
        if self.work_type == self.WORK_INDIVIDUAL:
            role = "individual project"
        elif self.work_type == self.WORK_TEAM:
            role = "team project"

        dur = self.duration_text.strip() if self.duration_text else None
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
            bits.append(f"It addressed: {self.problem_solved.strip()}")

        # Tools / skills
        tools = []
        if self.tools_used:
            tools.append(self.tools_used.strip())
        if self.skills_used and self.skills_used.strip() != (self.tools_used or "").strip():
            tools.append(self.skills_used.strip())
        if tools:
            bits.append(f"Key tools/skills: {', '.join(tools)}.")

        # Outcome (prefer outcome_short; keep fallback for legacy/alt fields)
        if self.outcome_short:
            bits.append(f"Outcome: {self.outcome_short.strip()}")
        elif hasattr(self, "impact") and self.impact:  # guard for optional/legacy field
            bits.append(f"Impact: {self.impact.strip()}")

        # Reflection / next steps
        if self.skills_to_improve:
            bits.append(f"Next, I plan to improve: {self.skills_to_improve.strip()}.")

        return " ".join(bits).strip()

    def save(self, *args, **kwargs):
        """
        On save:
        - If `description` is blank/whitespace, compose one from the guided fields.
        - If `description` already has content, we respect the author's text.
        """
        if not self.description or not self.description.strip():
            self.description = self._generated_description()
        super().save(*args, **kwargs)


class Goal(models.Model):
    """
    Goal
    =============================================================================
    A simple target like “complete 5 projects by YYYY-MM-DD”.

    Fields
    - target_projects: positive integer target
    - deadline: date by which the target should be met
    - created_at: timestamp when the goal was created

    Validation
    - clean(): ensures a positive target and non-past deadline

    Notes
    - Progress percentage is computed in the serializer based on the user's
      number of completed projects relative to target_projects.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="goals",
        help_text="Owner of this goal.",
    )
    target_projects = models.IntegerField(help_text="Number of projects to complete.")
    deadline = models.DateField(help_text="Target deadline.")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Creation timestamp.")

    class Meta:
        ordering = ["deadline"]
        verbose_name = "Goal"
        verbose_name_plural = "Goals"

    def clean(self):
        """
        Ensure data integrity:
        - target_projects must be a positive integer
        - deadline cannot be in the past
        """
        from datetime import date as _date
        errors = {}
        if self.target_projects is None or self.target_projects <= 0:
            errors["target_projects"] = "target_projects must be a positive integer."
        if self.deadline and self.deadline < _date.today():
            errors["deadline"] = "deadline cannot be in the past."
        if errors:
            from django.core.exceptions import ValidationError
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.user.username} - {self.target_projects} projects by {self.deadline}"