from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from archethosbackend.apps.api.fields import MediaDetailField, MediaReferenceField
from archethosbackend.apps.api.serializers import SEO_FIELDS, SEOBlockField

from ..models import Project, ProjectGalleryItem


class ProjectGalleryItemSerializer(serializers.ModelSerializer):
    media = MediaReferenceField(read_only=True)
    media_detail = MediaDetailField("media")

    class Meta:
        model = ProjectGalleryItem
        fields = ["id", "media", "media_detail", "caption", "order"]


class ProjectGalleryItemWriteSerializer(serializers.ModelSerializer):
    media = MediaReferenceField(required=True, allow_null=False)

    class Meta:
        model = ProjectGalleryItem
        fields = ["id", "media", "caption", "order"]

    def validate(self, attrs):
        project = self.context["project"]
        media = attrs.get("media") or getattr(self.instance, "media", None)

        # Mirrors the unique constraint so the client gets a field error rather
        # than a 409 from the database.
        clashes = ProjectGalleryItem.objects.filter(project=project, media=media)
        if self.instance:
            clashes = clashes.exclude(pk=self.instance.pk)
        if clashes.exists():
            raise serializers.ValidationError(
                {"media": ["This image is already in the gallery for this project."]}
            )
        return attrs

    def create(self, validated_data):
        validated_data["project"] = self.context["project"]
        return super().create(validated_data)


class ProjectListSerializer(serializers.ModelSerializer):
    featured_image = MediaReferenceField(read_only=True)
    gallery_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "title", "slug", "location", "project_year", "project_status",
            "featured_image", "is_featured", "status", "published_at",
            "gallery_count", "created_at",
        ]


class ProjectDetailSerializer(serializers.ModelSerializer):
    featured_image = MediaReferenceField(read_only=True)
    featured_image_detail = MediaDetailField("featured_image")
    og_image = MediaReferenceField(read_only=True)
    gallery_items = ProjectGalleryItemSerializer(many=True, read_only=True)
    services = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "title", "slug", "short_description", "description",
            "location", "project_year", "project_status",
            "featured_image", "featured_image_detail", "is_featured",
            "services", "gallery_items",
            "status", "published_at", "created_at", "updated_at",
        ] + SEO_FIELDS


class ProjectWriteSerializer(serializers.ModelSerializer):
    featured_image = MediaReferenceField()
    og_image = MediaReferenceField()

    class Meta:
        model = Project
        fields = [
            "id", "title", "slug", "short_description", "description",
            "location", "project_year", "project_status",
            "featured_image", "is_featured", "services", "status", "published_at",
        ] + SEO_FIELDS
        extra_kwargs = {"slug": {"required": False}}


class PublicProjectSerializer(serializers.ModelSerializer):
    featured_image = MediaReferenceField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "title", "slug", "short_description", "location",
            "project_year", "project_status", "featured_image", "is_featured",
        ]


class PublicProjectDetailSerializer(serializers.ModelSerializer):
    featured_image = MediaReferenceField(read_only=True)
    featured_image_detail = MediaDetailField("featured_image")
    gallery = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    seo = SEOBlockField()

    class Meta:
        model = Project
        fields = [
            "id", "title", "slug", "short_description", "description",
            "location", "project_year", "project_status",
            "featured_image", "featured_image_detail", "gallery", "services",
            "published_at", "seo",
        ]

    @extend_schema_field(ProjectGalleryItemSerializer(many=True))
    def get_gallery(self, obj):
        return ProjectGalleryItemSerializer(obj.gallery_items.all(), many=True).data

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_services(self, obj):
        # Only services that are themselves live: a draft service must not become
        # publicly visible by being linked from a published project.
        return [
            {"id": service.id, "title": service.title, "slug": service.slug}
            for service in obj.services.all()
            if service.is_live
        ]
