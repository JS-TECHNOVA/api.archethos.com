from django.db import models

from archethosbackend.apps.core.models import PublishableModel, TimeStampedModel


class Location(PublishableModel, TimeStampedModel):
    """A city the studio works from.

    Master content: the same location is listed on the home page preview, the
    about page and the locations page, and an address confirmed once should not
    have to be typed into three sections.

    Address, phone, email and map URL are all optional on purpose. The studio
    has confirmed the cities but not the premises, and a blank field renders as
    nothing rather than as a placeholder — never fill these with plausible
    values, they are the studio's to supply.
    """

    city = models.CharField(max_length=120)
    state = models.CharField(max_length=120, blank=True)
    #: An architectural annotation printed beside the city, not a map pin.
    coordinates = models.CharField(
        max_length=64, blank=True, help_text='e.g. "26.85° N / 80.95° E".'
    )
    blurb = models.TextField(blank=True)

    image = models.ForeignKey(
        "media_library.MediaAsset",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    address = models.TextField(blank=True)
    phone = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)
    map_url = models.URLField(blank=True)

    class Meta:
        ordering = ["city"]
        constraints = [
            models.UniqueConstraint(fields=["city"], name="unique_location_city"),
        ]

    def __str__(self):
        return self.city
