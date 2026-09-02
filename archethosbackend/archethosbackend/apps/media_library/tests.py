"""
Media Library tests.

The validation tests carry the weight here: an upload endpoint that trusts the
filename or the declared content type is a file-upload vulnerability, so the
suite asserts the bytes are actually checked.
"""

import io

from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from archethosbackend.apps.media_library.models import MediaAsset, MediaType, SourceType
from archethosbackend.apps.media_library.youtube import extract_video_id


def png_bytes(width=800, height=600, colour=(20, 40, 60)):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buffer, format="PNG")
    return buffer.getvalue()


def png_upload(name="villa.png", **kwargs):
    return SimpleUploadedFile(name, png_bytes(**kwargs), content_type="image/png")


class MediaTestCase(TestCase):
    password = "correct-horse-battery-staple"

    def make_user(self, email, *, superuser=False, permissions=()):
        user = User.objects.create_user(
            username=email, email=email, password=self.password
        )
        if superuser:
            user.is_superuser = user.is_staff = True
            user.save(update_fields=["is_superuser", "is_staff"])
        if permissions:
            user.user_permissions.add(
                *Permission.objects.filter(codename__in=permissions)
            )
        return User.objects.get(pk=user.pk)

    def client_for(self, user):
        client = Client()
        response = client.post(
            reverse("v1:auth:login"),
            {"email": user.email, "password": self.password},
            content_type="application/json",
        )
        assert response.status_code == 200, response.content
        return client


# ─── YouTube parsing (no DB, no HTTP) ────────────────────────────────────────


class YouTubeParsingTests(TestCase):
    def test_accepts_every_supported_url_shape(self):
        for url in [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ?t=42",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://www.youtube.com/live/dQw4w9WgXcQ",
            "https://www.youtube.com/v/dQw4w9WgXcQ",
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
        ]:
            with self.subTest(url=url):
                self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_rejects_lookalike_hosts(self):
        """A substring check for 'youtube' would accept these."""
        from django.core.exceptions import ValidationError

        for url in [
            "https://youtube.evil.example/watch?v=dQw4w9WgXcQ",
            "https://notyoutube.com/watch?v=dQw4w9WgXcQ",
            "https://vimeo.com/123456789",
            "javascript:alert(1)",
            "https://www.youtube.com/watch?v=short",
            "https://www.youtube.com/",
            "",
        ]:
            with self.subTest(url=url):
                with self.assertRaises(ValidationError):
                    extract_video_id(url)


# ─── Upload validation ───────────────────────────────────────────────────────


