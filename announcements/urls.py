"""
announcements/urls.py

Router + extra path for the random fact endpoint.
Include this under the global /api/ prefix.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AnnouncementViewSet, RandomFactView, PlatformSearchView


app_name = "announcements"

router = DefaultRouter()
router.register(r"announcements", AnnouncementViewSet, basename="announcement")

urlpatterns = [
    path("", include(router.urls)),
    path("facts/random/", RandomFactView.as_view(), name="fact-random"),
    path("platforms/", PlatformSearchView.as_view(), name="platforms-search"),
]
