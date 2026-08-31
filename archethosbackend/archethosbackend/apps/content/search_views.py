"""Public search endpoint."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .search import DEFAULT_LIMIT, search_all
from .serializers import (
    PublicBlogPostSerializer,
    PublicProjectSerializer,
    PublicServiceSerializer,
)


class PublicSearchAPIView(APIView):
    """`GET /api/v1/public/search/?q=architecture`

    Grouped by type rather than interleaved: a studio site's three content types
    are not really comparable, and a combined ranking would keep burying services
    under longer blog posts.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    envelope_message = "Search completed"

    @extend_schema(
        tags=["public"],
        summary="Search published content",
        operation_id="public_search",
        parameters=[
            OpenApiParameter("q", str, required=True, description="Search terms."),
            OpenApiParameter(
                "limit", int, description=f"Results per type, default {DEFAULT_LIMIT}."
            ),
        ],
        responses={200: None},
        description=(
            "PostgreSQL full-text across projects, services and posts, with a "
            "trigram fallback for misspellings. Only live content is searched."
        ),
    )
    def get(self, request):
        query = request.query_params.get("q", "")
        results = search_all(query, request.query_params.get("limit"))

        return Response(
            {
                "query": query.strip(),
                "results": {
                    "projects": PublicProjectSerializer(
                        results["projects"], many=True
                    ).data,
                    "services": PublicServiceSerializer(
                        results["services"], many=True
                    ).data,
                    "blogs": PublicBlogPostSerializer(results["blogs"], many=True).data,
                },
                "counts": {key: len(value) for key, value in results.items()},
            }
        )
