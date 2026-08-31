"""
Section admin API.

Every view here is generic over the registry: the URL segment names the type, the
registry supplies the model, serializers and prefetches. Adding a section type
adds no code in this file.

Class-based views only (plan §2.8).
"""

from django.db import transaction
from django.db.models import Count
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from archethosbackend.apps.api.generics import AdminListAPIView, SerializerDispatchMixin
from archethosbackend.apps.api.permissions import HasModelPermission

from .models import Section
from .registry import SECTION_REGISTRY, spec_for_segment
from .serializers import SectionBrowseSerializer


def _perm(model, action):
    return f"{model._meta.app_label}.{action}_{model._meta.model_name}"


class SectionTypeMixin:
    """Resolves the registry entry from the `<segment>` URL kwarg.

    Permissions come from the concrete section model, so a group can be granted
    "may edit FAQ sections" without also gaining hero sections.
    """

    permission_classes = [IsAuthenticated, HasModelPermission]

    @property
    def spec(self):
        segment = self.kwargs.get("segment")
        spec = spec_for_segment(segment)
        if spec is None:
            from rest_framework.exceptions import NotFound

            raise NotFound(f"Unknown section type '{segment}'.")
        return spec

    def get_required_permissions(self):
        model = self.spec.model
        action = {
            "GET": "view", "HEAD": "view", "OPTIONS": "view",
            "POST": "add", "PUT": "change", "PATCH": "change", "DELETE": "delete",
        }[self.request.method]
        return [_perm(model, action)]

    @property
    def required_permissions(self):
        if getattr(self, "swagger_fake_view", False):
            return []
        return self.get_required_permissions()


# ─── Browse every section, whatever its type ─────────────────────────────────


