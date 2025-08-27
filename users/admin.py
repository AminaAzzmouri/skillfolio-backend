"""
users/admin.py — Django Admin Config for Skillfolio

Purpose
===============================================================================
Expose models (Certificate, Project, Goal) in the Django admin dashboard
so developers and admins can view, search, and manage them easily.

Highlights
- Certificate: searchable and filterable by issuer/date_earned; ordered recent-first.
- Project: custom ModelAdmin to show key fields (title, user, certificate, status, date_created).
- Goal: filter by deadline; sort by created_at; simple search on target_projects.
"""

from django.contrib import admin
from .models import Certificate, Project, Goal


# -----------------------------------------------------------------------------
# Certificate Admin
# -----------------------------------------------------------------------------
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("title", "issuer", "user", "date_earned", "file_upload")
    list_filter = ("issuer", "date_earned")
    search_fields = ("title", "issuer")
    ordering = ("-date_earned",)


# -----------------------------------------------------------------------------
# Project Admin
# -----------------------------------------------------------------------------
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    
    """

    Custom admin config for Project model.

    Why customize?
    ----------------------------------------------------------------------------
    By default, Django only shows __str__() in list view.
    Here, we expose useful fields for quick scanning:
    - title: project title
    - user: owner of the project
    - certificate: linked certificate (nullable)
    - status: planned / in_progress / completed
    - date_created: auto timestamp

    This makes it easier to review many projects at once in admin.
    """
    list_display = (
        "title", "user", "certificate", "status", "work_type",
        "duration_text", "date_created"
    )
    list_filter = ("status", "work_type", "certificate", "date_created")
    search_fields = (
        "title", "description", "problem_solved", "tools_used", "impact",
        "challenges_short", "skills_used", "outcome_short", "skills_to_improve"
    )
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