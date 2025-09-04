"""
announcements/views.py

Endpoints:
- /api/announcements/   (GET list; auth required) with filter/search/order
- /api/announcements/{id}/ (GET retrieve; auth required)
- /api/facts/random/    (GET one random active fact; public)
- /api/platforms/       (GET helper that returns platform links for a query)

Filtering:
- platform=Coursera (iexact)
- type=enrollment|discount
- starts_at_after=YYYY-MM-DD
- ends_at_before=YYYY-MM-DD
- search=free text (title, platform, tags JSON as text)
- ordering=-starts_at (default), or any in ordering_fields
"""

from django_filters import rest_framework as dj_filters
from rest_framework import filters, permissions, viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Announcement, Fact
from .serializers import AnnouncementSerializer, FactSerializer

from urllib.parse import quote_plus
from .platforms import PLATFORMS

# Swagger / OpenAPI
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


# ----------------------------------------------------------------------------- #
# Filters                                                                       #
# ----------------------------------------------------------------------------- #
class AnnouncementFilter(dj_filters.FilterSet):
    platform = dj_filters.CharFilter(field_name="platform", lookup_expr="iexact")
    type = dj_filters.CharFilter(field_name="type", lookup_expr="iexact")
    starts_at_after = dj_filters.DateFilter(field_name="starts_at", lookup_expr="gte")
    ends_at_before = dj_filters.DateFilter(field_name="ends_at", lookup_expr="lte")

    class Meta:
        model = Announcement
        fields = ["platform", "type", "starts_at_after", "ends_at_before"]


# ----------------------------------------------------------------------------- #
# Announcements (Read-only)                                                     #
# ----------------------------------------------------------------------------- #
class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoints for announcements.

    Security: authentication is required so the feed can be tailored per-user later.
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

    # ---- Swagger docs for list/retrieve -------------------------------------
    _param_platform = openapi.Parameter(
        name="platform", in_=openapi.IN_QUERY, type=openapi.TYPE_STRING,
        description="Filter by platform (case-insensitive exact), e.g. Coursera"
    )
    _param_type = openapi.Parameter(
        name="type", in_=openapi.IN_QUERY, type=openapi.TYPE_STRING,
        description="Filter by type (e.g. enrollment, discount)"
    )
    _param_starts_after = openapi.Parameter(
        name="starts_at_after", in_=openapi.IN_QUERY, type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE,
        description="Only items with starts_at ≥ this date (YYYY-MM-DD)"
    )
    _param_ends_before = openapi.Parameter(
        name="ends_at_before", in_=openapi.IN_QUERY, type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE,
        description="Only items with ends_at ≤ this date (YYYY-MM-DD)"
    )
    _param_search = openapi.Parameter(
        name="search", in_=openapi.IN_QUERY, type=openapi.TYPE_STRING,
        description="Free-text search across title, platform, tags"
    )
    _param_ordering = openapi.Parameter(
        name="ordering", in_=openapi.IN_QUERY, type=openapi.TYPE_STRING,
        description=(
            "Sort by any of: starts_at, -starts_at, created_at, -created_at, "
            "discount_pct, -discount_pct, price_current, -price_current. Default: -starts_at,-created_at."
        ),
    )

    if True:  # keep swagger decoration grouped here
        _resp_list_ok = openapi.Response("OK", AnnouncementSerializer(many=True))
        _resp_item_ok = openapi.Response("OK", AnnouncementSerializer())

        @swagger_auto_schema(
            tags=["Announcements"],
            operation_description=(
                "List announcements (auth required).\n\n"
                "Filtering:\n"
                "- `?platform=<name>` (case-insensitive exact)\n"
                "- `?type=<enrollment|discount|...>`\n"
                "- `?starts_at_after=YYYY-MM-DD`\n"
                "- `?ends_at_before=YYYY-MM-DD`\n\n"
                "Search & Ordering:\n"
                "- `?search=<text>` across title, platform, tags\n"
                "- `?ordering=<field>` e.g. `-starts_at` (see param help)\n\n"
                "Responses:\n"
                "- 200: OK (array of announcements)\n"
                "- 401: Unauthorized"
            ),
            manual_parameters=[_param_platform, _param_type, _param_starts_after, _param_ends_before, _param_search, _param_ordering],
            responses={200: _resp_list_ok, 401: "Unauthorized"},
        )
        def list(self, request, *args, **kwargs):
            return super().list(request, *args, **kwargs)

        @swagger_auto_schema(
            tags=["Announcements"],
            operation_description="Retrieve a single announcement by ID (auth required).",
            responses={200: _resp_item_ok, 401: "Unauthorized", 404: "Not Found"},
        )
        def retrieve(self, request, *args, **kwargs):
            return super().retrieve(request, *args, **kwargs)


