from rest_framework import serializers

from apps.projects.models import Project, ProjectCategory, ProjectDetailedStage, ProjectGallery, ProjectPage

from .shared_serializer import PublicMediaSerializer
from .services_serializer import PublicServiceSerializer


class PublicProjectCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectCategory
        fields = ["id", "name", "description", "order"]


class PublicProjectGallerySerializer(serializers.ModelSerializer):
    asset_detail = PublicMediaSerializer(source="asset", read_only=True)

    class Meta:
        model = ProjectGallery
        fields = ["id", "asset", "asset_detail", "title", "caption", "description", "order"]


class PublicProjectDetailedStageSerializer(serializers.ModelSerializer):
    media_detail = PublicMediaSerializer(source="media", read_only=True)

    class Meta:
        model = ProjectDetailedStage
        fields = ["id", "eyebrow", "title", "description", "media", "media_detail", "order", "is_active"]


class PublicProjectSerializer(serializers.ModelSerializer):
    category_detail = PublicProjectCategorySerializer(source="category", read_only=True)
    cover_image_detail = serializers.SerializerMethodField()
    services_detail = PublicServiceSerializer(source="services", many=True, read_only=True)

    def get_cover_image_detail(self, obj):
        """Use the explicit cover, or the first gallery asset as a safe fallback."""
        media = obj.cover_image
        if media is None:
            gallery_item = next((item for item in obj.gallery.all() if item.asset_id), None)
            media = gallery_item.asset if gallery_item else None
        return PublicMediaSerializer(media, context=self.context).data if media else None

    class Meta:
        model = Project
        fields = [
            "id", "title", "slug", "category", "category_detail", "location", "year", "project_status",
            "services", "services_detail", "short_description", "description", "cover_image", "cover_image_detail",
            "is_featured", "published_at",
        ]


class PublicProjectDetailSerializer(PublicProjectSerializer):
    gallery = PublicProjectGallerySerializer(many=True, read_only=True)
    detailed_stages = PublicProjectDetailedStageSerializer(many=True, read_only=True)

    class Meta(PublicProjectSerializer.Meta):
        fields = PublicProjectSerializer.Meta.fields + ["gallery", "detailed_stages"]


class PublicProjectPageSerializer(serializers.ModelSerializer):
    hero_image_detail = PublicMediaSerializer(source="hero_image", read_only=True)
    categories = serializers.SerializerMethodField()
    featured_projects = serializers.SerializerMethodField()
    featured_project = serializers.SerializerMethodField()

    def get_categories(self, obj):
        return PublicProjectCategorySerializer(ProjectCategory.objects.all(), many=True).data

    def _featured_project_data(self, obj):
        if not hasattr(self, "_featured_projects_cache"):
            projects = obj.featured_projects.filter(status="published").select_related(
                "category", "cover_image"
            ).prefetch_related("services", "gallery__asset")
            self._featured_projects_cache = PublicProjectSerializer(
                projects, many=True, context=self.context
            ).data
        return self._featured_projects_cache

    def get_featured_projects(self, obj):
        return self._featured_project_data(obj)

    def get_featured_project(self, obj):
        """Return the first selected project for singular-field consumers."""
        projects = self._featured_project_data(obj)
        return projects[0] if projects else None

    class Meta:
        model = ProjectPage
        fields = [
            "hero_title", "hero_description", "hero_image", "hero_image_detail",
            "meta_title", "meta_description", "meta_keywords", "categories", "featured_projects", "featured_project",
        ]
