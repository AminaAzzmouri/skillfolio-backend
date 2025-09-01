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

- NEW (clickable certificate links from Projects):
  In the Projects list, the “Certificate” column is now a link that opens the
  Certificates changelist filtered to that certificate (no auto-edit). This uses
  the admin search query “?q=<certificate_id>”, so we allow exact-ID search by
  adding “=id” to CertificateAdmin.search_fields.

- NEW (inline → full add flow for Projects):
  * ProjectInline is now **view-only** (no inline add). This avoids half-filled
    rows and encourages complete project metadata.
  * The Certificate change page shows a prominent **“Add project for this
    certificate”** action. It opens the full Project **Add** form with the
    certificate pre-selected.
  * After saving a new project from that flow, the admin redirects **back to the
    certificate** you started from (so reviewers keep their context).
"""


from django.contrib import admin
from django.db.models import Count
from django.utils.safestring import mark_safe
from django.urls import reverse  # for building admin URLs
from urllib.parse import urlencode  # for ?q=<id> and next=...
from django.http import HttpResponseRedirect  # for post-add redirect


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

    NEW:
    - This inline is now **view-only**: we disable the ability to add inline
      rows so that users use the full Project Add form via the CTA on the
      Certificate page (pre-fills certificate and redirects back on save).
    """
    model = Project
    fk_name = "certificate"  # name of the FK field on Project
    extra = 0
    show_change_link = True

    # Display columns for rows already linked to this certificate
    fields = ("title", "status", "work_type", "start_date", "end_date", "duration_text", "date_created")
    readonly_fields = ("date_created", "duration_text")

    # Disable "Add another Project" inline button
    def has_add_permission(self, request, obj=None):
        return False


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
    - View-only inline + CTA to add a fully detailed Project pre-linked to this
      certificate (see add_project_cta and ProjectAdmin.response_add()).
    """
    list_display = ("title", "issuer", "date_earned", "project_count", "file_upload")
    list_filter = ("issuer", "date_earned")
    # allow exact-ID search so Projects list can link to a filtered view via ?q=<id>
    search_fields = ("title", "issuer", "user__username", "user__email", "=id")
    ordering = ("-date_earned",)  # newest certificates at the top
    inlines = [ProjectInline]

    # ---------- change/add form fields ----------
    def get_fields(self, request, obj=None):
        """
        Show normal model fields; on change pages also show an 'Add project' CTA.
        """
        base = ["user", "title", "issuer", "date_earned", "file_upload"]
        if obj:
            return base + ["add_project_cta"]
        return base

    def get_readonly_fields(self, request, obj=None):
        """
        Make 'user' editable only on add; CTA is always read-only.
        """
        ro = []
        if obj:
            ro = ["user", "add_project_cta"]
        return tuple(ro)

    def add_project_cta(self, obj):
        """
        Read-only action rendered on the Certificate change page that links to:
            Project Add form with ?certificate=<id>&next=<this certificate page>
        After the new Project is saved, we send the user back here for continuity.
        """
        add_url = reverse("admin:users_project_add")
        back_url = reverse("admin:users_certificate_change", args=[obj.pk])
        qs = urlencode({"certificate": obj.pk, "next": back_url})
        link = f'{add_url}?{qs}'
        return mark_safe(
            f'<a class="button" href="{link}" '
            f'style="display:inline-block;padding:6px 12px;border:1px solid #ccc;'
            f'border-radius:6px;text-decoration:none;">➕ Add project for this certificate</a>'
        )
    add_project_cta.short_description = "Quick actions"

    # ---------- save / queryset ----------
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

        Also:
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

    NEW (clickable certificate links):
    - The “Certificate” column renders as a link to the Certificates list
      filtered to that certificate only (no auto-edit).

    NEW (prefill + redirect when coming from a Certificate):
    - If the Project Add form is opened with ?certificate=<id>, the certificate
      field is pre-selected.
    - After saving that new project, if ?next=<url> is present, we redirect there
      (used to send the user back to the Certificate they started from).
    """
    list_display = (
        "title", "user", "certificate_link", "status", "work_type", "duration_text"
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

    # ---------- Prefill certificate from ?certificate=<id> on Add ----------
    def get_changeform_initial_data(self, request):
        """
        Pre-populate the Project Add form if opened from a Certificate page.
        """
        initial = super().get_changeform_initial_data(request)
        cert_id = request.GET.get("certificate")
        if cert_id:
            initial["certificate"] = cert_id
        return initial

    # ---------- Clickable certificate link in list ----------
    def certificate_link(self, obj):
        """
        Clickable link to Certificates list filtered to this certificate only.
        We link to the changelist with ?q=<certificate_id> so admins can view first
        and decide whether to edit.
        """
        if not obj.certificate_id:
            return "—"
        url = f"{reverse('admin:users_certificate_changelist')}?{urlencode({'q': obj.certificate_id})}"
        # Display the certificate’s __str__ (e.g., "Title - Issuer") as link text
        return mark_safe(f'<a href="{url}">{obj.certificate}</a>')
    certificate_link.short_description = "Certificate"
    certificate_link.admin_order_field = "certificate"

    # ---------- Save behavior / description refresh / owner defaults ----------
    def save_model(self, request, obj, form, change):
        """
        Safety nets for Admin:
        - On add, if no owner set, assign certificate owner if available,
          otherwise assign current admin.
        - If driver fields changed and description wasn't edited, regenerate
          the description so it stays in sync with the guided answers.
        - Always keep duration_text in sync (read-only display).
        """
        if not change and obj.user_id is None:
            # Prefer the certificate's owner when a certificate is set
            if obj.certificate_id and obj.certificate and obj.certificate.user_id:
                obj.user_id = obj.certificate.user_id
            else:
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

    # ---------- After adding a project, optionally redirect back ----------
    def response_add(self, request, obj, post_url_continue=None):
        """
        If ?next=<url> is present in the querystring (set by CertificateAdmin CTA),
        redirect there after creating the project (typically back to the certificate).
        """
        next_url = request.GET.get("next")
        if next_url:
            return HttpResponseRedirect(next_url)
        return super().response_add(request, obj, post_url_continue)


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


