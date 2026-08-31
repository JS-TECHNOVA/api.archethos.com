"""
Form submissions.

One table for every form on the site. `form_type` says which form it came from
and `extra` holds whatever that form asks beyond the common fields — so adding a
careers form or a brochure request needs no migration.
"""

from django.db import models

from archethosbackend.apps.core.models import TimeStampedModel


class EnquiryType(models.TextChoices):
    CONTACT = "CONTACT", "Contact"
    CONSULTATION = "CONSULTATION", "Consultation"
    PROJECT = "PROJECT", "Project enquiry"
    CAREER = "CAREER", "Career"
    GENERAL = "GENERAL", "General"


class Enquiry(TimeStampedModel):
    form_type = models.CharField(
        max_length=16,
        choices=EnquiryType.choices,
        default=EnquiryType.CONTACT,
        db_index=True,
    )

    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=64, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)

    #: Fields specific to one form — budget, timeline, plot size, CV link.
    #: JSONB so a new form is a frontend change, not a schema change.
    extra = models.JSONField(default=dict, blank=True)

    #: Which page it was submitted from, e.g. "/vastu". Useful for attribution
    #: without any tracking.
    source_page = models.CharField(max_length=255, blank=True)

    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name_plural = "Enquiries"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["form_type", "-created_at"]),
            models.Index(fields=["is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.get_form_type_display()} from {self.name}"
