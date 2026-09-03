"""
Project serializers.

Media is handled two ways on purpose. `materials` is written inline with the
project, because it is a short list edited alongside the prose. Gallery items,
floor plans and drawings keep their own endpoints, because they are added a few
at a time from the media picker and a project can carry dozens — replacing the
whole collection on every save would be the wrong shape for that workflow.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from archethosbackend.apps.api.fields import MediaDetailField, MediaReferenceField
from archethosbackend.apps.api.serializers import (
    SEO_FIELDS,
    NestedCollectionsMixin,
    SEOBlockField,
)

from ..models import Project, ProjectGalleryItem, ProjectMaterial, ProjectMediaKind

NARRATIVE = [
    "design_intent",
    "spatial_planning",
    "interior_note",
    "construction_note",
    "outcome_note",
]


class ProjectMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMaterial
        fields = ["name", "note"]


class ProjectGalleryItemSerializer(serializers.ModelSerializer):
    media = MediaReferenceField(read_only=True)
    media_detail = MediaDetailField("media")

    class Meta:
        model = ProjectGalleryItem
        fields = ["id", "media", "media_detail", "kind", "title", "caption",
                  "description", "order"]


class ProjectGalleryItemWriteSerializer(serializers.ModelSerializer):
    media = MediaReferenceField(required=True, allow_null=False)

    class Meta:
        model = ProjectGalleryItem
        fields = ["id", "media", "kind", "title", "caption", "description", "order"]

    def validate(self, attrs):
        project = self.context["project"]
        media = attrs.get("media") or getattr(self.instance, "media", None)
        kind = attrs.get("kind") or getattr(
            self.instance, "kind", ProjectMediaKind.GALLERY
        )

        # Mirrors the unique constraint so the client gets a field error rather
        # than a 409 from the database. Scoped to `kind`: the same drawing may
        # legitimately appear once in the gallery and once among the drawings.
        clashes = ProjectGalleryItem.objects.filter(
            project=project, media=media, kind=kind
        )
        if self.instance:
            clashes = clashes.exclude(pk=self.instance.pk)
        if clashes.exists():
            raise serializers.ValidationError(
                {
                    "media": [
                        f"This asset is already in this project's "
                        f"{ProjectMediaKind(kind).label.lower()} list."
                    ]
                }
            )
        return attrs

    def create(self, validated_data):
        validated_data["project"] = self.context["project"]
        return super().create(validated_data)


class ProjectListSerializer(serializers.ModelSerializer):
    cover_image = MediaReferenceField(read_only=True)
    gallery_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "title", "slug", "location", "category", "project_year",
            "project_status", "cover_image", "is_featured", "status",
            "published_at", "gallery_count", "created_at",
        ]


class ProjectDetailSerializer(serializers.ModelSerializer):
    cover_image = MediaReferenceField(read_only=True)
    cover_image_detail = MediaDetailField("cover_image")
    og_image = MediaReferenceField(read_only=True)

    materials = ProjectMaterialSerializer(many=True, read_only=True)
    gallery_items = ProjectGalleryItemSerializer(many=True, read_only=True)
    services = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "title", "slug", "short_description", "description",
            "location", "category", "layout", "project_year", "project_status",
            "cover_image", "cover_image_detail", "is_featured",
            "services", "materials", "gallery_items",
            "status", "published_at", "created_at", "updated_at",
        ] + NARRATIVE + SEO_FIELDS


class ProjectWriteSerializer(NestedCollectionsMixin, serializers.ModelSerializer):
    cover_image = MediaReferenceField()
    og_image = MediaReferenceField()
    materials = ProjectMaterialSerializer(many=True, required=False)

    collections = {"materials": "materials"}

    class Meta:
        model = Project
        fields = [
            "id", "title", "slug", "short_description", "description",
            "location", "category", "layout", "project_year", "project_status",
            "cover_image", "is_featured", "services", "materials",
            "status", "published_at",
        ] + NARRATIVE + SEO_FIELDS
        extra_kwargs = {"slug": {"required": False}}

    def to_representation(self, instance):
        return ProjectDetailSerializer(instance, context=self.context).data


class PublicProjectSerializer(serializers.ModelSerializer):
    cover_image = MediaReferenceField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "title", "slug", "short_description", "location", "category",
            "layout", "project_year", "project_status", "cover_image",
            "is_featured",
        ]


class PublicProjectDetailSerializer(serializers.ModelSerializer):
    cover_image = MediaReferenceField(read_only=True)
    cover_image_detail = MediaDetailField("cover_image")
    materials = ProjectMaterialSerializer(many=True, read_only=True)

    # Split by kind so the frontend renders three strips without filtering.
    gallery = serializers.SerializerMethodField()
    floor_plans = serializers.SerializerMethodField()
    drawings = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    seo = SEOBlockField()

    class Meta:
        model = Project
        fields = [
            "id", "title", "slug", "short_description", "description",
            "location", "category", "layout", "project_year", "project_status",
            "cover_image", "cover_image_detail", "materials",
            "gallery", "floor_plans", "drawings", "services",
            "published_at", "seo",
        ] + NARRATIVE

    def _by_kind(self, obj, kind):
        # Filtered in Python, not with a queryset filter: the view prefetches
        # gallery_items, and re-filtering in SQL would discard that and issue
        # three extra queries per project.
        return ProjectGalleryItemSerializer(
            [item for item in obj.gallery_items.all() if item.kind == kind],
            many=True,
        ).data

    @extend_schema_field(ProjectGalleryItemSerializer(many=True))
    def get_gallery(self, obj):
        return self._by_kind(obj, ProjectMediaKind.GALLERY)

    @extend_schema_field(ProjectGalleryItemSerializer(many=True))
    def get_floor_plans(self, obj):
        return self._by_kind(obj, ProjectMediaKind.FLOOR_PLAN)

    @extend_schema_field(ProjectGalleryItemSerializer(many=True))
    def get_drawings(self, obj):
        return self._by_kind(obj, ProjectMediaKind.DRAWING)

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_services(self, obj):
        # Only services that are themselves live: a draft service must not become
        # publicly visible by being linked from a published project.
        return [
            {"id": service.id, "title": service.title, "slug": service.slug}
            for service in obj.services.all()
            if service.is_live
        ]
