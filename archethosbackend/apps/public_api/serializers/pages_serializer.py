from rest_framework import serializers

from apps.pages.models import Page

from .shared_serializer import PublicMediaSerializer


class PublicPageSerializer(serializers.ModelSerializer):
    hero_image_detail = PublicMediaSerializer(source="hero_image", read_only=True)

    class Meta:
        model = Page
        fields = [
            "title", "slug", "hero_eyebrow", "hero_title", "hero_description", "hero_image",
            "hero_image_detail", "content_heading", "body", "meta_title", "meta_description",
            "meta_keywords", "created_at", "updated_at",
        ]
