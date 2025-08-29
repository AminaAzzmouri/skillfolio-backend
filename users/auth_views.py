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

# SimpleJWT login + blacklist tools
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

# Swagger tools
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import RegisterSerializer  # so Swagger knows the register body

# -----------------------------------------------------------------------------
# Email-based login
# -----------------------------------------------------------------------------
class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Accept {email, password} as an alternative to {username, password}.

    How it works
    - If the payload includes "email" and not "username", we copy email → username.
    - This matches Django's default User model which authenticates by "username".
    - Token issuance and validation remain handled by SimpleJWT.
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
    Body: {"email": "...", "password": "..."} OR {"username": "...", "password": "..."}
    Response: {"refresh": "...", "access": "..."}
    """
    serializer_class = EmailTokenObtainPairSerializer
    
    
EmailTokenObtainPairView.__doc__ = """
    POST /api/auth/login/
    Body: {"email": "...", "password": "..."} OR {"username": "...", "password": "..."}
    Response: {"refresh": "...", "access": "..."}
"""

EmailTokenObtainPairView.tags = ["Auth"]  # drf-yasg will group it under "Auth"



# -----------------------------------------------------------------------------
# Register (development helper)
# -----------------------------------------------------------------------------
User = get_user_model()

@swagger_auto_schema(
    method='post',
    tags=["Auth"],
    operation_description="Register a new user with email + password. Returns a minimal confirmation payload.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "email": openapi.Schema(type=openapi.TYPE_STRING, format="email"),
            "password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
            }),   # shows email + password fields in /api/docs
    responses={201: "User Created", 400: "Invalid Input"},
    security=[],  # public endpoint; no Bearer required
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register(request):
    """
    POST /api/auth/register/
    Body: {"email": "<str>", "password": "<str>"}

    Behavior
    - Creates a Django user using the supplied email as both username and email.
    - Returns 201 with a minimal confirmation (can be expanded later).
    - In production, add email verification, password strength checks, etc.
    """
    email = request.data.get("email")
    password = request.data.get("password")
   
    User = get_user_model()
   
    if not email or not password:
        return Response({"detail": "email and password required"}, status=status.HTTP_400_BAD_REQUEST)
    
    if User.objects.filter(username=email).exists():
        return Response({"detail": "User already exists."}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=email, email=email, password=password)
    user.save()
    
    return Response(
        {"id": user.id, "username": user.username, "email": user.email},
        status=status.HTTP_201_CREATED
    )


# -----------------------------------------------------------------------------
# Logout (server-side invalidation via refresh-token blacklist)
# -----------------------------------------------------------------------------
logout_request_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["refresh"],
    properties={
        "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="Refresh token to blacklist")
    },
)
@swagger_auto_schema(
    method='post',
    tags=["Auth"],
    operation_description="Blacklist a submitted refresh token to invalidate future use.",
    request_body=logout_request_schema,
    responses={205: "Reset Content", 400: "Bad Request"},
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
    """
    POST /api/auth/logout/
    Body: {"refresh": "<refresh_token>"}

    What this does
    - Takes the submitted refresh token and blacklists it.
    - Once blacklisted, that refresh token cannot be used to mint new access tokens.

    Returns
    - 205 Reset Content and {"detail": "..."} when successful
    - 400 Bad Request if the token is missing or invalid

    Requirements
    - 'rest_framework_simplejwt.token_blacklist' must be installed and migrated.
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