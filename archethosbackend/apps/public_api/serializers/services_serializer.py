from rest_framework import serializers

from apps.services.models import Service, ServicesPage, ServicesWorkProcess

from .shared_serializer import PublicMediaSerializer


class PublicServicesWorkProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicesWorkProcess
        fields = ["number", "title", "description", "order"]


class PublicServiceSerializer(serializers.ModelSerializer):
    hero_image_detail = PublicMediaSerializer(source="hero_image", read_only=True)
    index_image_detail = PublicMediaSerializer(source="index_image", read_only=True)
    gallery_detail = PublicMediaSerializer(source="gallery", many=True, read_only=True)
    work_processes = PublicServicesWorkProcessSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = [
            "number", "order", "title", "title_lines", "slug", "is_featured", "hero_heading",
            "short_description", "description", "hero_image", "hero_image_detail", "index_image",
            "index_image_detail", "sections", "process_eyebrow", "gallery", "gallery_detail",
            "work_processes", "meta_title", "meta_description", "meta_keywords",
        ]


class PublicServicesPageSerializer(serializers.ModelSerializer):
    hero_image_detail = PublicMediaSerializer(source="hero_image", read_only=True)
    services = serializers.SerializerMethodField()

    def get_services(self, obj):
        queryset = Service.objects.filter(is_visible=True).select_related(
            "hero_image", "index_image"
        ).prefetch_related("gallery", "work_processes")
        return PublicServiceSerializer(queryset, many=True, context=self.context).data

    class Meta:
        model = ServicesPage
        fields = [
            "hero_eyebrow", "hero_title", "hero_description", "hero_image", "hero_image_detail",
            "meta_title", "meta_description", "meta_keywords", "services",
        ]
