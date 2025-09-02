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
                             (username is auto-derived from the email local-part)  ← NEW
- POST /api/auth/logout/   → blacklist the provided refresh token

Security Notes
- Logout requires SimpleJWT blacklist tables; ensure
  'rest_framework_simplejwt.token_blacklist' is in INSTALLED_APPS and migrated.

Swagger notes
- This module adds drf-yasg annotations so /api/docs/ shows request bodies for:
  * login (username OR email OR login + password)  ← NEW
  * register (email + password)                    ← UPDATED (docs unchanged, behavior clarified)
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

# Swagger / OpenAPI
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Common response schemas for docs
TOKENS_PAIR_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "access": openapi.Schema(type=openapi.TYPE_STRING, description="Access JWT"),
        "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="Refresh JWT"),
    },
)
ACCESS_ONLY_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "access": openapi.Schema(type=openapi.TYPE_STRING, description="New access JWT"),
        # May also include 'refresh' if ROTATE_REFRESH_TOKENS=True (not required).
    },
)

# ---------------------------------------------------------------------------
# Flexible login: username OR email (or a single 'login' field)
# ---------------------------------------------------------------------------
class FlexibleLoginTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Accept either:
      - {"username": "<username>", "password": "..."}  OR
      - {"email": "<email>", "password": "..."}        OR
      - {"login": "<username-or-email>", "password": "..."}.

    If an email is provided, we resolve it to the account's username so that
    SimpleJWT can authenticate normally (Django's default backend expects 'username').
    """
    username = serializers.CharField(required=False)
    email = serializers.EmailField(write_only=True, required=False)
    login = serializers.CharField(write_only=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Don't force 'username'—we allow email/login instead
        self.fields["username"].required = False

    def validate(self, attrs):
        User = get_user_model()

        # Pull identifier from any accepted field
        identifier = (
            (attrs.pop("login", "") or "").strip()
            or (attrs.pop("email", "") or "").strip()
            or (attrs.get("username") or "").strip()
        )

        if not identifier:
            raise serializers.ValidationError(
                {"detail": "Provide 'username' or 'email' (or 'login')."}
            )

        # If it's an email, map it to the actual username for SimpleJWT
        if "@" in identifier:
            try:
                user = User.objects.get(email__iexact=identifier)
                attrs["username"] = user.get_username()
            except User.DoesNotExist:
                # Let parent class produce the standard invalid-credentials error
                attrs["username"] = identifier
        else:
            attrs["username"] = identifier

        return super().validate(attrs)


# Manual request body schema for Swagger (Swagger 2.0 doesn't support oneOf here)
LOGIN_REQUEST_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "username": openapi.Schema(type=openapi.TYPE_STRING, description="Your username (optional if providing email/login)"),
        "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", description="Your email (optional if providing username/login)"),
        "login": openapi.Schema(type=openapi.TYPE_STRING, description="Alternative single identifier (username or email)"),
        "password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
    },
    required=["password"],
    description="Provide either 'username' or 'email' (or use 'login') plus 'password'.",
)


class EmailTokenObtainPairView(TokenObtainPairView):
    """POST /api/auth/login/ — Returns refresh & access JWTs (username OR email)."""
    serializer_class = FlexibleLoginTokenObtainPairSerializer

    @swagger_auto_schema(
        tags=["Auth"],
        operation_description="Log in with **username or email** and receive access/refresh JWTs.",
        request_body=LOGIN_REQUEST_SCHEMA,
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
    Build a clean, unique username from the email local-part.               ← NEW
    - keep: a-z 0-9 . _ -
    - others → '_'
    - ensure unique with -2, -3, ...
    - cap to 150 chars (Django username max)
    """
    local = (email or "").split("@", 1)[0].lower()
    base = re.sub(r"[^a-z0-9._-]", "_", local).strip("._-") or "user"
    limit = 150

    cand = base[:limit]
    if not User.objects.filter(username=cand).exists():
        return cand

    n = 2
    while True:
        suffix = f"-{n}"
        head = base[: max(1, limit - len(suffix))]
        cand = f"{head}{suffix}"
        if not User.objects.filter(username=cand).exists():
            return cand
        n += 1


@swagger_auto_schema(
    method="post",
    tags=["Auth"],
    operation_description=(
        "Register a new user with email + password.\n\n"
        "Username is **auto-derived from the email local-part** (e.g., 'john' from 'john@gmail.com')."
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
    password = request.data.get("password")

    if not email or not password:
        return Response({"detail": "email and password required"}, status=status.HTTP_400_BAD_REQUEST)

    # Prevent duplicate accounts for the same email (case-insensitive)
    if User.objects.filter(email__iexact=email).exists():
        return Response({"detail": "User already exists."}, status=status.HTTP_400_BAD_REQUEST)

    # Auto-generate username from the email's local-part
    username = _suggest_username_from_email(email)

    user = User.objects.create_user(username=username, email=email, password=password)
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
    responses={205: "Reset Content", 400: "Bad Request", 401: "Unauthorized"},
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)
    except Exception:
        return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)
