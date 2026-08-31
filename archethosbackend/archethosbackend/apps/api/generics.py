"""
Base class-based views for the admin API.

ViewSets and routers are deliberately not used anywhere in this project
(DEVELOPMENT_PLAN.md §2.8). Every resource is expressed as explicit view classes
wired to explicit URLs.

A typical admin resource is two classes:

    class ProjectListCreateAPIView(AdminListCreateAPIView):
        queryset = Project.objects.all()
        list_serializer_class = ProjectListSerializer
        write_serializer_class = ProjectWriteSerializer

    class ProjectDetailAPIView(AdminRetrieveUpdateDestroyAPIView):
        queryset = Project.objects.all()
        detail_serializer_class = ProjectDetailSerializer
        write_serializer_class = ProjectWriteSerializer

Serializer dispatch is by HTTP method, since there is no `self.action` without a
ViewSet.
"""

from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import HasModelPermission, StrictDjangoModelPermissions

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class SerializerDispatchMixin:
    """Pick a serializer from the HTTP method.

    Falls back down the chain so a view only has to declare the ones that
    genuinely differ:

        list   -> list_serializer_class   -> serializer_class
        detail -> detail_serializer_class -> serializer_class
        write  -> write_serializer_class  -> serializer_class
    """

    serializer_class = None
    list_serializer_class = None
    detail_serializer_class = None
    write_serializer_class = None

    #: Set by the concrete view: "list" or "detail".
    read_mode = "detail"

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            if self.read_mode == "list":
                chosen = self.list_serializer_class
            else:
                chosen = self.detail_serializer_class
        else:
            chosen = self.write_serializer_class

        chosen = chosen or self.serializer_class
        assert chosen is not None, (
            f"{self.__class__.__name__} must define a serializer for "
            f"{self.request.method}."
        )
        return chosen


class AdminAPIViewMixin(SerializerDispatchMixin):
    """Authentication and model-permission enforcement for every admin view."""

    permission_classes = [IsAuthenticated, StrictDjangoModelPermissions]


class AdminListCreateAPIView(AdminAPIViewMixin, generics.ListCreateAPIView):
    """GET list (paginated, filtered, searched, ordered) + POST create."""

    read_mode = "list"


class AdminListAPIView(AdminAPIViewMixin, generics.ListAPIView):
    """GET list only, for resources that are never created through the API."""

    read_mode = "list"


class AdminRetrieveUpdateDestroyAPIView(
    AdminAPIViewMixin, generics.RetrieveUpdateDestroyAPIView
):
    """GET / PATCH / PUT / DELETE on a single object."""

    read_mode = "detail"


class AdminRetrieveUpdateAPIView(AdminAPIViewMixin, generics.RetrieveUpdateAPIView):
    """GET / PATCH / PUT, for resources that must never be deleted."""

    read_mode = "detail"


class AdminRetrieveAPIView(AdminAPIViewMixin, generics.RetrieveAPIView):
    read_mode = "detail"


class ReorderAPIView(APIView):
    """Atomic bulk reorder of an ordered child collection.

    Backs drag-and-drop in the admin. Reused by project galleries now and by
    every section-item collection in Phase 8, so the validation lives here once.

        PATCH { "items": [{"id": 10, "order": 1}, {"id": 12, "order": 2}] }

    `order` participates in no unique constraint (plan §2.3), so this is a plain
    bulk_update inside one transaction — no deferred-constraint juggling, and no
    intermediate state that could violate anything.
    """

    permission_classes = [IsAuthenticated, HasModelPermission]

    #: The ordered child model, e.g. ProjectGalleryItem.
    item_model = None
    #: The owning model, e.g. Project.
    parent_model = None
    #: Name of the FK on item_model pointing at the parent, e.g. "project".
    parent_field = None
    #: Payload key holding the list of {id, order} objects.
    payload_key = "items"

    envelope_message = "Order updated"

    def patch(self, request, pk):
        parent = generics.get_object_or_404(self.parent_model, pk=pk)

        entries = request.data.get(self.payload_key)
        error = self._validate_shape(entries)
        if error:
            return self._bad_request(error)

        ids = [entry["id"] for entry in entries]
        if len(ids) != len(set(ids)):
            return self._bad_request("The same item appears more than once.")

        owned = dict(
            self.item_model.objects.filter(
                **{self.parent_field: parent}, pk__in=ids
            ).in_bulk().items()
        )

        unknown = sorted(set(ids) - set(owned))
        if unknown:
            # Covers both "does not exist" and "belongs to a different parent";
            # the client should not be able to tell those apart.
            return self._bad_request(
                f"These items do not belong to this {self.parent_model._meta.verbose_name}: "
                + ", ".join(str(i) for i in unknown)
            )

        to_update = []
        for entry in entries:
            item = owned[entry["id"]]
            item.order = entry["order"]
            to_update.append(item)

        with transaction.atomic():
            self.item_model.objects.bulk_update(to_update, ["order"])

        return Response({"reordered": len(to_update)})

    def _validate_shape(self, entries):
        if not isinstance(entries, list) or not entries:
            return f"'{self.payload_key}' must be a non-empty list."
        for entry in entries:
            if not isinstance(entry, dict) or "id" not in entry or "order" not in entry:
                return f"Each entry in '{self.payload_key}' needs an 'id' and an 'order'."
            if not isinstance(entry["id"], int) or isinstance(entry["id"], bool):
                return "Each 'id' must be an integer."
            if not isinstance(entry["order"], int) or isinstance(entry["order"], bool):
                return "Each 'order' must be an integer."
            if entry["order"] < 0:
                return "'order' cannot be negative."
        return None

    @staticmethod
    def _bad_request(message):
        return Response(
            {
                "success": False,
                "message": message,
                "errors": {"items": [message]},
                "code": "invalid",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
