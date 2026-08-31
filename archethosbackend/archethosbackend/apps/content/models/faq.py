from django.db import models

from archethosbackend.apps.core.models import PublishableModel, TimeStampedModel


class FAQCategory(models.TextChoices):
    GENERAL = "GENERAL", "General"
    VASTU = "VASTU", "Vastu"
    PROCESS = "PROCESS", "Process"
    PRICING = "PRICING", "Pricing"


class FAQ(PublishableModel, TimeStampedModel):
    """A reusable question and answer.

    Master content: the same FAQ may appear in several FAQ sections, ordered
    differently in each, and is edited in exactly one place.
    """

    question = models.CharField(max_length=500)
    answer = models.TextField()
    category = models.CharField(
        max_length=16,
        choices=FAQCategory.choices,
        default=FAQCategory.GENERAL,
        db_index=True,
    )

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "published_at"])]

    def __str__(self):
        return self.question
