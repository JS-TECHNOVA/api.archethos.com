from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers

from apps.media_library.serializers import MediaAssetSerializer

from .models import Project, ProjectCategory, ProjectDetailedStage, ProjectGallery, ProjectPage


class ProjectCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectCategory
        fields = "__all__"


class ProjectGallerySerializer(serializers.ModelSerializer):
    asset_detail = MediaAssetSerializer(source="asset", read_only=True)

    class Meta:
        model = ProjectGallery
        fields = ["id", "project", "asset", "asset_detail", "title", "caption", "description", "order"]
        read_only_fields = ["project"]


class ProjectDetailedStageSerializer(serializers.ModelSerializer):
    media_detail = MediaAssetSerializer(source="media", read_only=True)

    class Meta:
        model = ProjectDetailedStage
        fields = ["id", "project", "eyebrow", "title", "description", "media", "media_detail", "order"]
        read_only_fields = ["project"]


class ProjectSerializer(serializers.ModelSerializer):
    category_detail = ProjectCategorySerializer(source="category", read_only=True)
    cover_image_detail = MediaAssetSerializer(source="cover_image", read_only=True)
    gallery = ProjectGallerySerializer(many=True, read_only=True)
    detailed_stages = ProjectDetailedStageSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "title", "slug", "category", "category_detail", "project_type", "location", "year", "project_status",
            "services", "short_description", "description", "cover_image", "cover_image_detail", "layout",
            "is_featured", "status", "published_at", "meta_title", "meta_description", "meta_keywords",
            "created_at", "updated_at", "gallery", "detailed_stages",
        ]
        read_only_fields = ["created_at", "updated_at", "gallery", "detailed_stages"]

    def create(self, validated_data):
        validated_data["slug"] = self._unique_slug(validated_data.get("slug") or validated_data["title"])
        if validated_data.get("status") == "published" and not validated_data.get("published_at"):
            validated_data["published_at"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("status") == "published" and not instance.published_at and not validated_data.get("published_at"):
            validated_data["published_at"] = timezone.now()
        return super().update(instance, validated_data)

    @staticmethod
    def _unique_slug(value):
        base = slugify(value) or "project"
        slug, number = base[:220], 2
        while Project.objects.filter(slug=slug).exists():
            suffix = f"-{number}"
            slug = f"{base[:220 - len(suffix)]}{suffix}"
            number += 1
        return slug


class ProjectPageSerializer(serializers.ModelSerializer):
    hero_image_detail = MediaAssetSerializer(source="hero_image", read_only=True)

    class Meta:
        model = ProjectPage
        fields = ["id", "hero_title", "hero_description", "hero_image", "hero_image_detail", "meta_title", "meta_description", "meta_keywords"]
