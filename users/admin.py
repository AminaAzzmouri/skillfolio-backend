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
  adding “=id” to CertificateAdmin.search_fields).

- NEW (inline → full add flow for Projects):
  * ProjectInline is now **view-only** (no inline add **and** no inline edit/delete).
  * On the Certificate change page we render each linked Project as:
        [Title]  |  [Change]
    where **Change** links to the Project edit page with a `?next=` back to the
    certificate page. This avoids redundancy (no partial inline editing).
  * The Certificate change page also shows a prominent **“Add project for this
    certificate”** action. It opens the full Project **Add** form with the
    certificate pre-selected and returns to the certificate page after save.

- UPDATED (End date UX & validation — *strict lock for non-completed*):
  * End date is **locked (disabled + greyed)** while Status is Planned/In progress,
    and instantly becomes editable + required when Status = Completed (client JS).
  * Server still enforces:
      - Completed ⇒ end_date required and strictly after start_date (no same-day)
      - Not Completed ⇒ end_date must be empty (we also clear it in save()).

- UPDATED (form requirements & layout):
  * **Start date** is required for all statuses with status-aware rules (see models).
  * **Description** can be left blank; we auto-generate when blank.
  * **End date** is placed on its own line (under Start date) for clarity.

- NEW/UPDATED (Admin UI refinements for Project form)
  * Start/End now appear **before** Work type (as requested).
  * Start and End are on **separate lines** (End under Start). Start label forced
    not bold via admin CSS to match your preference.
  * Start date help text shows **only a dynamic message** based on Status
    (we suppress the static model help in Admin so you don’t see two messages).
  * End date calendar icon/shortcuts are fully **non-clickable/hidden** when Status
    is Planned/In progress — including the initial “Add project” (default Planned) —
    then re-enabled for Completed while enforcing max=today and min=start+1.
  * NEW: **End date helper text updates live** by Status (client JS only):
      - Planned / In progress → “Required only when a project is completed”
      - Completed            → “Required field: End Date cannot be the same as Start date”

- NEW/UPDATED (Single start-date error in Admin)
  * To avoid duplicate errors (“This field is required.” + model error), the Start
    date is **not required** at the form level; the model clean() raises the single
    friendly error: “The project must have a start date”.

- NEW (Project form — Certificate FK limited to linking only)
  * On Project **add/edit** pages, the Certificate field is **link-only**:
    no “add”, “edit/change”, “delete”, or “view” icons are rendered next to it.
    This keeps certificate management in the Certificates admin, while still
    allowing you to **select** a certificate (and clear it with the per-field Reset
    link provided by the JS). Implementation: in ProjectAdmin.get_form() we toggle
    the related-field wrapper flags: can_add_related=False, can_change_related=False,
    can_delete_related=False, can_view_related=False.

- NEW (Project save redirect rules)
  * If a Project form URL includes `?next=/admin/users/certificate/<id>/change/`,
    then after **Save** we return to that certificate page (works for both Add and Change).
  * Otherwise (i.e., you came from the Projects list), **Save** returns you to the
    Projects changelist. “Save and continue” and “Save and add another” keep default behavior.

- NEW (Certificate form UI parity)
  * The Certificate form loads `users/admin/certificate_form_ui.js` which:
      - switches **Date earned** to the native **in-input** calendar,
      - hides Django’s “datetimeshortcuts” box,
      - clamps to **today** (`max=today`) and **greys out future days** in the popup,
      - shows the same **error-banner** behavior as Projects,
      - adds **per-field Reset** links (Title, Issuer, Date earned, File upload)
        and a **Reset all** button.
    Admin code below simply loads the assets and removes the static help so the
    JS can render a single dynamic helper under the field.

Notes
===============================================================================
- The per-field “Reset” links and “Reset all” button are purely client-side and
  live in users/static/users/admin/project_end_date_toggle.js (Projects) and
  users/static/users/admin/certificate_form_ui.js (Certificates). Admin code here
  ensures the forms cooperate with that behavior.
