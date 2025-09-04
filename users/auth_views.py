"""
users/auth_views.py — JWT auth helpers for Skillfolio


Purpose
===============================================================================
Provide a focused module for authentication endpoints:
- Login (JWT pair, email or username accepted)  ← UPDATED
- Register (simple dev helper; not a full signup flow)
- Refresh (via SimpleJWT)
- Logout (blacklist a submitted refresh token to invalidate future use)
- Me (profile): GET/PUT/PATCH/DELETE under Auth section in /api/docs
- Change Password: POST under Auth section in /api/docs


Why a dedicated file?
- Keeps auth concerns separate from domain ViewSets (certificates/projects/goals).
- Makes the codebase easier to reason about and test.
- Groups all identity & credential endpoints under a single Swagger tag ("Auth").


Endpoints (wired in root urls.py)
- POST /api/auth/login/            → returns {"access": "...", "refresh": "...", "username", "email"}
- POST /api/auth/refresh/          → (SimpleJWT's refresh view, tagged)
- POST /api/auth/register/         → create a Django user (username auto from email local-part)
- POST /api/auth/logout/           → blacklist provided refresh token (owner-checked)            ← UPDATED
- GET/PUT/PATCH/DELETE /api/auth/me/ → profile (username/email, delete account)                  ← NEW HERE
- (Legacy alias) /api/me/          → same as /api/auth/me/ for backward compatibility
- POST /api/auth/change-password/  → change password


Security Notes
- Logout requires SimpleJWT blacklist tables; ensure
  'rest_framework_simplejwt.token_blacklist' is in INSTALLED_APPS and migrated.
- Profile & password endpoints require authentication (IsAuthenticated).


Swagger notes
- All endpoints in this module are tagged **Auth** so they appear in one group:
  * login (two fields only: **email_or_username** + **password**)                      ← UPDATED
  * register (email + password)  (username auto from local-part)                       ← UPDATED
  * refresh (refresh token)
  * logout (refresh token)
  * me (GET/PUT/PATCH/DELETE)
  * change-password (current_password + new_password)
"""
import re

from django.contrib.auth import get_user_model
from rest_framework import status, permissions, serializers, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

# Serializers
from .serializers import (
    EmailOrUsernameTokenObtainPairSerializer,
    MeSerializer,                 # profile fields (id/username/email) + validation
    ChangePasswordSerializer,     # validates current_password & new_password
)

# SimpleJWT
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView as _TokenRefreshView,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

# Swagger / OpenAPI
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


