"""
models.py — Core data models for Skillfolio (backend)

Purpose
===============================================================================
This module defines the core domain models behind Skillfolio’s learning tracker:
- Certificate: proofs of learning (optionally with uploaded files).
- Project: practical work optionally linked to a Certificate.
- Goal: lightweight planning (e.g., “finish 5 projects by a deadline”).

Auth Model
-------------------------------------------------------------------------------
We use Django’s built-in `User` for authentication to keep things simple.
If we ever need to extend profile data (bio, avatar, etc.), we can add a
`Profile` model with OneToOne to `User` or switch to a custom user model.

General Notes
-------------------------------------------------------------------------------
- All models are **user-scoped** (FK to `User`) to make per-user filtering and
  permissions straightforward.
- File uploads for certificates are stored under MEDIA_ROOT/certificates/.
- Timestamps use `auto_now_add=True` to capture creation time where useful.

Week 4 Enhancements
-------------------------------------------------------------------------------
- Certificate: server-side validations for date_earned (no future dates) and
  uploaded file (type/size).
- Project: added `status` (planned / in_progress / completed) and guided fields
  (`problem_solved`, `tools_used`, `impact`) to help users describe outcomes.
- Goal: compute progress later at the serializer level (percentage of completed
  projects vs target_projects).
  
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from datetime import date


# -----------------------------
# Helpers / validators (inline)
# -----------------------------
def validate_file_size_5mb(f):
    """Restrict uploads to <= 5 MB."""
    max_bytes = 5 * 1024 * 1024
    if f and getattr(f, "size", 0) > max_bytes:
        raise ValidationError("File too large (max 5 MB).")


class Certificate(models.Model):
    """
    Certificate
    =============================================================================
    Purpose
    ---------------------------------------------------------------------------
    Represents a verified learning achievement (e.g., a course completion).
    Stores issuer metadata and an optional uploaded file (PDF/image).

    Relationships
    ---------------------------------------------------------------------------
    - user: the owner of the certificate (FK to `auth.User`).
    - projects: reverse relation from Project → Certificate (related_name="projects").

    Key Fields
    ---------------------------------------------------------------------------
    - title (CharField): The certificate name (e.g., “Django Basics”).
    - issuer (CharField): Who issued it (e.g., Coursera, Udacity).
    - date_earned (DateField): When the certificate was earned.
    - file_upload (FileField, optional): The uploaded proof, saved to "certificates/".

    Behavior
    ---------------------------------------------------------------------------
    - __str__: readable representation "Title - Issuer".
    - clean(): validates that date_earned is not in the future.

    Future Enhancements
    ---------------------------------------------------------------------------
    - Extra fields: certificate_id/code, specialization/track, skill tags.
    - Indexes: add indexes if we’ll filter heavily by issuer or date_earned.
    
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="certificates",
        help_text="Owner of this certificate.",
    )
    title = models.CharField(max_length=255, help_text="Certificate title.")
    issuer = models.CharField(max_length=255, help_text="Organization/platform that issued the certificate.")
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
        ordering = ["-date_earned"]  # Show most recent certificates first
        verbose_name = "Certificate"
        verbose_name_plural = "Certificates"  # Makes admin interface cleaner.

    def clean(self):
        # Prevent future dates for earned certificates
        if self.date_earned and self.date_earned > date.today():
            raise ValidationError({"date_earned": "date_earned cannot be in the future."})

    def __str__(self):
        return f"{self.title} - {self.issuer}"


class Project(models.Model):
    """
    Project
    =============================================================================
    Purpose
    ---------------------------------------------------------------------------
    Captures practical work a user completed. A project can optionally be linked
    to a specific Certificate to show how learning was applied.

    Relationships
    ---------------------------------------------------------------------------
    - user: the owner of the project.
    - certificate (optional): FK to Certificate, nullable → projects can stand alone.

    Key Fields
    ---------------------------------------------------------------------------
    - title (CharField): Project name.
    - description (TextField): Details (what, how, tools, impact).
    - status (CharField): planned / in_progress / completed (added Week 4).
    - problem_solved/tools_used/impact (TextFields): guided description fields (Week 4).
    - date_created (DateTimeField auto_now_add): Creation timestamp.

    Behavior
    ---------------------------------------------------------------------------
    - __str__: returns the project title.

    Future Enhancements
    ---------------------------------------------------------------------------
    - Validation: minimum description length, profanity checks, etc.
    - Ordering: default ordering by -date_created for recent-first listings.
    
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
    certificate = models.ForeignKey(
        Certificate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        help_text="Optionally link this project to a certificate.",
    )
    title = models.CharField(max_length=255, help_text="Project title.")
    description = models.TextField(help_text="What you built, how, tools used, and impact.")

    # Week 4 additions:
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PLANNED,
        help_text="Current status of the project.",
    )
    problem_solved = models.TextField(
        blank=True,
        help_text="(Optional) What problem did this project solve?"
    )
    tools_used = models.TextField(
        blank=True,
        help_text="(Optional) Which tools/technologies did you use?"
    )
    impact = models.TextField(
        blank=True,
        help_text="(Optional) What was the outcome or impact?"
    )

    date_created = models.DateTimeField(auto_now_add=True, help_text="When this project was created.")

    class Meta:
        ordering = ["-date_created"]  # Recent-first ordering
        verbose_name = "Project"
        verbose_name_plural = "Projects"  # Makes admin interface cleaner.

    def __str__(self):
        return self.title


class Goal(models.Model):
    """
    Goal
    =============================================================================
    Purpose
    ---------------------------------------------------------------------------
    Lightweight planning tool for a user to set targets (e.g., “Build 5 projects
    by 2025-12-31”).

    Relationships
    ---------------------------------------------------------------------------
    - user: the owner of the goal.

    Key Fields
    ---------------------------------------------------------------------------
    - target_projects (IntegerField): Numeric target to hit.
    - deadline (DateField): When the target should be achieved by.
    - created_at (DateTimeField auto_now_add): Goal creation timestamp.

    Behavior
    ---------------------------------------------------------------------------
    - __str__: human-friendly summary.

    Future Enhancements
    ---------------------------------------------------------------------------
    - Validation: ensure deadline is not in the past.
    - Computed progress: percentage of user.projects completed vs target_projects.
    - Status: not_started / on_track / at_risk / achieved.
    
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="goals",
        help_text="Owner of this goal.",
    )
    target_projects = models.IntegerField(help_text="How many projects the user aims to complete.")
    deadline = models.DateField(help_text="Deadline for completing the target.")
    created_at = models.DateTimeField(auto_now_add=True, help_text="When this goal was created.")

    class Meta:
        ordering = ["deadline"]  # Goals listed by upcoming deadlines
        verbose_name = "Goal"
        verbose_name_plural = "Goals"  # Makes admin interface cleaner.

    def __str__(self):
        return f"{self.user.username} - {self.target_projects} projects by {self.deadline}"
