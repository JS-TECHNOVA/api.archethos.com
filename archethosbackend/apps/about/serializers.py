from rest_framework import serializers

from apps.media_library.serializers import MediaAssetSerializer
from .models import AboutPage


class AboutPageSerializer(serializers.ModelSerializer):
    hero_media_detail = MediaAssetSerializer(source="hero_media", read_only=True)

    class Meta:
        model = AboutPage
        fields = [
            "id", "hero_eyebrow", "hero_title", "hero_description", "hero_media", "hero_media_detail",
            "who_we_are_title", "who_we_are_description", "who_we_are_media",
            "sections", "founders_section", "approach",
            "philosophy_eyebrow", "philosophy_title", "philosophy_short_description",
            "philosophy_description", "philosophy_media",
            "meta_title", "meta_description", "meta_keywords",
        ]
