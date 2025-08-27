"""
users/admin.py — Django Admin configuration for Skillfolio

Purpose
===============================================================================
Make the Django admin genuinely useful for day-to-day QA and debugging.
We expose the core models (Certificate, Project, Goal) with sensible list
columns, filters, search, and ordering so you can quickly find and inspect data.

How to read this file (plain English):
- list_display: columns shown in the admin list page (the big table).
- list_filter: right-hand sidebar filters to narrow results without typing.
- search_fields: text search across chosen fields (substring match).
- ordering: default sort order in the list page.

Highlights
- Certificate: search by title/issuer, filter by issuer/date, newest first.
- Project: show owner, linked certificate, status, work type, duration, created date.
- Goal: show deadline and target at a glance; quick filters and simple search.

Notes
- Admin is for trusted staff only; normal clients use the REST API.
- Project model uses `date_created` (auto timestamp). That’s why ordering and
  filters reference `date_created` (not `created_at`).
"""

from django.contrib import admin
from .models import Certificate, Project, Goal


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
    search_fields = ("title", "issuer")
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
      - Search spans both the core title/description and the guided text fields
        you often reference when verifying content.
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
        "impact",
        "challenges_short",
        "skills_used",
        "outcome_short",
        "skills_to_improve",
    )
    ordering = ("-date_created",)  # newest projects first


# -----------------------------------------------------------------------------
# Goal Admin
# -----------------------------------------------------------------------------
@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    """
    Goal list view:
      - Columns show the owner, numeric target, deadline, and when it was created.
      - Filters let you jump to upcoming deadlines or recent activity.
      - Simple search on target_projects helps when scanning goals by size.
    """
    list_display = ("user", "target_projects", "deadline", "created_at")
    list_filter = ("deadline", "created_at")
    search_fields = ("target_projects",)
    ordering = ("deadline",)  # sort by approaching deadlines
