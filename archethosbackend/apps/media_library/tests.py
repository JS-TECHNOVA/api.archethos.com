from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from .models import MediaAsset


class MediaLibraryAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "media-admin", password="test", is_staff=True
        )
        self.client.force_authenticate(self.user)
        MediaAsset.objects.create(
            title="Courtyard", media_type="image", file_name="courtyard.jpg", uploaded_by=self.user
        )
        MediaAsset.objects.create(
            title="Walkthrough", media_type="video", file_name="walkthrough.mp4", uploaded_by=self.user
        )

    def test_media_list_filters_searches_and_paginates(self):
        response = self.client.get("/api/v1/media/?media_type=IMAGES&search=court&page_size=1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Courtyard")

    def test_upload_uses_file_and_thumbnail_file(self):
        response = self.client.post(
            "/api/v1/media/",
            {
                "file": SimpleUploadedFile("walkthrough.mp4", b"video", content_type="video/mp4"),
                "thumbnail_file": SimpleUploadedFile("walkthrough.jpg", b"image", content_type="image/jpeg"),
                "title": "Walkthrough",
                "tags": "site, film",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["media_type"], "video")
        self.assertEqual(response.data["tags"], "site, film")
        self.assertIn("walkthrough", response.data["source"])
        self.assertTrue(response.data["source"].endswith(".mp4"))
        self.assertIn("walkthrough", response.data["thumbnail_url"])
        self.assertTrue(response.data["thumbnail_url"].endswith(".jpg"))
