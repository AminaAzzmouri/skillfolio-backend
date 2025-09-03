"""
users/auth_views.py — JWT auth helpers for Skillfolio

Purpose
===============================================================================
Provide a focused module for authentication endpoints:
- Login (JWT pair, email or username accepted)  ← UPDATED
- Register (simple dev helper; not a full signup flow)
- Logout (blacklist a submitted refresh token to invalidate future use)

Why a dedicated file?
- Keeps auth concerns separate from domain ViewSets (certificates/projects/goals).
- Makes the codebase to reason about and test.

Endpoints (wired in root urls.py)
- POST /api/auth/login/    → returns {"access": "...", "refresh": "..."}
- POST /api/auth/refresh/  → (SimpleJWT's refresh view, see urls.py)
- POST /api/auth/register/ → create a Django user
                             (username is auto-derived from the email **local-part**)  ← UPDATED
- POST /api/auth/logout/   → blacklist the provided refresh token

Security Notes
- Logout requires SimpleJWT blacklist tables; ensure
  'rest_framework_simplejwt.token_blacklist' is in INSTALLED_APPS and migrated.

Swagger notes
- This module adds drf-yasg annotations so /api/docs/ shows request bodies for:
  * login (two fields only: **email_or_username** + **password**)             ← UPDATED
  * register (email + password)  (username auto from local-part)              ← UPDATED
  * logout (refresh token)
"""

import re
from django.contrib.auth import get_user_model
from rest_framework import status, permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

# SimpleJWT
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView as _TokenRefreshView,
)

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

# Swagger / OpenAPI
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from rest_framework.permissions import AllowAny
from .serializers import EmailOrUsernameTokenObtainPairSerializer

# Common response schemas for docs
TOKENS_PAIR_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["access", "refresh"],
    properties={
        "access": openapi.Schema(type=openapi.TYPE_STRING, description="Access JWT"),
        "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="Refresh JWT"),
        "username": openapi.Schema(type=openapi.TYPE_STRING, description="Username for UI display"),
        "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", description="User email"),
    },
)
ACCESS_ONLY_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "access": openapi.Schema(type=openapi.TYPE_STRING, description="New access JWT"),
        # May also include 'refresh' if ROTATE_REFRESH_TOKENS=True (not required).
    },
)

# ---- Swagger request body for login (TWO FIELDS ONLY) ----------------------
class LoginDocSerializer(serializers.Serializer):
    email_or_username = serializers.CharField(help_text="Type your email address OR your username.")
    password = serializers.CharField(write_only=True, style={"input_type":"password"})

class EmailTokenObtainPairView(TokenObtainPairView):
    """POST /api/auth/login/ — Returns refresh & access JWTs (email_or_username + password)."""
    serializer_class = EmailOrUsernameTokenObtainPairSerializer

    @swagger_auto_schema(
        tags=["Auth"],
        operation_description="Log in with **email_or_username** (email or the short username) and **password**.",
        request_body=LoginDocSerializer,  # ← shows exactly two fields in /api/docs
        security=[],  # public endpoint
        responses={
            200: openapi.Response("JWT pair", TOKENS_PAIR_SCHEMA),
            400: "Bad Request",
            401: "Invalid credentials",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TokenRefreshTaggedView(_TokenRefreshView):
    """POST /api/auth/refresh/ — Exchange refresh for a new access token."""
    @swagger_auto_schema(
        tags=["Auth"],
        operation_description="Refresh access token using a refresh JWT.",
        security=[],  # public endpoint
        responses={
            200: openapi.Response("New access token", ACCESS_ONLY_SCHEMA),
            400: "Bad Request",
            401: "Invalid or blacklisted refresh token",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Register (development helper)
# ---------------------------------------------------------------------------
User = get_user_model()

def _suggest_username_from_email(email: str) -> str:
    """
    Build a clean, unique username from the **email local-part**.            ← UPDATED
    - keep: a-z 0-9 . _ -
    - others → '_'
    - ensure unique with -2, -3, ...
    - cap to 150 chars (Django username max)
    """
    local = (email or "").split("@", 1)[0].lower()
    base = re.sub(r"[^a-z0-9._-]", "_", local).strip("._-") or "user"
    limit = 150

    cand = base[:limit]
    if not User.objects.filter(username__iexact=cand).exists():
        return cand

    n = 2
    while True:
        suffix = f"-{n}"
        head = base[: max(1, limit - len(suffix))]
        cand = f"{head}{suffix}"
        if not User.objects.filter(username__iexact=cand).exists():
            return cand
        n += 1


@swagger_auto_schema(
    method="post",
    tags=["Auth"],
    operation_description=(
        "Register a new user with email + password.\n\n"
        "Username is **automatically derived from the part before '@'** "
        "(e.g., 'happy' from 'happy@example.com'). If taken, '-2', '-3', … are appended."
    ),
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "email": openapi.Schema(type=openapi.TYPE_STRING, format="email"),
            "password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
        },
        required=["email", "password"],
    ),
    responses={201: "User Created", 400: "Invalid Input"},
    security=[],  # public endpoint
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register(request):
    email = (request.data.get("email") or "").strip()
    email_lc = email.lower()
    password = request.data.get("password")

    if not email or not password:
        return Response({"detail": "email and password required"}, status=status.HTTP_400_BAD_REQUEST)

    # Prevent duplicate accounts for the same email (case-insensitive)
    if User.objects.filter(email__iexact=email_lc).exists():
        return Response({"detail": "User already exists."}, status=status.HTTP_400_BAD_REQUEST)

    # Store short username derived from local-part (NOT the full email)      ← UPDATED
    username = _suggest_username_from_email(email)
    user = User.objects.create_user(username=username, email=email_lc, password=password)
    return Response({"id": user.id, "username": user.username, "email": user.email}, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Logout (blacklist refresh token)
# ---------------------------------------------------------------------------
logout_request_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["refresh"],
    properties={"refresh": openapi.Schema(type=openapi.TYPE_STRING, description="Refresh token to blacklist")},
)

@swagger_auto_schema(
    method="post",
    tags=["Auth"],
    operation_description="Blacklist a submitted refresh token to invalidate future use.",
    request_body=logout_request_schema,
    responses={204: "No Content", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden"},
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            token = RefreshToken(refresh_token)
            # Ensure the token being blacklisted belongs to the caller
            if token.get("user_id") != request.user_id:
                return Response({"detail":"token does not belong to you"}, status=status.HTTP_403_FORBIDDEN)
            token.blacklist()
        except TokenError:
             return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)
         
        # No body for 204 = success
        return Response(status=status.HTTP_204_NO_CONTENT)
       