class UploadValidationTests(MediaTestCase):
    def setUp(self):
        self.client_ = self.client_for(
            self.make_user("uploader@archethos.test", superuser=True)
        )
        self.url = reverse("v1:admin:media-upload")

    def test_valid_image_upload_extracts_metadata(self):
        response = self.client_.post(
            self.url, {"file": png_upload(width=1200, height=800), "alt_text": "A villa"}
        )
        self.assertEqual(response.status_code, 201, response.content)

        data = response.json()["data"]
        self.assertEqual(data["media_type"], MediaType.IMAGE)
        self.assertEqual(data["width"], 1200)
        self.assertEqual(data["height"], 800)
        self.assertEqual(data["mime_type"], "image/png")
        self.assertEqual(data["alt_text"], "A villa")
        self.assertEqual(len(data["checksum"]), 64)

    def test_stored_path_is_relative_and_uuid_prefixed(self):
        response = self.client_.post(self.url, {"file": png_upload()})
        path = response.json()["data"]["path"]

        self.assertTrue(path.startswith("/media/uploads/"))
        self.assertTrue(path.endswith("-villa.png"))
        # No CDN domain is ever persisted.
        self.assertNotIn("http", path)

    def test_two_uploads_of_the_same_filename_do_not_collide(self):
        first = self.client_.post(self.url, {"file": png_upload(colour=(1, 2, 3))})
        second = self.client_.post(self.url, {"file": png_upload(colour=(9, 9, 9))})

        self.assertNotEqual(
            first.json()["data"]["path"], second.json()["data"]["path"]
        )
        self.assertEqual(MediaAsset.objects.count(), 2)

    def test_rejects_a_non_image_wearing_an_image_extension(self):
        """The whole point of verifying bytes rather than trusting the name."""
        payload = SimpleUploadedFile(
            "evil.jpg", b"<?php system($_GET['c']); ?>", content_type="image/jpeg"
        )
        response = self.client_.post(self.url, {"file": payload})

        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.json()["errors"])
        self.assertEqual(MediaAsset.objects.count(), 0)

    def test_rejects_a_disallowed_extension(self):
        payload = SimpleUploadedFile("run.exe", b"MZ\x90\x00", content_type="application/x-msdownload")
        response = self.client_.post(self.url, {"file": payload})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(MediaAsset.objects.count(), 0)

    def test_rejects_an_image_renamed_to_a_document_extension(self):
        payload = SimpleUploadedFile("sneaky.txt", png_bytes(), content_type="text/plain")
        response = self.client_.post(self.url, {"file": payload})
        self.assertEqual(response.status_code, 400)

    @override_settings(MAX_UPLOAD_SIZE_MB=0.0001)
    def test_rejects_an_oversize_file(self):
        response = self.client_.post(self.url, {"file": png_upload()})
        self.assertEqual(response.status_code, 400)
        self.assertIn("limit", str(response.json()["errors"]).lower())

    def test_rejects_an_empty_file(self):
        payload = SimpleUploadedFile("empty.png", b"", content_type="image/png")
        response = self.client_.post(self.url, {"file": payload})
        self.assertEqual(response.status_code, 400)

    def test_upload_requires_the_add_permission(self):
        viewer = self.make_user("viewer@archethos.test", permissions=["view_mediaasset"])
        response = self.client_for(viewer).post(self.url, {"file": png_upload()})
        self.assertEqual(response.status_code, 403)


# ─── YouTube endpoint ────────────────────────────────────────────────────────


