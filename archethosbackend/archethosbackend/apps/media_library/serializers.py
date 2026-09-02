"""Media Library serializers."""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import MediaAsset, MediaLocation, MediaType, SourceType
from .services import normalise_tags
from .validators import validate_upload
from .youtube import canonical_url, extract_video_id, thumbnail_url


#: Everything that is *about* a file rather than part of it. Declared once and
#: mixed into upload, YouTube and update, so the three can never drift into
#: accepting different fields.
DESCRIPTIVE_FIELDS = ["title", "alt_text", "caption", "description", "tags"]


class DescriptiveFieldsMixin(serializers.Serializer):
    """The editable metadata, with identical rules wherever it is accepted."""

    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    alt_text = serializers.CharField(required=False, allow_blank=True, max_length=255)
    caption = serializers.CharField(required=False, allow_blank=True, max_length=500)
    description = serializers.CharField(required=False, allow_blank=True)
    #: Untyped child on purpose. A `CharField` child would coerce 42 into "42"
    #: and reject a stray "" that should simply be dropped — `normalise_tags`
    #: owns both rules, and having them in one place is what keeps the three
    #: endpoints behaving identically.
    tags = serializers.ListField(required=False, allow_empty=True)

    def validate_tags(self, value):
        try:
            return normalise_tags(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc

    def descriptive_data(self, validated):
        """Just the descriptive keys, with sane defaults for the ones omitted."""
        return {
            "title": validated.get("title", ""),
            "alt_text": validated.get("alt_text", ""),
            "caption": validated.get("caption", ""),
            "description": validated.get("description", ""),
            "tags": validated.get("tags", []),
        }


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
            "media_location",
            "title",
            "alt_text",
            "caption",
            "tags",
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
            "description",
            "external_url",
            "external_id",
            "checksum",
            "uploaded_by_email",
            "updated_at",
        ]


class MediaAssetUpdateSerializer(DescriptiveFieldsMixin, serializers.ModelSerializer):
    """The descriptive fields — everything that is *about* the file.

    The stored file, its type and its derived metadata are not here. Changing
    the bytes is a deliberate, separate action with its own endpoint
    (`/replace/`), so an accidental extra key in a PATCH can never swap the
    image behind a live page.
    """

    class Meta:
        model = MediaAsset
        fields = DESCRIPTIVE_FIELDS


class MediaReplaceSerializer(serializers.Serializer):
    """The new bytes for an existing asset. Nothing else — by design."""

    file = serializers.FileField(write_only=True)


class MediaUploadSerializer(DescriptiveFieldsMixin, serializers.Serializer):
    """A new file plus everything known about it at the time.

    All the descriptive fields are accepted here, not just a title: whoever is
    uploading knows the caption and the tags right then, and making them come
    back for a second PATCH is how assets end up with no alt text.
    """

    file = serializers.FileField(write_only=True)

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

        details = self.descriptive_data(validated_data)
        # A file with no title is unfindable in the picker, so fall back to the
        # name it was uploaded under.
        details["title"] = details["title"] or uploaded.name[:255]

        return MediaAsset.objects.create(
            source_type=SourceType.UPLOAD,
            file=uploaded,
            file_name=uploaded.name[:255],
            uploaded_by=getattr(request, "user", None) if request else None,
            **details,
            **metadata,
        )

    def to_representation(self, instance):
        return MediaAssetDetailSerializer(instance, context=self.context).data


class YouTubeCreateSerializer(DescriptiveFieldsMixin, serializers.Serializer):
    url = serializers.CharField(write_only=True, max_length=500)

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

        details = self.descriptive_data(validated_data)
        details["title"] = details["title"] or f"YouTube video {video_id}"

        return MediaAsset.objects.create(
            media_type=MediaType.VIDEO,
            source_type=SourceType.YOUTUBE,
            media_location=MediaLocation.EXTERNAL,
            external_url=canonical_url(video_id),
            external_id=video_id,
            thumbnail_url=thumbnail_url(video_id),
            uploaded_by=getattr(request, "user", None) if request else None,
            **details,
        )

    def to_representation(self, instance):
        return MediaAssetDetailSerializer(instance, context=self.context).data
