import re

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from archethosbackend.apps.core.models import (
    PublishableModel,
    SEOModel,
    SluggedModel,
    TimeStampedModel,
)

#: Rough average adult reading speed, used only for a "5 min read" badge.
WORDS_PER_MINUTE = 200


class BlogCategory(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Blog categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:255]
        super().save(*args, **kwargs)


class BlogPost(SluggedModel, PublishableModel, SEOModel, TimeStampedModel):
    """An article in the studio journal.

    The public route is /journal/<slug> on the frontend; the model keeps the
    BlogPost name because that is what its permissions and API paths use.
    """

    excerpt = models.TextField(blank=True, help_text="Shown in listings and previews.")
    content = models.TextField(blank=True)

    featured_image = models.ForeignKey(
        "media_library.MediaAsset",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="blog_posts",
    )
    category = models.ForeignKey(
        BlogCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="posts",
    )

    #: Minutes, derived from the body on save so the frontend never counts words.
    reading_time = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["category", "status"]),
        ]

    def save(self, *args, **kwargs):
        self.reading_time = self._estimate_reading_time()
        super().save(*args, **kwargs)

    def _estimate_reading_time(self):
        text = re.sub(r"<[^>]+>", " ", self.content or "")
        words = len(text.split())
        return max(1, round(words / WORDS_PER_MINUTE)) if words else 0
