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


NEW (admin behavior improvements)
===============================================================================
- Owner propagation for inline Projects:
  When adding/editing Projects inside a Certificate page (TabularInline),
  we automatically set:
      project.user        = certificate.user
      project.certificate = certificate
  This prevents IntegrityError: NOT NULL constraint failed: users_project.user_id
  and ensures consistent ownership/linkage. (See CertificateAdmin.save_formset)

- Certificate owner on add:
  On the Certificate **add** page, the 'user' field is editable (so staff can
  explicitly pick the owner). On change pages, 'user' remains read-only.
  If left blank (or when created programmatically), we default the owner to the
  current admin user for safety. (See CertificateAdmin.get_readonly_fields and
  CertificateAdmin.save_model)

- NEW (calendar duration in Admin):
  * Project detail and inline show Start date / End date pickers.
  * Duration is a read-only field (duration_text) auto-filled from dates.

- NEW (description refresh in Admin):
  * Project detail page: if “driver” fields change and the admin user did NOT edit
    the description field, we auto-regenerate description to stay in sync with the
    updated guided fields (see ProjectAdmin.save_model()).
  * Inline Projects under a Certificate: if description is blank, we auto-generate
    right before saving (see CertificateAdmin.save_formset()).


Notes
- Admin is for trusted staff only; normal clients use the REST API.
- Project model uses `date_created` (auto timestamp). That’s why ordering and
  filters reference `date_created` (not `created_at`).
