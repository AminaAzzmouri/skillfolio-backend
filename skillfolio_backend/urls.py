"""
urls.py — Root URL configuration for Skillfolio Backend

Purpose
===============================================================================
- Wire Django admin, API routers, and auth endpoints.
- Serve media files in development.
- Expose DRF ViewSets for Certificates, Projects, Goals, and NEW GoalSteps.
- Provide small analytics endpoints for dashboard needs.
- Provide JWT auth endpoints (login, refresh, register, logout).
- Provide interactive API docs:
    * /api/docs/   → Swagger UI
    * /api/schema/ → OpenAPI JSON (machine-readable)

Notes
- ViewSets are grouped via a DRF router to reduce boilerplate.
- Auth views are centralized in users.auth_views.
- Swagger UI helps manual testing and is a handy reference for the FE.

NEW
- Registered GoalStepViewSet at /api/goalsteps/ for named checklist items
  under a goal (owner-scoped via parent goal).
- Profile endpoints:
  * /api/me/ (GET/PUT/PATCH/DELETE) → update identity or delete account
  * /api/auth/change-password/ (POST) → change password
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework import routers, permissions
from users import views  # resource ViewSets + analytics + profile
from django.conf import settings
from django.conf.urls.static import static

# Auth endpoints (centralized)
from users.auth_views import (
    EmailTokenObtainPairView,
    TokenRefreshTaggedView,
    register,
    logout as jwt_logout,
)
from rest_framework_simplejwt.views import TokenRefreshView

from django.shortcuts import redirect

from django.urls import path, include

# ----------------------------------------------------------------------------- #
# DRF Routers (ViewSets → automatic CRUD endpoints)                             #
# ----------------------------------------------------------------------------- #
router = routers.DefaultRouter()
router.register(r"certificates", views.CertificateViewSet, basename="certificate")
router.register(r"projects", views.ProjectViewSet, basename="project")
router.register(r"goals", views.GoalViewSet, basename="goal")
router.register(r"goalsteps", views.GoalStepViewSet, basename="goalstep")  # NEW

# ----------------------------------------------------------------------------- #
# API Docs (Swagger/OpenAPI via drf-yasg)                                       #
# ----------------------------------------------------------------------------- #
# /api/docs/   → Swagger UI
# /api/schema/ → OpenAPI JSON
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Skillfolio API",
        default_version="v1",
        description=(
            "Interactive API documentation for Skillfolio.\n\n"
            "Auth uses JWT (Bearer) tokens. Click 'Authorize' and paste: Bearer <ACCESS_TOKEN>.\n"
            "List endpoints support filtering/search/ordering where noted.\n\n"
            "Key endpoints:\n"
            "- /api/certificates/\n"
            "- /api/projects/\n"
            "- /api/goals/\n"
            "- /api/goalsteps/  (NEW: named checklist items per goal)\n"
            "- /api/me/         (NEW: profile)\n"
            "- /api/auth/change-password/  (NEW)\n"
        ),
        contact=openapi.Contact(email="support@skillfolio.example"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

# ----------------------------------------------------------------------------- #
# URL Patterns                                                                  #
# ----------------------------------------------------------------------------- #
urlpatterns = [
    # tiny root view that redirects to the FE (configurable per env)
    path("", lambda r: redirect(settings.FRONTEND_URL), name="root-redirect"),

    path("admin/", admin.site.urls),

    # API (ViewSets)
    path("api/", include(router.urls)),

    # Auth (JWT)
    path("api/auth/register/", register,                            name="register"),
    path("api/auth/login/",    EmailTokenObtainPairView.as_view(),  name="auth_login"),
    path("api/auth/refresh/",  TokenRefreshTaggedView.as_view(),    name="auth_refresh_create"),
    path("api/auth/logout/",   jwt_logout,                          name="logout"),

    # Profile (NEW)
    path("api/me/", views.MeView.as_view(),                         name="me"),
    path("api/auth/change-password/", views.ChangePasswordView.as_view(), name="auth_change_password"),

    # Analytics
    path("api/analytics/summary/",        views.analytics_summary,        name="analytics-summary"),
    path("api/analytics/goals-progress/", views.analytics_goals_progress, name="analytics-goals-progress"),

    # API docs
    path("api/docs/",   schema_view.with_ui("swagger", cache_timeout=0), name="api-docs-swagger"),
    path("api/schema/", schema_view.without_ui(cache_timeout=0),         name="openapi-schema"),

    path("api/", include("announcements.urls", namespace="announcements")),
]

# Dev-only media serving (uploads in /media/)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
