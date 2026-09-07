"""
Public page delivery.

    GET /api/v1/public/pages/home/
    GET /api/v1/public/pages/about/

One view per page, matching the admin side. Each returns everything its route
renders, in the shape the frontend consumes directly — sections as named keys,
master data inlined, no join rows and no admin bookkeeping.

The `pages/` prefix stays: `/public/projects/` is already the Project
master-data list, and `/public/pages/projects/` is the page that frames it.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

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
from .serializers.company import PublicCompanySerializer
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


class PublicPageAPIView(APIView):
    """An unpublished page is a 404, not an empty one.

    A draft must be indistinguishable from a page that does not exist —
    otherwise the API leaks that something is being worked on, and the frontend
    renders a half-built route.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    envelope_message = "Page retrieved"

    page_model = None
    serializer_class = None

    @extend_schema(tags=["public"], summary="Retrieve the page", responses={200: None})
    def get(self, request):
        is_live = self.page_model.objects.filter(
            pk=self.page_model.SINGLETON_PK, is_published=True
        ).exists()

        if not is_live:
            return Response(
                {
                    "success": False,
                    "message": "Page not found.",
                    "errors": {},
                    "code": "not_found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            self.serializer_class(
                load_page(self.page_model),
                context={"request": request, "public": True},
            ).data
        )


class PublicHomePageAPIView(PublicPageAPIView):
    page_model = HomePage
    serializer_class = HomePageSerializer


class PublicAboutPageAPIView(PublicPageAPIView):
    page_model = AboutPage
    serializer_class = AboutPageSerializer


class PublicServicesPageAPIView(PublicPageAPIView):
    page_model = ServicesPage
    serializer_class = ServicesPageSerializer


class PublicProjectsPageAPIView(PublicPageAPIView):
    page_model = ProjectsPage
    serializer_class = ProjectsPageSerializer


class PublicGalleryPageAPIView(PublicPageAPIView):
    page_model = GalleryPage
    serializer_class = GalleryPageSerializer


class PublicJournalPageAPIView(PublicPageAPIView):
    page_model = JournalPage
    serializer_class = JournalPageSerializer


class PublicLocationsPageAPIView(PublicPageAPIView):
    page_model = LocationsPage
    serializer_class = LocationsPageSerializer


class PublicContactPageAPIView(PublicPageAPIView):
    page_model = ContactPage
    serializer_class = ContactPageSerializer


class PublicPrivacyPageAPIView(PublicPageAPIView):
    page_model = PrivacyPage
    serializer_class = PrivacyPageSerializer


class PublicTermsPageAPIView(PublicPageAPIView):
    page_model = TermsPage
    serializer_class = TermsPageSerializer


class PublicPageIndexAPIView(APIView):
    """Which routes are live — what a sitemap or a static build asks for."""

    authentication_classes = []
    permission_classes = [AllowAny]
    envelope_message = "Routes retrieved"

    @extend_schema(
        tags=["public"], summary="List published routes", responses={200: None}
    )
    def get(self, request):
        published = []
        for route, model in ORDERED_PAGES.items():
            page = (
                model.objects.filter(pk=model.SINGLETON_PK, is_published=True)
                .values("updated_at")
                .first()
            )
            if page:
                published.append({"route": route, "updated_at": page["updated_at"]})
        return Response(published)


class PublicCompanyAPIView(APIView):
    """Header, footer and contact details — every page needs them."""

    authentication_classes = []
    permission_classes = [AllowAny]
    envelope_message = "Company settings retrieved"

    @extend_schema(
        tags=["public"], summary="Retrieve site settings", responses={200: None}
    )
    def get(self, request):
        return Response(
            PublicCompanySerializer(Company.load(), context={"request": request}).data
        )
