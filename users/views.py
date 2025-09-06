"""
users/views.py — DRF ViewSets & Analytics for Skillfolio

Purpose
===============================================================================
Expose owner-scoped CRUD APIs for Certificate, Project, Goal, and GoalStep.
Add small analytics endpoints for counts and goal progress.

Ownership Model
- Each ViewSet filters by request.user and assigns user on create (for parent).
- Steps are owner-scoped through their parent Goal (goal__user=request.user).

Highlights
- Per-user isolation via OwnerScopedModelViewSet base class.
- Filtering, search, and ordering are enabled for frontend integration.
- Analytics endpoints for quick dashboard counts and goal progress.

Auth Endpoints
- Auth (login/register/logout) are centralized in users.auth_views and wired in
  the root urls.py. Any auth classes that remain here are not wired to URLs.

NEW
- GoalViewSet:
  * ordering_fields include checklist columns (total_steps, completed_steps, deadline).
  * PATCH/PUT accepts total_steps and completed_steps (standard model fields).
  * steps_progress_percent is exposed as a computed read-only field alongside
    progress_percent.
    
- GoalStepViewSet:
  * CRUD for named steps under a Goal (owner-scoped through parent goal).
  * filterset/search/order helpers for admin-like convenience.
  
- CertificateViewSet:
  * Annotates each row with project_count via Count("projects", distinct=True).
    WHY: The Certificates page shows number of associated projects per card.
  * Adds filter by id (?id=<pk>).
    WHY: The Projects page “View certificate” link navigates to /certificates?id=<pk>.

- ProjectViewSet:
  * Accepts ?certificateId=<id> alias for filtering.
    WHY: Keeps FE query flexible and simple.

API Docs Alignment (Swagger / drf-yasg)
===============================================================================
drf-yasg targets Swagger 2.0 (not OpenAPI 3), so we AVOID oneOf/anyOf.
Instead, we:
- Provide a single unified request schema for Projects and document the
  status-aware rules in field descriptions (Admin parity).
- Keep field ORDER in request schemas to match Admin forms.
- Reuse Admin wording for labels/help so /api/docs reads like the Admin UI.
"""

from django.contrib.auth import get_user_model
from django.db.models import Count 
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db import models

from .models import Certificate, Project, Goal, GoalStep
from .serializers import (
    CertificateSerializer,
    ProjectSerializer,
    GoalSerializer,
    GoalStepSerializer,
)

# Optional: drf-yasg (only if installed)
try:
    from drf_yasg.utils import swagger_auto_schema
    from drf_yasg import openapi
    HAS_YASG = True
except Exception:
    HAS_YASG = False

# -----------------------------------------------------------------------------
# Base ViewSet enforcing per-user ownership
# -----------------------------------------------------------------------------
class OwnerScopedModelViewSet(viewsets.ModelViewSet):
    """
    A ModelViewSet with two guarantees:
    1) Authentication required (IsAuthenticated).
    2) Querysets and creates are constrained to the current user.

    Why this matters
    - Prevents accidental data leakage across users.
    - Keeps all per-user filters in one place instead of repeating logic.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Limit all list/retrieve queries to the authenticated user's records.
        Assumes the model includes a ForeignKey named `user`.
        """
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        """
        On create, assign ownership to request.user. Client cannot override `user`.
        """
        serializer.save(user=self.request.user)


