"""
Media reference serialization.

The one place DEVELOPMENT_PLAN.md §2.1 is enforced: the database holds a
ForeignKey to MediaAsset, the API speaks relative paths.

    DB        HeroSection.background_media_id = 42
    API out   "background_media": "/media/uploads/abc123-hero.webp"
    API in    accepts 42 (id) OR "/media/uploads/abc123-hero.webp"

Every media field on every model uses this field, so the rule cannot drift.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


@extend_schema_field(
    {
        "type": "string",
        "nullable": True,
        "description": (
            "Relative media path on read, e.g. '/media/uploads/abc123-hero.webp'. "
            "On write, accepts either that path or the numeric MediaAsset id."
        ),
    }
)
class MediaReferenceField(serializers.Field):
    """Reads as a relative path, writes from either an id or a path."""

    default_error_messages = {
        "not_found": "No media asset matches '{value}'. Upload it to the Media Library first.",
        "invalid": "Expected a media asset id or a relative media path, got {value!r}.",
    }

    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("allow_null", True)
        super().__init__(**kwargs)

    def to_representation(self, value):
        # `value` is the MediaAsset instance; PrimaryKeyRelatedField semantics do
        # not apply because we serialize a derived property, not the pk.
        return value.relative_path if value else None

    def to_internal_value(self, data):
        from archethosbackend.apps.media_library.models import MediaAsset

        if data in (None, ""):
            return None

        if isinstance(data, MediaAsset):
            return data

        if isinstance(data, bool):
            self.fail("invalid", value=data)

        # An id — the Media Picker sends this after the user selects an asset.
        if isinstance(data, int) or (isinstance(data, str) and data.isdigit()):
            asset = MediaAsset.objects.filter(pk=int(data)).first()
            if asset is None:
                self.fail("not_found", value=data)
            return asset

        if not isinstance(data, str):
            self.fail("invalid", value=data)

        # A relative path — accepted so a payload round-trips unchanged, which
        # matters when the frontend PATCHes back a record it just GET'd.
        asset = _resolve_path(data)
        if asset is None:
            self.fail("not_found", value=data)
        return asset


def _resolve_path(path):
    """Find the asset whose stored file matches this relative path.

    Matching is done on the stored `file` name rather than by rebuilding the URL,
    so a change to MEDIA_URL cannot break existing references.
    """
    from django.conf import settings

    from archethosbackend.apps.media_library.models import MediaAsset

    cleaned = path.strip()

    # YouTube assets are referenced by their external URL.
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return MediaAsset.objects.filter(external_url=cleaned).first()

    prefix = settings.MEDIA_URL if settings.MEDIA_URL.startswith("/") else f"/{settings.MEDIA_URL}"
    relative = cleaned
    if relative.startswith(prefix):
        relative = relative[len(prefix) :]
    relative = relative.lstrip("/")

    return MediaAsset.objects.filter(file=relative).first()


@extend_schema_field(
    {
        "type": "object",
        "nullable": True,
        "properties": {
            "id": {"type": "integer"},
            "path": {"type": "string"},
            "alt_text": {"type": "string"},
            "title": {"type": "string"},
            "width": {"type": "integer", "nullable": True},
            "height": {"type": "integer", "nullable": True},
            "media_type": {"type": "string"},
        },
    }
)
class MediaDetailField(serializers.Field):
    """Companion read-only field exposing what a template needs beyond the path.

    Declared as `<name>_detail` alongside the `MediaReferenceField` so the
    frontend can render `alt` text and reserve layout space from width/height
    without a second request.

    A plain Field with `source="*"` rather than a SerializerMethodField: the
    latter would need a `get_<field_name>` method on every serializer that uses
    it, which is exactly the duplication this class exists to remove.
    """

    def __init__(self, source_field, **kwargs):
        self.source_field = source_field
        kwargs["read_only"] = True
        kwargs["source"] = "*"
        super().__init__(**kwargs)

    def to_representation(self, instance):
        asset = getattr(instance, self.source_field, None)
        if asset is None:
            return None
        return {
            "id": asset.id,
            "path": asset.relative_path,
            "alt_text": asset.alt_text,
            "title": asset.title,
            "width": asset.width,
            "height": asset.height,
            "media_type": asset.media_type,
        }
