from rest_framework import serializers

from archethosbackend.apps.api.fields import MediaDetailField, MediaReferenceField
from archethosbackend.apps.api.serializers import SEO_FIELDS, SEOBlockField

from ..models import BlogCategory, BlogPost


class BlogCategoryListSerializer(serializers.ModelSerializer):
    posts_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = BlogCategory
        fields = ["id", "name", "slug", "posts_count", "created_at"]


class BlogCategoryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ["id", "name", "slug", "description", "created_at", "updated_at"]


class BlogCategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ["id", "name", "slug", "description"]
        extra_kwargs = {"slug": {"required": False}}


class BlogPostListSerializer(serializers.ModelSerializer):
    featured_image = MediaReferenceField(read_only=True)
    category_name = serializers.CharField(
        source="category.name", read_only=True, default=None
    )
    author_email = serializers.EmailField(
        source="author.email", read_only=True, default=None
    )

    class Meta:
        model = BlogPost
        fields = [
            "id", "title", "slug", "excerpt", "featured_image",
            "category_name", "author_email", "status", "published_at",
            "reading_time", "created_at",
        ]


class BlogPostDetailSerializer(serializers.ModelSerializer):
    featured_image = MediaReferenceField(read_only=True)
    featured_image_detail = MediaDetailField("featured_image")
    og_image = MediaReferenceField(read_only=True)
    category_name = serializers.CharField(
        source="category.name", read_only=True, default=None
    )
    author_email = serializers.EmailField(
        source="author.email", read_only=True, default=None
    )

    class Meta:
        model = BlogPost
        fields = [
            "id", "title", "slug", "excerpt", "content",
            "featured_image", "featured_image_detail",
            "category", "category_name", "author", "author_email",
            "status", "published_at", "reading_time", "created_at", "updated_at",
        ] + SEO_FIELDS


class BlogPostWriteSerializer(serializers.ModelSerializer):
    featured_image = MediaReferenceField()
    og_image = MediaReferenceField()

    class Meta:
        model = BlogPost
        fields = [
            "id", "title", "slug", "excerpt", "content", "featured_image",
            "category", "author", "status", "published_at",
        ] + SEO_FIELDS
        extra_kwargs = {"slug": {"required": False}}

    def create(self, validated_data):
        # Attribute to whoever is writing it, rather than leaving posts
        # unattributed whenever the field is omitted.
        if not validated_data.get("author"):
            request = self.context.get("request")
            if request and request.user.is_authenticated:
                validated_data["author"] = request.user
        return super().create(validated_data)


class PublicBlogPostSerializer(serializers.ModelSerializer):
    featured_image = MediaReferenceField(read_only=True)
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = BlogPost
        fields = [
            "id", "title", "slug", "excerpt", "featured_image",
            "category", "published_at", "reading_time",
        ]


class PublicBlogPostDetailSerializer(serializers.ModelSerializer):
    featured_image = MediaReferenceField(read_only=True)
    featured_image_detail = MediaDetailField("featured_image")
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    author_name = serializers.SerializerMethodField()
    seo = SEOBlockField()

    class Meta:
        model = BlogPost
        fields = [
            "id", "title", "slug", "excerpt", "content",
            "featured_image", "featured_image_detail", "category",
            "author_name", "published_at", "reading_time", "seo",
        ]

    def get_author_name(self, obj) -> str | None:
        # A display name only. The author's email is internal staff data and must
        # never reach the public API, which is why this is not `author_email`.
        if not obj.author:
            return None
        return obj.author.get_full_name() or None


class PublicBlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ["id", "name", "slug", "description"]
