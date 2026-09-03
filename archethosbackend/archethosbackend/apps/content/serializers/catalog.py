"""
Gallery items and locations.

Both were hardcoded in the frontend before this refactor and are master data
now: the same image appears in the gallery grid and the home page slider, and
the same two cities on three different pages.
"""

from rest_framework import serializers

from archethosbackend.apps.api.fields import MediaDetailField, MediaReferenceField

from ..models import GalleryItem, Location


class GalleryItemListSerializer(serializers.ModelSerializer):
    image = MediaReferenceField(read_only=True)

    class Meta:
        model = GalleryItem
        fields = [
            "id", "title", "caption", "category", "image",
            "status", "published_at", "created_at",
        ]


class GalleryItemDetailSerializer(serializers.ModelSerializer):
    image = MediaReferenceField(read_only=True)
    image_detail = MediaDetailField("image")

    class Meta:
        model = GalleryItem
        fields = [
            "id", "title", "caption", "category", "image", "image_detail",
            "status", "published_at", "created_at", "updated_at",
        ]


class GalleryItemWriteSerializer(serializers.ModelSerializer):
    image = MediaReferenceField(required=True, allow_null=False)

    class Meta:
        model = GalleryItem
        fields = ["id", "title", "caption", "category", "image", "status", "published_at"]

    def to_representation(self, instance):
        return GalleryItemDetailSerializer(instance, context=self.context).data


class PublicGalleryItemSerializer(serializers.ModelSerializer):
    image = MediaReferenceField(read_only=True)
    image_detail = MediaDetailField("image")

    class Meta:
        model = GalleryItem
        fields = ["id", "title", "caption", "category", "image", "image_detail"]


class LocationListSerializer(serializers.ModelSerializer):
    image = MediaReferenceField(read_only=True)

    class Meta:
        model = Location
        fields = [
            "id", "city", "state", "coordinates", "image",
            "status", "published_at", "created_at",
        ]


class LocationDetailSerializer(serializers.ModelSerializer):
    image = MediaReferenceField(read_only=True)
    image_detail = MediaDetailField("image")

    class Meta:
        model = Location
        fields = [
            "id", "city", "state", "coordinates", "blurb",
            "image", "image_detail", "address", "phone", "email", "map_url",
            "status", "published_at", "created_at", "updated_at",
        ]


class LocationWriteSerializer(serializers.ModelSerializer):
    image = MediaReferenceField()

    class Meta:
        model = Location
        fields = [
            "id", "city", "state", "coordinates", "blurb", "image",
            "address", "phone", "email", "map_url", "status", "published_at",
        ]

    def to_representation(self, instance):
        return LocationDetailSerializer(instance, context=self.context).data


class PublicLocationSerializer(serializers.ModelSerializer):
    """Blank contact fields stay blank.

    The studio has confirmed the cities but not the premises. The frontend omits
    an empty address rather than printing a placeholder, so nothing here should
    ever be filled in with a plausible-looking value to make the payload tidy.
    """

    image = MediaReferenceField(read_only=True)
    image_detail = MediaDetailField("image")

    class Meta:
        model = Location
        fields = [
            "id", "city", "state", "coordinates", "blurb",
            "image", "image_detail", "address", "phone", "email", "map_url",
        ]