class SectionBrowseAPIView(AdminListAPIView):
    """`GET /admin/sections/` — the picker for page composition.

    Reads the parent table only, so listing every section of every type costs one
    query regardless of how many types exist.
    """

    ordering = ["-created_at", "-id"]
    queryset = Section.objects.annotate(used_by_count=Count("page_usages"))
    list_serializer_class = SectionBrowseSerializer
    filterset_fields = ["section_type"]
    search_fields = ["internal_label"]
    ordering_fields = ["created_at", "internal_label", "section_type"]

    @extend_schema(
        tags=["admin:sections"],
        operation_id="admin_sections_browse",
        summary="Browse all sections",
        parameters=[
            OpenApiParameter(
                "section_type",
                str,
                description="Filter by type: " + ", ".join(SECTION_REGISTRY),
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SectionTypeCatalogueAPIView(APIView):
    """The registry, as data.

    Lets the admin UI build its "add a section" menu from the backend instead of
    keeping a hardcoded list that drifts.
    """

    permission_classes = [IsAuthenticated]
    envelope_message = "Section types retrieved successfully"

    @extend_schema(
        tags=["admin:sections"], summary="List available section types",
        responses={200: None},
    )
    def get(self, request):
        return Response(
            [
                {
                    "section_type": key,
                    "label": spec.model._meta.verbose_name.title(),
                    "url_segment": spec.url_segment,
                    "has_items": spec.items is not None,
                }
                for key, spec in SECTION_REGISTRY.items()
            ]
        )


# ─── Per-type CRUD ───────────────────────────────────────────────────────────


class SectionListCreateAPIView(
    SectionTypeMixin, SerializerDispatchMixin, generics.ListCreateAPIView
):
    read_mode = "list"
    ordering = ["-created_at", "-id"]
    search_fields = ["internal_label"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Section.objects.none()
        spec = self.spec
        queryset = spec.model.objects.all()
        for alias, relation in spec.list_annotations.items():
            queryset = queryset.annotate(**{alias: Count(relation, distinct=True)})
        return queryset

    def get_serializer_class(self):
        if getattr(self, "swagger_fake_view", False):
            return SectionBrowseSerializer
        return (
            self.spec.list_serializer
            if self.request.method in ("GET", "HEAD", "OPTIONS")
            else self.spec.write_serializer
        )

    @extend_schema(
        tags=["admin:sections"],
        operation_id="admin_sections_list_by_type",
        summary="List sections of one type",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:sections"], summary="Create a section")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class SectionDetailAPIView(
    SectionTypeMixin, SerializerDispatchMixin, generics.RetrieveUpdateDestroyAPIView
):
    read_mode = "detail"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Section.objects.none()
        spec = self.spec
        return spec.admin_queryset(spec.model.objects.all())

    def get_serializer_class(self):
        if getattr(self, "swagger_fake_view", False):
            return SectionBrowseSerializer
        return (
            self.spec.detail_serializer
            if self.request.method in ("GET", "HEAD", "OPTIONS")
            else self.spec.write_serializer
        )

    @extend_schema(tags=["admin:sections"], summary="Retrieve a section with its items")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:sections"], summary="Update a section")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        tags=["admin:sections"],
        summary="Delete a section",
        description=(
            "Deletes the section and its item rows only. Master content it "
            "references is PROTECTed and survives. A section still attached to a "
            "page can be deleted, which blanks that slot - call the usage "
            "endpoint first."
        ),
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class SectionUsageAPIView(SectionTypeMixin, APIView):
    """Which pages compose this section, before you delete or edit it."""

    envelope_message = "Usage retrieved successfully"

    def get_required_permissions(self):
        return [_perm(self.spec.model, "view")]

    @extend_schema(
        tags=["admin:sections"],
        summary="List pages using this section",
        responses={200: None},
    )
    def get(self, request, segment, pk):
        section = generics.get_object_or_404(self.spec.model, pk=pk)
        usage = section.used_by_pages
        return Response({"count": len(usage), "used_by": usage})


# ─── Section items ───────────────────────────────────────────────────────────


class SectionItemMixin(SectionTypeMixin):
    """Item permissions derive from the parent section.

    Editing an FAQSectionItem checks `sections.change_faqsection`. Per-item
    permission rows would triple the group picker's size without expressing
    anything an administrator would think to grant separately.
    """

    def get_required_permissions(self):
        model = self.spec.model
        action = "view" if self.request.method in ("GET", "HEAD", "OPTIONS") else "change"
        return [_perm(model, action)]

    def get_item_spec(self):
        spec = self.spec
        if spec.items is None:
            from rest_framework.exceptions import NotFound

            raise NotFound(f"'{spec.url_segment}' sections have no items.")
        return spec.items

    def get_section(self):
        return generics.get_object_or_404(self.spec.model, pk=self.kwargs["pk"])


class SectionItemListCreateAPIView(
    SectionItemMixin, SerializerDispatchMixin, generics.ListCreateAPIView
):
    read_mode = "list"
    #: A section's items are a short, always-complete list; paginating them would
    #: break drag-and-drop ordering in the UI.
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Section.objects.none()
        item_spec = self.get_item_spec()
        return item_spec.model.objects.filter(section=self.get_section())

    def get_serializer_class(self):
        if getattr(self, "swagger_fake_view", False):
            return SectionBrowseSerializer
        item_spec = self.get_item_spec()
        return (
            item_spec.serializer
            if self.request.method in ("GET", "HEAD", "OPTIONS")
            else item_spec.write_serializer
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if not getattr(self, "swagger_fake_view", False):
            context["section"] = self.get_section()
        return context

    @extend_schema(tags=["admin:sections"], summary="List a section's items")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:sections"], summary="Add an item to a section")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class SectionItemDetailAPIView(
    SectionItemMixin, SerializerDispatchMixin, generics.RetrieveUpdateDestroyAPIView
):
    read_mode = "detail"
    lookup_url_kwarg = "item_id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Section.objects.none()
        return self.get_item_spec().model.objects.filter(section=self.get_section())

    def get_serializer_class(self):
        if getattr(self, "swagger_fake_view", False):
            return SectionBrowseSerializer
        item_spec = self.get_item_spec()
        return (
            item_spec.serializer
            if self.request.method in ("GET", "HEAD", "OPTIONS")
            else item_spec.write_serializer
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if not getattr(self, "swagger_fake_view", False):
            context["section"] = self.get_section()
        return context

    @extend_schema(tags=["admin:sections"], summary="Update a section item")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        tags=["admin:sections"],
        summary="Remove an item from a section",
        description="Removes the placement only; the master content is untouched.",
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class SectionItemReorderAPIView(SectionItemMixin, APIView):
    """Atomic drag-and-drop reorder, generic over every section type.

    `order` participates in no unique constraint (plan §2.3), so this is a plain
    bulk_update in one transaction with no intermediate state to violate.
    """

    envelope_message = "Order updated"

    def get_required_permissions(self):
        return [_perm(self.spec.model, "change")]

    @extend_schema(
        tags=["admin:sections"],
        summary="Reorder a section's items",
        request=None,
        responses={200: None},
        description='Atomic. Body: {"items": [{"id": 10, "order": 1}, ...]}',
    )
    def patch(self, request, segment, pk):
        item_spec = self.get_item_spec()
        section = self.get_section()

        entries = request.data.get("items")
        error = _validate_reorder(entries)
        if error:
            return _bad_request(error)

        ids = [entry["id"] for entry in entries]
        if len(ids) != len(set(ids)):
            return _bad_request("The same item appears more than once.")

        owned = item_spec.model.objects.filter(section=section, pk__in=ids).in_bulk()
        unknown = sorted(set(ids) - set(owned))
        if unknown:
            # Covers both "does not exist" and "belongs to another section"; the
            # client should not be able to tell those apart.
            return _bad_request(
                "These items do not belong to this section: "
                + ", ".join(str(i) for i in unknown)
            )

        to_update = []
        for entry in entries:
            item = owned[entry["id"]]
            item.order = entry["order"]
            to_update.append(item)

        with transaction.atomic():
            item_spec.model.objects.bulk_update(to_update, ["order"])

        return Response({"reordered": len(to_update)})


def _validate_reorder(entries):
    if not isinstance(entries, list) or not entries:
        return "'items' must be a non-empty list."
    for entry in entries:
        if not isinstance(entry, dict) or "id" not in entry or "order" not in entry:
            return "Each entry in 'items' needs an 'id' and an 'order'."
        for key in ("id", "order"):
            if not isinstance(entry[key], int) or isinstance(entry[key], bool):
                return f"Each '{key}' must be an integer."
        if entry["order"] < 0:
            return "'order' cannot be negative."
    return None


def _bad_request(message):
    return Response(
        {"success": False, "message": message, "errors": {"items": [message]},
         "code": "invalid"},
        status=status.HTTP_400_BAD_REQUEST,
    )
