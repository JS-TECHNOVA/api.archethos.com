from urllib.parse import parse_qs, urlparse

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import MediaAsset


@extend_schema_field(OpenApiTypes.STR)
class TagsField(serializers.Field):
    default_error_messages = {"invalid": "Tags must be a comma-separated string or a list."}

    def to_internal_value(self, value):
        if isinstance(value, str):
            return [tag.strip() for tag in value.split(",") if tag.strip()]
        if isinstance(value, list) and all(isinstance(tag, str) for tag in value):
            return [tag.strip() for tag in value if tag.strip()]
        self.fail("invalid")

    def to_representation(self, value):
        if not value:
            return ""
        return ", ".join(value) if isinstance(value, list) else str(value)


class AssetUrlField(serializers.Field):
    def get_attribute(self, instance):
        return instance

    def absolute_url(self, value):
        if not value:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(value) if request else value


@extend_schema_field(OpenApiTypes.URI)
class SourceField(AssetUrlField):
    def to_internal_value(self, value):
        return {"external_url": serializers.URLField().run_validation(value)}

    def to_representation(self, asset):
        return self.absolute_url(asset.external_url or (asset.file.url if asset.file else None))


@extend_schema_field(OpenApiTypes.URI)
class ThumbnailUrlField(AssetUrlField):
    def to_internal_value(self, value):
        return {"thumbnail_url": serializers.URLField().run_validation(value)}

    def to_representation(self, asset):
        return self.absolute_url(asset.thumbnail_url or (asset.thumbnail_file.url if asset.thumbnail_file else None))


class MediaAssetSerializer(serializers.ModelSerializer):
    tags = TagsField(required=False)
    source = SourceField(source="*", required=False)
    thumbnail_url = ThumbnailUrlField(source="*", required=False)
    youtube_url = serializers.URLField(write_only=True, required=False)
    video_url = serializers.URLField(write_only=True, required=False)

    class Meta:
        model = MediaAsset
        fields = [
            "id", "file", "thumbnail_file", "source", "thumbnail_url", "media_type", "source_type",
            "external_url", "external_id", "file_name", "mime_type", "title", "alt_text", "caption",
            "description", "tags", "media_location", "youtube_url", "video_url", "uploaded_by", "created_at",
        ]
        read_only_fields = ["uploaded_by", "created_at"]
        extra_kwargs = {
            "file": {"required": False, "allow_null": True},
            "thumbnail_file": {"required": False, "allow_null": True},
            "media_type": {"read_only": True},
            "source_type": {"read_only": True},
            "external_url": {"read_only": True},
            "external_id": {"read_only": True},
            "file_name": {"read_only": True},
            "mime_type": {"read_only": True},
            "media_location": {"read_only": True},
        }

    def validate(self, attrs):
        source_url = attrs.get("external_url")
        youtube_url = attrs.pop("youtube_url", None)
        video_url = attrs.pop("video_url", None)
        url_values = [value for value in [source_url, youtube_url, video_url] if value]
        if len(url_values) > 1:
            raise serializers.ValidationError("Send one video URL in source, video_url, or youtube_url.")
        if url_values:
            attrs["external_url"] = url_values[0]

        has_file = bool(attrs.get("file"))
        has_source = bool(attrs.get("external_url"))
        if has_file and has_source:
            raise serializers.ValidationError("Send either a file or a video source URL, not both.")
        if attrs.get("thumbnail_file") and not has_file:
            raise serializers.ValidationError({"thumbnail_file": "A thumbnail file requires an uploaded video file."})
        if has_file:
            media_type = self._file_metadata(attrs["file"])["media_type"]
            if attrs.get("thumbnail_file") and media_type != "video":
                raise serializers.ValidationError({"thumbnail_file": "Only uploaded videos can have a thumbnail file."})
            if attrs.get("thumbnail_url"):
                raise serializers.ValidationError({"thumbnail_url": "Use thumbnail_file for an uploaded video."})
        elif has_source:
            if attrs.get("thumbnail_file"):
                raise serializers.ValidationError({"thumbnail_file": "Use thumbnail_url for an external video."})
        elif not self.instance:
            raise serializers.ValidationError({"file": "Upload a file or provide a video source URL."})
        return attrs

    @staticmethod
    def _youtube_video_id(value):
        parsed = urlparse(value)
        host = parsed.netloc.lower().removeprefix("www.")
        if host == "youtu.be":
            video_id = parsed.path.strip("/").split("/")[0]
        elif host in {"youtube.com", "m.youtube.com", "youtube-nocookie.com"}:
            if parsed.path == "/watch":
                video_id = parse_qs(parsed.query).get("v", [""])[0]
            else:
                parts = parsed.path.strip("/").split("/")
                video_id = parts[1] if len(parts) > 1 and parts[0] in {"embed", "shorts"} else ""
        else:
            return None
        if len(video_id) != 11 or not all(character.isalnum() or character in "-_" for character in video_id):
            raise serializers.ValidationError({"source": "Enter a valid YouTube video URL."})
        return video_id

    @staticmethod
    def _file_metadata(file):
        mime_type = getattr(file, "content_type", "")
        return {
            "media_type": mime_type.split("/", 1)[0] if "/" in mime_type else "file",
            "source_type": "UPLOAD",
            "file_name": getattr(file, "name", ""),
            "mime_type": mime_type,
            "media_location": "local",
        }

    def _external_video_metadata(self, source_url, thumbnail_url):
        video_id = self._youtube_video_id(source_url)
        if video_id:
            return {
                "file": None,
                "thumbnail_file": None,
                "media_type": "video",
                "source_type": "YOUTUBE",
                "external_id": video_id,
                "external_url": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail_url": thumbnail_url or f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
                "file_name": "",
                "mime_type": "",
                "media_location": None,
            }
        return {
            "file": None,
            "thumbnail_file": None,
            "media_type": "video",
            "source_type": "EXTERNAL",
            "external_id": "",
            "external_url": source_url,
            "thumbnail_url": thumbnail_url or "",
            "file_name": "",
            "mime_type": "",
            "media_location": None,
        }

    def create(self, validated_data):
        source_url = validated_data.get("external_url")
        if source_url:
            thumbnail_url = validated_data.get("thumbnail_url")
            validated_data.update(self._external_video_metadata(source_url, thumbnail_url))
        else:
            validated_data.update(self._file_metadata(validated_data["file"]))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        source_url = validated_data.get("external_url")
        if source_url:
            thumbnail_url = validated_data.get("thumbnail_url")
            validated_data.update(self._external_video_metadata(source_url, thumbnail_url))
        elif "file" in validated_data and validated_data["file"]:
            validated_data.update(self._file_metadata(validated_data["file"]))
            validated_data.update({"external_url": "", "external_id": ""})
            if self._file_metadata(validated_data["file"])["media_type"] != "video":
                validated_data.update({"thumbnail_file": None, "thumbnail_url": ""})
        return super().update(instance, validated_data)
