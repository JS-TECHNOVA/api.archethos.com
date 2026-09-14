from django.conf import settings
from django.db import models


class Company(models.Model):
    SINGLETON_PK = 1
    name = models.CharField(max_length=255, blank=True)
    tagline = models.CharField(max_length=500, blank=True)
    whatsapp_link = models.URLField(blank=True)
    gst = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    header_links = models.JSONField(default=list, blank=True)
    footer_links = models.JSONField(default=list, blank=True)
    locations = models.JSONField(default=list, blank=True)
    contacts = models.JSONField(default=list, blank=True)
    socials = models.JSONField(default=list, blank=True)
    logo = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="company_logos")
    icon = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="company_icons")
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    head_inject_code = models.TextField(blank=True)
    body_inject_code = models.TextField(blank=True)
    smtp_host = models.CharField(max_length=255, blank=True)
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_username = models.CharField(max_length=255, blank=True)
    smtp_password = models.CharField(max_length=255, blank=True)
    smtp_from_email = models.EmailField(blank=True)
    smtp_use_tls = models.BooleanField(default=True)
    smtp_use_ssl = models.BooleanField(default=False)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="company_singleton")]


ENQUIRY_STATUS_CHOICES = [
    ("unread", "Unread"), ("read", "Read"), ("replied", "Replied"),
]


class Enquiry(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    project_type = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=255, blank=True)
    scope = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=100, blank=True)
    services = models.JSONField(default=list, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=ENQUIRY_STATUS_CHOICES, default="unread")
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class EnquiryReply(models.Model):
    enquiry = models.ForeignKey(Enquiry, on_delete=models.CASCADE, related_name="replies")
    subject = models.CharField(max_length=255)
    message = models.TextField()
    to_email = models.EmailField()
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="enquiry_replies")
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]