"""

from django.contrib import admin
from django.db.models import Count
from django.utils.safestring import mark_safe
from django.urls import reverse
from urllib.parse import urlencode
from django.http import HttpResponseRedirect
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper  # for FK widget flags

from .models import Certificate, Project, Goal, GoalStep


# -----------------------------------------------------------------------------
# Certificate Admin
# -----------------------------------------------------------------------------
class ProjectInline(admin.TabularInline):
    """
    View-only inline of Projects under a Certificate.

    Rendered columns:
      - title (read-only)
      - change_link (custom action that adds ?next=<back to this certificate>)

    We also disable add/delete inline actions entirely.
    """
    model = Project
    fk_name = "certificate"
    extra = 0
    can_delete = False
    show_change_link = False  # we provide our own Change link with ?next=
    fields = ("title", "change_link")
    readonly_fields = ("title", "change_link")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        # Inline rows are purely view-only; editing happens in the full Project form.
        return False

    def change_link(self, obj):
        if not obj.pk:
            return "—"
        change_url = reverse("admin:users_project_change", args=[obj.pk])
        back_url = reverse("admin:users_certificate_change", args=[obj.certificate_id])
        link = f"{change_url}?{urlencode({'next': back_url})}"
        return mark_safe(f'<a class="button" href="{link}">Change</a>')
    change_link.short_description = "Actions"


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    # Load certificate-specific JS and reuse the shared CSS (notes + calendar greying).
    class Media:
        js = ("users/admin/certificate_form_ui.js",)
        css = {"all": ("users/admin/project_end_date_toggle.css",)}

    list_display = ("title", "issuer", "date_earned", "project_count", "file_upload")
    list_filter = ("issuer", "date_earned")
    search_fields = ("title", "issuer", "user__username", "user__email", "=id")
    ordering = ("-date_earned",)
    inlines = [ProjectInline]

    def get_fields(self, request, obj=None):
        base = ["user", "title", "issuer", "date_earned", "file_upload"]
        if obj:
            return base + ["add_project_cta"]
        return base

    def get_readonly_fields(self, request, obj=None):
        return ("user", "add_project_cta") if obj else ()

    def get_form(self, request, obj=None, **kwargs):
        """
        Remove the static help on 'date_earned' so the JS can render a single,
        status-agnostic helper under the field (and avoid duplicate messages).
        """
        form = super().get_form(request, obj, **kwargs)
        if "date_earned" in form.base_fields:
            form.base_fields["date_earned"].help_text = ""
        return form

    def add_project_cta(self, obj):
        """Button to open the full Project add form pre-filtered to this certificate."""
        add_url = reverse("admin:users_project_add")
        back_url = reverse("admin:users_certificate_change", args=[obj.pk])
        qs = urlencode({"certificate": obj.pk, "next": back_url})
        link = f"{add_url}?{qs}"
        return mark_safe(
            f'<a class="button" href="{link}" '
            f'style="display:inline-block;padding:6px 12px;border:1px solid #ccc;'
            f'border-radius:6px;text-decoration:none;">➕ Add project for this certificate</a>'
        )
    add_project_cta.short_description = "Quick actions"

    def save_model(self, request, obj, form, change):
        # Default owner to current admin user on ADD if none provided.
        if not change and obj.user_id is None:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_project_count=Count("projects", distinct=True))

    def project_count(self, obj):
        """
        Show the number of linked projects; when > 0, make it a link to the
        Projects changelist filtered to this certificate.
        Uses the standard FK filter param: certificate__id__exact=<cert_id>.
        """
        count = getattr(obj, "_project_count", obj.projects.count())
        if count:
            url = f"{reverse('admin:users_project_changelist')}?{urlencode({'certificate__id__exact': obj.pk})}"
        return mark_safe(f'<a href="{url}">{count}</a>')
        return "0"
        project_count.short_description = "Projects"
        project_count.admin_order_field = "_project_count"

    def save_formset(self, request, form, formset, change):
        """
        Keep inline projects consistent with their parent certificate.
        (Inline is view-only now, but we keep this for safety/back-compat.)
        """
        instances = formset.save(commit=False)
        parent_cert = form.instance
        for obj in instances:
            if isinstance(obj, Project):
                obj.certificate = parent_cert
                if obj.user_id is None:
                    obj.user = parent_cert.user
                if not obj.description or not str(obj.description).strip():
                    obj.description = obj._generated_description()
                obj._sync_duration_text()
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()


# -----------------------------------------------------------------------------
# Project Admin
# -----------------------------------------------------------------------------
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    See module docstring above for full UX notes.

    Important UI notes for this admin:
    - The Certificate FK is *link-only* on the Project form (no add/change/delete/view icons).
      This prevents accidental certificate edits from the project context.
    - The date fields’ UX (lock/unlock, min/max, helper text, reset links, error banner)
      is implemented in the static JS/CSS declared in Media below.

    Redirect behavior:
    - If the Project form URL includes ?next=<url>, after Save we redirect to that URL.
      (Used by the Certificate inline “Change” link and the “Add project for this certificate” CTA.)
    - Otherwise, Save returns to the Projects list (changelist).
    - “Save and continue” / “Save and add another” keep default Django behavior.
    """
    list_display = ("title", "user", "certificate_link", "status", "work_type", "duration_text", "description_short")
    autocomplete_fields = ("certificate",)
    readonly_fields = ("user", "date_created", "duration_text")
    list_filter = ("status", "work_type", "certificate", "date_created")
    search_fields = (
        "title", "description", "problem_solved", "tools_used", "skills_used",
        "challenges_short", "skills_to_improve", "user__username", "user__email",
    )
    ordering = ("-date_created",)

    fields = (
        "user",
        "title",
        "status",
        "start_date",
        "end_date",
        "work_type",
        "duration_text",
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

    class Media:
        js = ("users/admin/project_end_date_toggle.js",)
        css = {"all": ("users/admin/project_end_date_toggle.css",)}

    def get_form(self, request, obj=None, **kwargs):
        """
        Customize the Project form:
        - Description optional (we auto-generate on save when blank).
        - Start/End help text is removed so JS can inject dynamic help.
        - Certificate field is forced to *link-only* by disabling all related-object icons.
        """
        form = super().get_form(request, obj, **kwargs)

        # Description optional
        if "description" in form.base_fields:
            form.base_fields["description"].required = False

        # Start date: not required at form level (single error comes from model.clean())
        if "start_date" in form.base_fields:
            sd = form.base_fields["start_date"]
            sd.required = False
            sd.help_text = ""   # dynamic help via JS

        # End date: dynamic help via JS only (no static text here)
        if "end_date" in form.base_fields:
            ed = form.base_fields["end_date"]
            ed.required = False
            ed.help_text = ""   # dynamic help via JS

        # Certificate FK: link-only — hide add/change/delete/view icons next to the widget
        if "certificate" in form.base_fields:
            w = form.base_fields["certificate"].widget
            # With autocomplete_fields, Django wraps the widget in RelatedFieldWidgetWrapper.
            # Turn off all related-object action icons regardless of wrapper/widget type.
            if isinstance(w, RelatedFieldWidgetWrapper) or hasattr(w, "can_add_related"):
                for attr in ("can_add_related", "can_change_related", "can_delete_related", "can_view_related"):
                    if hasattr(w, attr):
                        setattr(w, attr, False)

        return form

    def description_short(self, obj):
        text = (obj.description or "").strip()
        if not text:
            return "—"
        return (text[:120] + "…") if len(text) > 120 else text
    description_short.short_description = "Description"

    def get_changeform_initial_data(self, request):
        # Pre-select certificate when arriving from Certificate page CTA
        initial = super().get_changeform_initial_data(request)
        cert_id = request.GET.get("certificate")
        if cert_id:
            initial["certificate"] = cert_id
        return initial

    def certificate_link(self, obj):
        """
        Render the Certificate column as a link that opens the Certificates changelist
        filtered to that certificate (read-only navigation; no auto-edit).
        """
        if not obj.certificate_id:
            return "—"
        url = f"{reverse('admin:users_certificate_changelist')}?{urlencode({'q': obj.certificate_id})}"
        return mark_safe(f'<a href="{url}">{obj.certificate}</a>')
    certificate_link.short_description = "Certificate"
    certificate_link.admin_order_field = "certificate"

    def save_model(self, request, obj, form, change):
        """
        - Ensure user is set on add; prefer the linked certificate's owner if present.
        - Keep duration_text synced.
        - If “driver” fields changed but description wasn’t manually edited this time,
          re-generate the description to keep it aligned with guided fields.
        """
        if not change and obj.user_id is None:
            if obj.certificate_id and obj.certificate and obj.certificate.user_id:
                obj.user_id = obj.certificate.user_id
            else:
                obj.user = request.user

        driver_fields = {
            "title", "status", "work_type",
            "start_date", "end_date",
            "duration_text",
            "primary_goal",
            "problem_solved", "tools_used", "skills_used",
            "challenges_short",
            "skills_to_improve",
        }
        changed_driver = any(f in getattr(form, "changed_data", ()) for f in driver_fields)
        description_changed = "description" in getattr(form, "changed_data", ())

        obj._sync_duration_text()

        if changed_driver and not description_changed:
            obj.description = obj._generated_description()

        if (not obj.description) or (not str(obj.description).strip()):
            obj.description = obj._generated_description()

        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        """
        If we arrived via the Certificate page CTA, go back there after save.
        Otherwise, keep Django’s default behavior.
        """
        next_url = request.GET.get("next")
        if next_url:
            return HttpResponseRedirect(next_url)
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        """
        Respect ?next= on change (edit) saves. Otherwise, return to the Projects list
        for a plain “Save”. “Save and continue” / “Save and add another” keep defaults.
        """
        # Keep Django defaults for these buttons:
        if "_continue" in request.POST or "_saveasnew" in request.POST or "_addanother" in request.POST:
            return super().response_change(request, obj)

        # If a ?next= is present, prefer it.
        next_url = request.GET.get("next")
        if next_url:
            return HttpResponseRedirect(next_url)

        # Default: return to Projects changelist.
        return HttpResponseRedirect(reverse("admin:users_project_changelist"))


# -----------------------------------------------------------------------------
# Goal & GoalStep
# -----------------------------------------------------------------------------
class GoalStepInline(admin.TabularInline):
    model = GoalStep
    extra = 0
    fields = ("title", "is_done", "order", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("order", "id")


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    def steps_progress_display(self, obj):
        try:
            return f"{obj.steps_progress_percent}%"
        except Exception:
            return "—"
    steps_progress_display.short_description = "Steps progress"

    list_display = (
        "user", "title", "target_projects", "deadline",
        "total_steps", "completed_steps", "steps_progress_display", "created_at",
    )
    list_editable = ("total_steps", "completed_steps")
    list_filter = ("deadline", "created_at", "total_steps", "completed_steps")
    search_fields = ("title", "target_projects", "user__username", "user__email")
    ordering = ("deadline",)
    inlines = [GoalStepInline]

    fields = (
        "user",
        "title",
        ("target_projects", "deadline"),
        ("total_steps", "completed_steps"),
        "created_at",
    )
    readonly_fields = ("created_at",)
