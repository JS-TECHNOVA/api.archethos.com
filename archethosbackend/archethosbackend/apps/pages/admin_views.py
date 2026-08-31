"""
Page composition admin API.

Class-based views only (plan §2.8). Attaching, detaching and reordering sections
are separate view classes rather than router actions.
"""

from django.db import transaction
from django.db.models import Count, Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from archethosbackend.apps.api.generics import (
    AdminListCreateAPIView,
    AdminRetrieveUpdateDestroyAPIView,
    AdminRetrieveUpdateAPIView,
)
from archethosbackend.apps.api.permissions import HasModelPermission

from .models import Company, Page, PageSection
from .serializers import (
    CompanySerializer,
    CompanyWriteSerializer,
    PageDetailSerializer,
    PageListSerializer,
    PageSectionSerializer,
    PageSectionWriteSerializer,
    PageWriteSerializer,
)


# ─── Pages ───────────────────────────────────────────────────────────────────


class PageListCreateAPIView(AdminListCreateAPIView):
    ordering = ["name", "id"]
    queryset = Page.objects.annotate(
        sections_count=Count("page_sections", distinct=True)
    )
    list_serializer_class = PageListSerializer
    write_serializer_class = PageWriteSerializer
    filterset_fields = ["status"]
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "slug", "status", "updated_at"]

    @extend_schema(tags=["admin:pages"], summary="List pages")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:pages"], summary="Create a page")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class PageDetailAPIView(AdminRetrieveUpdateDestroyAPIView):
    queryset = Page.objects.select_related("og_image").prefetch_related(
        Prefetch(
            "page_sections",
            queryset=PageSection.objects.select_related("section"),
        )
    )
    detail_serializer_class = PageDetailSerializer
    write_serializer_class = PageWriteSerializer

    @extend_schema(
        tags=["admin:pages"],
        summary="Retrieve a page with its composition",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:pages"], summary="Update a page")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        tags=["admin:pages"],
        summary="Delete a page",
        description=(
            "Deletes the page and its composition rows. The sections themselves "
            "are PROTECTed and survive, since they may be used by other pages."
        ),
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# ─── Composition ─────────────────────────────────────────────────────────────


class PageCompositionMixin:
    """Permissions derive from Page.

    "May edit pages" is the real mental model; a separate add/change/delete
    triple for PageSection would clutter the group picker without expressing
    anything an administrator would think to grant on its own.
    """

    permission_classes = [IsAuthenticated, HasModelPermission]
    queryset = PageSection.objects.none()  # lets spectacular introspect the model

    def get_page(self):
        return generics.get_object_or_404(Page, pk=self.kwargs["pk"])


class PageSectionListCreateAPIView(PageCompositionMixin, AdminListCreateAPIView):
    required_permissions = ["pages.change_page"]
    list_serializer_class = PageSectionSerializer
    write_serializer_class = PageSectionWriteSerializer
    #: A page's composition is short and always shown whole; paginating it would
    #: break drag-and-drop ordering in the admin.
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PageSection.objects.none()
        return PageSection.objects.filter(page=self.get_page()).select_related("section")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if not getattr(self, "swagger_fake_view", False):
            context["page"] = self.get_page()
        return context

    @extend_schema(tags=["admin:pages"], summary="List a page's sections")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["admin:pages"],
        summary="Attach a section to a page",
        description=(
            "Creates a placement. The same section may be attached to several "
            "pages, and the same section type may appear twice on one page under "
            "different section keys."
        ),
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class PageSectionDetailAPIView(
    PageCompositionMixin, AdminRetrieveUpdateDestroyAPIView
):
    required_permissions = ["pages.change_page"]
    detail_serializer_class = PageSectionSerializer
    write_serializer_class = PageSectionWriteSerializer
    lookup_url_kwarg = "page_section_id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PageSection.objects.none()
        return PageSection.objects.filter(page=self.get_page()).select_related("section")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if not getattr(self, "swagger_fake_view", False):
            context["page"] = self.get_page()
        return context

    @extend_schema(
        tags=["admin:pages"], summary="Update a placement (key, order, visibility)"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        tags=["admin:pages"],
        summary="Detach a section from a page",
        description=(
            "Removes the placement only. The section itself is untouched and "
            "stays available to other pages."
        ),
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class PageSectionReorderAPIView(APIView):
    """Atomic drag-and-drop reorder of a page's composition."""

    permission_classes = [IsAuthenticated, HasModelPermission]
    required_permissions = ["pages.change_page"]
    envelope_message = "Order updated"

    @extend_schema(
        tags=["admin:pages"],
        summary="Reorder a page's sections",
        request=None,
        responses={200: None},
        description='Atomic. Body: {"sections": [{"id": 1, "order": 1}, ...]}',
    )
    def patch(self, request, pk):
        page = generics.get_object_or_404(Page, pk=pk)

        entries = request.data.get("sections")
        error = _validate_reorder(entries)
        if error:
            return _bad_request(error)

        ids = [entry["id"] for entry in entries]
        if len(ids) != len(set(ids)):
            return _bad_request("The same placement appears more than once.")

        owned = PageSection.objects.filter(page=page, pk__in=ids).in_bulk()
        unknown = sorted(set(ids) - set(owned))
        if unknown:
            return _bad_request(
                "These placements do not belong to this page: "
                + ", ".join(str(i) for i in unknown)
            )

        to_update = []
        for entry in entries:
            placement = owned[entry["id"]]
            placement.order = entry["order"]
            to_update.append(placement)

        with transaction.atomic():
            PageSection.objects.bulk_update(to_update, ["order"])

        return Response({"reordered": len(to_update)})


def _validate_reorder(entries):
    if not isinstance(entries, list) or not entries:
        return "'sections' must be a non-empty list."
    for entry in entries:
        if not isinstance(entry, dict) or "id" not in entry or "order" not in entry:
            return "Each entry in 'sections' needs an 'id' and an 'order'."
        for key in ("id", "order"):
            if not isinstance(entry[key], int) or isinstance(entry[key], bool):
                return f"Each '{key}' must be an integer."
        if entry["order"] < 0:
            return "'order' cannot be negative."
    return None


def _bad_request(message):
    return Response(
        {"success": False, "message": message,
         "errors": {"sections": [message]}, "code": "invalid"},
        status=status.HTTP_400_BAD_REQUEST,
    )


# ─── Company ─────────────────────────────────────────────────────────────────


class CompanyAPIView(AdminRetrieveUpdateAPIView):
    """Singleton: there is no id in the URL and no list endpoint."""

    queryset = Company.objects.select_related("logo", "favicon")
    detail_serializer_class = CompanySerializer
    write_serializer_class = CompanyWriteSerializer

    def get_object(self):
        obj = Company.load()
        self.check_object_permissions(self.request, obj)
        return obj

    @extend_schema(tags=["admin:company"], summary="Retrieve site settings")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["admin:company"],
        summary="Update site settings",
        description=(
            "head_inject and body_inject are superuser-only: they render on every "
            "page of the live site."
        ),
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
