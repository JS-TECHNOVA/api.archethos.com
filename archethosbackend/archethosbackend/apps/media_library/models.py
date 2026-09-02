"""
The Media Library — the single source of truth for every file and video the CMS
references.

Content and section models never store a path string; they hold
`ForeignKey(MediaAsset, on_delete=PROTECT)` and serialize it as a relative path
(DEVELOPMENT_PLAN.md §2.1). That is what makes "where is this image used?"
answerable and stops an in-use asset being deleted out from under a live page.
"""

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from archethosbackend.apps.core.models import TimeStampedModel


def upload_to(instance, filename):
    """Build a collision-proof storage path.

    The user's filename never determines uniqueness — two people uploading
    `hero.jpg` must not overwrite each other. The original name is kept in
    `file_name` for display and preserved here only as a readable suffix.
    """
    stem = Path(filename).stem
    suffix = Path(filename).suffix.lower()
    readable = slugify(stem)[:60] or "file"
    return f"uploads/{uuid.uuid4().hex}-{readable}{suffix}"


class MediaType(models.TextChoices):
    IMAGE = "IMAGE", "Image"
    VIDEO = "VIDEO", "Video"
    DOCUMENT = "DOCUMENT", "Document"


class SourceType(models.TextChoices):
    UPLOAD = "UPLOAD", "Uploaded file"
    YOUTUBE = "YOUTUBE", "YouTube"


class MediaLocation(models.TextChoices):
    """Where the bytes physically live.

    Distinct from `source_type`, which says how the asset was *created*. This
    says where it is *stored now*, and the two move independently: an uploaded
    file starts on local disk and may later be moved to object storage without
    ever stopping being an upload.

    It exists so that migration can be incremental — flip the storage backend,
    move files in batches, and `?media_location=local` tells you what is left.
    Without it, "have we moved everything yet?" is unanswerable.
    """

    LOCAL = "local", "Local disk"
    S3 = "s3", "S3-compatible object storage"
    EXTERNAL = "external", "External URL or CDN"


class MediaAssetQuerySet(models.QuerySet):
    def images(self):
        return self.filter(media_type=MediaType.IMAGE)

    def uploads(self):
        return self.filter(source_type=SourceType.UPLOAD)


class MediaAsset(TimeStampedModel):
    media_type = models.CharField(
        max_length=16, choices=MediaType.choices, db_index=True
    )
    source_type = models.CharField(
        max_length=16, choices=SourceType.choices, default=SourceType.UPLOAD
    )

    #: Read-only through the API: this is a fact about storage, not something an
    #: editor decides. It changes when files actually move, which is a
    #: management command's job, not a PATCH.
    media_location = models.CharField(
        max_length=16,
        choices=MediaLocation.choices,
        default=MediaLocation.LOCAL,
        db_index=True,
    )

    # Exactly one of these is populated, enforced by the check constraints below.
    file = models.FileField(upload_to=upload_to, blank=True)
    external_url = models.URLField(max_length=500, blank=True)

    #: YouTube video id, extracted on save so the frontend need not re-parse URLs.
    external_id = models.CharField(max_length=64, blank=True)
    thumbnail_url = models.URLField(max_length=500, blank=True)

    #: The name the user uploaded it under. Display only — never used for storage.
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveBigIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)

    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    # ── Descriptive fields. Editable for the life of the asset; none of them
    #    affect the stored file. ──────────────────────────────────────────────
    title = models.CharField(max_length=255, blank=True)
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Describes the image for screen readers and search engines.",
    )
    caption = models.CharField(
        max_length=500,
        blank=True,
        help_text="Shown beside the image where a layout has room for one.",
    )
    description = models.TextField(
        blank=True,
        help_text="Internal notes: where it came from, usage rights, who is in it.",
    )
    #: Free-form labels, normalised to lowercase on save so "Villa" and "villa"
    #: are the same tag. JSONB rather than a join table: tags here are a search
    #: aid on a few hundred rows, not a taxonomy with its own screens.
    tags = models.JSONField(default=list, blank=True)

    #: sha256 of the uploaded bytes. Indexed so re-uploading an identical file can
    #: be detected and the existing asset offered instead of a duplicate.
    checksum = models.CharField(max_length=64, blank=True, db_index=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_media",
    )

    objects = MediaAssetQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["media_type", "-created_at"]),
            models.Index(fields=["source_type"]),
        ]
        constraints = [
            # An UPLOAD without a file, or a YOUTUBE without a URL, is a broken
            # row that would render as a missing image on the live site. Reject
            # it at the database level so no code path can create one.
            models.CheckConstraint(
                condition=(
                    models.Q(source_type=SourceType.UPLOAD) & ~models.Q(file="")
                )
                | (
                    models.Q(source_type=SourceType.YOUTUBE)
                    & ~models.Q(external_url="")
                ),
                name="media_asset_source_has_payload",
            ),
        ]

    def __str__(self):
        return self.title or self.file_name or self.relative_path or f"Media #{self.pk}"

    @property
    def relative_path(self):
        """What the API exposes and what the frontend prepends its CDN base to.

        Uploads yield `/media/uploads/<uuid>-name.webp`; YouTube assets yield the
        external URL, which is already absolute and not ours to rewrite.
        """
        if self.source_type == SourceType.YOUTUBE:
            return self.external_url
        if not self.file:
            return ""
        media_url = settings.MEDIA_URL if settings.MEDIA_URL.startswith("/") else f"/{settings.MEDIA_URL}"
        return f"{media_url.rstrip('/')}/{self.file.name}"

    @property
    def extension(self):
        """The stored file's extension, lowercased, including the dot."""
        name = self.file.name if self.file else ""
        dot = name.rfind(".")
        return name[dot:].lower() if dot != -1 else ""

    def usage(self, limit=50):
        """Every object currently pointing at this asset.

        Scans the app registry for ForeignKeys whose target is MediaAsset,
        rather than walking `_meta.related_objects`.

        That distinction is the whole bug this replaced: every media FK in the
        project declares `related_name="+"`, which tells Django not to create a
        reverse accessor at all — so `related_objects` is empty and the previous
        implementation always reported "used by 0" while `PROTECT` was
        simultaneously refusing the delete. The two answers contradicted each
        other, and the wrong one was the reassuring one.

        Scanning forward FKs also means a new model with a media field appears
        here the moment it is added, with no `related_name` to remember.
        """
        from django.apps import apps

        found = []
        for model in apps.get_models():
            for field in model._meta.get_fields():
                if not getattr(field, "many_to_one", False):
                    continue
                if field.related_model is not type(self):
                    continue

                for obj in model._default_manager.filter(
                    **{field.name: self.pk}
                )[:limit]:
                    found.append(
                        {
                            "app_label": model._meta.app_label,
                            "model": model._meta.model_name,
                            "label": str(obj),
                            "id": obj.pk,
                            "field": field.name,
                        }
                    )
        return found
