"""
Shared abstract models.

Nothing here creates a table. These are the building blocks every content model
composes, so that timestamps, slugs, SEO, publishing and ordering behave
identically everywhere (DEVELOPMENT_PLAN.md §4).
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SluggedModel(models.Model):
    """Title plus a URL slug that is generated once and then stays put.

    The slug is deliberately not regenerated when the title changes: published
    URLs must not break because someone fixed a typo.
    """

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    #: Field the slug is derived from.
    slug_source_field = "title"

    class Meta:
        abstract = True

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base = slugify(getattr(self, self.slug_source_field, "")) or "item"
        base = base[:240]
        candidate = base
        model = self.__class__
        suffix = 2
        while (
            model._default_manager.filter(slug=candidate).exclude(pk=self.pk).exists()
        ):
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate


class PublishStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    ARCHIVED = "ARCHIVED", "Archived"


class PublishableQuerySet(models.QuerySet):
    def live(self):
        """Rows the public API is allowed to expose.

        A null published_at means "published, not scheduled"; a future one means
        the row is queued and must stay hidden until then.
        """
        return self.filter(status=PublishStatus.PUBLISHED).filter(
            Q(published_at__isnull=True) | Q(published_at__lte=timezone.now())
        )

    def drafts(self):
        return self.filter(status=PublishStatus.DRAFT)


class PublishableModel(models.Model):
    """One publishing flag for every content type — no is_active/is_published mix.

    See DEVELOPMENT_PLAN.md §2.6.
    """

    status = models.CharField(
        max_length=16,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set automatically on first publish. A future value schedules the item.",
    )

    objects = PublishableQuerySet.as_manager()

    class Meta:
        abstract = True

    @property
    def is_live(self):
        return self.status == PublishStatus.PUBLISHED and (
            self.published_at is None or self.published_at <= timezone.now()
        )

    def save(self, *args, **kwargs):
        # Stamp the first publish; never overwrite a date already chosen.
        if self.status == PublishStatus.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class SEOModel(models.Model):
    """Per-page SEO overrides. Blank fields fall back to Company defaults."""

    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)

    og_title = models.CharField(max_length=255, blank=True)
    og_description = models.TextField(blank=True)
    # String reference so core carries no import-time dependency on media_library.
    og_image = models.ForeignKey(
        "media_library.MediaAsset",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    canonical_url = models.URLField(blank=True)
    robots_index = models.BooleanField(default=True)
    robots_follow = models.BooleanField(default=True)

    class Meta:
        abstract = True


class OrderedItemModel(models.Model):
    """Display order for section items.

    `order` intentionally participates in no unique constraint: it controls
    presentation only, duplicates are tolerated, and `id` breaks ties. That is
    what makes drag-and-drop reordering a plain bulk_update rather than a
    constraint-juggling exercise (DEVELOPMENT_PLAN.md §2.3).
    """

    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        abstract = True
        ordering = ["order", "id"]


class SingletonModel(models.Model):
    """Exactly one row, pinned to pk=1.

    Used for page models and Company, where "the homepage" must be unambiguous.
    """

    SINGLETON_PK = 1

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_PK
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            f"{self._meta.verbose_name} is a singleton and cannot be deleted."
        )

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=cls.SINGLETON_PK)
        return obj
