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
- Project: 
        1. added `status` (planned / in_progress / completed)
        
        2. added *guided question* fields used to **auto-generate** a polished
  description on the server if `description` is blank:
            - work_type (individual/team)
            - duration_text (short free text)
            - primary_goal (practice_skill/deliver_feature/build_demo/solve_problem)
            - challenges_short, skills_used, outcome_short, skills_to_improve (short texts)
            
        - On save(), if `description` is empty, we compose it from the guided fields
  (user can still edit/override on the next updates).

- Goal: compute progress later at the serializer level (percentage of completed
  projects vs target_projects).
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from datetime import date
...
class Project(models.Model):
    """
    Project
    =============================================================================
    Purpose
    ---------------------------------------------------------------------------
    Captures practical work a user completed. A project can optionally be linked
    to a specific Certificate to show how learning was applied.
    ...
    Key Fields
    ---------------------------------------------------------------------------
    - title (CharField): Project name.
    - description (TextField): Details (what, how, tools, impact).
    - status (CharField): planned / in_progress / completed (added Week 4).
    - problem_solved/tools_used/impact (TextFields): guided description fields (Week 4).
    - date_created (DateTimeField auto_now_add): Creation timestamp.

    Week 4.5 additions (guided questions → auto description)
    ---------------------------------------------------------------------------
    - work_type (CharField, choices: individual/team)
    - duration_text (CharField): short human-readable duration (e.g., "2 weeks")
    - primary_goal (CharField, choices: practice_skill/deliver_feature/build_demo/solve_problem)
    - challenges_short / skills_used / outcome_short / skills_to_improve (TextFields)
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
        'users.Certificate',  # or simply 'Certificate' since it’s the same app
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="projects",
    help_text="Optionally link this project to a certificate.",
    )
    title = models.CharField(max_length=255, help_text="Project title.")
    description = models.TextField(help_text="What you built, how, tools used, and impact.", blank=True)

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

    # Week 4.5 guided questions (stored as raw answers; used to auto-build description)
    WORK_INDIVIDUAL = "individual"
    WORK_TEAM = "team"
    WORK_TYPE_CHOICES = [
        (WORK_INDIVIDUAL, "Individual"),
        (WORK_TEAM, "Team"),
    ]
    work_type = models.CharField(
        max_length=20,
        choices=WORK_TYPE_CHOICES,
        blank=True,
        null=True,
        help_text="Was this an individual or team project?"
    )
    duration_text = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Rough duration (e.g., '2 weeks', 'a weekend')."
    )

    GOAL_PRACTICE = "practice_skill"
    GOAL_DELIVER = "deliver_feature"
    GOAL_DEMO = "build_demo"
    GOAL_SOLVE = "solve_problem"
    PRIMARY_GOAL_CHOICES = [
        (GOAL_PRACTICE, "Practice a skill"),
        (GOAL_DELIVER, "Deliver a feature"),
        (GOAL_DEMO, "Build a demo"),
        (GOAL_SOLVE, "Solve a problem"),
    ]
    primary_goal = models.CharField(
        max_length=30,
        choices=PRIMARY_GOAL_CHOICES,
        blank=True,
        null=True,
        help_text="The main intent behind this project."
    )
    challenges_short = models.TextField(blank=True, null=True, help_text="Key challenges faced (short).")
    skills_used = models.TextField(blank=True, null=True, help_text="Skills/tools used (CSV or short text).")
    outcome_short = models.TextField(blank=True, null=True, help_text="Concise outcome/impact.")
    skills_to_improve = models.TextField(blank=True, null=True, help_text="What to practice more next time.")

    date_created = models.DateTimeField(auto_now_add=True, help_text="When this project was created.")

    class Meta:
        ordering = ["-date_created"]  # Recent-first ordering
        verbose_name = "Project"
        verbose_name_plural = "Projects"  # Makes admin interface cleaner.

    def __str__(self):
        return self.title

    # -----------------------------
    # Auto-generate description
    # -----------------------------
    def _generated_description(self) -> str:
        """
        Build a concise, polished description from guided answers.
        Only uses fields that are present; keeps it readable.
        """
        bits = []

        # Opening line
        opening = f"{self.title}".strip() if self.title else "This project"
        role = None
        if self.work_type == self.WORK_INDIVIDUAL:
            role = "individual project"
        elif self.work_type == self.WORK_TEAM:
            role = "team project"

        dur = self.duration_text.strip() if self.duration_text else None
        if role and dur:
            bits.append(f"{opening} was a {role} completed in {dur}.")
        elif role:
            bits.append(f"{opening} was a {role}.")
        elif dur:
            bits.append(f"{opening} was completed in {dur}.")
        else:
            bits.append(f"{opening}.")

        # Primary goal
        goal_map = {
            self.GOAL_PRACTICE: "practice and strengthen key skills",
            self.GOAL_DELIVER: "deliver a functional feature",
            self.GOAL_DEMO: "build a demonstrable prototype",
            self.GOAL_SOLVE: "solve a specific problem",
        }
        if self.primary_goal in goal_map:
            bits.append(f"The main goal was to {goal_map[self.primary_goal]}.")

        # Problem solved
        if self.problem_solved:
            bits.append(f"It addressed: {self.problem_solved.strip()}")

        # Tools used / skills
        tools = []
        if self.tools_used:
            tools.append(self.tools_used.strip())
        if self.skills_used and self.skills_used.strip() != (self.tools_used or "").strip():
            tools.append(self.skills_used.strip())
        if tools:
            bits.append(f"Key tools/skills: {', '.join(tools)}.")

        # Outcome
        if self.outcome_short:
            bits.append(f"Outcome: {self.outcome_short.strip()}")
        elif self.impact:
            bits.append(f"Impact: {self.impact.strip()}")

        # Reflection
        if self.skills_to_improve:
            bits.append(f"Next, I plan to improve: {self.skills_to_improve.strip()}.")

        return " ".join(bits).strip()

    def save(self, *args, **kwargs):
        """
        If the client left `description` blank, auto-generate it from the guided
        answers. If description is provided, we keep the user's text.
        """
        if not self.description or not self.description.strip():
            self.description = self._generated_description()
        super().save(*args, **kwargs)
