from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


class ResetRouteTests(APITestCase):
    def test_auth_and_media_routes(self):
        self.assertEqual(self.client.get("/api/v1/auth/csrf/").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get("/api/v1/media/").status_code, status.HTTP_401_UNAUTHORIZED)

        user = get_user_model().objects.create_user("editor", password="test", is_staff=True)
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get("/api/v1/media/").status_code, status.HTTP_200_OK)

        response = self.client.post(
            "/api/v1/media/",
            {"youtube_url": "https://www.youtube.com/watch?v=G8nlbcmDXNE", "tags": "video, hero"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["file"])
        self.assertEqual(response.data["source_type"], "YOUTUBE")
        self.assertEqual(response.data["external_id"], "G8nlbcmDXNE")
        self.assertEqual(response.data["source"], "https://www.youtube.com/watch?v=G8nlbcmDXNE")
        self.assertIsNone(response.data["media_location"])
        self.assertEqual(
            response.data["thumbnail_url"],
            "https://i.ytimg.com/vi/G8nlbcmDXNE/maxresdefault.jpg",
        )

        listing = self.client.get(
            "/api/v1/media/?page=1&page_size=1&media_type=images,videos&source_type=youtube&tags=hero&ordering=-created"
        )
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(len(listing.data["results"]), 1)

    def test_api_docs_ignore_an_invalid_access_cookie(self):
        self.client.cookies["access_token"] = "invalid"

        self.assertEqual(self.client.get("/api/docs/").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get("/api/schema/?format=json").status_code, status.HTTP_200_OK)
