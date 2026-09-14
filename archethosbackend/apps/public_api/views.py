from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.blogs.models import Blog, BlogsPage
from apps.master.models import FAQ, Gallery, GalleryItem
from apps.projects.models import Project, ProjectPage
from apps.services.models import Service, ServicesPage
from apps.home.models import HomePage
from apps.about.models import AboutPage
from apps.core.models import Company
from apps.contact.models import ContactPage
from apps.pages.models import Page

from .serializers.blogs_serializer import PublicBlogSerializer, PublicBlogsPageSerializer
from .serializers.gallery_serializer import PublicGalleryItemSerializer, PublicGalleryPageSerializer
from .serializers.projects_serializer import PublicProjectDetailSerializer, PublicProjectPageSerializer, PublicProjectSerializer
from .serializers.services_serializer import PublicServiceSerializer, PublicServicesPageSerializer
from .serializers.home_serializer import PublicHomePageSerializer
from .serializers.about_serializer import PublicAboutPageSerializer
from .serializers.company_serializer import PublicCompanySerializer
from .serializers.contact_serializer import PublicContactPageSerializer
from .serializers.pages_serializer import PublicPageSerializer
from apps.master.serializers import FAQSerializer


class PublicAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]


class PublicPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


@extend_schema(tags=["Public FAQs"])
class PublicFAQListAPIView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = FAQSerializer
    pagination_class = None
    queryset = FAQ.objects.filter(is_active=True)


@extend_schema(tags=["Public blogs"])
class PublicBlogsPageAPIView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicBlogsPageSerializer

    def get_object(self):
        page, _ = BlogsPage.objects.select_related("hero_image").get_or_create(pk=BlogsPage.SINGLETON_PK)
        return page


@extend_schema(tags=["Public blogs"])
class PublicBlogListAPIView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicBlogSerializer
    pagination_class = PublicPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "excerpt", "content", "tags"]

    def get_queryset(self):
        return Blog.objects.filter(status="published").select_related("featured_image")


@extend_schema(tags=["Public blogs"])
class PublicBlogDetailAPIView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicBlogSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Blog.objects.filter(status="published").select_related("featured_image")


@extend_schema(tags=["Public gallery"])
class PublicGalleryPageAPIView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicGalleryPageSerializer

    def get_object(self):
        page, _ = Gallery.objects.select_related("hero_image").get_or_create(pk=Gallery.SINGLETON_PK)
        return page


@extend_schema(tags=["Public gallery"])
class PublicGalleryItemListAPIView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicGalleryItemSerializer
    pagination_class = PublicPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["category"]
    search_fields = ["title", "description", "category__name"]

    def get_queryset(self):
        return GalleryItem.objects.filter(is_visible=True).select_related("category", "asset")


@extend_schema(tags=["Public projects"])
class PublicProjectPageAPIView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicProjectPageSerializer

    def get_object(self):
        page, _ = ProjectPage.objects.select_related("hero_image").get_or_create(pk=ProjectPage.SINGLETON_PK)
        return page


@extend_schema(tags=["Public projects"])
class PublicProjectListAPIView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicProjectSerializer
    pagination_class = PublicPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["category", "project_type", "is_featured"]
    search_fields = ["title", "short_description", "description", "location", "project_status", "services"]

    def get_queryset(self):
        return Project.objects.filter(status="published").select_related("category", "cover_image")


@extend_schema(tags=["Public projects"])
class PublicProjectDetailAPIView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicProjectDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Project.objects.filter(status="published").select_related("category", "cover_image").prefetch_related("gallery__asset", "detailed_stages__media")


@extend_schema(tags=["Public services"])
class PublicServicesPageAPIView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicServicesPageSerializer

    def get_object(self):
        page, _ = ServicesPage.objects.select_related("hero_image").get_or_create(pk=ServicesPage.SINGLETON_PK)
        return page


@extend_schema(tags=["Public services"])
class PublicServiceDetailAPIView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicServiceSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Service.objects.filter(is_visible=True).select_related("hero_image", "index_image").prefetch_related("gallery", "work_processes")


@extend_schema(tags=["Public home"])
class PublicHomePageAPIView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicHomePageSerializer

    def get_object(self):
        page, _ = HomePage.objects.prefetch_related(
            "sliders", "selected_gallery_items", "work_process_group__steps", "services_group__services", "projects_group__projects", "gallery_group__gallery_items", "counters_group__counters", "content_groups__media", "content_groups__secondary_media"
        ).get_or_create(pk=HomePage.SINGLETON_PK)
        return page


@extend_schema(tags=["Public about"])
class PublicAboutPageAPIView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicAboutPageSerializer

    def get_object(self):
        page, _ = AboutPage.objects.select_related(
            "slider__media", "work_process_group", "studio_image", "founder_image", "philosophy_image", "cta_image"
        ).prefetch_related("work_process_group__steps").get_or_create(pk=AboutPage.SINGLETON_PK)
        return page


@extend_schema(tags=["Public company"])
class PublicCompanyAPIView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicCompanySerializer

    def get_object(self):
        company, _ = Company.objects.select_related("logo", "icon").get_or_create(pk=Company.SINGLETON_PK)
        return company


@extend_schema(tags=["Public contact"])
class PublicContactPageAPIView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicContactPageSerializer

    def get_object(self):
        page, _ = ContactPage.objects.select_related("slider__media", "sidebar_image").get_or_create(pk=ContactPage.SINGLETON_PK)
        return page


@extend_schema(tags=["Public custom pages"])
class PublicPageDetailAPIView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicPageSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Page.objects.filter(is_active=True).select_related("hero_image")
