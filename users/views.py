"""
users/views.py — DRF ViewSets & Analytics for Skillfolio

Purpose
===============================================================================
Expose owner-scoped CRUD APIs for Certificate, Project, and Goal.
Add small analytics endpoints for counts and goal progress.

Ownership Model
- Each ViewSet filters by request.user and assigns user on create.
- This ensures an authenticated user can only see and modify their own data.

Highlights
- Per-user isolation via OwnerScopedModelViewSet base class.
- Filtering, search, and ordering are enabled for frontend integration.
- Analytics endpoints for quick dashboard counts and goal progress.

Auth Endpoints
- Auth (login/register/logout) are centralized in users.auth_views and wired in
  the root urls.py. Any auth classes that remain here are not wired to URLs.
"""

from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Certificate, Project, Goal
from .serializers import CertificateSerializer, ProjectSerializer, GoalSerializer

# The SimpleJWT email-login classes previously lived here; we now wire auth via
# users.auth_views. Keeping imports minimal in this module.


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
    search_fields = ["title", "description", "problem_solved", "tools_used", "impact"]
    ordering_fields = ["date_created", "title"]
    ordering = ["-date_created"]  # default newest first


class GoalViewSet(OwnerScopedModelViewSet):
    """
    Goals API
    - Filtering:   ?deadline=<YYYY-MM-DD>
    - Ordering:    ?ordering=created_at | -created_at
    """
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
    filterset_fields = ["deadline"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]  # default newest first


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
