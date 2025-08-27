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

    Why?
    ----------------------------------------------------------------------------
    By default, Django's auth uses "username". For a quick MVP with the default
    User model, we simply treat the provided email as the username. This keeps
    things simple until we decide to introduce a custom user model.

    Behavior:
    - If an "email" is provided and "username" is not, this serializer maps
      email -> username before calling the parent validation.

    Security:
    - This still relies on SimpleJWT’s secure token issuance. Rate limiting and
      brute-force protection can be added at the view or gateway layer later.
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
    ----------------------------------------------------------------------------
    Accepts JSON: {"email": "...", "password": "..."} or {"username": "...", "password": "..."} via a custom serializer that maps email → username), /api/auth/refresh/ to renew tokens, and /api/auth/register/ to create a user quickly.

    These endpoints return { "refresh": "...", "access": "..." } tokens so the frontend can authenticate requests without a session cookie.
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
    ----------------------------------------------------------------------------
    Minimal registration helper for development.

    Input JSON:
      - email (required)
      - password (required)

    Behavior:
      - Uses default Django User; stores email as both username and email.
      - Returns created user's id/username/email on success.

    Notes:
      - No email verification or password validation here (MVP). We might consider adding:
        * Django's password validators
        * Email confirmation
        * Unique email checks beyond username
    """
    email = request.data.get("email")
    password = request.data.get("password")
    if not email or not password:
        return Response({"detail": "email and password required"}, status=status.HTTP_400_BAD_REQUEST)

    # Default User requires "username". We use the email as username for MVP.
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
    A reusable base class that:
    ----------------------------------------------------------------------------
    - Requires authentication (IsAuthenticated).
    - Restricts all list/retrieve/update/delete operations to the current user.
    - Automatically assigns request.user on create.

    Why?
    ----------------------------------------------------------------------------
    Ensures users only ever see and manage their own resources, without repeating
    the same logic in each ViewSet.

    Extend:
      class MyViewSet(OwnerScopedModelViewSet):
          queryset = MyModel.objects.all()
          serializer_class = MySerializer
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Assumes the model has a ForeignKey `user` field.
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Inject the authenticated user
        serializer.save(user=self.request.user)


# -----------------------------------------------------------------------------
# Resource ViewSets
# -----------------------------------------------------------------------------
class CertificateViewSet(OwnerScopedModelViewSet):
    """
    Certificates API
    ----------------------------------------------------------------------------
    - List only the authenticated user's certificates.
    - Create assigns the authenticated user automatically.
    - Filtering/Search/Ordering support for FE list views.

    Query params:
      - filter:   ?issuer=<str>&date_earned=<YYYY-MM-DD>                              > filters by issuer/date
      - search:   ?search=<substring>  (title, issuer)                                > searches title or issuer
      - ordering: ?ordering=date_earned  or  ?ordering=-date_earned  (also "title")   > orders newest first
    """
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    filterset_fields = ["issuer", "date_earned"]
    search_fields = ["title", "issuer"]
    ordering_fields = ["date_earned", "title"]


class ProjectViewSet(OwnerScopedModelViewSet):
    """
    Projects API
    ----------------------------------------------------------------------------
    - List/create/update/delete projects owned by the authenticated user.
    - Optionally link a project to a certificate (nullable FK).
    - Guided answers are stored (work_type, duration_text, primary_goal,
      challenges_short, skills_used, outcome_short, skills_to_improve).
      If `description` is blank, the backend auto-generates it from these fields.
    - Includes select_related('certificate') for efficient list queries.

    Query params:
      - filter:   ?certificate=<id> &/or ?status=<planned|in_progress|completed>
      - search:   ?search=<substring>  (title, description, problem_solved, tools_used, impact)
      - ordering: ?ordering=date_created  or  ?ordering=-date_created  (also "title")
    """
    queryset = Project.objects.select_related("certificate").all()
    serializer_class = ProjectSerializer
    filterset_fields = ["certificate", "status"]   # /api/projects/?certificate=<id>&status=<choice>
    search_fields = ["title", "description", "problem_solved", "tools_used", "impact"]
    ordering_fields = ["date_created", "title"]


class GoalViewSet(OwnerScopedModelViewSet):
    """
    Goals API
    ----------------------------------------------------------------------------
    - Track user goals (e.g., target number of projects before a deadline).
    - List/create/update/delete goals owned by the authenticated user.

    Query params:
      - filter:   ?deadline=<YYYY-MM-DD>                          > filters by deadline
      - ordering: ?ordering=created_at or ?ordering=-created_at   > shows most recent first.

    Week 4 ideas:
      - Expose computed progress (% completed / target_projects) as a read-only
        serializer field (implemented in serializer).
      - Add validation to prevent past deadlines (still optional).
    """
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
    filterset_fields = ["deadline"]
    ordering_fields = ["created_at"]
