from django.db import connection
from django.http import JsonResponse
from drf_spectacular.utils import OpenApiExample, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(
    tags=["meta"],
    summary="Liveness probe",
    responses={
        200: inline_serializer(
            name="Health",
            fields={
                "status": serializers.CharField(),
                "database": serializers.CharField(),
            },
        )
    },
    examples=[
        OpenApiExample("healthy", value={"status": "ok", "database": "ok"}),
    ],
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    """Confirm the process is up and the database answers."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database = "ok"
    except Exception:
        database = "unavailable"

    payload = {"status": "ok" if database == "ok" else "degraded", "database": database}
    code = status.HTTP_200_OK if database == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(payload, status=code)


# ─── Fallback handlers ───────────────────────────────────────────────────────
# URL-resolution and server errors happen outside DRF, so they would otherwise
# return Django's HTML error pages. Under /api/ the client is always the Next.js
# frontend, which needs the same JSON envelope as every other response.


def _is_api(request):
    return request.path.startswith("/api/")


def api_not_found(request, exception=None):
    if not _is_api(request):
        from django.views.defaults import page_not_found

        return page_not_found(request, exception)
    return JsonResponse(
        {
            "success": False,
            "message": "Not found",
            "errors": {},
            "code": "not_found",
        },
        status=404,
    )


def api_server_error(request):
    if not _is_api(request):
        from django.views.defaults import server_error

        return server_error(request)
    return JsonResponse(
        {
            "success": False,
            "message": "Internal server error",
            "errors": {},
            "code": "server_error",
        },
        status=500,
    )
