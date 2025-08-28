"""
Management command: seed_demo
-----------------------------

Purpose:
    Creates a demo user and some sample data (certificate, project, goal)
    so that a fresh database can be quickly populated for demos, dev testing,
    or onboarding.

Behavior:
    - Idempotent: uses get_or_create so running it multiple times will not
      create duplicate rows.
    - Demo user: demo@skillfolio.dev / pass1234
    - Adds one certificate, one linked project, and one goal for that user.

Usage:
    python manage.py seed_demo

Notes:
    * Safe to run against an existing DB (no duplicates).
    * Ideal for local dev, test runs, or showcasing the app without needing
      manual setup.
    * Not used in CI (tests create their own data).
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Certificate, Project, Goal
from datetime import date, datetime

class Command(BaseCommand):
    help = "Create demo user and a few sample records (idempotent)."

    def handle(self, *args, **options):
        User = get_user_model()

        user, created = User.objects.get_or_create(
            username="demo@skillfolio.dev",
            defaults={
                "email": "demo@skillfolio.dev",
            },
        )
        if created:
            user.set_password("pass1234")
            user.save()
            self.stdout.write(self.style.SUCCESS("Created demo user demo@skillfolio.dev / pass1234"))
        else:
            self.stdout.write("Demo user already exists.")

        cert, _ = Certificate.objects.get_or_create(
            user=user,
            title="Django Basics",
            issuer="Coursera",
            date_earned=date(2024, 8, 1),
        )

        proj, _ = Project.objects.get_or_create(
            user=user,
            title="Portfolio Dashboard",
            defaults=dict(
                status=Project.STATUS_COMPLETED,
                work_type=Project.WORK_TEAM,
                duration_text="2 weeks",
                primary_goal=Project.GOAL_DELIVER,
                certificate=cert,
                tools_used="React, Django, DRF",
                skills_used="React, Zustand, Tailwind",
                problem_solved="Visualize certificate progress in one place.",
                outcome_short="Shipped a responsive dashboard showing live stats.",
                skills_to_improve="Test coverage and CI",
                description="",
            ),
        )

        goal, _ = Goal.objects.get_or_create(
            user=user,
            target_projects=5,
            deadline=date(2025, 12, 31),
        )

        self.stdout.write(self.style.SUCCESS("Seeded demo certificate, project, and goal."))
