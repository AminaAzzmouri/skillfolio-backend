"""
users/views.py — DRF ViewSets & Auth helpers for Skillfolio

Purpose
===============================================================================
Expose authenticated CRUD APIs for Certificate, Project, and Goal models,
and provide minimal JWT-based authentication endpoints tailored for email login.

Each get_queryset() filters objects by user=self.request.user, and perform_create() automatically assigns the currently authenticated user.
This means every CRUD operation you perform via /api/certificates/, /api/projects/ or /api/goals/ will only show or modify data belonging to the logged-in user, and nothing else.

Highlights
- Email-based JWT login (posts {email, password}, internally mapped to username).
- Simple register endpoint (dev helper) that creates a Django User using email as username.
- OwnerScopedModelViewSet base class enforces per-user data isolation:
    * Only returns request.user’s objects.
    * Automatically assigns user on create.
- Filtering/Search/Ordering enabled for FE integration (DRF + django-filter).

Week 4 Enhancements
-------------------------------------------------------------------------------
- Projects API: now exposes `status` and guided fields; adds filtering by `status`
  and retains optional filtering by `certificate`.
- Goals API: still CRUD; progress is exposed via serializer (`progress_percent`).
"""

# DRF ViewSets & Auth helpers for Skillfolio
from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Certificate, Project, Goal
from .serializers import CertificateSerializer, ProjectSerializer, GoalSerializer

# --- JWT (email login convenience) ---
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


# -----------------------------------------------------------------------------
# EmailTokenObtainPairSerializer
# -----------------------------------------------------------------------------
class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Allow clients to post {email, password} instead of {username, password}.
    """
    email = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        email = attrs.pop("email", None)
        if email and "username" not in attrs:
            attrs["username"] = email  # map email to username for default User
        return super().validate(attrs)


class EmailTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Accepts {"email": "...", "password": "..."} or {"username": "...", "password": "..."}.
    Returns {"refresh": "...", "access": "..."}.
    """
    serializer_class = EmailTokenObtainPairSerializer


# -----------------------------------------------------------------------------
# Quick register endpoint (developer helper)
# -----------------------------------------------------------------------------
User = get_user_model()


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register(request):
    """
    POST /api/auth/register/
    Minimal registration helper for development.
    """
    email = request.data.get("email")
    password = request.data.get("password")
    if not email or not password:
        return Response({"detail": "email and password required"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=email).exists():
        return Response({"detail": "user already exists"}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=email, email=email, password=password)
    return Response(
        {"id": user.id, "username": user.username, "email": user.email},
        status=status.HTTP_201_CREATED
    )


# -----------------------------------------------------------------------------
# Base ViewSet enforcing per-user ownership
# -----------------------------------------------------------------------------
class OwnerScopedModelViewSet(viewsets.ModelViewSet):
    """
    - Requires authentication (IsAuthenticated).
    - Restricts all list/retrieve/update/delete operations to the current user.
    - Automatically assigns request.user on create.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Assumes the model has a ForeignKey `user` field.
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# -----------------------------------------------------------------------------
# Resource ViewSets
# -----------------------------------------------------------------------------
class CertificateViewSet(OwnerScopedModelViewSet):
    """
    Certificates API
    Filter:   ?issuer=<str>&date_earned=<YYYY-MM-DD>
    Search:   ?search=<substring>  (title, issuer)
    Ordering: ?ordering=date_earned | -date_earned | title | -title
    """
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    filterset_fields = ["issuer", "date_earned"]
    search_fields = ["title", "issuer"]
    ordering_fields = ["date_earned", "title"]
    # Default ordering if FE doesn't pass ?ordering=...
    ordering = ["-date_earned"]


class ProjectViewSet(OwnerScopedModelViewSet):
    """
    Projects API
    Filter:   ?certificate=<id>&status=<planned|in_progress|completed>
    Search:   ?search=<substring>  (title, description[, problem_solved, tools_used, impact if present])
    Ordering: ?ordering=date_created | -date_created | title | -title
    """
    queryset = Project.objects.select_related("certificate").all()
    serializer_class = ProjectSerializer
    filterset_fields = ["certificate", "status"]
    # Keep search minimal/robust (title/description) — include extras if your model has them:
    search_fields = ["title", "description", "problem_solved", "tools_used", "impact"]
    ordering_fields = ["date_created", "title"]
    # Default: newest first
    ordering = ["-date_created"]


class GoalViewSet(OwnerScopedModelViewSet):
    """
    Goals API
    Filter:   ?deadline=<YYYY-MM-DD>
    Ordering: ?ordering=created_at | -created_at
    """
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
    filterset_fields = ["deadline"]
    ordering_fields = ["created_at"]
    # Default: most recent first
    ordering = ["-created_at"]