# ---------------------------------------------------------------------------
# Common response schemas for docs
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Login (email or username) → JWT pair
# ---------------------------------------------------------------------------
class LoginDocSerializer(serializers.Serializer):
    email_or_username = serializers.CharField(help_text="Type your email address OR your username.")
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class EmailTokenObtainPairView(TokenObtainPairView):
    """POST /api/auth/login/ — Returns refresh & access JWTs (email_or_username + password)."""
    serializer_class = EmailOrUsernameTokenObtainPairSerializer

    @swagger_auto_schema(
        tags=["Auth"],
        operation_description="Log in with **email_or_username** (email or the short username) and **password**.",
        request_body=LoginDocSerializer,  # ← exactly two fields in /api/docs
        security=[],  # public endpoint
        responses={
            200: openapi.Response("JWT pair", TOKENS_PAIR_SCHEMA),
            400: "Bad Request",
            401: "Invalid credentials",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Refresh access token
# ---------------------------------------------------------------------------
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
    Build a clean, unique username from the **email local-part**.
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
# Logout (blacklist refresh token) — FIXED user ownership check + status code
# ---------------------------------------------------------------------------
logout_request_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["refresh"],
    properties={"refresh": openapi.Schema(type=openapi.TYPE_STRING, description="Refresh token to blacklist")},
)


@swagger_auto_schema(
    method="post",
    tags=["Auth"],
    operation_description=(
        "Blacklist a submitted refresh token to invalidate future use.\n\n"
        "**Ownership check**: the submitted token must belong to the authenticated caller."
    ),
    request_body=logout_request_schema,
    responses={
        205: "Reset Content",  # we return 205 to match tests expecting 200/205
        200: "OK",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
    },
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
    """
    POST /api/auth/logout/
    Body: { "refresh": "<refresh_token>" }

    Behavior
    - Requires authentication (the caller presents a valid access token).
    - Validates the provided refresh token and ensures it belongs to the caller.
    - Blacklists the refresh token (SimpleJWT blacklist app).
    - Returns **205 Reset Content** to align with existing tests.

    FIX
    - Previously used `request.user_id` which doesn't exist. Use `request.user.id`.
    - Adds robust guards for anonymous/no-user scenarios (should not happen with IsAuthenticated).
    """
    refresh_token = request.data.get("refresh")
    if not refresh_token:
        return Response({"detail": "refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Guard (normally redundant due to IsAuthenticated)
    if not hasattr(request, "user") or not request.user or not request.user.is_authenticated:
        return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        token = RefreshToken(refresh_token)

        # Ensure the token being blacklisted belongs to the caller
        token_user_id = token.get("user_id")
        caller_id = getattr(request.user, "id", None)
        if caller_id is None or token_user_id != caller_id:
            return Response({"detail": "token does not belong to you"}, status=status.HTTP_403_FORBIDDEN)

        token.blacklist()
    except TokenError:
        return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)

    # Match your test suite's expectation (200 or 205). We pick 205.
    return Response({"detail": "Logged out."}, status=status.HTTP_205_RESET_CONTENT)


# ---------------------------------------------------------------------------
# Me (Profile / Account) endpoints — GET/PUT/PATCH/DELETE (under "Auth" in Swagger)
# ---------------------------------------------------------------------------
class AuthMeView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve/Update/Delete the authenticated user.

    Methods
    - GET    /api/auth/me/      → return { id, username, email }
    - PUT    /api/auth/me/      → update username & email (both required)
    - PATCH  /api/auth/me/      → update subset of fields
    - DELETE /api/auth/me/      → permanently delete the account

    Notes
    - Password changes are handled by POST /api/auth/change-password/.
    - Unique email is enforced (case-insensitive).
    - A legacy alias /api/me/ is provided in urls.py for backward compatibility.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user
    
    # Swagger method-by-method docs with success/error codes:
    @swagger_auto_schema(
        tags=["Auth"],
        operation_description="Get your profile (id, username, email).",
        responses={200: MeSerializer, 401: "Unauthorized"},
    )
    
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=["Auth"],
        operation_description=(
            "Replace your profile (username & email **both required**).\n\n"
            "Errors:\n"
            "- 400: invalid fields (e.g., bad email format)\n"
            "- 400: duplicate email (case-insensitive)\n"
            "- 401: unauthorized"
        ),
        request_body=MeSerializer,
        responses={200: MeSerializer, 400: "Bad Request", 401: "Unauthorized"},
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=["Auth"],
        operation_description=(
            "Partially update your profile (username and/or email).\n\n"
            "Errors:\n"
            "- 400: invalid field(s) or duplicate email\n"
            "- 401: unauthorized"
        ),
        request_body=MeSerializer,
        responses={200: MeSerializer, 400: "Bad Request", 401: "Unauthorized"},
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=["Auth"],
        operation_description="Delete your account permanently.",
        responses={204: "No Content", 401: "Unauthorized"},
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Change Password — POST (under "Auth" in Swagger)
# ---------------------------------------------------------------------------
class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/

    Body:
      {
        "current_password": "<string>",
        "new_password": "<string>"
      }

    Behavior:
    - Verifies the current password matches.
    - Validates the new password via Django's password validators.
    - Updates the password atomically.
    - Returns 200 on success, with a simple message payload:
        { "detail": "Password updated." }

    Notes
    - Clients may prompt the user to log in again if desired; this endpoint does
      not automatically invalidate tokens (kept simple for now).
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Auth"],
        operation_description=(
            "Change your password (must provide current_password and new_password).\n\n"
            "Errors:\n"
            "- 400: invalid payload or new password fails validators\n"
            "- 401: unauthorized\n"
            "- 400: current password incorrect"
        ),
        request_body=ChangePasswordSerializer,
        responses={200: "OK", 400: "Bad Request", 401: "Unauthorized"},
    )
    def post(self, request):
        ser = ChangePasswordSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        user = request.user
        user.set_password(ser.validated_data["new_password"])
        user.save()
        return Response({"detail": "Password updated."}, status=status.HTTP_200_OK)
