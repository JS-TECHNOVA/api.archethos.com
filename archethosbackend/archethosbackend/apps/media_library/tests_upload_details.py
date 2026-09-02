"""
Descriptive metadata supplied at creation time.

Upload, YouTube and update all share `DescriptiveFieldsMixin`, so these tests
check the three accept the same fields with the same rules — the failure mode
being that one of them quietly drifts and starts ignoring, say, tags.
"""

import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from PIL import Image

from archethosbackend.apps.media_library.models import MediaAsset

FULL_DETAILS = {
    "title": "Courtyard at dusk",
    "alt_text": "A brick courtyard in evening light",
    "caption": "Photographed on handover day.",
    "description": "Shot by the studio. Cleared for web use.",
}


def png_upload(name="villa.png", width=800, height=600):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (20, 40, 60)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class UploadDetailsTests(TestCase):
    password = "correct-horse-battery-staple"

    def setUp(self):
        user = User.objects.create_user(
            username="root@archethos.test",
            email="root@archethos.test",
            password=self.password,
            is_superuser=True,
            is_staff=True,
        )
        self.client_ = Client()
        assert self.client_.post(
            reverse("v1:auth:login"),
            {"email": user.email, "password": self.password},
            content_type="application/json",
        ).status_code == 200

    def upload(self, **extra):
        """multipart, so lists arrive the way a browser sends them."""
        payload = {"file": png_upload(), **extra}
        return self.client_.post(reverse("v1:admin:media-upload"), payload)

    # ── upload ──

    def test_every_descriptive_field_can_be_set_at_upload(self):
        response = self.upload(**FULL_DETAILS, tags=["Villa", "Lucknow"])
        self.assertEqual(response.status_code, 201, response.content)

        data = response.json()["data"]
        for field, value in FULL_DETAILS.items():
            self.assertEqual(data[field], value, field)
        self.assertEqual(data["tags"], ["villa", "lucknow"])

    def test_they_are_all_optional(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201)

        data = response.json()["data"]
        self.assertEqual(data["caption"], "")
        self.assertEqual(data["description"], "")
        self.assertEqual(data["tags"], [])

    def test_title_falls_back_to_the_filename(self):
        """An asset with no title is unfindable in the picker."""
        data = self.upload().json()["data"]
        self.assertEqual(data["title"], "villa.png")

    def test_an_explicit_title_wins_over_the_filename(self):
        data = self.upload(title="Courtyard").json()["data"]
        self.assertEqual(data["title"], "Courtyard")

    def test_tags_are_normalised_at_upload_too(self):
        """Same rule as PATCH — case-folded, trimmed, de-duplicated."""
        data = self.upload(tags=["Villa", "villa", "  LUCKNOW  "]).json()["data"]
        self.assertEqual(data["tags"], ["villa", "lucknow"])

    def test_bad_tags_are_rejected_before_the_file_is_stored(self):
        response = self.client_.post(
            reverse("v1:admin:media-upload"),
            {"file": png_upload(), "tags": ["x" * 80]},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("tags", response.json()["errors"])
        self.assertEqual(MediaAsset.objects.count(), 0)

    def test_an_invalid_file_is_still_rejected_with_details_present(self):
        """Metadata must never make a bad file acceptable."""
        response = self.client_.post(
            reverse("v1:admin:media-upload"),
            {
                "file": SimpleUploadedFile(
                    "evil.jpg", b"<?php echo 1; ?>", content_type="image/jpeg"
                ),
                **FULL_DETAILS,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(MediaAsset.objects.count(), 0)

    # ── youtube ──

    def test_youtube_accepts_the_same_fields(self):
        response = self.client_.post(
            reverse("v1:admin:media-youtube"),
            {
                "url": "https://youtu.be/dQw4w9WgXcQ",
                **FULL_DETAILS,
                "tags": ["Film", "studio"],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)

        data = response.json()["data"]
        self.assertEqual(data["caption"], FULL_DETAILS["caption"])
        self.assertEqual(data["description"], FULL_DETAILS["description"])
        self.assertEqual(data["tags"], ["film", "studio"])

    def test_youtube_title_falls_back_to_the_video_id(self):
        data = self.client_.post(
            reverse("v1:admin:media-youtube"),
            {"url": "https://youtu.be/dQw4w9WgXcQ"},
            content_type="application/json",
        ).json()["data"]
        self.assertEqual(data["title"], "YouTube video dQw4w9WgXcQ")

    # ── the three stay in step ──

    def test_upload_and_update_accept_the_same_field_set(self):
        """They share one mixin; this fails if either grows a field alone."""
        from archethosbackend.apps.media_library.serializers import (
            DESCRIPTIVE_FIELDS,
            MediaAssetUpdateSerializer,
            MediaUploadSerializer,
            YouTubeCreateSerializer,
        )

        expected = set(DESCRIPTIVE_FIELDS)
        for serializer in (
            MediaUploadSerializer,
            YouTubeCreateSerializer,
            MediaAssetUpdateSerializer,
        ):
            with self.subTest(serializer=serializer.__name__):
                self.assertTrue(
                    expected.issubset(set(serializer().fields)),
                    f"{serializer.__name__} is missing "
                    f"{expected - set(serializer().fields)}",
                )


class MediaLocationTests(TestCase):
    """Where the bytes live — separate from how the asset was created."""

    password = "correct-horse-battery-staple"

    def setUp(self):
        user = User.objects.create_user(
            username="root@archethos.test",
            email="root@archethos.test",
            password=self.password,
            is_superuser=True,
            is_staff=True,
        )
        self.client_ = Client()
        assert self.client_.post(
            reverse("v1:auth:login"),
            {"email": user.email, "password": self.password},
            content_type="application/json",
        ).status_code == 200

    def test_an_upload_defaults_to_local(self):
        data = self.client_.post(
            reverse("v1:admin:media-upload"), {"file": png_upload()}
        ).json()["data"]
        self.assertEqual(data["media_location"], "local")

    def test_a_youtube_asset_is_external(self):
        """It has no local file, so claiming local disk would be untrue."""
        data = self.client_.post(
            reverse("v1:admin:media-youtube"),
            {"url": "https://youtu.be/dQw4w9WgXcQ"},
            content_type="application/json",
        ).json()["data"]
        self.assertEqual(data["media_location"], "external")

    def test_it_cannot_be_changed_through_the_api(self):
        """Storage location is a fact, not an editor's choice — it changes when
        files actually move, which is a management command's job."""
        asset = self.client_.post(
            reverse("v1:admin:media-upload"), {"file": png_upload()}
        ).json()["data"]

        self.client_.patch(
            reverse("v1:admin:media-detail", args=[asset["id"]]),
            {"media_location": "s3"},
            content_type="application/json",
        )
        self.assertEqual(
            MediaAsset.objects.get(pk=asset["id"]).media_location, "local"
        )

    def test_filtering_answers_what_is_left_to_move(self):
        self.client_.post(reverse("v1:admin:media-upload"), {"file": png_upload()})
        self.client_.post(
            reverse("v1:admin:media-youtube"),
            {"url": "https://youtu.be/dQw4w9WgXcQ"},
            content_type="application/json",
        )

        local = self.client_.get(
            reverse("v1:admin:media-list") + "?media_location=local"
        ).json()
        external = self.client_.get(
            reverse("v1:admin:media-list") + "?media_location=external"
        ).json()

        self.assertEqual(local["pagination"]["total_items"], 1)
        self.assertEqual(external["pagination"]["total_items"], 1)
