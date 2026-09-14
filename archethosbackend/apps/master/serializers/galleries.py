from rest_framework import serializers

from apps.master.models import Gallery, GalleryCategory, GalleryItem
from apps.media_library.serializers import MediaAssetSerializer


class GallerySerializer(serializers.ModelSerializer):
    hero_image_detail = MediaAssetSerializer(source="hero_image", read_only=True)

    class Meta:
        model = Gallery
        fields = [
            "id", "hero_title", "hero_description", "hero_image", "hero_image_detail",
            "meta_title", "meta_description", "meta_keywords",
        ]


class GalleryCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryCategory
        fields = ["id", "name", "order"]


class GalleryItemSerializer(serializers.ModelSerializer):
    asset_detail = MediaAssetSerializer(source="asset", read_only=True)
    category_detail = GalleryCategorySerializer(source="category", read_only=True)

    class Meta:
        model = GalleryItem
        fields = [
            "id", "category", "category_detail", "asset", "asset_detail", "title", "description",
            "order", "is_visible", "added_at", "added_by",
        ]
        read_only_fields = ["added_at", "added_by"]
