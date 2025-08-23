"""
users/apps.py — App Configuration for Skillfolio Users App

Purpose
===============================================================================
Defines the configuration for the `users` app in the Skillfolio backend.

- This tells Django that the app exists, what its name is, and sets defaults.
- Django uses this class when initializing the app (e.g., migrations, signals).

Key Points
===============================================================================
- default_auto_field: Ensures all models in this app use BigAutoField for IDs.
  (This is Django’s recommended default for new projects since 3.2.)
- name: Declares the app’s name as 'users', which Django maps to INSTALLED_APPS.

Future Enhancements
===============================================================================
- We can attach signals here later (e.g., auto-create Profile when User created).
- Any app-specific startup logic (logging, caching) can also go inside ready().
"""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
