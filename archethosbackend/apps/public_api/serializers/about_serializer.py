from rest_framework import serializers

from apps.about.models import AboutPage

class PublicAboutPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutPage
        fields = [
            "id", "hero_title", "hero_description", "hero_image",
            "who_we_are_title", "who_we_are_description", "who_we_are_media",
            "sections", "founders_section", "approach",
            "philosophy_eyebrow", "philosophy_title", "philosophy_short_description",
            "philosophy_description", "philosophy_media",
            "meta_title", "meta_description", "meta_keywords",
        ]
