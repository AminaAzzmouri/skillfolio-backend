"""
users/auth_views.py — JWT Auth helpers for Skillfolio

Purpose
===============================================================================
Centralizes all authentication-related views:
- Login (email-based JWT: {email,password} or {username,password})
- Register (simple dev helper)
- Logout (blacklist refresh token so it can't be reused)

Why this file?
-------------------------------------------------------------------------------
Keeps auth code isolated from resource ViewSets to avoid mixing concerns with
domain logic (certificates/projects/goals/analytics).

Endpoints
-------------------------------------------------------------------------------
POST /api/auth/login/      → returns {access, refresh}
POST /api/auth/refresh/    → (wired in urls.py via SimpleJWT)
POST /api/auth/register/   → creates a basic Django user (email-as-username)
POST /api/auth/logout/     → blacklists the provided refresh token
"""

from django.contrib.auth import get_user_model
from rest_framework import status, permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

# SimpleJWT login + blacklist tools
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken


# -------------------------------------------------------------------
# Email-based login
# -------------------------------------------------------------------
class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Allow clients to post {email, password} instead of {username, password}.

    Behavior:
      - If "email" is provided and "username" is not, we map email → username
        to work with Django's default User model.
    Security:
      - Relies on SimpleJWT for token issuance; add rate limiting at gateway later.
    """
    email = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        email = attrs.pop("email", None)
        if email and "username" not in attrs:
            attrs["username"] = email
        return super().validate(attrs)


class EmailTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Accepts {"email": "...", "password": "..."} OR {"username": "...", "password": "..."}.
    Returns {"refresh": "...", "access": "..."} on success.
    """
    serializer_class = EmailTokenObtainPairSerializer


# -------------------------------------------------------------------
# Register (dev helper) — minimal; add validation/verification in prod
# -------------------------------------------------------------------
User = get_user_model()

@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register(request):
    """
    POST /api/auth/register/
    Body: {"email": "...", "password": "..."}
    Creates a Django user with email stored as both username and email.
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


# -------------------------------------------------------------------
# Logout (blacklist refresh token)
# -------------------------------------------------------------------
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
    """
    POST /api/auth/logout/
    Expects JSON body: { "refresh": "<refresh_token>" }

    What it does:
      - Blacklists the submitted refresh token so it can no longer be used
        to obtain new access tokens (server-side logout).

    Returns:
      - 205 Reset Content on success
      - 400 Bad Request if the token is missing/invalid

    Notes:
      - You must install and enable 'rest_framework_simplejwt.token_blacklist'
        in INSTALLED_APPS and run migrations for this to work.
    """
    try:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)
    except Exception:
        return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)
