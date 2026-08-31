from django.db import models

from archethosbackend.apps.core.models import PublishableModel, TimeStampedModel


class Counter(PublishableModel, TimeStampedModel):
    """A single statistic in an "at a glance" band.

    Master content, not an inline row: the same stat ("40+ Projects Delivered")
    appears on the home and about pages and must be edited in one place.
    """

    #: Text rather than an integer — "1.5K", "24/7" and "100" are all valid.
    content = models.CharField(max_length=32, help_text='The value itself, e.g. "40".')
    #: Separate from `content` because the design styles them differently: the
    #: "+" and "%" render in the accent colour, smaller than the number.
    prefix = models.CharField(max_length=8, blank=True, help_text='e.g. "$", "~".')
    postfix = models.CharField(max_length=8, blank=True, help_text='e.g. "+", "%".')

    subtitle = models.CharField(max_length=255, help_text='e.g. "PROJECTS DELIVERED".')
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "published_at"])]

    def __str__(self):
        return f"{self.prefix}{self.content}{self.postfix} {self.subtitle}".strip()
