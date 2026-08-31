"""Serializers for sections with no child collection."""

from rest_framework import serializers

from archethosbackend.apps.api.fields import MediaDetailField, MediaReferenceField

from ..models import ContactInfoSection, CTASection, IntroSection, RichTextSection
from .base import SECTION_BASE_FIELDS, SECTION_META_FIELDS, BaseSectionListSerializer

# ─── Intro ───────────────────────────────────────────────────────────────────

INTRO_FIELDS = ["eyebrow", "heading", "body", "image", "cta_label", "cta_url"]


class IntroSectionListSerializer(BaseSectionListSerializer):
    class Meta(BaseSectionListSerializer.Meta):
        model = IntroSection
        fields = BaseSectionListSerializer.Meta.fields + ["heading"]


class IntroSectionDetailSerializer(serializers.ModelSerializer):
    image = MediaReferenceField(read_only=True)
    image_detail = MediaDetailField("image")

    class Meta:
        model = IntroSection
        fields = (
            SECTION_BASE_FIELDS + INTRO_FIELDS + ["image_detail"] + SECTION_META_FIELDS
        )


class IntroSectionWriteSerializer(serializers.ModelSerializer):
    image = MediaReferenceField()

    class Meta:
        model = IntroSection
        fields = ["id", "internal_label"] + INTRO_FIELDS


class PublicIntroSectionSerializer(serializers.ModelSerializer):
    image = MediaReferenceField(read_only=True)
    image_detail = MediaDetailField("image")

    class Meta:
        model = IntroSection
        fields = INTRO_FIELDS + ["image_detail"]


# ─── CTA ─────────────────────────────────────────────────────────────────────

CTA_FIELDS = [
    "eyebrow", "heading", "body", "background_media", "button_label", "button_url",
]


class CTASectionListSerializer(BaseSectionListSerializer):
    class Meta(BaseSectionListSerializer.Meta):
        model = CTASection
        fields = BaseSectionListSerializer.Meta.fields + ["heading"]


class CTASectionDetailSerializer(serializers.ModelSerializer):
    background_media = MediaReferenceField(read_only=True)
    background_media_detail = MediaDetailField("background_media")

    class Meta:
        model = CTASection
        fields = (
            SECTION_BASE_FIELDS + CTA_FIELDS + ["background_media_detail"]
            + SECTION_META_FIELDS
        )


class CTASectionWriteSerializer(serializers.ModelSerializer):
    background_media = MediaReferenceField()

    class Meta:
        model = CTASection
        fields = ["id", "internal_label"] + CTA_FIELDS


class PublicCTASectionSerializer(serializers.ModelSerializer):
    background_media = MediaReferenceField(read_only=True)
    background_media_detail = MediaDetailField("background_media")

    class Meta:
        model = CTASection
        fields = CTA_FIELDS + ["background_media_detail"]


# ─── Contact info ────────────────────────────────────────────────────────────

CONTACT_FIELDS = [
    "heading", "address", "phone", "email", "office_hours", "map_embed_url",
]


class ContactInfoSectionListSerializer(BaseSectionListSerializer):
    class Meta(BaseSectionListSerializer.Meta):
        model = ContactInfoSection
        fields = BaseSectionListSerializer.Meta.fields + ["heading"]


class ContactInfoSectionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInfoSection
        fields = SECTION_BASE_FIELDS + CONTACT_FIELDS + SECTION_META_FIELDS


class ContactInfoSectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInfoSection
        fields = ["id", "internal_label"] + CONTACT_FIELDS


class PublicContactInfoSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInfoSection
        fields = CONTACT_FIELDS


# ─── Rich text ───────────────────────────────────────────────────────────────

RICH_TEXT_FIELDS = ["heading", "body", "updated_note"]


class RichTextSectionListSerializer(BaseSectionListSerializer):
    class Meta(BaseSectionListSerializer.Meta):
        model = RichTextSection
        fields = BaseSectionListSerializer.Meta.fields + ["heading"]


class RichTextSectionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = RichTextSection
        fields = SECTION_BASE_FIELDS + RICH_TEXT_FIELDS + SECTION_META_FIELDS


class RichTextSectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RichTextSection
        fields = ["id", "internal_label"] + RICH_TEXT_FIELDS


class PublicRichTextSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RichTextSection
        fields = RICH_TEXT_FIELDS
