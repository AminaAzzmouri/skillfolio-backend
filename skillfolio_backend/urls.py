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

Documentation of endpoints is included inline for clarity.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from users import views  # resource ViewSets + analytics live here
from django.conf import settings
from django.conf.urls.static import static

# Auth endpoints (moved to users.auth_views to keep auth logic centralized)
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

    # Analytics (feature/analytics-endpoints)
    # GET /api/analytics/summary/         → counts for current user
    # GET /api/analytics/goals-progress/  → list of goals with computed progress_percent
    path("api/analytics/summary/",        views.analytics_summary,        name="analytics-summary"),
    path("api/analytics/goals-progress/", views.analytics_goals_progress, name="analytics-goals-progress"),
]

# -------------------------------------------------------------------
#   --- Development-only media serving (uploads in /media/) ---
# -------------------------------------------------------------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
