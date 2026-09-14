from rest_framework import serializers

from apps.blogs.models import Blog, BlogCategory, BlogsPage

from .shared_serializer import PublicMediaSerializer


class PublicBlogSerializer(serializers.ModelSerializer):
    featured_image_detail = PublicMediaSerializer(source="featured_image", read_only=True)

    class Meta:
        model = Blog
        fields = [
            "id", "title", "slug", "excerpt", "featured_image", "featured_image_detail",
            "tags", "published_at",
        ]


class PublicBlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ["id", "name", "description"]


class PublicBlogsPageSerializer(serializers.ModelSerializer):
    hero_image_detail = PublicMediaSerializer(source="hero_image", read_only=True)
    categories = serializers.SerializerMethodField()

    def get_categories(self, obj):
        return PublicBlogCategorySerializer(BlogCategory.objects.all(), many=True).data

    class Meta:
        model = BlogsPage
        fields = [
            "hero_title", "hero_description", "hero_image", "hero_image_detail",
            "meta_title", "meta_description", "meta_keywords", "categories",
        ]
