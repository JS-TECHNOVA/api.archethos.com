"""
Media Library API.

Class-based views only (DEVELOPMENT_PLAN.md §2.8). Upload and YouTube creation
are separate view classes rather than modes of one endpoint, because they take
different payloads (multipart vs JSON) and have nothing in common but the table
they write to.
"""

import django_filters
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from archethosbackend.apps.api.generics import (
    AdminListAPIView,
    AdminRetrieveUpdateDestroyAPIView,
)
from archethosbackend.apps.api.permissions import HasModelPermission

from .models import MediaAsset
from .serializers import (
    MediaAssetDetailSerializer,
    MediaAssetListSerializer,
    MediaAssetUpdateSerializer,
    MediaUploadSerializer,
    YouTubeCreateSerializer,
)


class MediaFilterSet(django_filters.FilterSet):
    created_after = django_filters.DateFilter(
        field_name="created_at", lookup_expr="date__gte"
    )
    created_before = django_filters.DateFilter(
        field_name="created_at", lookup_expr="date__lte"
    )

    class Meta:
        model = MediaAsset
        fields = ["media_type", "source_type", "mime_type"]


class MediaListAPIView(AdminListAPIView):
    """Browse and search the library — this backs the reusable Media Picker.

    Creation goes through the upload and youtube endpoints, so this is list-only.
    """

    queryset = MediaAsset.objects.select_related("uploaded_by")
    list_serializer_class = MediaAssetListSerializer
    filterset_class = MediaFilterSet
    search_fields = ["title", "alt_text", "file_name"]
    ordering_fields = ["created_at", "file_size", "title", "media_type"]

    @extend_schema(
        tags=["admin:media"],
        summary="Browse the media library",
        parameters=[
            OpenApiParameter("media_type", str, description="IMAGE, VIDEO or DOCUMENT"),
            OpenApiParameter("source_type", str, description="UPLOAD or YOUTUBE"),
            OpenApiParameter("search", str, description="Matches title, alt text, filename"),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MediaDetailAPIView(AdminRetrieveUpdateDestroyAPIView):
    queryset = MediaAsset.objects.select_related("uploaded_by")
    detail_serializer_class = MediaAssetDetailSerializer
    write_serializer_class = MediaAssetUpdateSerializer

    @extend_schema(tags=["admin:media"], summary="Retrieve a media asset")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["admin:media"],
        summary="Update title or alt text",
        description="Only descriptive fields are editable; the file itself is immutable.",
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        tags=["admin:media"],
        summary="Delete a media asset",
        description=(
            "Returns 409 with the list of referencing objects if the asset is "
            "still in use anywhere."
        ),
    )
    def delete(self, request, *args, **kwargs):
        # ProtectedError is translated to a 409 naming the referents by the
        # envelope exception handler, so no special handling is needed here.
        return super().delete(request, *args, **kwargs)


class MediaUploadAPIView(APIView):
    permission_classes = [IsAuthenticated, HasModelPermission]
    required_permissions = ["media_library.add_mediaasset"]
    parser_classes = [MultiPartParser, FormParser]
    envelope_message = "Media uploaded successfully"

    @extend_schema(
        tags=["admin:media"],
        summary="Upload a file",
        request={"multipart/form-data": MediaUploadSerializer},
        responses={201: MediaAssetDetailSerializer},
    )
    def post(self, request):
        serializer = MediaUploadSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        asset = serializer.save()
        return Response(
            MediaAssetDetailSerializer(asset, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MediaYouTubeAPIView(APIView):
    permission_classes = [IsAuthenticated, HasModelPermission]
    required_permissions = ["media_library.add_mediaasset"]
    envelope_message = "YouTube video added successfully"

    @extend_schema(
        tags=["admin:media"],
        summary="Add a YouTube video",
        request=YouTubeCreateSerializer,
        responses={201: MediaAssetDetailSerializer},
        description=(
            "Accepts watch, youtu.be, embed, shorts and live URLs. The canonical "
            "video id is extracted and stored so the frontend never parses URLs."
        ),
    )
    def post(self, request):
        serializer = YouTubeCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        asset = serializer.save()
        return Response(
            MediaAssetDetailSerializer(asset, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MediaUsageAPIView(APIView):
    """Where an asset is referenced.

    The admin UI calls this before offering a delete, so the user sees what would
    break instead of hitting a 409 they cannot interpret.
    """

    permission_classes = [IsAuthenticated, HasModelPermission]
    required_permissions = ["media_library.view_mediaasset"]
    envelope_message = "Usage retrieved successfully"

    @extend_schema(
        tags=["admin:media"],
        summary="List objects referencing this asset",
        responses={200: None},
    )
    def get(self, request, pk):
        asset = get_object_or_404(MediaAsset, pk=pk)
        usage = asset.usage()
        return Response({"count": len(usage), "used_by": usage})


class MediaDuplicateCheckAPIView(APIView):
    """Look up an existing asset by checksum before uploading.

    Lets the frontend offer "you already uploaded this" instead of silently
    creating a second copy of the same bytes.
    """

    permission_classes = [IsAuthenticated, HasModelPermission]
    required_permissions = ["media_library.view_mediaasset"]
    envelope_message = "Checksum lookup complete"

    @extend_schema(
        tags=["admin:media"],
        summary="Find an asset by sha256 checksum",
        parameters=[OpenApiParameter("checksum", str, required=True)],
        responses={200: MediaAssetDetailSerializer},
    )
    def get(self, request):
        checksum = (request.query_params.get("checksum") or "").strip().lower()
        if len(checksum) != 64:
            return Response(
                {
                    "success": False,
                    "message": "A 64-character sha256 checksum is required.",
                    "errors": {"checksum": ["Must be a 64-character sha256 hex digest."]},
                    "code": "invalid",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        asset = MediaAsset.objects.filter(checksum=checksum).first()
        return Response(
            {
                "exists": asset is not None,
                "asset": MediaAssetDetailSerializer(
                    asset, context={"request": request}
                ).data
                if asset
                else None,
            }
        )
