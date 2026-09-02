"""Hero section serializers."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from archethosbackend.apps.api.fields import MediaDetailField, MediaReferenceField

from ..models import HeroSection, HeroSlide
from .base import SECTION_BASE_FIELDS, SECTION_META_FIELDS, BaseSectionListSerializer


class HeroSlideSerializer(serializers.ModelSerializer):
    media = MediaReferenceField(read_only=True)
    media_detail = MediaDetailField("media")
    heading_lines = serializers.SerializerMethodField()

    class Meta:
        model = HeroSlide
        fields = [
            "id", "label", "eyebrow", "heading", "heading_lines", "lead",
            "media", "media_detail",
            "primary_cta_label", "primary_cta_url",
            "secondary_cta_label", "secondary_cta_url",
            "order",
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_heading_lines(self, obj):
        return obj.heading_lines


class HeroSlideWriteSerializer(serializers.ModelSerializer):
    media = MediaReferenceField()

    class Meta:
        model = HeroSlide
        fields = ["id", "label", "eyebrow", "heading", "lead", "media",
                  "primary_cta_label", "primary_cta_url",
                  "secondary_cta_label", "secondary_cta_url", "order"]

    def create(self, validated_data):
        validated_data["section"] = self.context["section"]
        return super().create(validated_data)


class HeroSectionListSerializer(BaseSectionListSerializer):
    slides_count = serializers.IntegerField(read_only=True)

    class Meta(BaseSectionListSerializer.Meta):
        model = HeroSection
        fields = BaseSectionListSerializer.Meta.fields + ["variant", "slides_count"]


class HeroSectionDetailSerializer(serializers.ModelSerializer):
    slides = HeroSlideSerializer(many=True, read_only=True)

    class Meta:
        model = HeroSection
        fields = (
            SECTION_BASE_FIELDS
            + ["variant", "autoplay_seconds", "slides"]
            + SECTION_META_FIELDS
        )


class HeroSectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroSection
        fields = ["id", "internal_label", "variant", "autoplay_seconds"]


class PublicHeroSectionSerializer(serializers.ModelSerializer):
    """Independent of the admin serializers (plan §12).

    `internal_label` is absent here on purpose — it is a CMS-only label and must
    never reach the public payload.
    """

    slides = serializers.SerializerMethodField()

    class Meta:
        model = HeroSection
        fields = ["variant", "autoplay_seconds", "slides"]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_slides(self, obj):
        return [
            {
                "label": slide.label,
                "eyebrow": slide.eyebrow,
                "heading_lines": slide.heading_lines,
                "lead": slide.lead,
                "media": slide.media.relative_path if slide.media else None,
                "media_detail": (
                    {
                        "alt_text": slide.media.alt_text,
                        "width": slide.media.width,
                        "height": slide.media.height,
                    }
                    if slide.media
                    else None
                ),
                "primary_cta_label": slide.primary_cta_label,
                "primary_cta_url": slide.primary_cta_url,
                "secondary_cta_label": slide.secondary_cta_label,
                "secondary_cta_url": slide.secondary_cta_url,
            }
            for slide in obj.slides.all()
        ]
