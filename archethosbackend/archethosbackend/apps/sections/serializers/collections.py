"""
Serializers for the sections that select and order master content.

All five follow one shape, so the differences are only in which content model the
item points at and what extra per-placement fields it carries.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from archethosbackend.apps.api.fields import MediaDetailField, MediaReferenceField
from archethosbackend.apps.content.models import FAQ, Counter, Project, Service

from ..models import (
    CounterSection,
    CounterSectionItem,
    FAQSection,
    FAQSectionItem,
    FeaturedProjectItem,
    FeaturedProjectsSection,
    GallerySection,
    GallerySectionItem,
    ServiceSectionItem,
    ServicesSection,
)
from .base import SECTION_BASE_FIELDS, SECTION_META_FIELDS, BaseSectionListSerializer

HEADING_FIELDS = ["eyebrow", "heading", "subheading"]


class _ItemWriteMixin:
    """Attaches the item to the section from the URL, and mirrors the unique
    constraint as a field error rather than letting the database raise a 409."""

    content_field = None

    def create(self, validated_data):
        validated_data["section"] = self.context["section"]
        return super().create(validated_data)

    def validate(self, attrs):
        section = self.context["section"]
        value = attrs.get(self.content_field) or getattr(
            self.instance, self.content_field, None
        )

        clashes = self.Meta.model.objects.filter(
            section=section, **{self.content_field: value}
        )
        if self.instance:
            clashes = clashes.exclude(pk=self.instance.pk)
        if clashes.exists():
            raise serializers.ValidationError(
                {self.content_field: ["This item is already in this section."]}
            )
        return attrs


# ─── Counters ────────────────────────────────────────────────────────────────


class CounterSectionItemSerializer(serializers.ModelSerializer):
    counter_id = serializers.IntegerField(source="counter.id", read_only=True)
    content = serializers.CharField(source="counter.content", read_only=True)
    prefix = serializers.CharField(source="counter.prefix", read_only=True)
    postfix = serializers.CharField(source="counter.postfix", read_only=True)
    subtitle = serializers.CharField(source="counter.subtitle", read_only=True)

    class Meta:
        model = CounterSectionItem
        fields = ["id", "counter_id", "prefix", "content", "postfix", "subtitle", "order"]


class CounterSectionItemWriteSerializer(_ItemWriteMixin, serializers.ModelSerializer):
    content_field = "counter"
    counter = serializers.PrimaryKeyRelatedField(queryset=Counter.objects.all())

    class Meta:
        model = CounterSectionItem
        fields = ["id", "counter", "order"]


class CounterSectionListSerializer(BaseSectionListSerializer):
    items_count = serializers.IntegerField(read_only=True)

    class Meta(BaseSectionListSerializer.Meta):
        model = CounterSection
        fields = BaseSectionListSerializer.Meta.fields + ["heading", "items_count"]


class CounterSectionDetailSerializer(serializers.ModelSerializer):
    items = CounterSectionItemSerializer(many=True, read_only=True)

    class Meta:
        model = CounterSection
        fields = SECTION_BASE_FIELDS + HEADING_FIELDS + ["items"] + SECTION_META_FIELDS


class CounterSectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CounterSection
        fields = ["id", "internal_label"] + HEADING_FIELDS


class PublicCounterSectionSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = CounterSection
        fields = HEADING_FIELDS + ["items"]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_items(self, obj):
        return [
            {
                "id": item.counter.id,
                "prefix": item.counter.prefix,
                "content": item.counter.content,
                "postfix": item.counter.postfix,
                "subtitle": item.counter.subtitle,
                "description": item.counter.description,
            }
            for item in obj.items.all()
            if item.counter.is_live
        ]


# ─── Featured projects ───────────────────────────────────────────────────────


class FeaturedProjectItemSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(source="project.id", read_only=True)
    title = serializers.CharField(source="project.title", read_only=True)
    slug = serializers.CharField(source="project.slug", read_only=True)
    status = serializers.CharField(source="project.status", read_only=True)

    class Meta:
        model = FeaturedProjectItem
        fields = ["id", "project_id", "title", "slug", "status", "display_variant", "order"]


class FeaturedProjectItemWriteSerializer(_ItemWriteMixin, serializers.ModelSerializer):
    content_field = "project"
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())

    class Meta:
        model = FeaturedProjectItem
        fields = ["id", "project", "display_variant", "order"]


class FeaturedProjectsSectionListSerializer(BaseSectionListSerializer):
    items_count = serializers.IntegerField(read_only=True)

    class Meta(BaseSectionListSerializer.Meta):
        model = FeaturedProjectsSection
        fields = BaseSectionListSerializer.Meta.fields + ["heading", "items_count"]


class FeaturedProjectsSectionDetailSerializer(serializers.ModelSerializer):
    items = FeaturedProjectItemSerializer(many=True, read_only=True)

    class Meta:
        model = FeaturedProjectsSection
        fields = SECTION_BASE_FIELDS + HEADING_FIELDS + ["items"] + SECTION_META_FIELDS


class FeaturedProjectsSectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeaturedProjectsSection
        fields = ["id", "internal_label"] + HEADING_FIELDS


class PublicFeaturedProjectsSectionSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = FeaturedProjectsSection
        fields = HEADING_FIELDS + ["items"]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_items(self, obj):
        # A draft project must not surface just because a section references it.
        return [
            {
                "id": item.project.id,
                "title": item.project.title,
                "slug": item.project.slug,
                "short_description": item.project.short_description,
                "location": item.project.location,
                "project_year": item.project.project_year,
                "featured_image": (
                    item.project.featured_image.relative_path
                    if item.project.featured_image
                    else None
                ),
                "display_variant": item.display_variant,
            }
            for item in obj.items.all()
            if item.project.is_live
        ]


# ─── Services ────────────────────────────────────────────────────────────────


class ServiceSectionItemSerializer(serializers.ModelSerializer):
    service_id = serializers.IntegerField(source="service.id", read_only=True)
    title = serializers.CharField(source="service.title", read_only=True)
    slug = serializers.CharField(source="service.slug", read_only=True)
    status = serializers.CharField(source="service.status", read_only=True)

    class Meta:
        model = ServiceSectionItem
        fields = ["id", "service_id", "title", "slug", "status", "label_override", "order"]


class ServiceSectionItemWriteSerializer(_ItemWriteMixin, serializers.ModelSerializer):
    content_field = "service"
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all())

    class Meta:
        model = ServiceSectionItem
        fields = ["id", "service", "label_override", "order"]


class ServicesSectionListSerializer(BaseSectionListSerializer):
    items_count = serializers.IntegerField(read_only=True)

    class Meta(BaseSectionListSerializer.Meta):
        model = ServicesSection
        fields = BaseSectionListSerializer.Meta.fields + ["heading", "items_count"]


class ServicesSectionDetailSerializer(serializers.ModelSerializer):
    items = ServiceSectionItemSerializer(many=True, read_only=True)

    class Meta:
        model = ServicesSection
        fields = SECTION_BASE_FIELDS + HEADING_FIELDS + ["items"] + SECTION_META_FIELDS


class ServicesSectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicesSection
        fields = ["id", "internal_label"] + HEADING_FIELDS


class PublicServicesSectionSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = ServicesSection
        fields = HEADING_FIELDS + ["items"]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_items(self, obj):
        return [
            {
                "id": item.service.id,
                "title": item.label_override or item.service.title,
                "slug": item.service.slug,
                "short_description": item.service.short_description,
                "icon": item.service.icon.relative_path if item.service.icon else None,
                "featured_image": (
                    item.service.featured_image.relative_path
                    if item.service.featured_image
                    else None
                ),
            }
            for item in obj.items.all()
            if item.service.is_live
        ]


# ─── Gallery ─────────────────────────────────────────────────────────────────


class GallerySectionItemSerializer(serializers.ModelSerializer):
    media = MediaReferenceField(read_only=True)
    media_detail = MediaDetailField("media")

    class Meta:
        model = GallerySectionItem
        fields = ["id", "media", "media_detail", "caption", "order"]


class GallerySectionItemWriteSerializer(_ItemWriteMixin, serializers.ModelSerializer):
    content_field = "media"
    media = MediaReferenceField(required=True, allow_null=False)

    class Meta:
        model = GallerySectionItem
        fields = ["id", "media", "caption", "order"]


class GallerySectionListSerializer(BaseSectionListSerializer):
    items_count = serializers.IntegerField(read_only=True)

    class Meta(BaseSectionListSerializer.Meta):
        model = GallerySection
        fields = BaseSectionListSerializer.Meta.fields + [
            "heading", "layout_variant", "items_count",
        ]


class GallerySectionDetailSerializer(serializers.ModelSerializer):
    items = GallerySectionItemSerializer(many=True, read_only=True)

    class Meta:
        model = GallerySection
        fields = (
            SECTION_BASE_FIELDS + HEADING_FIELDS + ["layout_variant", "items"]
            + SECTION_META_FIELDS
        )


class GallerySectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = GallerySection
        fields = ["id", "internal_label", "layout_variant"] + HEADING_FIELDS


class PublicGallerySectionSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = GallerySection
        fields = HEADING_FIELDS + ["layout_variant", "items"]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_items(self, obj):
        return [
            {
                "media": item.media.relative_path,
                "alt_text": item.media.alt_text,
                "width": item.media.width,
                "height": item.media.height,
                "caption": item.caption,
            }
            for item in obj.items.all()
        ]


# ─── FAQ ─────────────────────────────────────────────────────────────────────


class FAQSectionItemSerializer(serializers.ModelSerializer):
    faq_id = serializers.IntegerField(source="faq.id", read_only=True)
    question = serializers.CharField(source="faq.question", read_only=True)
    status = serializers.CharField(source="faq.status", read_only=True)

    class Meta:
        model = FAQSectionItem
        fields = ["id", "faq_id", "question", "status", "order"]


class FAQSectionItemWriteSerializer(_ItemWriteMixin, serializers.ModelSerializer):
    content_field = "faq"
    faq = serializers.PrimaryKeyRelatedField(queryset=FAQ.objects.all())

    class Meta:
        model = FAQSectionItem
        fields = ["id", "faq", "order"]


class FAQSectionListSerializer(BaseSectionListSerializer):
    items_count = serializers.IntegerField(read_only=True)

    class Meta(BaseSectionListSerializer.Meta):
        model = FAQSection
        fields = BaseSectionListSerializer.Meta.fields + ["heading", "items_count"]


class FAQSectionDetailSerializer(serializers.ModelSerializer):
    items = FAQSectionItemSerializer(many=True, read_only=True)

    class Meta:
        model = FAQSection
        fields = SECTION_BASE_FIELDS + HEADING_FIELDS + ["items"] + SECTION_META_FIELDS


class FAQSectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQSection
        fields = ["id", "internal_label"] + HEADING_FIELDS


class PublicFAQSectionSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = FAQSection
        fields = HEADING_FIELDS + ["items"]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_items(self, obj):
        return [
            {
                "id": item.faq.id,
                "question": item.faq.question,
                "answer": item.faq.answer,
            }
            for item in obj.items.all()
            if item.faq.is_live
        ]
