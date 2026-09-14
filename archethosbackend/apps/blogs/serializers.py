from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers

from apps.media_library.serializers import MediaAssetSerializer

from .models import Blog, BlogCategory, BlogComment, BlogsPage


class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = "__all__"


class BlogCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = BlogComment
        fields = ["id", "blog", "author", "author_name", "content", "created_at", "updated_at"]
        read_only_fields = ["blog", "author", "created_at", "updated_at"]


class BlogSerializer(serializers.ModelSerializer):
    category_detail = BlogCategorySerializer(source="category", read_only=True)
    comments = BlogCommentSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Blog
        fields = [
            "id", "title", "slug", "excerpt", "content", "category", "category_detail", "featured_image",
            "status", "tags", "view_count", "meta_title", "meta_description", "meta_keywords", "author",
            "author_name", "created_at", "updated_at", "published_at", "comments",
        ]
        read_only_fields = ["author", "view_count", "created_at", "updated_at", "comments"]

    def create(self, validated_data):
        validated_data["slug"] = self._unique_slug(validated_data.get("slug") or validated_data["title"])
        if validated_data.get("status") == "published" and not validated_data.get("published_at"):
            validated_data["published_at"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("status") == "published" and not instance.published_at and not validated_data.get("published_at"):
            validated_data["published_at"] = timezone.now()
        return super().update(instance, validated_data)

    def _unique_slug(self, value):
        base = slugify(value) or "blog"
        slug = base[:220]
        number = 2
        while Blog.objects.filter(slug=slug).exists():
            suffix = f"-{number}"
            slug = f"{base[:220 - len(suffix)]}{suffix}"
            number += 1
        return slug


class BlogsPageSerializer(serializers.ModelSerializer):
    hero_image_detail = MediaAssetSerializer(source="hero_image", read_only=True)

    class Meta:
        model = BlogsPage
        fields = [
            "id", "hero_title", "hero_description", "hero_image", "hero_image_detail",
            "meta_title", "meta_description", "meta_keywords",
        ]
