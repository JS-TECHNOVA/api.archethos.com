"""
Master content tests.

The public-exposure tests matter most: the single worst failure mode of this API
is a draft or archived record reaching the public endpoints.
"""

from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from archethosbackend.apps.core.models import PublishStatus
from archethosbackend.apps.media_library.models import MediaAsset, MediaType, SourceType

from .models import FAQ, BlogCategory, BlogPost, Counter, Project, ProjectGalleryItem, Service


class ContentTestCase(TestCase):
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

    def make_media(self, name="hero.png"):
        return MediaAsset.objects.create(
            media_type=MediaType.IMAGE,
            source_type=SourceType.UPLOAD,
            file=f"uploads/{name}",
            alt_text="An image",
        )


# ─── Publishing ──────────────────────────────────────────────────────────────


class PublishingTests(ContentTestCase):
    def test_published_at_is_stamped_once_and_never_overwritten(self):
        service = Service.objects.create(title="Architecture")
        self.assertIsNone(service.published_at)

        service.status = PublishStatus.PUBLISHED
        service.save()
        first = service.published_at
        self.assertIsNotNone(first)

        service.title = "Architecture & Design"
        service.save()
        service.refresh_from_db()
        self.assertEqual(service.published_at, first)

    def test_live_excludes_draft_archived_and_future(self):
        Service.objects.create(title="Draft one")
        Service.objects.create(title="Archived", status=PublishStatus.ARCHIVED)
        Service.objects.create(title="Live", status=PublishStatus.PUBLISHED)
        Service.objects.create(
            title="Scheduled",
            status=PublishStatus.PUBLISHED,
            published_at=timezone.now() + timezone.timedelta(days=7),
        )

        live = list(Service.objects.live().values_list("title", flat=True))
        self.assertEqual(live, ["Live"])

    def test_slug_is_generated_and_deduplicated(self):
        a = Project.objects.create(title="Modern Residence")
        b = Project.objects.create(title="Modern Residence")
        self.assertEqual(a.slug, "modern-residence")
        self.assertEqual(b.slug, "modern-residence-2")

    def test_slug_is_not_regenerated_when_the_title_changes(self):
        """A published URL must not break because someone fixed a typo."""
        project = Project.objects.create(title="Moderrn Residence")
        original = project.slug

        project.title = "Modern Residence"
        project.save()
        project.refresh_from_db()
        self.assertEqual(project.slug, original)

    def test_reading_time_is_derived_from_the_body(self):
        post = BlogPost.objects.create(title="Light", content=" ".join(["w"] * 400))
        self.assertEqual(post.reading_time, 2)


# ─── Public exposure ─────────────────────────────────────────────────────────


