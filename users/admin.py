"""
users/admin.py — Django Admin Config for Skillfolio

Purpose
===============================================================================
Expose models (Certificate, Project, Goal) in the Django admin dashboard
so developers and admins can view, search, and manage them easily.

Highlights
- Certificate: registered with default admin (all fields visible in detail).
- Project: custom ModelAdmin to show key fields (title, user, certificate, date_created) in list view.
- Goal: registered with default admin.
"""

from django.contrib import admin
from .models import Certificate, Project, Goal


# -----------------------------------------------------------------------------
# Certificate Admin
# -----------------------------------------------------------------------------
# Registered with the default admin interface.
# Shows all fields in detail view, basic list display.
admin.site.register(Certificate)


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
    - date_created: auto timestamp
    
    This makes it easier to review many projects at once in admin.
    """
    list_display = ("title", "user", "certificate", "date_created")


# -----------------------------------------------------------------------------
# Goal Admin
# -----------------------------------------------------------------------------
# Registered with default admin, shows all fields as defined in model.
admin.site.register(Goal)
