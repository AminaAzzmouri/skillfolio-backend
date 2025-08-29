"""
users/admin.py — Django Admin configuration for Skillfolio

Purpose
===============================================================================
Make the Django admin genuinely useful for day-to-day QA and debugging.
We expose the core models (Certificate, Project, Goal, and NEW GoalStep) with
sensible list columns, filters, search, and ordering so you can quickly find
and inspect data.

How to read this file (plain English):
- list_display: columns shown in the admin list page (the big table).
- list_filter: right-hand sidebar filters to narrow results without typing.
- search_fields: text search across chosen fields (substring match).
- ordering: default sort order in the list page.

Highlights
- Certificate: search by title/issuer, filter by issuer/date, newest first.
- Project: show owner, linked certificate, status, work type, duration, created date.
- Goal: now also shows a title; includes deadline/target and NEW checklist fields
        (total_steps, completed_steps) and a computed steps_progress% column.
        Inline editing of named steps (GoalStep) is provided.
- GoalStep: lightweight inline rows (title, is_done, order), tied to a Goal.

Notes
- Admin is for trusted staff only; normal clients use the REST API.
- Project model uses `date_created` (auto timestamp). That’s why ordering and
  filters reference `date_created` (not `created_at`).
"""

from django.contrib import admin
from .models import Certificate, Project, Goal, GoalStep


# -----------------------------------------------------------------------------
# Certificate Admin
# -----------------------------------------------------------------------------
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    """
    Certificate list view:
      - Columns show the basics you care about during review (title/issuer/owner/date).
      - Filters let you jump to a specific issuer or day quickly.
      - Search helps when you only remember part of a title or issuer name.
    """
    list_display = ("title", "issuer", "user", "date_earned", "file_upload")
    list_filter = ("issuer", "date_earned")
    search_fields = ("title", "issuer", "user__username", "user__email")
    ordering = ("-date_earned",)  # newest certificates at the top


# -----------------------------------------------------------------------------
# Project Admin
# -----------------------------------------------------------------------------
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    Project list view:
      - Columns surface ownership and linkage (user/certificate), delivery state
        (status), and quick context (work_type, duration_text).
      - Filters make it easy to audit completed projects, team work, or specific
        certificate relationships.
      - Search spans both the core title/description and the guided text fields.
    """
    list_display = (
        "title", "user", "certificate", "status", "work_type",
        "duration_text", "date_created",
    )
    list_filter = ("status", "work_type", "certificate", "date_created")
    search_fields = (
        "title",
        "description",
        "problem_solved",
        "tools_used",
        "challenges_short",
        "skills_used",
        "outcome_short",
        "skills_to_improve",
        "user__username",
        "user__email",
    )
    ordering = ("-date_created",)  # newest projects first


# -----------------------------------------------------------------------------
# GoalStep Inline (under Goal)
# -----------------------------------------------------------------------------
class GoalStepInline(admin.TabularInline):
    """
    Inline rows for a Goal's named steps.
    """
    model = GoalStep
    extra = 0
    fields = ("title", "is_done", "order", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("order", "id")


# -----------------------------------------------------------------------------
# Goal Admin
# -----------------------------------------------------------------------------
@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    """
    Goal list view:
      - Columns show the owner, title, numeric target, deadline, NEW checklist
        fields (total_steps/completed_steps), a computed steps progress %,
        and when it was created.
      - Filters let you jump to upcoming deadlines or recent activity.
      - Simple search on title/target_projects/user helps during audits.
      - In-line editing for the integer steps fields speeds manual adjustments.
      - Inline GoalStep rows allow adding/checking/reordering named steps quickly.
    """

    # Show computed steps progress as a column
    def steps_progress_display(self, obj):
        # models.Goal has @property steps_progress_percent
        try:
            return f"{obj.steps_progress_percent}%"
        except Exception:
            return "—"
    steps_progress_display.short_description = "Steps progress"

    list_display = (
        "user",
        "title",
        "target_projects",
        "deadline",
        "total_steps",
        "completed_steps",
        "steps_progress_display",
        "created_at",
    )
    list_editable = ("total_steps", "completed_steps")
    list_filter = ("deadline", "created_at", "total_steps", "completed_steps")
    search_fields = ("title", "target_projects", "user__username", "user__email")
    ordering = ("deadline",)  # sort by approaching deadlines

    # Inline steps editor
    inlines = [GoalStepInline]

    # Optional: form layout in the detail page
    fields = (
        "user",
        "title",
        ("target_projects", "deadline"),
        ("total_steps", "completed_steps"),
        "created_at",
    )
    readonly_fields = ("created_at",)
