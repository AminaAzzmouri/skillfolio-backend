"""
users/apps.py — App configuration for the Skillfolio "users" app

Purpose
===============================================================================
Register the app with Django and set default behavior (like BigAutoField IDs).

Key Points
- default_auto_field: Use BigAutoField for primary keys across models in this app.
- name: Must match the dotted path used in INSTALLED_APPS ("users").

Future Enhancements
- If you later add signals (e.g., auto-create a Profile on user creation),
  you can connect them in a ready() method here.
"""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