# -----------------------------------------------------------------------------
# Resource ViewSets
# -----------------------------------------------------------------------------
class CertificateViewSet(OwnerScopedModelViewSet):
    """
    Certificates API
    - Filtering:   ?issuer=<str>&date_earned=<YYYY-MM-DD>&id=<pk>
    - Search:      ?search=<substring> (title, issuer)
    - Ordering:    ?ordering=date_earned | -date_earned | title | -title

    Notes for /api/docs
    - Each certificate row is annotated with `project_count` (read-only int).
      This mirrors the Admin list column showing how many Projects are linked.
    """
    # Annotate with related projects count (distinct for safety)
    queryset = Certificate.objects.all().annotate(
        project_count=Count("projects", distinct=True)
    )
    serializer_class = CertificateSerializer
    filterset_fields = ["id", "issuer", "date_earned"]
    search_fields = ["title", "issuer"]
    ordering_fields = ["date_earned", "title"]
    ordering = ["-date_earned"]  # default newest first

    if HAS_YASG:
        _resp_list_ok = openapi.Response("OK", CertificateSerializer(many=True))
        _resp_item_ok = openapi.Response("OK", CertificateSerializer())
        _resp_created = openapi.Response("Created", CertificateSerializer())
        _resp_ok = _resp_item_ok

        @swagger_auto_schema(
            operation_description=(
                "List your certificates (owner-scoped).\n\n"
                "Certificates API\n\n"
                "• Filtering: `?issuer=` & `date_earned=<YYYY-MM-DD>` & `id`\n"
                "• Search: `?search=` (title, issuer)\n"
                "• Ordering: `?ordering=date_earned | -date_earned | title | -title`\n\n"
                "Notes for /api/docs\n\n"
                "• Each certificate row is annotated with **project_count** (read-only int). "
                "This mirrors the Admin list column showing how many Projects are linked."
            ),
            responses={200: _resp_list_ok, 401: "Unauthorized"},
        )
        def list(self, request, *args, **kwargs):
            return super().list(request, *args, **kwargs)

        @swagger_auto_schema(
            operation_description="Retrieve a certificate you own by ID.",
            responses={200: _resp_item_ok, 401: "Unauthorized", 404: "Not Found"},
        )
        def retrieve(self, request, *args, **kwargs):
            return super().retrieve(request, *args, **kwargs)

        @swagger_auto_schema(
            operation_description="Create a certificate.",
            responses={201: _resp_created, 400: "Bad Request", 401: "Unauthorized"},
        )
        def create(self, request, *args, **kwargs):
            return super().create(request, *args, **kwargs)

        @swagger_auto_schema(
            operation_description="Fully update a certificate (PUT).",
            responses={200: _resp_ok, 400: "Bad Request", 401: "Unauthorized", 404: "Not Found"},
        )
        def update(self, request, *args, **kwargs):
            return super().update(request, *args, **kwargs)

        @swagger_auto_schema(
            operation_description="Partially update a certificate (PATCH).",
            responses={200: _resp_ok, 400: "Bad Request", 401: "Unauthorized", 404: "Not Found"},
        )
        def partial_update(self, request, *args, **kwargs):
            return super().partial_update(request, *args, **kwargs)

        @swagger_auto_schema(
            operation_description="Delete a certificate.",
            responses={204: "No Content", 401: "Unauthorized", 404: "Not Found"},
        )
        def destroy(self, request, *args, **kwargs):
            return super().destroy(request, *args, **kwargs)


