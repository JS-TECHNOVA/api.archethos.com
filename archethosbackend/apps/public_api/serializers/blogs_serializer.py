from rest_framework import serializers

from apps.blogs.models import Blog, BlogCategory, BlogsPage

from .shared_serializer import PublicMediaSerializer


class PublicBlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ["id", "name", "description"]


class PublicBlogSerializer(serializers.ModelSerializer):
    featured_image_detail = PublicMediaSerializer(source="featured_image", read_only=True)
    category_detail = PublicBlogCategorySerializer(source="category", read_only=True)

    class Meta:
        model = Blog
        fields = [
            "id", "title", "slug", "excerpt", "content", "category", "category_detail", "featured_image", "featured_image_detail",
            "tags", "published_at", "is_featured",
        ]


class PublicBlogsPageSerializer(serializers.ModelSerializer):
    hero_image_detail = PublicMediaSerializer(source="hero_image", read_only=True)
    categories = serializers.SerializerMethodField()
    featured_blogs = serializers.SerializerMethodField()

    def get_categories(self, obj):
        return PublicBlogCategorySerializer(BlogCategory.objects.all(), many=True).data

    def get_featured_blogs(self, obj):
        blogs = obj.featured_blogs.filter(status="published").select_related("category", "featured_image")
        return PublicBlogSerializer(blogs, many=True, context=self.context).data

    class Meta:
        model = BlogsPage
        fields = [
            "hero_title", "hero_description", "hero_image", "hero_image_detail",
            "meta_title", "meta_description", "meta_keywords", "categories", "featured_blogs",
        ]
