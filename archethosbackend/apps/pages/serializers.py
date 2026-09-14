from django.utils.text import slugify
from rest_framework import serializers

from apps.media_library.serializers import MediaAssetSerializer

from .models import Page


class PageSerializer(serializers.ModelSerializer):
    hero_image_detail = MediaAssetSerializer(source="hero_image", read_only=True)

    class Meta:
        model = Page
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["slug"] = self._unique_slug(validated_data.get("slug") or validated_data["title"])
        return super().create(validated_data)

    @staticmethod
    def _unique_slug(value):
        base = slugify(value) or "page"
        slug, number = base[:220], 2
        while Page.objects.filter(slug=slug).exists():
            suffix = f"-{number}"
            slug = f"{base[:220 - len(suffix)]}{suffix}"
            number += 1
        return slug