class ProjectViewSet(OwnerScopedModelViewSet):
    """
    Projects API
    - Filtering:   ?certificate=<id>&status=<planned|in_progress|completed>
                   Also accepts: ?certificateId=<id> (alias)
    - Search:      ?search=<substring> (title, description[, other fields if present])
    - Ordering:    ?ordering=date_created | -date_created | title | -title

    Status-aware rules (same as Admin)
    - Start date is required for all statuses.
    - Planned:      start_date >= today.
    - In Progress:  start_date <= today.
    - Completed:    start_date <  today (yesterday or earlier),
                    end_date required,
                    end_date > start_date,
                    end_date <= today.
    - If status != Completed, end_date must be empty (server will clear it on save).

    Description
    - If blank on create/update, the server generates a status-aware description
      using the same phrasing as the Admin form.
    """
    queryset = Project.objects.select_related("certificate").all()
    serializer_class = ProjectSerializer
    filterset_fields = ["certificate", "status"]
    # Keep search pragmatic: title/description + optional fields if present in model
    search_fields = ["title", "description", "problem_solved", "tools_used"]
    ordering_fields = ["date_created", "title"]
    ordering = ["-date_created"]  # default newest first
    
    # NEW: support ?certificateId=<id> as an alias
    def get_queryset(self):
        qs = super().get_queryset().select_related("certificate")
        cert_id = self.request.query_params.get("certificateId")
        if cert_id:
            qs = qs.filter(certificate_id=cert_id)
        return qs

    if HAS_YASG:
        _certificate_id_param = openapi.Parameter(
            name="certificateId",
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_INTEGER,
            required=False,
            description="Alias for ?certificate=<id>. Filters projects by linked certificate ID.",
        )

        _resp_list_ok = openapi.Response("OK", ProjectSerializer(many=True))
        _resp_item_ok = openapi.Response("OK", ProjectSerializer())
        _resp_created = openapi.Response("Created", ProjectSerializer())
        _resp_ok = _resp_item_ok

        @swagger_auto_schema(
            manual_parameters=[_certificate_id_param],
            operation_description=(
                "List your projects (owner-scoped). Use `?certificate=<id>` or the alias `?certificateId=<id>` "
                "to filter by linked certificate. Status-aware validation matches the Admin interface."
            ),
            responses={200: _resp_list_ok, 401: "Unauthorized"},
        )
        def list(self, request, *args, **kwargs):
            return super().list(request, *args, **kwargs)

        # Request body that mirrors Admin field ORDER and help (single schema for Swagger 2)
        _project_props = {
            "title": openapi.Schema(type=openapi.TYPE_STRING, description="Project title."),
            "status": openapi.Schema(
                type=openapi.TYPE_STRING,
                enum=[Project.STATUS_PLANNED, Project.STATUS_IN_PROGRESS, Project.STATUS_COMPLETED],
                description=(
                    "Project status. Rules:\n"
                    "- Planned → start_date must be today or future; end_date must be empty.\n"
                    "- In Progress → start_date must be today or past; end_date must be empty.\n"
                    "- Completed → start_date must be before today, end_date is required, end_date > start_date, and not in the future."
                ),
            ),
            "start_date": openapi.Schema(type=openapi.TYPE_STRING, format="date", description="Start date (YYYY-MM-DD). Required for all statuses."),
            "end_date": openapi.Schema(type=openapi.TYPE_STRING, format="date", description="End date (YYYY-MM-DD). Only for Completed; must be after start_date and not in the future."),
            "work_type": openapi.Schema(type=openapi.TYPE_STRING, enum=["individual", "team"], description="Was this an individual or team project?"),
            "duration_text": openapi.Schema(type=openapi.TYPE_STRING, description="Read-only in Admin. Derived from dates on the server when status=completed."),
            "primary_goal": openapi.Schema(
                type=openapi.TYPE_STRING,
                enum=["practice_skill", "deliver_feature", "build_demo", "solve_problem"],
                description="The main intent behind this project."
            ),
            "certificate": openapi.Schema(type=openapi.TYPE_INTEGER, description="Optional FK to a Certificate (ID)."),
            "problem_solved": openapi.Schema(type=openapi.TYPE_STRING, description="(Optional) What problem did this project solve? (Admin label varies by status)"),
            "tools_used": openapi.Schema(type=openapi.TYPE_STRING, description="(Optional) Tools/technologies used (or to be used)"),
            "skills_used": openapi.Schema(type=openapi.TYPE_STRING, description="(Optional) Skills practiced (free text or CSV)"),
            "challenges_short": openapi.Schema(type=openapi.TYPE_STRING, description="(Optional) Key challenges faced"),
            "skills_to_improve": openapi.Schema(type=openapi.TYPE_STRING, description="(Optional) What to practice more next time"),
            "description": openapi.Schema(type=openapi.TYPE_STRING, description="If blank, the server will auto-generate a status-aware description."),
        }

        _project_required = ["title", "start_date"]

        _project_request_schema = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            # ORDER mirrors Admin form:
            # title → status → start_date → end_date → work_type → duration_text → primary_goal → certificate →
            # problem_solved → tools_used → skills_used → challenges_short → skills_to_improve → description
            properties=_project_props,
            required=_project_required,
            example={
                "title": "Portfolio Website",
                "status": "completed",
                "start_date": "2025-07-01",
                "end_date": "2025-07-20",
                "work_type": "individual",
                "primary_goal": "build_demo",
                "certificate": None,
                "problem_solved": "Showcase personal projects and skills",
                "tools_used": "Django, React, Tailwind",
                "skills_used": "Python, APIs, CSS",
                "challenges_short": "SEO, image optimization",
                "skills_to_improve": "Accessibility",
                "description": ""
            },
        )

        @swagger_auto_schema(
            request_body=_project_request_schema,
            operation_description="Create a project. Field order and rules mirror the Admin form. If `description` is blank, it will be generated server-side.",
            responses={201: _resp_created, 400: "Bad Request", 401: "Unauthorized"},
        )
        def create(self, request, *args, **kwargs):
            return super().create(request, *args, **kwargs)

        @swagger_auto_schema(
            request_body=_project_request_schema,
            operation_description="Fully update a project (PUT).",
            responses={200: _resp_ok, 400: "Bad Request", 401: "Unauthorized", 404: "Not Found"},
        )
        def update(self, request, *args, **kwargs):
            return super().update(request, *args, **kwargs)

        @swagger_auto_schema(
            request_body=_project_request_schema,
            operation_description="Partially update a project (PATCH). Status-aware date rules apply; `description` is regenerated if driver fields change and you didn't edit it.",
            responses={200: _resp_ok, 400: "Bad Request", 401: "Unauthorized", 404: "Not Found"},
        )
        def partial_update(self, request, *args, **kwargs):
            return super().partial_update(request, *args, **kwargs)

        @swagger_auto_schema(
            operation_description="Retrieve a project you own by ID. Status-aware fields/validation match Admin.",
            responses={200: _resp_item_ok, 401: "Unauthorized", 404: "Not Found"},
        )
        def retrieve(self, request, *args, **kwargs):
            return super().retrieve(request, *args, **kwargs)

        @swagger_auto_schema(
            operation_description="Delete a project.",
            responses={204: "No Content", 401: "Unauthorized", 404: "Not Found"},
        )
        def destroy(self, request, *args, **kwargs):
            return super().destroy(request, *args, **kwargs)


