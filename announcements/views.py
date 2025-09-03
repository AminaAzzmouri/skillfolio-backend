"""
announcements/views.py

Endpoints:
- /api/announcements/  (GET list; auth required) with filter/search/order
- /api/facts/random/   (GET one random active fact; public)

Filtering:
- platform=Coursera (iexact)
- type=enrollment|discount
- starts_at_after=YYYY-MM-DD
- ends_at_before=YYYY-MM-DD
- search=free text (title, platform, tags JSON as text)
- ordering=-starts_at (default), or any in ordering_fields
"""
from django.db.models import Value
from django.db.models.functions import Cast
from django.utils import timezone
from django_filters import rest_framework as dj_filters
from rest_framework import filters, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Announcement, Fact
from .serializers import AnnouncementSerializer, FactSerializer


from urllib.parse import quote_plus
from .platforms import PLATFORMS



class AnnouncementFilter(dj_filters.FilterSet):
    platform = dj_filters.CharFilter(field_name="platform", lookup_expr="iexact")
    type = dj_filters.CharFilter(field_name="type", lookup_expr="iexact")
    starts_at_after = dj_filters.DateFilter(field_name="starts_at", lookup_expr="gte")
    ends_at_before = dj_filters.DateFilter(field_name="ends_at", lookup_expr="lte")

    class Meta:
        model = Announcement
        fields = ["platform", "type", "starts_at_after", "ends_at_before"]


class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only list endpoint for announcements.

    Security: we require authentication so the feed can be tailored per-user later.
    (Switch to AllowAny if you want it public.)
    """
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [dj_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AnnouncementFilter
    search_fields = ["title", "platform", "tags"]  # JSONField search is DB-dependent; basic contains works on Postgres.
    ordering_fields = ["starts_at", "created_at", "discount_pct", "price_current"]
    ordering = ["-starts_at", "-created_at"]


class RandomFactView(APIView):
    """
    Return exactly one random *active* fact.

    Keep it public so the home page can show a fact even for logged-out users.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = Fact.objects.filter(active=True)
        fact = qs.order_by("?").first()
        if not fact:
            return Response({"detail": "No active facts available."}, status=404)
        return Response(FactSerializer(fact).data)

class PlatformSearchView(APIView):
    """
    GET /api/platforms/?q=machine learning
    Returns platform list with direct search links for the given query.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        out = []
        for p in PLATFORMS:
            search_url = p["home"]
            if q:
                search_url = p["search"].format(q=quote_plus(q))
            out.append({
                "name": p["name"],
                "category": p.get("category", ""),
                "home": p["home"],
                "search_url": search_url,
            })
        return Response({"query": q, "platforms": out})
