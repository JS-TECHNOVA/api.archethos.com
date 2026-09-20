from django.db import models


class AboutPage(models.Model):
    SINGLETON_PK = 1

    hero_title = models.CharField(max_length=255, blank=True)
    hero_description = models.TextField(blank=True)
    hero_image = models.URLField(blank=True)

    who_we_are_title = models.CharField(max_length=255, blank=True)
    who_we_are_description = models.TextField(blank=True)
    who_we_are_media = models.URLField(blank=True)

    sections = models.JSONField(default=list, blank=True)

    founders_section = models.JSONField(default=dict, blank=True)
    approach = models.JSONField(default=dict, blank=True)

    philosophy_eyebrow = models.CharField(max_length=255, blank=True)
    philosophy_title = models.CharField(max_length=255, blank=True)
    philosophy_short_description = models.TextField(blank=True)
    philosophy_description = models.JSONField(default=dict, blank=True)
    philosophy_media = models.URLField(blank=True)

    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="about_page_singleton")]