class PublicExposureTests(ContentTestCase):
    """Nothing unpublished may ever be reachable publicly."""

    def setUp(self):
        self.live_project = Project.objects.create(
            title="Live Villa", status=PublishStatus.PUBLISHED
        )
        self.draft_project = Project.objects.create(title="Secret Villa")
        self.archived_project = Project.objects.create(
            title="Old Villa", status=PublishStatus.ARCHIVED
        )

    def test_list_shows_only_live_records(self):
        body = Client().get(reverse("v1:public:project-list")).json()
        titles = [row["title"] for row in body["data"]]
        self.assertEqual(titles, ["Live Villa"])

    def test_draft_detail_is_404_not_403(self):
        response = Client().get(
            reverse("v1:public:project-detail", args=[self.draft_project.slug])
        )
        self.assertEqual(response.status_code, 404)

    def test_archived_detail_is_404(self):
        response = Client().get(
            reverse("v1:public:project-detail", args=[self.archived_project.slug])
        )
        self.assertEqual(response.status_code, 404)

    def test_live_detail_is_reachable(self):
        response = Client().get(
            reverse("v1:public:project-detail", args=[self.live_project.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("seo", response.json()["data"])

    def test_public_payload_omits_admin_fields(self):
        data = Client().get(
            reverse("v1:public:project-detail", args=[self.live_project.slug])
        ).json()["data"]

        for leaked in ("status", "created_at", "updated_at", "meta_title"):
            self.assertNotIn(leaked, data, f"{leaked} must not reach the public API")

    def test_a_draft_service_is_hidden_even_when_linked_from_a_live_project(self):
        draft = Service.objects.create(title="Unannounced Service")
        live = Service.objects.create(title="Architecture", status=PublishStatus.PUBLISHED)
        self.live_project.services.add(draft, live)

        data = Client().get(
            reverse("v1:public:project-detail", args=[self.live_project.slug])
        ).json()["data"]

        titles = [s["title"] for s in data["services"]]
        self.assertEqual(titles, ["Architecture"])

    def test_public_blog_detail_never_exposes_the_author_email(self):
        author = self.make_user("writer@archethos.test")
        author.first_name, author.last_name = "Ed", "Itor"
        author.save()
        post = BlogPost.objects.create(
            title="On Light", status=PublishStatus.PUBLISHED, author=author
        )

        data = Client().get(
            reverse("v1:public:blog-detail", args=[post.slug])
        ).json()["data"]

        self.assertEqual(data["author_name"], "Ed Itor")
        self.assertNotIn("author_email", data)
        self.assertNotIn("writer@archethos.test", str(data))

    def test_public_endpoints_need_no_authentication(self):
        for name in ("project-list", "service-list", "blog-list", "faq-list", "counter-list"):
            with self.subTest(endpoint=name):
                self.assertEqual(
                    Client().get(reverse(f"v1:public:{name}")).status_code, 200
                )


# ─── Admin CRUD and permissions ──────────────────────────────────────────────


class AdminContentTests(ContentTestCase):
    def setUp(self):
        self.admin = self.make_user("root@archethos.test", superuser=True)
        self.client_ = self.client_for(self.admin)

    def test_create_project_with_media_by_path(self):
        media = self.make_media()
        response = self.client_.post(
            reverse("v1:admin:project-list"),
            {"title": "Hillside House", "featured_image": media.relative_path},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)

        project = Project.objects.get(title="Hillside House")
        self.assertEqual(project.featured_image, media)

    def test_create_project_with_media_by_id(self):
        media = self.make_media()
        response = self.client_.post(
            reverse("v1:admin:project-list"),
            {"title": "Courtyard House", "featured_image": media.pk},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Project.objects.get(title="Courtyard House").featured_image, media)

    def test_unknown_media_path_is_rejected(self):
        response = self.client_.post(
            reverse("v1:admin:project-list"),
            {"title": "Ghost House", "featured_image": "/media/uploads/nope.webp"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("featured_image", response.json()["errors"])

    def test_media_round_trips_unchanged(self):
        """A GET'd payload must PATCH back without the client rewriting it."""
        media = self.make_media()
        project = Project.objects.create(title="Round Trip", featured_image=media)

        fetched = self.client_.get(
            reverse("v1:admin:project-detail", args=[project.pk])
        ).json()["data"]

        response = self.client_.patch(
            reverse("v1:admin:project-detail", args=[project.pk]),
            {"featured_image": fetched["featured_image"]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        project.refresh_from_db()
        self.assertEqual(project.featured_image, media)

    def test_in_use_media_cannot_be_deleted(self):
        media = self.make_media()
        Project.objects.create(title="Uses It", featured_image=media)

        response = self.client_.delete(
            reverse("v1:admin:media-detail", args=[media.pk])
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "protected")
        self.assertIn("Uses It", response.json()["message"])

    def test_list_is_light_and_detail_is_full(self):
        Project.objects.create(title="Villa")
        row = self.client_.get(reverse("v1:admin:project-list")).json()["data"][0]
        self.assertNotIn("gallery_items", row)
        self.assertNotIn("description", row)
        self.assertIn("gallery_count", row)

        detail = self.client_.get(
            reverse("v1:admin:project-detail", args=[Project.objects.first().pk])
        ).json()["data"]
        self.assertIn("gallery_items", detail)
        self.assertIn("meta_title", detail)

    def test_publish_and_unpublish_endpoints(self):
        post = BlogPost.objects.create(title="Draft Post")

        self.client_.post(reverse("v1:admin:blog-publish", args=[post.pk]))
        post.refresh_from_db()
        self.assertEqual(post.status, PublishStatus.PUBLISHED)
        self.assertIsNotNone(post.published_at)

        self.client_.post(reverse("v1:admin:blog-unpublish", args=[post.pk]))
        post.refresh_from_db()
        self.assertEqual(post.status, PublishStatus.DRAFT)

    def test_blog_author_defaults_to_the_creator(self):
        response = self.client_.post(
            reverse("v1:admin:blog-list"),
            {"title": "Unattributed"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(BlogPost.objects.get(title="Unattributed").author, self.admin)

    def test_filters_and_search(self):
        Project.objects.create(title="Villa Rossi", location="Lucknow", is_featured=True)
        Project.objects.create(title="Office Block", location="Kushinagar")

        featured = self.client_.get(
            reverse("v1:admin:project-list") + "?is_featured=true"
        ).json()
        self.assertEqual(featured["pagination"]["total_items"], 1)

        found = self.client_.get(
            reverse("v1:admin:project-list") + "?search=Kushinagar"
        ).json()
        self.assertEqual(found["pagination"]["total_items"], 1)


class ContentPermissionTests(ContentTestCase):
    def test_view_permission_alone_grants_read_but_not_write(self):
        user = self.make_user("viewer@archethos.test", permissions=["view_project"])
        client = self.client_for(user)

        self.assertEqual(client.get(reverse("v1:admin:project-list")).status_code, 200)
        self.assertEqual(
            client.post(
                reverse("v1:admin:project-list"),
                {"title": "Nope"},
                content_type="application/json",
            ).status_code,
            403,
        )

    def test_no_permission_is_forbidden(self):
        user = self.make_user("nobody@archethos.test")
        self.assertEqual(
            self.client_for(user).get(reverse("v1:admin:project-list")).status_code, 403
        )

    def test_permission_on_one_model_does_not_grant_another(self):
        """User A manages Projects; that must not let them read Blogs."""
        user = self.make_user("projects@archethos.test", permissions=["view_project"])
        client = self.client_for(user)

        self.assertEqual(client.get(reverse("v1:admin:project-list")).status_code, 200)
        self.assertEqual(client.get(reverse("v1:admin:blog-list")).status_code, 403)

    def test_anonymous_cannot_reach_admin(self):
        self.assertEqual(Client().get(reverse("v1:admin:project-list")).status_code, 401)


# ─── Project gallery + reorder ───────────────────────────────────────────────


class ProjectGalleryTests(ContentTestCase):
    def setUp(self):
        self.client_ = self.client_for(
            self.make_user("root@archethos.test", superuser=True)
        )
        self.project = Project.objects.create(title="Villa")
        self.media = [self.make_media(f"img{i}.png") for i in range(3)]

    def add(self, media, order=0):
        return self.client_.post(
            reverse("v1:admin:project-gallery-list", args=[self.project.pk]),
            {"media": media.pk, "order": order},
            content_type="application/json",
        )

    def test_add_and_list(self):
        for index, media in enumerate(self.media):
            self.assertEqual(self.add(media, index).status_code, 201)

        body = self.client_.get(
            reverse("v1:admin:project-gallery-list", args=[self.project.pk])
        ).json()
        self.assertEqual(len(body["data"]), 3)
        # Small collection, always shown whole.
        self.assertNotIn("pagination", body)

    def test_the_same_image_cannot_be_added_twice(self):
        self.add(self.media[0])
        response = self.add(self.media[0])
        self.assertEqual(response.status_code, 400)
        self.assertIn("media", response.json()["errors"])

    def test_reorder_is_applied(self):
        items = []
        for index, media in enumerate(self.media):
            items.append(self.add(media, index).json()["data"]["id"])

        response = self.client_.patch(
            reverse("v1:admin:project-gallery-reorder", args=[self.project.pk]),
            {"items": [
                {"id": items[2], "order": 1},
                {"id": items[0], "order": 2},
                {"id": items[1], "order": 3},
            ]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        ordered = list(
            ProjectGalleryItem.objects.filter(project=self.project).values_list(
                "id", flat=True
            )
        )
        self.assertEqual(ordered, [items[2], items[0], items[1]])

    def test_reorder_rejects_an_item_from_another_project(self):
        other = Project.objects.create(title="Other")
        foreign = ProjectGalleryItem.objects.create(
            project=other, media=self.media[0], order=1
        )
        mine = self.add(self.media[1], 1).json()["data"]["id"]

        response = self.client_.patch(
            reverse("v1:admin:project-gallery-reorder", args=[self.project.pk]),
            {"items": [{"id": mine, "order": 1}, {"id": foreign.pk, "order": 2}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        foreign.refresh_from_db()
        self.assertEqual(foreign.order, 1)

    def test_reorder_rejects_duplicate_ids(self):
        item = self.add(self.media[0]).json()["data"]["id"]
        response = self.client_.patch(
            reverse("v1:admin:project-gallery-reorder", args=[self.project.pk]),
            {"items": [{"id": item, "order": 1}, {"id": item, "order": 2}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_reorder_rejects_a_malformed_payload(self):
        for payload in ({}, {"items": []}, {"items": [{"id": 1}]}, {"items": "nope"}):
            with self.subTest(payload=payload):
                response = self.client_.patch(
                    reverse("v1:admin:project-gallery-reorder", args=[self.project.pk]),
                    payload,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)

    def test_removing_a_gallery_item_leaves_the_media_intact(self):
        item = self.add(self.media[0]).json()["data"]["id"]
        self.client_.delete(
            reverse("v1:admin:project-gallery-item", args=[self.project.pk, item])
        )
        self.assertFalse(ProjectGalleryItem.objects.filter(pk=item).exists())
        self.assertTrue(MediaAsset.objects.filter(pk=self.media[0].pk).exists())

    def test_deleting_a_project_removes_items_but_not_the_media(self):
        self.add(self.media[0])
        self.client_.delete(reverse("v1:admin:project-detail", args=[self.project.pk]))

        self.assertEqual(ProjectGalleryItem.objects.count(), 0)
        self.assertEqual(MediaAsset.objects.count(), 3)


# ─── FAQ and Counter ─────────────────────────────────────────────────────────


class FAQAndCounterTests(ContentTestCase):
    def setUp(self):
        self.client_ = self.client_for(
            self.make_user("root@archethos.test", superuser=True)
        )

    def test_faq_crud_and_category_filter(self):
        response = self.client_.post(
            reverse("v1:admin:faq-list"),
            {"question": "Do you provide vastu consultancy?", "answer": "Yes.",
             "category": "VASTU", "status": "PUBLISHED"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        body = Client().get(reverse("v1:public:faq-list") + "?category=VASTU").json()
        self.assertEqual(body["pagination"]["total_items"], 1)

    def test_counter_keeps_prefix_and_postfix_separate(self):
        response = self.client_.post(
            reverse("v1:admin:counter-list"),
            {"content": "40", "postfix": "+", "subtitle": "PROJECTS DELIVERED",
             "description": "Residential, commercial and interior",
             "status": "PUBLISHED"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)

        # The admin table wants the assembled string…
        row = self.client_.get(reverse("v1:admin:counter-list")).json()["data"][0]
        self.assertEqual(row["display"], "40+")

        # …but the public API keeps them apart, because the design renders the
        # "+" in the accent colour at a smaller size than the number.
        public = Client().get(reverse("v1:public:counter-list")).json()["data"][0]
        self.assertEqual(public["content"], "40")
        self.assertEqual(public["postfix"], "+")
        self.assertNotIn("display", public)

    def test_draft_counters_are_not_public(self):
        Counter.objects.create(content="99", subtitle="HIDDEN")
        body = Client().get(reverse("v1:public:counter-list")).json()
        self.assertEqual(body["pagination"]["total_items"], 0)


class BlogCategoryTests(ContentTestCase):
    def test_category_slug_is_generated_and_posts_are_counted(self):
        client = self.client_for(self.make_user("root@archethos.test", superuser=True))

        response = client.post(
            reverse("v1:admin:blog-category-list"),
            {"name": "Design Notes"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        category = BlogCategory.objects.get(name="Design Notes")
        self.assertEqual(category.slug, "design-notes")

        BlogPost.objects.create(title="A post", category=category)
        row = client.get(reverse("v1:admin:blog-category-list")).json()["data"][0]
        self.assertEqual(row["posts_count"], 1)

    def test_deleting_a_category_keeps_its_posts(self):
        category = BlogCategory.objects.create(name="Temp")
        post = BlogPost.objects.create(title="Survivor", category=category)

        category.delete()
        post.refresh_from_db()
        self.assertIsNone(post.category)
