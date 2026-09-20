from django.utils.text import slugify
from rest_framework import serializers

from apps.media_library.serializers import MediaAssetSerializer

from .models import Service, ServiceWorkStage, ServicesGallery, ServicesPage


class ServiceWorkStageSerializer(serializers.ModelSerializer):
    media_detail = MediaAssetSerializer(source="media", read_only=True)

    class Meta:
        model = ServiceWorkStage
        fields = ["id", "service", "eyebrow", "title", "description", "media", "media_detail", "order"]
        read_only_fields = ["service"]


class ServicesGallerySerializer(serializers.ModelSerializer):
    asset_detail = MediaAssetSerializer(source="asset", read_only=True)

    class Meta:
        model = ServicesGallery
        fields = ["id", "service", "asset", "asset_detail", "title", "caption", "description", "order"]
        read_only_fields = ["service"]


class ServiceSerializer(serializers.ModelSerializer):
    image_detail = MediaAssetSerializer(source="image", read_only=True)
    gallery = ServicesGallerySerializer(many=True, read_only=True)
    work_stages = ServiceWorkStageSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "eyebrow", "title", "short_description", "slug", "description", "is_active",
            "image", "image_detail", "how_it_moves", "meta_title", "meta_description", "meta_keywords",
            "created_at", "updated_at", "gallery", "work_stages",
        ]
        read_only_fields = ["created_at", "updated_at", "gallery", "work_stages"]

    def create(self, validated_data):
        validated_data["slug"] = self._unique_slug(validated_data.get("slug") or validated_data["title"])
        return super().create(validated_data)

    @staticmethod
    def _unique_slug(value):
        base = slugify(value) or "service"
        slug, number = base[:220], 2
        while Service.objects.filter(slug=slug).exists():
            suffix = f"-{number}"
            slug = f"{base[:220 - len(suffix)]}{suffix}"
            number += 1
        return slug


class ServicesPageSerializer(serializers.ModelSerializer):
    hero_image_detail = MediaAssetSerializer(source="hero_image", read_only=True)

    class Meta:
        model = ServicesPage
        fields = [
            "id", "hero_eyebrow", "hero_title", "hero_description", "hero_image", "hero_image_detail",
            "how_project_moves", "meta_title", "meta_description", "meta_keywords",
        ]
