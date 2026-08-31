"""
The aggregate page API — the endpoint the whole architecture exists to serve.

    GET /api/v1/public/pages/home/

One request returns everything needed to render a page: its SEO block and every
visible section, in order, each carrying the `type` the frontend registry maps to
a component and the `key` that says what it is for on this page.

Never paginated: a partial page is not a page.
"""

import hashlib

from django.utils.http import http_date
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from archethosbackend.apps.api.serializers import PublicSEOSerializer

from .models import Company
from .selectors import get_live_page, last_modified, resolve_page
from .serializers import PublicCompanySerializer

#: Long enough that a burst of traffic hits the cache, short enough that an edit
#: appears quickly. `stale-while-revalidate` lets Next.js serve instantly while
#: refreshing in the background.
CACHE_CONTROL = "public, max-age=60, stale-while-revalidate=300"


class PageAggregateAPIView(APIView):
    """Everything needed to render one page, in one request."""

    authentication_classes = []
    permission_classes = [AllowAny]
    envelope_message = "Page retrieved successfully"

    @extend_schema(
        tags=["public"],
        summary="Render a page",
        operation_id="public_page_aggregate",
        responses={200: None},
        description=(
            "Returns the page's SEO block and its visible sections in order. Each "
            "section carries `type` (which component renders it) and `key` (what "
            "it is for on this page). Unpublished pages return 404."
        ),
    )
    def get(self, request, slug):
        page = get_live_page(slug)
        if page is None:
            return Response(
                {
                    "success": False,
                    "message": "Page not found.",
                    "errors": {},
                    "code": "not_found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        resolved, placements, concrete = resolve_page(page)
        modified = last_modified(page, placements, concrete)
        etag = _etag(page.slug, modified)

        # Nothing changed since the client's copy — save the bandwidth.
        if request.headers.get("If-None-Match") == etag:
            response = Response(status=status.HTTP_304_NOT_MODIFIED)
            response["ETag"] = etag
            response["Cache-Control"] = CACHE_CONTROL
            return response

        payload = {
            "id": page.id,
            "name": page.name,
            "slug": page.slug,
            "seo": PublicSEOSerializer(page).data,
            "sections": [
                {
                    "id": section.placement_id,
                    "key": section.section_key,
                    "type": section.section_type,
                    "data": section.data,
                }
                for section in resolved.sections
            ],
        }

        response = Response(payload)
        response["ETag"] = etag
        response["Last-Modified"] = http_date(modified.timestamp())
        response["Cache-Control"] = CACHE_CONTROL
        return response


class PublicCompanyAPIView(APIView):
    """Site-wide settings: logo, nav, contacts, injected code, default SEO."""

    authentication_classes = []
    permission_classes = [AllowAny]
    envelope_message = "Company retrieved successfully"

    @extend_schema(
        tags=["public"],
        summary="Site-wide settings",
        operation_id="public_company",
        responses={200: PublicCompanySerializer},
    )
    def get(self, request):
        company = Company.load()
        response = Response(PublicCompanySerializer(company).data)
        response["ETag"] = _etag("company", company.updated_at)
        response["Cache-Control"] = CACHE_CONTROL
        return response


def _etag(key, modified):
    digest = hashlib.sha256(f"{key}:{modified.isoformat()}".encode()).hexdigest()[:32]
    return f'"{digest}"'