# ----------------------------------------------------------------------------- #
# Random Fact (public)                                                          #
# ----------------------------------------------------------------------------- #
class RandomFactView(APIView):
    """
    Return exactly one random *active* fact.

    Keep it public so the home page can show a fact even for logged-out users.
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        tags=["Facts"],
        operation_description=(
            "Return a single random **active** fact.\n\n"
        ),
        responses={200: openapi.Response("OK", FactSerializer), 404: "Not Found"},
    )
    def get(self, request):
        qs = Fact.objects.filter(active=True)
        fact = qs.order_by("?").first()
        if not fact:
            return Response({"detail": "No active facts available."}, status=status.HTTP_404_NOT_FOUND)
        return Response(FactSerializer(fact).data)


# ----------------------------------------------------------------------------- #
# Platform search helper (public)                                               #
# ----------------------------------------------------------------------------- #
class PlatformSearchView(APIView):
    """
    GET /api/platforms/?q=machine learning
    Returns platform list with direct search links for the given query.

    Optional filters:
      ?cost=free|freemium|subscription|paid|mixed
      ?certs=yes|no

    Returns metadata so the UI can show badges (cost_model, offers_certificates, description).
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        tags=["Platforms"],
        operation_description=(
            "Return a list of learning platforms with direct search links for the given query.\n\n"
            "Query params:\n"
            "- `q`: search text to embed in platform search links\n"
            "- `cost`: filter by cost model (free|freemium|subscription|paid|mixed)\n"
            "- `certs`: filter by certificate availability (yes|no)\n\n"
            "Response includes name, category, description, cost_model, offers_certificates, home, search_url."
        ),
        manual_parameters=[
            openapi.Parameter("q", openapi.IN_QUERY, description="Search phrase to embed in platform search URLs", type=openapi.TYPE_STRING),
            openapi.Parameter("cost", openapi.IN_QUERY, description="Cost model filter", type=openapi.TYPE_STRING),
            openapi.Parameter("certs", openapi.IN_QUERY, description="Whether the platform offers certificates (yes|no)", type=openapi.TYPE_STRING),
        ],
        responses={200: "OK", 400:"Bad Request"},
    )
    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        cost = (request.query_params.get("cost") or "").strip().lower()       # free|freemium|subscription|paid|mixed
        certs = (request.query_params.get("certs") or "").strip().lower()     # yes|no

        out = []
        for p in PLATFORMS:
            # --- server-side filtering (optional) ---
            if cost and p.get("cost_model", "").lower() != cost:
                continue
            if certs in ("yes", "true", "1") and not p.get("offers_certificates", False):
                continue
            if certs in ("no", "false", "0") and p.get("offers_certificates", False):
                continue

            search_url = p["home"]
            if q:
                search_url = p["search"].format(q=quote_plus(q))

            out.append({
                "name": p["name"],
                "category": p.get("category", ""),
                "description": p.get("description", ""),
                "cost_model": p.get("cost_model", ""),
                "offers_certificates": bool(p.get("offers_certificates", False)),
                "home": p["home"],
                "search_url": search_url,
            })
        return Response({"query": q, "platforms": out})
