from rest_framework import serializers

from apps.services.models import Service, ServiceWorkStage, ServicesGallery, ServicesPage

from .shared_serializer import PublicMediaSerializer


class PublicServiceWorkStageSerializer(serializers.ModelSerializer):
    media_detail = PublicMediaSerializer(source="media", read_only=True)

    class Meta:
        model = ServiceWorkStage
        fields = ["eyebrow", "title", "description", "media", "media_detail", "order"]


class PublicServicesGallerySerializer(serializers.ModelSerializer):
    asset_detail = PublicMediaSerializer(source="asset", read_only=True)

    class Meta:
        model = ServicesGallery
        fields = ["id", "asset", "asset_detail", "title", "caption", "description", "order"]


class PublicServiceSerializer(serializers.ModelSerializer):
    image_detail = PublicMediaSerializer(source="image", read_only=True)
    gallery = PublicServicesGallerySerializer(many=True, read_only=True)
    work_stages = PublicServiceWorkStageSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "eyebrow", "title", "tagline", "short_description", "slug", "description", "is_active",
            "image", "image_detail", "how_it_moves", "gallery", "work_stages",
            "meta_title", "meta_description", "meta_keywords",
        ]


class PublicServicesPageSerializer(serializers.ModelSerializer):
    hero_image_detail = PublicMediaSerializer(source="hero_image", read_only=True)
    services = serializers.SerializerMethodField()

    def get_services(self, obj):
        queryset = (
            Service.objects.filter(is_active=True)
            .select_related("image")
            .prefetch_related("gallery__asset", "work_stages__media")
        )
        return PublicServiceSerializer(queryset, many=True, context=self.context).data

    class Meta:
        model = ServicesPage
        fields = [
            "hero_eyebrow", "hero_title", "hero_description", "hero_image", "hero_image_detail",
            "how_project_moves", "meta_title", "meta_description", "meta_keywords", "services",
        ]
