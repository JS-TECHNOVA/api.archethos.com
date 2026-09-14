from django.utils.text import slugify
from rest_framework import serializers

from apps.media_library.serializers import MediaAssetSerializer

from .models import Service, ServicesPage, ServicesWorkProcess


class ServicesWorkProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicesWorkProcess
        fields = ["id", "service", "number", "title", "description", "order"]
        read_only_fields = ["service"]


class ServiceSerializer(serializers.ModelSerializer):
    hero_image_detail = MediaAssetSerializer(source="hero_image", read_only=True)
    index_image_detail = MediaAssetSerializer(source="index_image", read_only=True)
    gallery_detail = MediaAssetSerializer(source="gallery", many=True, read_only=True)
    work_processes = ServicesWorkProcessSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "work_processes"]

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
        fields = "__all__"
