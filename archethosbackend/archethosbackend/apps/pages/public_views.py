"""
Public page delivery.

    GET /api/v1/public/pages/home/

One request returns everything the route renders, in the shape the frontend
consumes directly (§13) — sections as named keys, master data inlined, no
join rows and no admin bookkeeping.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from archethosbackend.apps.api.fields import MediaDetailField, MediaReferenceField
from rest_framework import serializers

from .models import ORDERED_PAGES, Company
from .selectors import load_page
from .serializers.company import PublicCompanySerializer
from .serializers.pages import PAGE_SERIALIZERS


class PublicPageAPIView(APIView):
    """An unpublished page is a 404, not an empty one.

    A draft page must be indistinguishable from a page that does not exist —
    otherwise the API leaks that something is being worked on, and the frontend
    renders a half-built route.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    envelope_message = "Page retrieved"

    @extend_schema(
        tags=["public"],
        summary="Retrieve a page",
        description=(
            "Routes: " + ", ".join(ORDERED_PAGES) + ". "
            "Returns 404 while a page is unpublished."
        ),
        responses={200: None},
    )
    def get(self, request, route):
        model = ORDERED_PAGES.get(route)
        if model is None:
            return self._not_found()

        page = model.objects.filter(
            pk=model.SINGLETON_PK, is_published=True
        ).exists()
        if not page:
            return self._not_found()

        serializer_class = PAGE_SERIALIZERS[route]
        data = serializer_class(
            load_page(model), context={"request": request, "public": True}
        ).data
        return Response(data)

    @staticmethod
    def _not_found():
        return Response(
            {
                "success": False,
                "message": "Page not found.",
                "errors": {},
                "code": "not_found",
            },
            status=status.HTTP_404_NOT_FOUND,
        )


class PublicPageIndexAPIView(APIView):
    """Which routes are live — what a sitemap or a static build asks for."""

    authentication_classes = []
    permission_classes = [AllowAny]
    envelope_message = "Routes retrieved"

    @extend_schema(tags=["public"], summary="List published routes", responses={200: None})
    def get(self, request):
        published = []
        for route, model in ORDERED_PAGES.items():
            page = model.objects.filter(
                pk=model.SINGLETON_PK, is_published=True
            ).values("updated_at").first()
            if page:
                published.append({"route": route, "updated_at": page["updated_at"]})
        return Response(published)


class PublicCompanyAPIView(APIView):
    """Header, footer and contact details — every page needs them."""

    authentication_classes = []
    permission_classes = [AllowAny]
    envelope_message = "Company settings retrieved"

    @extend_schema(tags=["public"], summary="Retrieve site settings", responses={200: None})
    def get(self, request):
        company = Company.load()
        return Response(PublicCompanySerializer(company, context={"request": request}).data)
