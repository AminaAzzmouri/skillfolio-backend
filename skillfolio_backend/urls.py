"""
urls.py — Root URL configuration for Skillfolio Backend

Purpose
===============================================================================
- Connects Django admin, API routers, and authentication endpoints.
- Serves media files in development (certificates, project uploads, etc.).
- Exposes DRF ViewSets for Certificates, Projects, and Goals.
- Adds JWT authentication endpoints (login, refresh) and a simple register.
- Adds Analytics endpoints for FE summaries/progress.
- Adds Logout (feature/auth-logout-blacklist) to blacklist refresh tokens.
- NEW (feature/api-docs): Adds Swagger/OpenAPI documentation:
    * /api/docs/   → Swagger UI (interactive)
    * /api/schema/ → OpenAPI JSON (machine-readable; FE reference)

Documentation of endpoints is included inline for clarity.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework import routers, permissions
from users import views  # resource ViewSets + analytics live here
from django.conf import settings
from django.conf.urls.static import static

# Auth endpoints (centralized in users.auth_views)
from users.auth_views import (
    EmailTokenObtainPairView,
    register,
    logout as jwt_logout,
)
from rest_framework_simplejwt.views import TokenRefreshView

# -------------------------------------------------------------------
#    --- DRF Routers (ViewSets → automatic CRUD endpoints) ---
# -------------------------------------------------------------------
# Routers automatically generate CRUD endpoints for viewsets.
# Example: /api/certificates/ → CertificateViewSet

router = routers.DefaultRouter()

# Certificates API
# /api/certificates/           → list (GET), create (POST)
# /api/certificates/{id}/      → retrieve (GET), update (PUT/PATCH), delete (DELETE)
router.register(r"certificates", views.CertificateViewSet)

# Projects API
# /api/projects/               → list (GET), create (POST)
# /api/projects/{id}/          → retrieve (GET), update (PUT/PATCH), delete (DELETE)
# Filtering examples:
#   /api/projects/?certificate=3
# Searching examples:
#   /api/projects/?search=django
router.register(r"projects", views.ProjectViewSet)

# Goals API
# /api/goals/                  → list (GET), create (POST)
# /api/goals/{id}/             → retrieve (GET), update (PUT/PATCH), delete (DELETE)
router.register(r"goals", views.GoalViewSet)

# -------------------------------------------------------------------
#   --- API Docs (Swagger/OpenAPI via drf-yasg) ---
# -------------------------------------------------------------------
# /api/docs/   → Swagger UI
# /api/schema/ → OpenAPI JSON
#
# Basic grouping/tags:
# - Router prefixes typically appear as tags (Certificates, Projects, Goals).
# - Function-based views (auth/register, analytics/*, auth/logout) are grouped by path.
# To add per-operation tags/descriptions later, decorate view methods with
# @swagger_auto_schema(tags=[...], operation_description="...").

from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Skillfolio API",
        default_version="v1",
        description=(
            "Interactive API documentation for Skillfolio.\n\n"
            "Auth uses JWT (Bearer) tokens.\n"
            "List endpoints support filtering/search/ordering where noted.\n"
            "Use the 'Authorize' button and paste: Bearer <ACCESS_TOKEN>."
        ),
        contact=openapi.Contact(email="support@skillfolio.example"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

# -------------------------------------------------------------------
#                      --- URL Patterns ---
# -------------------------------------------------------------------
urlpatterns = [
    path("admin/", admin.site.urls),  #  → Django admin panel

    # API (ViewSets)
    path("api/", include(router.urls)),  # → all app API endpoints (certificates, projects, goals)

    # Authentication endpoints (JWT)
    path("api/auth/login/",   EmailTokenObtainPairView.as_view(), name="token_obtain_pair"),  # /api/auth/login/
    path("api/auth/refresh/", TokenRefreshView.as_view(),         name="token_refresh"),      # /api/auth/refresh/
    path("api/auth/register/", register,                          name="register"),           # /api/auth/register/
    path("api/auth/logout/",   jwt_logout,                        name="logout"),             # /api/auth/logout/ (blacklist refresh)

    # Analytics
    # GET /api/analytics/summary/         → counts for current user
    # GET /api/analytics/goals-progress/  → list of goals with computed progress_percent
    path("api/analytics/summary/",        views.analytics_summary,        name="analytics-summary"),
    path("api/analytics/goals-progress/", views.analytics_goals_progress, name="analytics-goals-progress"),

    # API docs (drf-yasg)
    path("api/docs/",  schema_view.with_ui("swagger", cache_timeout=0), name="api-docs-swagger"),
    path("api/schema/", schema_view.without_ui(cache_timeout=0),        name="openapi-schema"),
]

# -------------------------------------------------------------------
#   --- Development-only media serving (uploads in /media/) ---
# -------------------------------------------------------------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