# -----------------------------------------------------------------------------
# Goals & GoalSteps
# -----------------------------------------------------------------------------

class GoalViewSet(OwnerScopedModelViewSet):
    """
    Goals API
    - Filtering:   ?deadline=<YYYY-MM-DD>
    - Ordering:    ?ordering=created_at | -created_at | deadline | -deadline
                   | total_steps | -total_steps | completed_steps | -completed_steps
                   | completed_projects | -completed_projects | title | -title

    Admin parity
    - Field naming in /api/docs uses Admin-like titles:
      * target_projects     → "Target number of projects to build"
      * completed_projects  → "Accomplished projects" (optional; clamped to target)
      * total_steps         → "Overall required steps" (optional)
      * completed_steps     → "Accomplished steps" (optional)
    - Field order in request body mirrors Admin form:
      title → target_projects → completed_projects → deadline → total_steps → completed_steps.
    """
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
    filterset_fields = ["deadline"]
    ordering_fields = [
        "created_at", "deadline",
        "total_steps", "completed_steps",
        "completed_projects",
        "title",
    ]
    ordering = ["-created_at"]  # default newest first

    # Optional: schema docs for create/partial update (only if drf-yasg is present)
    if HAS_YASG:
        _resp_list_ok = openapi.Response("OK", GoalSerializer(many=True))
        _resp_item_ok = openapi.Response("OK", GoalSerializer())
        _resp_created = openapi.Response("Created", GoalSerializer())
        _resp_ok = _resp_item_ok

        _steps_props = {
            # ORDER mirrors Admin form
            "title": openapi.Schema(type=openapi.TYPE_STRING, description="Goal title"),
            "target_projects": openapi.Schema(
                type=openapi.TYPE_INTEGER,
                title="Target number of projects to build",
                description="Must be ≥ 1.",
            ),
            "completed_projects": openapi.Schema(
                type=openapi.TYPE_INTEGER,
                title="Accomplished projects",
                description="Optional; clamped to target_projects.",
            ),
            "deadline": openapi.Schema(
                type=openapi.TYPE_STRING,
                format="date",
                description="Goal deadline (YYYY-MM-DD). Cannot be in the past.",
            ),
            "total_steps": openapi.Schema(
                type=openapi.TYPE_INTEGER,
                title="Overall required steps",
                description="Optional checklist total (defaults to 0).",
            ),
            "completed_steps": openapi.Schema(
                type=openapi.TYPE_INTEGER,
                title="Accomplished steps",
                description="Optional completed count (capped to total_steps).",
            ),
        }

        @swagger_auto_schema(
            operation_description=(
                "List your goals (owner-scoped).\n\n"
                "Goals API\n\n"
                "• Filtering: `?deadline=<YYYY-MM-DD>`\n"
                "• Ordering: `?ordering=created_at | -created_at | deadline | -deadline | "
                "total_steps | -total_steps | completed_steps | -completed_steps | "
                "completed_projects | -completed_projects | title | -title`\n\n"
                "Admin parity\n\n"
                "• Field naming in /api/docs uses Admin-like titles.\n"
                "• Field order in request body mirrors Admin forms."
            ),
            responses={200: _resp_list_ok, 401: "Unauthorized"},
        )
        def list(self, request, *args, **kwargs):
            return super().list(request, *args, **kwargs)

        @swagger_auto_schema(
            request_body=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties=_steps_props,
                required=["title", "target_projects", "deadline"],
                example={
                    "title": "Finish 3 portfolio projects",
                    "target_projects": 3,
                    "completed_projects": 1,
                    "deadline": "2025-12-31",
                    "total_steps": 6,
                    "completed_steps": 2
                },
            ),
            responses={201: _resp_created, 400: "Bad Request", 401: "Unauthorized"},
            operation_description="Create a goal. Field titles/order mirror Admin; projects/steps are optional.",
        )
        def create(self, request, *args, **kwargs):
            return super().create(request, *args, **kwargs)

        @swagger_auto_schema(
            request_body=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties=_steps_props,
            ),
            responses={200: _resp_ok, 400: "Bad Request", 401: "Unauthorized", 404: "Not Found"},
            operation_description="Fully update a goal (PUT).",
        )
        def update(self, request, *args, **kwargs):
            return super().update(request, *args, **kwargs)

        @swagger_auto_schema(
            request_body=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties=_steps_props,
                example={"completed_steps": 3, "completed_projects": 2},
            ),
            responses={200: _resp_ok, 400: "Bad Request", 401: "Unauthorized", 404: "Not Found"},
            operation_description="Partially update a goal (PATCH). Titles/order mirror Admin.",
        )
        def partial_update(self, request, *args, **kwargs):
            return super().partial_update(request, *args, **kwargs)

        @swagger_auto_schema(
            operation_description="Retrieve a goal you own by ID. Titles/order match Admin.",
            responses={200: _resp_item_ok, 401: "Unauthorized", 404: "Not Found"},
        )
        def retrieve(self, request, *args, **kwargs):
            return super().retrieve(request, *args, **kwargs)

        @swagger_auto_schema(
            operation_description="Delete a goal.",
            responses={204: "No Content", 401: "Unauthorized", 404: "Not Found"},
        )
        def destroy(self, request, *args, **kwargs):
            return super().destroy(request, *args, **kwargs)


