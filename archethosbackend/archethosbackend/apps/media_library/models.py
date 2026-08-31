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

    title = models.CharField(max_length=255, blank=True)
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Describes the image for screen readers and search engines.",
    )

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

    def usage(self):
        """Every object currently pointing at this asset.

        Walks the reverse relations Django already tracks, so a new model with a
        media ForeignKey shows up here without touching this method.
        """
        found = []
        for relation in self._meta.related_objects:
            if not relation.one_to_many and not relation.one_to_one:
                continue
            accessor = relation.get_accessor_name()
            related_model = relation.related_model
            # Skip the reverse side of uploaded_by — that is authorship, not usage.
            if relation.field.name == "uploaded_by":
                continue
            manager = getattr(self, accessor, None)
            if manager is None:
                continue
            for obj in manager.all()[:50]:
                found.append(
                    {
                        "app_label": related_model._meta.app_label,
                        "model": related_model._meta.model_name,
                        "id": obj.pk,
                        "label": str(obj),
                        "field": relation.field.name,
                    }
                )
        return found
