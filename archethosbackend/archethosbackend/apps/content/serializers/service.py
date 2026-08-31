from rest_framework import serializers

from archethosbackend.apps.api.fields import MediaDetailField, MediaReferenceField
from archethosbackend.apps.api.serializers import SEO_FIELDS, SEOBlockField

from ..models import Service


class ServiceListSerializer(serializers.ModelSerializer):
    """Flat row for the admin data table — no nested objects."""

    featured_image = MediaReferenceField(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "title", "slug", "short_description", "featured_image",
            "status", "published_at", "order", "created_at",
        ]


class ServiceDetailSerializer(serializers.ModelSerializer):
    featured_image = MediaReferenceField(read_only=True)
    featured_image_detail = MediaDetailField("featured_image")
    icon = MediaReferenceField(read_only=True)
    og_image = MediaReferenceField(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "title", "slug", "short_description", "description",
            "featured_image", "featured_image_detail", "icon",
            "status", "published_at", "order", "created_at", "updated_at",
        ] + SEO_FIELDS


class ServiceWriteSerializer(serializers.ModelSerializer):
    featured_image = MediaReferenceField()
    icon = MediaReferenceField()
    og_image = MediaReferenceField()

    class Meta:
        model = Service
        fields = [
            "id", "title", "slug", "short_description", "description",
            "featured_image", "icon", "status", "published_at", "order",
        ] + SEO_FIELDS
        extra_kwargs = {"slug": {"required": False}}


class PublicServiceSerializer(serializers.ModelSerializer):
    """Independent of the admin serializers by design (plan §12): inheritance is
    how admin-only fields leak into public payloads months later."""

    featured_image = MediaReferenceField(read_only=True)
    icon = MediaReferenceField(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "title", "slug", "short_description",
            "featured_image", "icon", "order",
        ]


class PublicServiceDetailSerializer(serializers.ModelSerializer):
    featured_image = MediaReferenceField(read_only=True)
    featured_image_detail = MediaDetailField("featured_image")
    icon = MediaReferenceField(read_only=True)
    seo = SEOBlockField()

    class Meta:
        model = Service
        fields = [
            "id", "title", "slug", "short_description", "description",
            "featured_image", "featured_image_detail", "icon",
            "published_at", "seo",
        ]
