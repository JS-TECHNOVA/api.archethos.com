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

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .permissions import StrictDjangoModelPermissions

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
