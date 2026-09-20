from rest_framework import serializers

from apps.about.models import AboutPage
from apps.home.models import HomePage, Slider
from apps.services.models import Service

from .gallery_serializer import PublicGalleryItemSerializer
from .projects_serializer import PublicProjectSerializer
from .services_serializer import PublicServiceSerializer
from .shared_serializer import PublicMediaSerializer


class PublicSliderSerializer(serializers.ModelSerializer):
    media_detail = PublicMediaSerializer(source="media", read_only=True)

    class Meta:
        model = Slider
        fields = ["eyebrow", "title", "description", "media", "media_detail", "primary_cta_label", "primary_cta_url", "secondary_cta_label", "secondary_cta_url", "order"]


class PublicHomePageSerializer(serializers.ModelSerializer):
    sliders = serializers.SerializerMethodField()
    featured_project_detail = PublicProjectSerializer(source="featured_project", read_only=True)
    featured_service_detail = PublicServiceSerializer(source="featured_service", read_only=True)
    selected_work_detail = PublicProjectSerializer(source="selected_work", many=True, read_only=True)
    gallery_detail = PublicGalleryItemSerializer(source="gallery", many=True, read_only=True)
    services = serializers.SerializerMethodField()
    who_we_are = serializers.SerializerMethodField()

    def get_sliders(self, obj):
        return PublicSliderSerializer(obj.sliders.filter(is_visible=True), many=True, context=self.context).data

    def get_services(self, obj):
        queryset = Service.objects.filter(is_active=True).select_related("image").prefetch_related("gallery__asset", "work_stages__media")
        return PublicServiceSerializer(queryset, many=True, context=self.context).data

    def get_who_we_are(self, obj):
        about = AboutPage.objects.first()
        if not about:
            return None
        return {
            "title": about.who_we_are_title,
            "description": about.who_we_are_description,
            "media": about.who_we_are_media,
        }

    class Meta:
        model = HomePage
        fields = [
            "meta_title", "meta_description", "meta_keywords", "sliders", "featured_project", "featured_project_detail",
            "featured_service", "featured_service_detail", "services", "who_we_are", "home_counters",
            "design_build_process", "selected_work_title", "selected_work_description", "selected_work",
            "selected_work_detail", "gallery", "gallery_detail",
        ]
