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
"""

from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

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
    - Filtering:   ?issuer=<str>&date_earned=<YYYY-MM-DD>
    - Search:      ?search=<substring> (title, issuer)
    - Ordering:    ?ordering=date_earned | -date_earned | title | -title
    """
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    filterset_fields = ["issuer", "date_earned"]
    search_fields = ["title", "issuer"]
    ordering_fields = ["date_earned", "title"]
    ordering = ["-date_earned"]  # default newest first


class ProjectViewSet(OwnerScopedModelViewSet):
    """
    Projects API
    - Filtering:   ?certificate=<id>&status=<planned|in_progress|completed>
    - Search:      ?search=<substring> (title, description[, other fields if present])
    - Ordering:    ?ordering=date_created | -date_created | title | -title
    """
    queryset = Project.objects.select_related("certificate").all()
    serializer_class = ProjectSerializer
    filterset_fields = ["certificate", "status"]
    # Keep search pragmatic: title/description + optional fields if present in model
    search_fields = ["title", "description", "problem_solved", "tools_used"]
    ordering_fields = ["date_created", "title"]
    ordering = ["-date_created"]  # default newest first


class GoalViewSet(OwnerScopedModelViewSet):
    """
    Goals API
    - Filtering:   ?deadline=<YYYY-MM-DD>
    - Ordering:    ?ordering=created_at | -created_at | deadline | -deadline
                   | total_steps | -total_steps | completed_steps | -completed_steps
    """
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
    filterset_fields = ["deadline"]
    ordering_fields = ["created_at", "deadline", "total_steps", "completed_steps", "title"]
    ordering = ["-created_at"]  # default newest first

    # Optional: schema docs for create/partial update (only if drf-yasg is present)
    if HAS_YASG:
        _steps_props = {
            "title": openapi.Schema(type=openapi.TYPE_STRING, description="Goal title"),
            "target_projects": openapi.Schema(type=openapi.TYPE_INTEGER, description="Target number of completed projects"),
            "deadline": openapi.Schema(type=openapi.TYPE_STRING, format="date", description="Goal deadline (YYYY-MM-DD)"),
            "total_steps": openapi.Schema(type=openapi.TYPE_INTEGER, description="Optional checklist total"),
            "completed_steps": openapi.Schema(type=openapi.TYPE_INTEGER, description="Optional checklist completed"),
        }

        @swagger_auto_schema(
            request_body=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties=_steps_props,
                required=["title", "target_projects", "deadline"],
            ),
            responses={201: GoalSerializer},
        )
        def create(self, request, *args, **kwargs):
            return super().create(request, *args, **kwargs)

        @swagger_auto_schema(
            request_body=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties=_steps_props,
            ),
            responses={200: GoalSerializer},
        )
        def partial_update(self, request, *args, **kwargs):
            return super().partial_update(request, *args, **kwargs)


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
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def analytics_summary(request):
    """
    GET /api/analytics/summary/
    Return owner-scoped counts for:
    - certificates_count
    - projects_count
    - goals_count

    Useful for: showing KPIs on a dashboard without multiple round-trips.
    """
    user = request.user
    data = {
        "certificates_count": Certificate.objects.filter(user=user).count(),
        "projects_count": Project.objects.filter(user=user).count(),
        "goals_count": Goal.objects.filter(user=user).count(),
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def analytics_goals_progress(request):
    """
    GET /api/analytics/goals-progress/
    Return the current user's goals with computed `progress_percent`.

    Implementation detail
    - The serializer needs the request context to determine which user's
      completed projects to count for progress.
    """
    qs = Goal.objects.filter(user=request.user).order_by("-created_at")
    ser = GoalSerializer(qs, many=True, context={"request": request})
    return Response(ser.data, status=status.HTTP_200_OK)
