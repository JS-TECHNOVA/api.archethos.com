from rest_framework import serializers

from apps.projects.models import Project, ProjectCategory, ProjectDetailedStage, ProjectGallery, ProjectPage

from .shared_serializer import PublicMediaSerializer


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
        fields = ["id", "eyebrow", "title", "description", "media", "media_detail", "order"]


class PublicProjectSerializer(serializers.ModelSerializer):
    category_detail = PublicProjectCategorySerializer(source="category", read_only=True)
    cover_image_detail = PublicMediaSerializer(source="cover_image", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "title", "slug", "category", "category_detail", "project_type", "location", "year", "project_status",
            "services", "short_description", "description", "cover_image", "cover_image_detail", "layout",
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

    def get_categories(self, obj):
        return PublicProjectCategorySerializer(ProjectCategory.objects.all(), many=True).data

    class Meta:
        model = ProjectPage
        fields = [
            "hero_title", "hero_description", "hero_image", "hero_image_detail",
            "meta_title", "meta_description", "meta_keywords", "categories",
        ]
