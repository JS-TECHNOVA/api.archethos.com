"""
Editing an asset's details, and replacing its file in place.

Replace is the risky one: it writes over bytes that live pages are already
serving, so the tests pin what must survive (identity, path, description) and
what must not be possible (a different extension, a non-image, a YouTube asset).
"""

import io

from django.contrib.auth.models import Permission, User
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from PIL import Image

from archethosbackend.apps.media_library.models import (
    MediaAsset,
    MediaType,
    SourceType,
)

PHP_PAYLOAD = b"<?php system($_GET['c']); ?>"


def png_bytes(width=800, height=600, colour=(20, 40, 60)):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buffer, format="PNG")
    return buffer.getvalue()


def png_upload(name="villa.png", **kwargs):
    return SimpleUploadedFile(name, png_bytes(**kwargs), content_type="image/png")


class MediaBaseTestCase(TestCase):
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

    def admin_client(self):
        return self.client_for(self.make_user("root@archethos.test", superuser=True))


# ─── Descriptive fields ──────────────────────────────────────────────────────


class MediaDetailsTests(MediaBaseTestCase):
    def setUp(self):
        self.client_ = self.admin_client()
        self.asset = self.client_.post(
            reverse("v1:admin:media-upload"), {"file": png_upload()}
        ).json()["data"]

    def patch(self, payload):
        return self.client_.patch(
            reverse("v1:admin:media-detail", args=[self.asset["id"]]),
            payload,
            content_type="application/json",
        )

    def test_all_descriptive_fields_are_editable(self):
        response = self.patch(
            {
                "title": "Courtyard at dusk",
                "alt_text": "A brick courtyard in evening light",
                "caption": "Photographed on handover day.",
                "description": "Shot by the studio. Cleared for web use.",
                "tags": ["Villa", "courtyard", "  Lucknow  "],
            }
        )
        self.assertEqual(response.status_code, 200, response.content)

        data = response.json()["data"]
        self.assertEqual(data["title"], "Courtyard at dusk")
        self.assertEqual(data["alt_text"], "A brick courtyard in evening light")
        self.assertEqual(data["caption"], "Photographed on handover day.")
        self.assertIn("Cleared for web use", data["description"])

    def test_tags_are_normalised(self):
        """Case-folded and trimmed, so "Villa" and "villa" are one tag."""
        data = self.patch({"tags": ["Villa", "villa", "  LUCKNOW  ", ""]}).json()["data"]
        self.assertEqual(data["tags"], ["villa", "lucknow"])

    def test_tags_reject_non_text(self):
        response = self.patch({"tags": ["ok", 42]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("tags", response.json()["errors"])

    def test_too_many_tags_are_rejected(self):
        response = self.patch({"tags": [f"tag{i}" for i in range(40)]})
        self.assertEqual(response.status_code, 400)

    def test_the_file_cannot_be_changed_through_patch(self):
        """Swapping bytes is a separate, deliberate action with its own endpoint."""
        original = MediaAsset.objects.get(pk=self.asset["id"]).file.name
        self.patch({"file": "uploads/hacked.png", "checksum": "0" * 64})

        current = MediaAsset.objects.get(pk=self.asset["id"])
        self.assertEqual(current.file.name, original)
        self.assertNotEqual(current.checksum, "0" * 64)

    def test_filter_by_tag_is_case_insensitive(self):
        self.patch({"tags": ["villa"]})
        body = self.client_.get(reverse("v1:admin:media-list") + "?tag=Villa").json()
        self.assertEqual(body["pagination"]["total_items"], 1)

    def test_search_covers_caption_and_description(self):
        self.patch({"caption": "handover day", "description": "cleared for web"})
        for term in ("handover", "cleared"):
            with self.subTest(term=term):
                body = self.client_.get(
                    reverse("v1:admin:media-list") + f"?search={term}"
                ).json()
                self.assertEqual(body["pagination"]["total_items"], 1)


# ─── Replace ─────────────────────────────────────────────────────────────────


class MediaReplaceTests(MediaBaseTestCase):
    def setUp(self):
        self.client_ = self.admin_client()

        created = self.client_.post(
            reverse("v1:admin:media-upload"),
            {"file": png_upload("villa.png", width=800, height=600)},
        ).json()["data"]

        self.client_.patch(
            reverse("v1:admin:media-detail", args=[created["id"]]),
            {
                "title": "Villa",
                "alt_text": "The villa",
                "caption": "At dusk",
                "description": "Studio photo",
                "tags": ["villa"],
            },
            content_type="application/json",
        )
        self.asset = MediaAsset.objects.get(pk=created["id"])

    def replace(self, upload, client=None):
        return (client or self.client_).post(
            reverse("v1:admin:media-replace", args=[self.asset.pk]), {"file": upload}
        )

    def test_identity_and_every_descriptive_field_survive(self):
        """The whole point: nothing referencing this asset has to be repointed."""
        original_path = self.asset.file.name
        original_checksum = self.asset.checksum

        response = self.replace(png_upload("different.png", width=1600, height=900))
        self.assertEqual(response.status_code, 200, response.content)

        self.asset.refresh_from_db()
        self.assertEqual(self.asset.file.name, original_path)
        self.assertEqual(self.asset.title, "Villa")
        self.assertEqual(self.asset.alt_text, "The villa")
        self.assertEqual(self.asset.caption, "At dusk")
        self.assertEqual(self.asset.description, "Studio photo")
        self.assertEqual(self.asset.tags, ["villa"])

        # Everything derived from the bytes is recomputed.
        self.assertEqual((self.asset.width, self.asset.height), (1600, 900))
        self.assertNotEqual(self.asset.checksum, original_checksum)
        self.assertEqual(self.asset.file_name, "different.png")

    def test_the_bytes_on_disk_actually_change(self):
        before = self.asset.file.read()
        self.asset.file.close()

        self.replace(png_upload("new.png", width=400, height=300, colour=(200, 30, 30)))

        self.asset.refresh_from_db()
        after = self.asset.file.read()
        self.asset.file.close()
        self.assertNotEqual(before, after)

    def test_no_orphan_file_is_left_behind(self):
        """`save()` without deleting first appends a suffix and strands the
        original, leaving two files and an asset pointing at the stale one."""
        before = set(default_storage.listdir("uploads")[1])
        self.replace(png_upload("new.png"))
        after = set(default_storage.listdir("uploads")[1])

        self.assertEqual(before, after)

    def test_a_different_extension_is_refused(self):
        """The path is kept, so a JPEG written to a .png path would be served
        under the wrong extension for the rest of its life."""
        jpeg = io.BytesIO()
        Image.new("RGB", (400, 300), (10, 20, 30)).save(jpeg, format="JPEG")
        upload = SimpleUploadedFile(
            "swap.jpg", jpeg.getvalue(), content_type="image/jpeg"
        )

        response = self.replace(upload)
        self.assertEqual(response.status_code, 400)
        self.assertIn(".png", response.json()["message"])

    def test_a_non_image_is_refused_even_with_the_right_extension(self):
        upload = SimpleUploadedFile("villa.png", PHP_PAYLOAD, content_type="image/png")
        response = self.replace(upload)
        self.assertEqual(response.status_code, 400)

    def test_a_failed_replace_leaves_the_original_intact(self):
        original = self.asset.file.read()
        self.asset.file.close()

        self.replace(SimpleUploadedFile("villa.png", PHP_PAYLOAD, content_type="image/png"))

        self.asset.refresh_from_db()
        current = self.asset.file.read()
        self.asset.file.close()
        self.assertEqual(current, original)

    def test_a_youtube_asset_cannot_be_replaced(self):
        video = MediaAsset.objects.create(
            media_type=MediaType.VIDEO,
            source_type=SourceType.YOUTUBE,
            external_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            external_id="dQw4w9WgXcQ",
        )
        response = self.client_.post(
            reverse("v1:admin:media-replace", args=[video.pk]), {"file": png_upload()}
        )
        self.assertEqual(response.status_code, 400)

    def test_replacing_needs_the_change_permission(self):
        viewer = self.make_user("viewer@archethos.test", permissions=["view_mediaasset"])
        response = self.replace(png_upload(), client=self.client_for(viewer))
        self.assertEqual(response.status_code, 403)

    def test_references_keep_resolving_after_a_replace(self):
        """A project pointing at this asset still resolves — same id, same path."""
        from archethosbackend.apps.content.models import Project

        project = Project.objects.create(title="Villa", featured_image=self.asset)
        path_before = self.asset.relative_path

        self.replace(png_upload("new.png", width=1000, height=1000))

        project.refresh_from_db()
        self.assertEqual(project.featured_image_id, self.asset.pk)
        self.assertEqual(project.featured_image.relative_path, path_before)
