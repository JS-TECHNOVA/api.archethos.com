from rest_framework import serializers

from apps.media_library.serializers import MediaAssetSerializer

from .models import ContactPage


class ContactPageSerializer(serializers.ModelSerializer):
    hero_media_detail = MediaAssetSerializer(source="hero_media", read_only=True)
    sidebar_image_detail = MediaAssetSerializer(source="sidebar_image", read_only=True)

    class Meta:
        model = ContactPage
        fields = [
            "id", "hero_eyebrow", "hero_title", "hero_description", "hero_media",
            "hero_media_detail", "sidebar_image",
            "sidebar_image_detail", "next_section", "meta_title", "meta_description",
            "meta_keywords",
        ]
