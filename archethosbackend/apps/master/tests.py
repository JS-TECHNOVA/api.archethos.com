from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.media_library.models import MediaAsset
from apps.master.models import FAQ, Gallery, GalleryItem


class BlogAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("editor", password="test")
        self.client.force_authenticate(self.user)

    def test_blog_list_is_paginated_and_uses_a_media_asset(self):
        category = self.client.post("/api/v1/categories/", {"name": "Design"}, format="json")
        image = MediaAsset.objects.create(file="media/blog-cover.jpg", uploaded_by=self.user)
        blog = self.client.post(
            "/api/v1/blogs/",
            {
                "title": "A better courtyard",
                "excerpt": "A compact look at the redesigned courtyard.",
                "content": "Article body",
                "category": category.data["id"],
                "featured_image": image.id,
                "status": "published",
            },
            format="json",
        )
        self.assertEqual(blog.status_code, status.HTTP_201_CREATED)
        self.assertEqual(blog.data["featured_image"], image.id)
        self.assertEqual(blog.data["slug"], "a-better-courtyard")
        self.assertEqual(blog.data["excerpt"], "A compact look at the redesigned courtyard.")
        self.assertIsNotNone(blog.data["published_at"])

        blogs_page = self.client.get("/api/v1/blogs/page/")
        self.assertEqual(blogs_page.status_code, status.HTTP_200_OK)
        self.assertEqual(blogs_page.data["id"], 1)
        blogs_page = self.client.patch(
            "/api/v1/blogs/page/",
            {"hero_title": "Stories", "featured_blogs": [blog.data["id"]]},
            format="json",
        )
        self.assertEqual(blogs_page.status_code, status.HTTP_200_OK)
        self.assertEqual(blogs_page.data["featured_blogs"], [blog.data["id"]])
        self.assertEqual(blogs_page.data["featured_blogs_detail"][0]["slug"], "a-better-courtyard")

        public_client = APIClient()
        public_page = public_client.get("/api/v1/public/blog/page/")
        self.assertEqual(public_page.status_code, status.HTTP_200_OK)
        self.assertEqual(public_page.data["featured_blogs"][0]["slug"], "a-better-courtyard")

        public_blogs = public_client.get("/api/v1/public/blogs/?search=courtyard&page_size=1")
        self.assertEqual(public_blogs.status_code, status.HTTP_200_OK)
        self.assertEqual(public_blogs.data["count"], 1)
        self.assertEqual(public_blogs.data["results"][0]["slug"], "a-better-courtyard")
        public_blog = public_client.get("/api/v1/public/blogs/a-better-courtyard/")
        self.assertEqual(public_blog.status_code, status.HTTP_200_OK)
        self.assertEqual(public_blog.data["title"], "A better courtyard")

        listing = self.client.get("/api/v1/blogs/?page_size=1")
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(listing.data["results"][0]["id"], blog.data["id"])

        filtered = self.client.get(
            f"/api/v1/blogs/?category={category.data['id']}&status=published&slug=a-better-courtyard"
        )
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(filtered.data["count"], 1)

        comment = self.client.post(
            f"/api/v1/blogs/{blog.data['id']}/comments/", {"content": "Great read."}, format="json"
        )
        self.assertEqual(comment.status_code, status.HTTP_201_CREATED)
        self.assertEqual(comment.data["author"], self.user.id)

        comments = self.client.get(f"/api/v1/blogs/{blog.data['id']}/comments/?author={self.user.id}")
        self.assertEqual(comments.status_code, status.HTTP_200_OK)
        self.assertEqual(len(comments.data), 1)

    def test_swagger_schema_is_available(self):
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("/api/v1/blogs/", response.data["paths"])

    def test_faq_crud(self):
        created = self.client.post(
            "/api/v1/faqs/",
            {"question": "Do you work internationally?", "answer": "Yes.", "order": 1},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        updated = self.client.patch(
            f"/api/v1/faqs/{created.data['id']}/", {"is_active": False}, format="json"
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertFalse(updated.data["is_active"])

        filtered = self.client.get("/api/v1/faqs/?is_active=false")
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(len(filtered.data), 1)

        FAQ.objects.create(question="How do projects begin?", answer="With a conversation.")
        public_client = APIClient()
        public_faqs = public_client.get("/api/v1/public/faqs/")
        self.assertEqual(public_faqs.status_code, status.HTTP_200_OK)
        self.assertEqual([faq["question"] for faq in public_faqs.data], ["How do projects begin?"])
        self.assertIn(
            public_client.post("/api/v1/faqs/", {"question": "No", "answer": "No"}).status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_gallery_items_are_paginated_and_use_media_assets(self):
        Gallery.objects.all().delete()
        self.assertEqual(Gallery.objects.count(), 0)

        gallery = self.client.get("/api/v1/gallery/")
        self.assertEqual(gallery.status_code, status.HTTP_200_OK)
        self.assertEqual(gallery.data["id"], Gallery.SINGLETON_PK)

        gallery = self.client.patch(
            "/api/v1/gallery/",
            {"meta_title": "Gallery", "meta_description": "Project photography."},
            format="json",
        )
        self.assertEqual(gallery.status_code, status.HTTP_200_OK)
        self.assertEqual(Gallery.objects.count(), 1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Gallery.objects.create()

        first_category = self.client.post(
            "/api/v1/gallery/categories/", {"name": "Residential", "order": 1}, format="json"
        )
        self.assertEqual(first_category.status_code, status.HTTP_201_CREATED)
        second_category = self.client.post(
            "/api/v1/gallery/categories/", {"name": "Commercial", "order": 2}, format="json"
        )
        self.assertEqual(second_category.status_code, status.HTTP_201_CREATED)

        first_asset = MediaAsset.objects.create(file="media/gallery-one.jpg", uploaded_by=self.user)
        second_asset = MediaAsset.objects.create(file="media/gallery-two.jpg", uploaded_by=self.user)

        gallery = self.client.patch(
            "/api/v1/gallery/",
            {
                "hero_title": "Every frame we've kept.",
                "hero_description": "Buildings, rooms, sites and details.",
                "hero_image": first_asset.id,
            },
            format="json",
        )
        self.assertEqual(gallery.status_code, status.HTTP_200_OK)
        self.assertEqual(gallery.data["hero_image"], first_asset.id)
        self.assertEqual(gallery.data["hero_image_detail"]["id"], first_asset.id)

        public_client = APIClient()
        self.assertEqual(public_client.get("/api/v1/gallery/").status_code, status.HTTP_200_OK)
        self.assertEqual(public_client.get("/api/v1/gallery/categories/").status_code, status.HTTP_200_OK)

        first_item = self.client.post(
            "/api/v1/gallery/items/",
            {
                "category": first_category.data["id"],
                "asset": first_asset.id,
                "title": "Courtyard",
                "description": "A shaded courtyard.",
                "order": 1,
            },
            format="json",
        )
        self.assertEqual(first_item.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first_item.data["added_by"], self.user.id)
        self.assertEqual(first_item.data["title"], "Courtyard")

        self.client.post(
            "/api/v1/gallery/items/",
            {
                "category": second_category.data["id"],
                "asset": second_asset.id,
                "title": "Lobby",
                "order": 2,
                "is_visible": False,
            },
            format="json",
        )
        listing = self.client.get("/api/v1/gallery/items/?page_size=1")
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(listing.data["results"][0]["asset"], first_asset.id)

        filtered = self.client.get(
            f"/api/v1/gallery/items/?category={first_category.data['id']}&is_visible=true"
        )
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(filtered.data["count"], 1)
        self.assertEqual(filtered.data["results"][0]["id"], first_item.data["id"])

        public_client = APIClient()
        hidden_for_public = public_client.get("/api/v1/gallery/items/?is_visible=false")
        self.assertEqual(hidden_for_public.status_code, status.HTTP_200_OK)
        self.assertEqual(hidden_for_public.data["count"], 0)

        staff = get_user_model().objects.create_user("gallery-admin", password="test", is_staff=True)
        staff_client = APIClient()
        staff_client.force_authenticate(staff)
        hidden_for_staff = staff_client.get("/api/v1/gallery/items/?is_visible=false")
        self.assertEqual(hidden_for_staff.status_code, status.HTTP_200_OK)
        self.assertEqual(hidden_for_staff.data["count"], 1)

        public_gallery_page = public_client.get("/api/v1/public/gallery/page/")
        self.assertEqual(public_gallery_page.status_code, status.HTTP_200_OK)
        self.assertEqual(public_gallery_page.data["hero_title"], "Every frame we've kept.")
        public_gallery_items = public_client.get("/api/v1/public/gallery/?page_size=1&search=courtyard")
        self.assertEqual(public_gallery_items.status_code, status.HTTP_200_OK)
        self.assertEqual(public_gallery_items.data["count"], 1)
        self.assertEqual(public_gallery_items.data["results"][0]["id"], first_item.data["id"])

        first_asset.delete()
        self.assertIsNone(GalleryItem.objects.get(pk=first_item.data["id"]).asset_id)
        gallery = Gallery.objects.get(pk=Gallery.SINGLETON_PK)
        self.assertIsNone(gallery.hero_image_id)
