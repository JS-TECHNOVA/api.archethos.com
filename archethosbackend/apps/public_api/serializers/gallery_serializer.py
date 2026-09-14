from rest_framework import serializers

from apps.master.models import Gallery, GalleryCategory, GalleryItem

from .shared_serializer import PublicMediaSerializer


class PublicGalleryCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryCategory
        fields = ["id", "name", "order"]


class PublicGalleryItemSerializer(serializers.ModelSerializer):
    category_detail = PublicGalleryCategorySerializer(source="category", read_only=True)
    asset_detail = PublicMediaSerializer(source="asset", read_only=True)

    class Meta:
        model = GalleryItem
        fields = [
            "id", "category", "category_detail", "asset", "asset_detail", "title",
            "description", "order", "added_at",
        ]


class PublicGalleryPageSerializer(serializers.ModelSerializer):
    hero_image_detail = PublicMediaSerializer(source="hero_image", read_only=True)
    categories = serializers.SerializerMethodField()

    def get_categories(self, obj):
        return PublicGalleryCategorySerializer(GalleryCategory.objects.all(), many=True).data

    class Meta:
        model = Gallery
        fields = [
            "hero_title", "hero_description", "hero_image", "hero_image_detail",
            "meta_title", "meta_description", "meta_keywords", "categories",
        ]