class YouTubeEndpointTests(MediaTestCase):
    def setUp(self):
        self.client_ = self.client_for(
            self.make_user("uploader@archethos.test", superuser=True)
        )
        self.url = reverse("v1:admin:media-youtube")

    def test_creates_a_video_asset_with_canonical_url_and_thumbnail(self):
        response = self.client_.post(
            self.url,
            {"url": "https://youtu.be/dQw4w9WgXcQ?t=42", "title": "Studio film"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)

        data = response.json()["data"]
        self.assertEqual(data["media_type"], MediaType.VIDEO)
        self.assertEqual(data["source_type"], SourceType.YOUTUBE)
        self.assertEqual(data["external_id"], "dQw4w9WgXcQ")
        self.assertEqual(
            data["external_url"], "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        self.assertIn("dQw4w9WgXcQ", data["thumbnail_url"])

    def test_rejects_an_invalid_url(self):
        response = self.client_.post(
            self.url,
            {"url": "https://vimeo.com/123456789"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("url", response.json()["errors"])

    def test_rejects_the_same_video_twice_even_via_a_different_url_shape(self):
        self.client_.post(
            self.url,
            {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            content_type="application/json",
        )
        response = self.client_.post(
            self.url,
            {"url": "https://youtu.be/dQw4w9WgXcQ"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(MediaAsset.objects.count(), 1)


# ─── Listing, filtering, picker support ──────────────────────────────────────


class MediaListTests(MediaTestCase):
    def setUp(self):
        self.admin = self.make_user("root@archethos.test", superuser=True)
        self.client_ = self.client_for(self.admin)

        MediaAsset.objects.create(
            media_type=MediaType.IMAGE, source_type=SourceType.UPLOAD,
            file="uploads/a-villa.png", title="Villa exterior", alt_text="villa",
        )
        MediaAsset.objects.create(
            media_type=MediaType.IMAGE, source_type=SourceType.UPLOAD,
            file="uploads/b-office.png", title="Office interior",
        )
        MediaAsset.objects.create(
            media_type=MediaType.DOCUMENT, source_type=SourceType.UPLOAD,
            file="uploads/c-brochure.pdf", title="Brochure",
        )
        MediaAsset.objects.create(
            media_type=MediaType.VIDEO, source_type=SourceType.YOUTUBE,
            external_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            external_id="dQw4w9WgXcQ", title="Studio film",
        )

    def test_list_is_paginated_with_envelope(self):
        body = self.client_.get(reverse("v1:admin:media-list") + "?page_size=2").json()

        self.assertTrue(body["success"])
        self.assertEqual(len(body["data"]), 2)
        self.assertEqual(body["pagination"]["total_items"], 4)
        self.assertEqual(body["pagination"]["total_pages"], 2)

    def test_filter_by_media_type(self):
        body = self.client_.get(
            reverse("v1:admin:media-list") + "?media_type=IMAGE"
        ).json()
        self.assertEqual(body["pagination"]["total_items"], 2)

    def test_filter_by_source_type(self):
        body = self.client_.get(
            reverse("v1:admin:media-list") + "?source_type=YOUTUBE"
        ).json()
        self.assertEqual(body["pagination"]["total_items"], 1)

    def test_search_matches_title_and_alt_text(self):
        body = self.client_.get(reverse("v1:admin:media-list") + "?search=villa").json()
        self.assertEqual(body["pagination"]["total_items"], 1)

    def test_rows_carry_the_relative_path(self):
        body = self.client_.get(
            reverse("v1:admin:media-list") + "?search=Villa"
        ).json()
        self.assertEqual(body["data"][0]["path"], "/media/uploads/a-villa.png")

    def test_listing_requires_the_view_permission(self):
        nobody = self.make_user("nobody@archethos.test")
        response = self.client_for(nobody).get(reverse("v1:admin:media-list"))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_is_rejected(self):
        self.assertEqual(Client().get(reverse("v1:admin:media-list")).status_code, 401)


class MediaDetailTests(MediaTestCase):
    def setUp(self):
        self.client_ = self.client_for(
            self.make_user("root@archethos.test", superuser=True)
        )
        self.asset = MediaAsset.objects.create(
            media_type=MediaType.IMAGE, source_type=SourceType.UPLOAD,
            file="uploads/a-villa.png", title="Villa", checksum="a" * 64,
        )

    def test_only_descriptive_fields_are_editable(self):
        response = self.client_.patch(
            reverse("v1:admin:media-detail", args=[self.asset.pk]),
            {"title": "Renamed", "alt_text": "New alt", "file": "uploads/hacked.png"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        self.asset.refresh_from_db()
        self.assertEqual(self.asset.title, "Renamed")
        self.assertEqual(self.asset.alt_text, "New alt")
        # The file is immutable: swapping bytes under a stable id would silently
        # change every page referencing it.
        self.assertEqual(self.asset.file.name, "uploads/a-villa.png")

    def test_delete_removes_an_unused_asset(self):
        response = self.client_.delete(
            reverse("v1:admin:media-detail", args=[self.asset.pk])
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(MediaAsset.objects.filter(pk=self.asset.pk).exists())

    def test_usage_finds_content_that_references_the_asset(self):
        """Regression.

        Every media FK declares `related_name="+"`, so Django creates no reverse
        accessor and `_meta.related_objects` is empty. The first implementation
        walked that list and therefore always answered "used by 0" — while
        PROTECT was refusing the delete of the very same asset. The endpoint
        exists to warn before a delete, so answering zero was worse than not
        having it.
        """
        from archethosbackend.apps.content.models import Project, ProjectGalleryItem
        from archethosbackend.apps.sections.models import HeroSection, HeroSlide

        project = Project.objects.create(title="Villa", featured_image=self.asset)
        ProjectGalleryItem.objects.create(
            project=project, media=self.asset, order=0
        )
        hero = HeroSection.objects.create(internal_label="Home hero")
        HeroSlide.objects.create(section=hero, heading="Hi", media=self.asset, order=0)

        usage = self.asset.usage()
        found = {(row["model"], row["field"]) for row in usage}

        self.assertEqual(len(usage), 3, usage)
        self.assertIn(("project", "featured_image"), found)
        self.assertIn(("projectgalleryitem", "media"), found)
        self.assertIn(("heroslide", "media"), found)

    def test_usage_endpoint_agrees_with_what_delete_does(self):
        """The two must never contradict each other."""
        from archethosbackend.apps.content.models import Project

        Project.objects.create(title="Villa", featured_image=self.asset)

        body = self.client_.get(
            reverse("v1:admin:media-usage", args=[self.asset.pk])
        ).json()["data"]
        self.assertEqual(body["count"], 1)

        response = self.client_.delete(
            reverse("v1:admin:media-detail", args=[self.asset.pk])
        )
        self.assertEqual(response.status_code, 409)

    def test_usage_endpoint_reports_nothing_for_an_unused_asset(self):
        body = self.client_.get(
            reverse("v1:admin:media-usage", args=[self.asset.pk])
        ).json()["data"]
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["used_by"], [])

    def test_duplicate_check_finds_an_existing_asset(self):
        body = self.client_.get(
            reverse("v1:admin:media-check-duplicate") + f"?checksum={'a' * 64}"
        ).json()["data"]
        self.assertTrue(body["exists"])
        self.assertEqual(body["asset"]["id"], self.asset.pk)

    def test_duplicate_check_rejects_a_malformed_checksum(self):
        response = self.client_.get(
            reverse("v1:admin:media-check-duplicate") + "?checksum=nope"
        )
        self.assertEqual(response.status_code, 400)


# ─── MediaReferenceField ─────────────────────────────────────────────────────


class MediaReferenceFieldTests(TestCase):
    """Decision 2.1: FK in the database, relative path over the wire."""

    @classmethod
    def setUpTestData(cls):
        cls.asset = MediaAsset.objects.create(
            media_type=MediaType.IMAGE, source_type=SourceType.UPLOAD,
            file="uploads/abc123-hero.webp", alt_text="Hero", width=2400, height=1600,
        )
        cls.video = MediaAsset.objects.create(
            media_type=MediaType.VIDEO, source_type=SourceType.YOUTUBE,
            external_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            external_id="dQw4w9WgXcQ",
        )

    def field(self):
        from archethosbackend.apps.api.fields import MediaReferenceField

        return MediaReferenceField()

    def test_reads_as_a_relative_path(self):
        self.assertEqual(
            self.field().to_representation(self.asset), "/media/uploads/abc123-hero.webp"
        )

    def test_accepts_an_integer_id(self):
        self.assertEqual(self.field().to_internal_value(self.asset.pk), self.asset)

    def test_accepts_a_numeric_string_id(self):
        self.assertEqual(self.field().to_internal_value(str(self.asset.pk)), self.asset)

    def test_accepts_the_path_it_emitted(self):
        """A GET'd payload must PATCH back unchanged."""
        emitted = self.field().to_representation(self.asset)
        self.assertEqual(self.field().to_internal_value(emitted), self.asset)

    def test_accepts_a_path_without_the_media_prefix(self):
        self.assertEqual(
            self.field().to_internal_value("uploads/abc123-hero.webp"), self.asset
        )

    def test_accepts_a_youtube_url(self):
        self.assertEqual(
            self.field().to_internal_value("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            self.video,
        )

    def test_rejects_an_unknown_path(self):
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.field().to_internal_value("/media/uploads/does-not-exist.webp")

    def test_rejects_an_unknown_id(self):
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.field().to_internal_value(999999)

    def test_empty_becomes_none(self):
        self.assertIsNone(self.field().to_internal_value(""))
        self.assertIsNone(self.field().to_internal_value(None))
        self.assertIsNone(self.field().to_representation(None))
