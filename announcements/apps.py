"""
announcements/apps.py

AppConfig for the Announcements app.

Why this app exists
-------------------
This app provides two tiny, read-only APIs used by the Home page:

1) /api/announcements/  — list enrollments/discounts (filterable & orderable)
2) /api/facts/random/   — one motivational "Did you know?" fact

Keep this app focused on read models and simple endpoints. Admin users can
curate data (manual entry, CSV import, or later automated ingesters).
"""
from django.apps import AppConfig


class AnnouncementsConfig(AppConfig):
    name = "announcements"
    verbose_name = "Announcements & Facts"
