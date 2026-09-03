"""
Service serializers.

The detail page is the whole record — chapters, process and gallery included —
so those are written as part of the service rather than through endpoints of
their own. A service is edited as one document; the API says so.
"""

from rest_framework import serializers

from archethosbackend.apps.api.fields import MediaDetailField, MediaReferenceField
from archethosbackend.apps.api.serializers import (
    SEO_FIELDS,
    NestedCollectionsMixin,
    SEOBlockField,
)

from ..models import (
    Service,
    ServiceDetailSection,
    ServiceGalleryItem,
    ServiceProcessStep,
)

#: Owned collections, named once — they appear in three serializers below.
CHILDREN = ["detail_sections", "process_steps", "gallery_items"]

COLLECTIONS = {
    "detail_sections": "detail_sections",
    "process_steps": "process_steps",
    "gallery_items": "gallery_items",
}


class ServiceDetailSectionSerializer(serializers.ModelSerializer):
    image = MediaReferenceField()
    image_detail = MediaDetailField("image")

    class Meta:
        model = ServiceDetailSection
        fields = ["label", "heading", "body", "items", "image", "image_detail", "image_ratio"]


class ServiceProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProcessStep
        fields = ["number", "title", "body"]


class ServiceGalleryItemSerializer(serializers.ModelSerializer):
    media = MediaReferenceField()
    media_detail = MediaDetailField("media")

    class Meta:
        model = ServiceGalleryItem
        fields = ["media", "media_detail", "caption"]


class ServiceListSerializer(serializers.ModelSerializer):
    """Flat row for the admin data table — no nested objects."""

    index_image = MediaReferenceField(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "number", "title", "slug", "short_description", "index_image",
            "is_featured", "status", "published_at", "order", "created_at",
        ]


class ServiceDetailSerializer(serializers.ModelSerializer):
    hero_image = MediaReferenceField(read_only=True)
    hero_image_detail = MediaDetailField("hero_image")
    index_image = MediaReferenceField(read_only=True)
    index_image_detail = MediaDetailField("index_image")
    icon = MediaReferenceField(read_only=True)
    og_image = MediaReferenceField(read_only=True)

    detail_sections = ServiceDetailSectionSerializer(many=True, read_only=True)
    process_steps = ServiceProcessStepSerializer(many=True, read_only=True)
    gallery_items = ServiceGalleryItemSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "number", "title", "title_lines", "slug", "hero_heading",
            "short_description", "description",
            "hero_image", "hero_image_detail", "index_image", "index_image_detail",
            "icon", "is_featured", "process_label",
            "status", "published_at", "order", "created_at", "updated_at",
        ] + CHILDREN + SEO_FIELDS


class ServiceWriteSerializer(NestedCollectionsMixin, serializers.ModelSerializer):
    hero_image = MediaReferenceField()
    index_image = MediaReferenceField()
    icon = MediaReferenceField()
    og_image = MediaReferenceField()

    detail_sections = ServiceDetailSectionSerializer(many=True, required=False)
    process_steps = ServiceProcessStepSerializer(many=True, required=False)
    gallery_items = ServiceGalleryItemSerializer(many=True, required=False)

    collections = COLLECTIONS

    class Meta:
        model = Service
        fields = [
            "id", "number", "title", "title_lines", "slug", "hero_heading",
            "short_description", "description",
            "hero_image", "index_image", "icon", "is_featured", "process_label",
            "status", "published_at", "order",
        ] + CHILDREN + SEO_FIELDS
        extra_kwargs = {"slug": {"required": False}}

    def validate_title_lines(self, value):
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            raise serializers.ValidationError("Expected a list of strings.")
        return value

    def to_representation(self, instance):
        return ServiceDetailSerializer(instance, context=self.context).data


class PublicServiceSerializer(serializers.ModelSerializer):
    """Independent of the admin serializers by design (plan §12): inheritance is
    how admin-only fields leak into public payloads months later."""

    image = MediaReferenceField(source="index_image", read_only=True)
    icon = MediaReferenceField(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "number", "title", "title_lines", "slug",
            "short_description", "image", "icon", "is_featured", "order",
        ]


class PublicServiceDetailSerializer(serializers.ModelSerializer):
    hero_image = MediaReferenceField(read_only=True)
    hero_image_detail = MediaDetailField("hero_image")
    index_image = MediaReferenceField(read_only=True)
    icon = MediaReferenceField(read_only=True)
    seo = SEOBlockField()

    sections = ServiceDetailSectionSerializer(
        source="detail_sections", many=True, read_only=True
    )
    process_steps = ServiceProcessStepSerializer(many=True, read_only=True)
    gallery = ServiceGalleryItemSerializer(
        source="gallery_items", many=True, read_only=True
    )

    class Meta:
        model = Service
        fields = [
            "id", "number", "title", "title_lines", "slug", "hero_heading",
            "short_description", "description",
            "hero_image", "hero_image_detail", "index_image", "icon",
            "process_label", "sections", "process_steps", "gallery",
            "published_at", "seo",
        ]