"""

from django.contrib import admin
from django.db.models import Count
from django.utils.safestring import mark_safe

from .models import Certificate, Project, Goal, GoalStep


# -----------------------------------------------------------------------------
# Certificate Admin
# -----------------------------------------------------------------------------
class ProjectInline(admin.TabularInline):
    """
    Inline Projects under a Certificate.

    Why fields are arranged this way:
    - 'date_created' and 'duration_text' are included in 'fields' AND in
      'readonly_fields' so they show up but cannot be edited.
    """
    model = Project
    fk_name = "certificate"  # name of the FK field on Project
    extra = 0
    show_change_link = True

    # Editable inputs in the inline row:
    fields = ("title", "status", "work_type", "start_date", "end_date", "duration_text", "date_created")
    # Non-editable display columns:
    readonly_fields = ("date_created", "duration_text")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    """
    Certificate list view:
      - Columns show the basics you care about during review (title/issuer/owner/date).
      - Filters let you jump to a specific issuer or day quickly.
      - Search helps when you only remember part of a title or issuer name.

    NEW
    - On add, 'user' is editable; on change, 'user' is read-only.
    - When saving inline Projects, we copy the Certificate's owner into each
      Project user to prevent NOT NULL violations and keep data consistent.
    """
    list_display = ("title", "issuer", "date_earned", "project_count", "file_upload")
    list_filter = ("issuer", "date_earned")
    search_fields = ("title", "issuer", "user__username", "user__email")
    ordering = ("-date_earned",)  # newest certificates at the top
    inlines = [ProjectInline]

    # 'user' is protected on change, editable on add
    def get_readonly_fields(self, request, obj=None):
        """
        Make 'user' editable only on add.
        - Add form: return () so user can be chosen explicitly
        - Change form: keep 'user' read-only to avoid accidental reassignment
        """
        return ("user",) if obj else ()

    def save_model(self, request, obj, form, change):
        """
        Ensure a sensible default owner on add if none is provided.
        (In practice, staff should pick an owner on add; this is a safety net.)
        """
        if not change and obj.user_id is None:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        # Annotate so we can display & sort by project count efficiently
        qs = super().get_queryset(request)
        return qs.annotate(_project_count=Count("projects", distinct=True))

    def project_count(self, obj):
        # Use the annotation if present, else fall back to a count()
        return getattr(obj, "_project_count", obj.projects.count())
    project_count.short_description = "Projects"
    project_count.admin_order_field = "_project_count"

    def file_preview(self, obj):
        """
        Tiny image preview or fallback link for non-images.
        Not in list_display by default (we already show file_upload),
        but available if you want to add it.
        """
        if not obj.file_upload:
            return "—"
        url = obj.file_upload.url
        if any(url.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif")):
            return mark_safe(f'<a href="{url}" target="_blank"><img src="{url}" style="height:40px"/></a>')
        return mark_safe(f'<a href="{url}" target="_blank">Open file</a>')
    file_preview.short_description = "File"

    def save_formset(self, request, form, formset, change):
        """
        Critical fix: make inline Project rows inherit the certificate owner
        and link back to the certificate. Prevents NOT NULL errors for
        Project.user and guarantees consistent ownership.

        NEW:
        - If an inline Project's description is blank, auto-generate it so the
          admin experience matches the API behavior.
        - Duration is recomputed (read-only) from dates.
        """
        instances = formset.save(commit=False)
        parent_cert = form.instance  # the Certificate being saved

        for obj in instances:
            if isinstance(obj, Project):
                obj.certificate = parent_cert
                if obj.user_id is None:
                    obj.user = parent_cert.user
                # auto description if blank
                if not obj.description or not str(obj.description).strip():
                    obj.description = obj._generated_description()
                # ensure duration_text is in sync for display
                obj._sync_duration_text()
            obj.save()

        # Handle deletions + m2m
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()


# -----------------------------------------------------------------------------
# Project Admin
# -----------------------------------------------------------------------------
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    Project list view:
      - Columns surface ownership and linkage (user/certificate), delivery state
        (status), and quick context (work_type, Duration).
      - Filters make it easy to audit completed projects, team work, or specific
        certificate relationships.
      - Search spans both the core title/description and the guided text fields.

    Note:
    - 'user' is read-only in the form; if you add a Project directly here,
      we default it to the current admin in save_model() when missing.
      (Inline creation under a Certificate uses the Certificate's owner instead.)

    NEW (description refresh in Admin):
    - If the admin edits any “driver” fields but does NOT touch the description
      field, we refresh description automatically (mirrors the serializer behavior).

    NEW (calendar fields):
    - Show Start date / End date; Duration (read-only) auto-fills.
    """
    list_display = (
        "title", "user", "certificate", "status", "work_type", "duration_text"
    )
    autocomplete_fields = ("certificate",)
    readonly_fields = ("user", "date_created", "duration_text")
    list_filter = ("status", "work_type", "certificate", "date_created")
    search_fields = (
        "title",
        "description",
        "problem_solved",
        "tools_used",
        "skills_used",
        "challenges_short",
        # outcome_short removed from model
        "skills_to_improve",
        "user__username",
        "user__email",
    )
    ordering = ("-date_created",)  # newest projects first

    # Optional: form layout
    fields = (
        "user",
        "title",
        ("status", "work_type"),
        ("start_date", "end_date"),
        "duration_text",  # read-only, computed from dates
        "primary_goal",
        "certificate",
        "problem_solved",
        "tools_used",
        "skills_used",
        "challenges_short",
        "skills_to_improve",
        "description",
        "date_created",
    )

    def save_model(self, request, obj, form, change):
        """
        Safety nets for Admin:
        - On add, if no owner set, assign current admin.
        - If driver fields changed and description wasn't edited, regenerate
          the description so it stays in sync with the guided answers.
        - Always keep duration_text in sync (read-only display).
        """
        if not change and obj.user_id is None:
            obj.user = request.user

        driver_fields = {
            "title", "work_type",
            "start_date", "end_date",   # calendar drivers
            "duration_text",            # will be re-synced anyway
            "primary_goal",
            "problem_solved", "tools_used", "skills_used",
            "challenges_short",
            "skills_to_improve",
        }
        changed_driver = any(f in getattr(form, "changed_data", ()) for f in driver_fields)
        description_changed = "description" in getattr(form, "changed_data", ())

        # sync duration_text for display
        obj._sync_duration_text()

        if changed_driver and not description_changed:
            obj.description = obj._generated_description()

        super().save_model(request, obj, form, change)


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



