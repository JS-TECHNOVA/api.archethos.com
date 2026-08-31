"""Media Library serializers."""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import MediaAsset, MediaType, SourceType
from .validators import validate_upload
from .youtube import canonical_url, extract_video_id, thumbnail_url


class MediaAssetListSerializer(serializers.ModelSerializer):
    """Flat row for the media grid and the picker. No nested objects."""

    path = serializers.CharField(source="relative_path", read_only=True)

    class Meta:
        model = MediaAsset
        fields = [
            "id",
            "path",
            "thumbnail_url",
            "media_type",
            "source_type",
            "title",
            "alt_text",
            "file_name",
            "file_size",
            "mime_type",
            "width",
            "height",
            "created_at",
        ]


class MediaAssetDetailSerializer(MediaAssetListSerializer):
    uploaded_by_email = serializers.EmailField(
        source="uploaded_by.email", read_only=True, default=None
    )

    class Meta(MediaAssetListSerializer.Meta):
        fields = MediaAssetListSerializer.Meta.fields + [
            "external_url",
            "external_id",
            "checksum",
            "uploaded_by_email",
            "updated_at",
        ]


class MediaAssetUpdateSerializer(serializers.ModelSerializer):
    """Only the descriptive fields are editable.

    The file itself, its type and its derived metadata are immutable: swapping
    the bytes under a stable id would silently change every page referencing it.
    Replacing an asset means uploading a new one and repointing the references.
    """

    class Meta:
        model = MediaAsset
        fields = ["title", "alt_text"]


class MediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField(write_only=True)
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    alt_text = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, attrs):
        try:
            attrs["metadata"] = validate_upload(attrs["file"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"file": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        metadata = validated_data.pop("metadata")
        uploaded = validated_data["file"]
        request = self.context.get("request")

        return MediaAsset.objects.create(
            source_type=SourceType.UPLOAD,
            file=uploaded,
            file_name=uploaded.name[:255],
            title=validated_data.get("title", "") or uploaded.name[:255],
            alt_text=validated_data.get("alt_text", ""),
            uploaded_by=getattr(request, "user", None) if request else None,
            **metadata,
        )

    def to_representation(self, instance):
        return MediaAssetDetailSerializer(instance, context=self.context).data


class YouTubeCreateSerializer(serializers.Serializer):
    url = serializers.CharField(write_only=True, max_length=500)
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    alt_text = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_url(self, value):
        try:
            self.context["video_id"] = extract_video_id(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def validate(self, attrs):
        video_id = self.context["video_id"]
        existing = MediaAsset.objects.filter(
            source_type=SourceType.YOUTUBE, external_id=video_id
        ).first()
        if existing is not None:
            # Adding the same video twice would give two ids for one thing, and
            # the picker would show duplicates.
            raise serializers.ValidationError(
                {
                    "url": [
                        f"This video is already in the Media Library as asset "
                        f"#{existing.pk}."
                    ]
                }
            )
        return attrs

    def create(self, validated_data):
        video_id = self.context["video_id"]
        request = self.context.get("request")

        return MediaAsset.objects.create(
            media_type=MediaType.VIDEO,
            source_type=SourceType.YOUTUBE,
            external_url=canonical_url(video_id),
            external_id=video_id,
            thumbnail_url=thumbnail_url(video_id),
            title=validated_data.get("title", "") or f"YouTube video {video_id}",
            alt_text=validated_data.get("alt_text", ""),
            uploaded_by=getattr(request, "user", None) if request else None,
        )

    def to_representation(self, instance):
        return MediaAssetDetailSerializer(instance, context=self.context).data
