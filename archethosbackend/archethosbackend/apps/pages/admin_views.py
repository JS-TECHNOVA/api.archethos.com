"""
Admin routes for pages and site settings.

One endpoint per page, addressed by its public route:

    GET   /api/v1/admin/pages/home/     the whole page, every section
    PATCH /api/v1/admin/pages/home/     write back whatever changed

There is no create and no delete. The site has ten pages, they are declared in
code, and `ensure_pages` makes the rows — so a page cannot be added or removed
through the API any more than a database table can.
"""

from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from archethosbackend.apps.api.generics import AdminRetrieveUpdateAPIView
from archethosbackend.apps.api.permissions import HasModelPermission

from .models import ORDERED_PAGES, Company
from .selectors import load_page
from .serializers.company import CompanySerializer, CompanyWriteSerializer
from .serializers.pages import PAGE_SERIALIZERS

# Every route in ORDERED_PAGES must have a serializer, or a page would 404 with
# no clue why. Checked at import so it fails on boot rather than in a request.
assert set(ORDERED_PAGES) == set(PAGE_SERIALIZERS), (
    "ORDERED_PAGES and PAGE_SERIALIZERS disagree: "
    f"{set(ORDERED_PAGES) ^ set(PAGE_SERIALIZERS)}"
)


class PageListAPIView(APIView):
    """The admin's Pages menu (§14).

    Returns the ten pages in navigation order with just enough to render the
    list: route, name, whether it is live and what is stopping it.
    """

    permission_classes = [IsAuthenticated]
    envelope_message = "Pages retrieved"

    @extend_schema(tags=["admin:pages"], summary="List the site's pages", responses={200: None})
    def get(self, request):
        rows = []
        for route, model in ORDERED_PAGES.items():
            if not request.user.has_perm(
                f"{model._meta.app_label}.view_{model._meta.model_name}"
            ):
                continue

            page = model.objects.first()
            rows.append(
                {
                    "route": route,
                    "name": model._meta.verbose_name,
                    "sections": list(model.required_sections),
                    "is_published": bool(page and page.is_published),
                    "missing_sections": page.missing_sections() if page else None,
                    "updated_at": page.updated_at if page else None,
                }
            )
        return Response(rows)


class PageDetailAPIView(APIView):
    """Read or write one page, sections and all.

    A PATCH is one transaction: either every section in the payload is written
    or none is, so a half-saved page is not a state the site can be left in.
    """

    permission_classes = [IsAuthenticated, HasModelPermission]
    envelope_message = "Page retrieved"

    def _resolve(self, route):
        model = ORDERED_PAGES.get(route)
        if model is None:
            return None, None
        return model, PAGE_SERIALIZERS[route]

    def get_queryset(self):
        """`HasModelPermission` reads the model off the queryset."""
        model, _ = self._resolve(self.kwargs.get("route", ""))
        return model.objects.all() if model else None

    @extend_schema(
        tags=["admin:pages"],
        summary="Retrieve a page with all of its sections",
        responses={200: None},
    )
    def get(self, request, route):
        model, serializer_class = self._resolve(route)
        if model is None:
            return self._unknown_route(route)

        page = load_page(model)
        return Response(serializer_class(page, context={"request": request}).data)

    @extend_schema(
        tags=["admin:pages"],
        summary="Update a page and any of its sections",
        description=(
            "Partial. Omitted sections are untouched; an omitted item collection "
            "is left alone, while an empty list clears it. Item order is the "
            "array order."
        ),
        responses={200: None},
    )
    def patch(self, request, route):
        model, serializer_class = self._resolve(route)
        if model is None:
            return self._unknown_route(route)

        page = load_page(model)
        serializer = serializer_class(
            page, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.envelope_message = "Page updated"
        return Response(serializer_class(load_page(model), context={"request": request}).data)

    @staticmethod
    def _unknown_route(route):
        return Response(
            {
                "success": False,
                "message": (
                    f"No page at '{route}'. The site has: "
                    f"{', '.join(ORDERED_PAGES)}."
                ),
                "errors": {},
                "code": "not_found",
            },
            status=status.HTTP_404_NOT_FOUND,
        )


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
