"""
users/admin.py — Django Admin Config for Skillfolio

Purpose
===============================================================================
Expose the core models (Certificate, Project, Goal) in the Django admin so
developers and admins can browse, search, and manage data efficiently.

Highlights
- Certificate: searchable and filterable; recent-first ordering by date_earned.
- Project: custom list columns (title, owner, linked certificate, status, etc.)
  to make scanning many items quick and informative.
- Goal: quick filters on deadlines and created_at; simple search.

Notes
- The admin is only for trusted users; API clients should use the DRF endpoints.
"""

from django.contrib import admin
from .models import Certificate, Project, Goal


# -----------------------------------------------------------------------------
# Certificate Admin
# -----------------------------------------------------------------------------
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    # list_display controls which columns appear in the admin list view.
    list_display = ("title", "issuer", "user", "date_earned", "file_upload")

    # list_filter adds right-side filters to quickly narrow records.
    list_filter = ("issuer", "date_earned")

    # search_fields enables substring search; use minimal fields for speed.
    search_fields = ("title", "issuer")

    # newest certificates first in the list view.
    ordering = ("-date_earned",)


# -----------------------------------------------------------------------------
# Project Admin
# -----------------------------------------------------------------------------
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    Custom admin config for Project.

    Why this customization matters:
    - Admin list views default to showing only __str__().
    - By surfacing key fields (owner, status, link to certificate, created date,
      guided fields), admins can audit content and relationships at a glance.
    """

    list_display = (
        "title", "user", "certificate", "status", "work_type",
        "duration_text", "date_created"
    )

    # Quick filters help drill into specific subsets (e.g., completed projects).
    list_filter = ("status", "work_type", "certificate", "date_created")

    # Keep searches small and practical. These fields reflect what authors
    # commonly remember when locating a project.
    search_fields = (
        "title", "description", "problem_solved", "tools_used", "impact",
        "challenges_short", "skills_used", "outcome_short", "skills_to_improve"
    )

    # Show newest first so recent work is immediately visible.
    ordering = ("-date_created",)


# -----------------------------------------------------------------------------
# Goal Admin
# -----------------------------------------------------------------------------
@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("user", "target_projects", "deadline", "created_at")
    list_filter = ("deadline", "created_at")
    search_fields = ("target_projects",)
    ordering = ("deadline",)