class GoalStepViewSet(viewsets.ModelViewSet):
    """
    GoalStep API (owner-scoped via parent goal)
    - Filtering: ?goal=<id>&is_done=<bool>
    - Search:    ?search=<substring> (title)
    - Ordering:  ?ordering=order | -order | created_at | -created_at

    Security
    - Queryset limited to steps whose goal belongs to request.user.
    - Create/update/delete validate ownership via perform_create/get_queryset.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GoalStepSerializer
    queryset = GoalStep.objects.select_related("goal").all()
    filterset_fields = ["goal", "is_done"]
    search_fields = ["title"]
    ordering_fields = ["order", "created_at", "id"]
    ordering = ["order", "id"]

    def get_queryset(self):
        return super().get_queryset().filter(goal__user=self.request.user)

    def perform_create(self, serializer):
        goal = serializer.validated_data.get("goal")
        if goal.user != self.request.user:
            raise serializers.ValidationError("You do not own this goal.")
        serializer.save()


# -----------------------------------------------------------------------------
# Analytics Endpoints (owner-scoped)
# -----------------------------------------------------------------------------

@swagger_auto_schema(
    method="get",
    tags=["Analytics"],
    operation_description=(
        "Owner-scoped KPI counts for the authenticated user.\n\n"
        "Returns counts of certificates, projects, and goals, plus goal completion stats.\n\n"
        "Responses:\n"
        "- 200: OK — object with *_count fields and completion metrics\n"
        "- 401: Unauthorized — missing/invalid token"
    ),
    responses={
        200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "certificates_count": openapi.Schema(type=openapi.TYPE_INTEGER),
                "projects_count": openapi.Schema(type=openapi.TYPE_INTEGER),
                "goals_count": openapi.Schema(type=openapi.TYPE_INTEGER),
                # NEW fields:
                "goals_completed_count": openapi.Schema(type=openapi.TYPE_INTEGER),
                "goals_in_progress_count": openapi.Schema(type=openapi.TYPE_INTEGER),
                "goals_completion_rate_percent": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
            },
        ),
        401: "Unauthorized",
    },
)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def analytics_summary(request):
    """
    GET /api/analytics/summary/
    Return owner-scoped counts for:
    - certificates_count
    - projects_count
    - goals_count
    And NEW completion stats:
    - goals_completed_count
    - goals_in_progress_count
    - goals_completion_rate_percent
    """
    user = request.user

    qs_goals = Goal.objects.filter(user=user)
    total_goals = qs_goals.count()

    # A goal is "completed" when:
    # - completed_projects >= target_projects
    # - AND (no steps required OR completed_steps >= total_steps)
    completed_goals = qs_goals.filter(
        completed_projects__gte=models.F("target_projects")
    ).filter(
        models.Q(total_steps=0) | models.Q(completed_steps__gte=models.F("total_steps"))
    ).count()

    completion_rate = round(100 * (completed_goals / float(total_goals)), 1) if total_goals else 0.0

    data = {
        "certificates_count": Certificate.objects.filter(user=user).count(),
        "projects_count": Project.objects.filter(user=user).count(),
        "goals_count": total_goals,
        # NEW:
        "goals_completed_count": completed_goals,
        "goals_in_progress_count": max(0, total_goals - completed_goals),
        "goals_completion_rate_percent": completion_rate,
    }
    return Response(data, status=status.HTTP_200_OK)



@swagger_auto_schema(
    method="get",
    tags=["Analytics"],
    operation_description=(
        "List your goals including computed progress fields:\n"
        "• projects_progress_percent\n"
        "• steps_progress_percent\n"
        "• overall_progress_percent\n\n"
        "Responses:\n"
        "- 200: OK — array of Goal objects with progress fields\n"
        "- 401: Unauthorized"
    ),
    responses={
        200: openapi.Response("OK", GoalSerializer(many=True)),
        401: "Unauthorized",
    },
)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def analytics_goals_progress(request):
    """
    GET /api/analytics/goals-progress/
    Return the current user's goals with computed per-goal progress:
      - projects_progress_percent (completed_projects / target_projects)
      - steps_progress_percent    (from named steps when present, else totals)
      - overall_progress_percent  (average of the two)
    """
    qs = Goal.objects.filter(user=request.user).order_by("-created_at")
    ser = GoalSerializer(qs, many=True)  # no external context needed
    return Response(ser.data, status=status.HTTP_200_OK)
