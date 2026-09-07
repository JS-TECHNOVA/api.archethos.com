"""
Admin routes for pages and site settings.

One model, one view, one URL — written out:

    HomePage   -> HomePageAPIView   -> /api/v1/admin/pages/home/
    AboutPage  -> AboutPageAPIView  -> /api/v1/admin/pages/about/

Each view names its own model and its own serializer. Nothing looks a page up by
string at request time: `/api/v1/admin/pages/shop/` is a 404 from Django's URL
resolver, not a lookup that missed, and the ten endpoints are visible in the
route table rather than hidden behind one dynamic segment.

There is no create and no delete. The site has ten pages, they are declared in
code, and `ensure_pages` makes the rows — so a page cannot be added or removed
through the API any more than a database table can.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from archethosbackend.apps.api.generics import AdminRetrieveUpdateAPIView
from archethosbackend.apps.api.permissions import HasModelPermission

from .models import (
    ORDERED_PAGES,
    AboutPage,
    Company,
    ContactPage,
    GalleryPage,
    HomePage,
    JournalPage,
    LocationsPage,
    PrivacyPage,
    ProjectsPage,
    ServicesPage,
    TermsPage,
)
from .selectors import load_page
from .serializers.company import CompanySerializer, CompanyWriteSerializer
from .serializers.pages import (
    AboutPageSerializer,
    ContactPageSerializer,
    GalleryPageSerializer,
    HomePageSerializer,
    JournalPageSerializer,
    LocationsPageSerializer,
    PrivacyPageSerializer,
    ProjectsPageSerializer,
    ServicesPageSerializer,
    TermsPageSerializer,
)


class PageListAPIView(APIView):
    """The admin's Pages menu.

    The one place that enumerates the site. Not a dispatch table — nothing is
    resolved through it — just the inventory the menu renders, with enough state
    to show what is live and what is blocked.
    """

    permission_classes = [IsAuthenticated]
    envelope_message = "Pages retrieved"

    @extend_schema(
        tags=["admin:pages"], summary="List the site's pages", responses={200: None}
    )
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


class PageAPIView(APIView):
    """One page, read and written whole.

    Subclasses supply `page_model` and `serializer_class` and nothing else. The
    behaviour is identical for all ten — a page is a singleton, so there is no
    id in the URL and no list to page through — and that shared behaviour is
    what this base is for. It resolves nothing: which page this is, is which
    class you are looking at.

    A PATCH is one transaction: either every section in the payload is written
    or none is, so a half-saved page is not a state the site can be left in.
    """

    permission_classes = [IsAuthenticated, HasModelPermission]
    envelope_message = "Page retrieved"

    page_model = None
    serializer_class = None

    def get_queryset(self):
        """`HasModelPermission` reads the model off the queryset.

        Permissions are therefore per page: `pages.change_homepage` lets someone
        edit the home page and nothing else, which is the granularity the studio
        actually works at.
        """
        return self.page_model.objects.all()

    def _render(self, request):
        return self.serializer_class(
            load_page(self.page_model), context={"request": request}
        ).data

    @extend_schema(
        tags=["admin:pages"],
        summary="Retrieve the page with all of its sections",
        responses={200: None},
    )
    def get(self, request):
        return Response(self._render(request))

    @extend_schema(
        tags=["admin:pages"],
        summary="Update the page, or any of its sections",
        description=(
            "Partial at every level. An omitted section is untouched; an omitted "
            "item collection is left alone, while an empty list clears it. Item "
            "order is the array order — there is no reorder endpoint."
        ),
        responses={200: None},
    )
    def patch(self, request):
        serializer = self.serializer_class(
            load_page(self.page_model),
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.envelope_message = "Page updated"
        return Response(self._render(request))


# ─── One per page ────────────────────────────────────────────────────────────
# Three lines each, and deliberately not generated in a loop: this list is the
# site, and it should be greppable.


class HomePageAPIView(PageAPIView):
    page_model = HomePage
    serializer_class = HomePageSerializer


class AboutPageAPIView(PageAPIView):
    page_model = AboutPage
    serializer_class = AboutPageSerializer


class ServicesPageAPIView(PageAPIView):
    page_model = ServicesPage
    serializer_class = ServicesPageSerializer


class ProjectsPageAPIView(PageAPIView):
    page_model = ProjectsPage
    serializer_class = ProjectsPageSerializer


class GalleryPageAPIView(PageAPIView):
    page_model = GalleryPage
    serializer_class = GalleryPageSerializer


class JournalPageAPIView(PageAPIView):
    page_model = JournalPage
    serializer_class = JournalPageSerializer


class LocationsPageAPIView(PageAPIView):
    page_model = LocationsPage
    serializer_class = LocationsPageSerializer


class ContactPageAPIView(PageAPIView):
    page_model = ContactPage
    serializer_class = ContactPageSerializer


class PrivacyPageAPIView(PageAPIView):
    page_model = PrivacyPage
    serializer_class = PrivacyPageSerializer


class TermsPageAPIView(PageAPIView):
    page_model = TermsPage
    serializer_class = TermsPageSerializer


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
