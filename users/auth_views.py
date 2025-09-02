"""
users/auth_views.py — JWT auth helpers for Skillfolio

Purpose
===============================================================================
Provide a focused module for authentication endpoints:
- Login (JWT pair, email or username accepted)
- Register (simple dev helper; not a full signup flow)
- Logout (blacklist a submitted refresh token to invalidate future use)

Why a dedicated file?
- Keeps auth concerns separate from domain ViewSets (certificates/projects/goals).
- Makes the codebase to reason about and test.

Endpoints (wired in root urls.py)
- POST /api/auth/login/    → returns {"access": "...", "refresh": "..."}
- POST /api/auth/refresh/  → (SimpleJWT's refresh view, see urls.py)
- POST /api/auth/register/ → create a Django user (email-as-username)
- POST /api/auth/logout/   → blacklist the provided refresh token

Security Notes
- Logout requires SimpleJWT blacklist tables; ensure
  'rest_framework_simplejwt.token_blacklist' is in INSTALLED_APPS and migrated.

Swagger notes
- This module adds drf-yasg annotations so /api/docs/ shows request bodies for:
  * register (email + password)
  * logout (refresh token)
"""
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

# -----------------------------------------------------------------------------
# Email-based login
# -----------------------------------------------------------------------------
class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Accept {email,password} as an alias to {username,password}."""
    email = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        email = attrs.pop("email", None)
        if email and "username" not in attrs:
            attrs["username"] = email
        return super().validate(attrs)


class EmailTokenObtainPairView(TokenObtainPairView):
    """POST /api/auth/login/ — Returns refresh & access JWTs."""
    serializer_class = EmailTokenObtainPairSerializer

    @swagger_auto_schema(
        tags=["Auth"],
        operation_description="Log in and receive access/refresh JWTs.",
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


# -----------------------------------------------------------------------------
# Register (development helper)
# -----------------------------------------------------------------------------
User = get_user_model()

@swagger_auto_schema(
    method="post",
    tags=["Auth"],
    operation_description="Register a new user with email + password.",
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
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response({"detail": "email and password required"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=email).exists():
        return Response({"detail": "User already exists."}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=email, email=email, password=password)
    return Response({"id": user.id, "username": user.username, "email": user.email}, status=status.HTTP_201_CREATED)


# -----------------------------------------------------------------------------
# Logout (blacklist refresh token)
# -----------------------------------------------------------------------------
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
