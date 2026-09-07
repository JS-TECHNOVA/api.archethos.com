"""
Pages: structure, writes and the properties the architecture depends on.

The point of this refactor was to make the site's structure a fact about the
code rather than data in a table. These tests pin the consequences of that —
that a page's fields are its render order, that master data is referenced and
never copied, that an unpublished page is invisible, and that reading a whole
page costs a bounded number of queries however much content it holds.
"""

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db.models import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse

from archethosbackend.apps.content.models import Counter, GalleryItem, Location, Service
from archethosbackend.apps.core.models import PublishStatus
from archethosbackend.apps.media_library.models import MediaAsset
from archethosbackend.apps.pages.models import (
    ORDERED_PAGES,
    HomePage,
    HomeServicesSection,
    StatsSection,
)

def page_url(route, public=False):
    """The URL for a page, from its public route.

    Each page has its own named endpoint now — `v1:admin:page-home`,
    `v1:admin:page-legal-privacy` — so this maps the route the tests speak in
    onto the name the resolver wants.
    """
    space = "public" if public else "admin"
    return reverse(f"v1:{space}:page-" + route.replace("/", "-"))


PASSWORD = "correct-horse-battery-staple"


def asset(name="hero.webp"):
    return MediaAsset.objects.create(
        file=f"uploads/{name}", title=name, media_type="IMAGE", source_type="UPLOAD"
    )


class AdminTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="root@archethos.test",
            email="root@archethos.test",
            password=PASSWORD,
            is_superuser=True,
            is_staff=True,
        )

    def setUp(self):
        self.client_ = Client()
        assert self.client_.post(
            reverse("v1:auth:login"),
            {"email": self.user.email, "password": PASSWORD},
            content_type="application/json",
        ).status_code == 200

    def patch(self, route, payload):
        return self.client_.patch(
            page_url(route),
            payload,
            content_type="application/json",
        )


class StructureTests(TestCase):
    """The site's shape is code. These are the invariants that makes true."""

    def test_every_route_has_a_model_and_a_serializer(self):
        from archethosbackend.apps.pages.serializers.pages import PAGE_SERIALIZERS

        self.assertEqual(set(ORDERED_PAGES), set(PAGE_SERIALIZERS))

    def test_a_pages_fields_are_its_render_order(self):
        """`HomePage` read top to bottom is the home page top to bottom.

        If this ever needs changing, the frontend component order changes with
        it — that coupling is deliberate and is what replaced the ordering
        column on the old PageSection table.
        """
        from django.db.models import OneToOneField

        order = [
            field.name
            for field in HomePage._meta.get_fields()
            if isinstance(field, OneToOneField) and field.concrete
        ]
        self.assertEqual(
            order,
            [
                "hero", "intro", "stats", "featured_project", "services",
                "design_build", "projects", "gallery", "vastu", "locations",
                "cta",
            ],
        )

    def test_no_section_carries_an_order_field(self):
        """Ordering belongs to item collections, not to page structure (§16)."""
        for route, model in ORDERED_PAGES.items():
            with self.subTest(route=route):
                self.assertNotIn(
                    "order", [f.name for f in model._meta.get_fields()]
                )

    def test_ensure_pages_is_idempotent(self):
        call_command("ensure_pages", verbosity=0)
        call_command("ensure_pages", verbosity=0)

        for route, model in ORDERED_PAGES.items():
            with self.subTest(route=route):
                self.assertEqual(model.objects.count(), 1)

    def test_pages_are_created_unpublished(self):
        call_command("ensure_pages", verbosity=0)
        for route, model in ORDERED_PAGES.items():
            with self.subTest(route=route):
                self.assertFalse(model.objects.get().is_published)


class PageReadTests(AdminTestCase):
    def test_opening_a_page_for_the_first_time_creates_it(self):
        """An editor must get a blank form, not a 404 they cannot act on."""
        self.assertFalse(HomePage.objects.exists())

        response = self.client_.get(page_url("home"))

        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(HomePage.objects.exists())

    def test_the_payload_names_every_section(self):
        data = self.client_.get(
            page_url("home")
        ).json()["data"]

        for section in ("hero", "intro", "stats", "services", "cta"):
            self.assertIn(section, data)

    def test_an_unknown_route_is_not_routed_at_all(self):
        """There is no dynamic segment to miss.

        Each page has its own URL, so `/pages/shop/` never reaches a view — it
        is a 404 from the resolver. That is the property worth pinning: a page
        the site does not have cannot be *asked for*, let alone half-handled.
        """
        response = self.client_.get("/api/v1/admin/pages/shop/")
        self.assertEqual(response.status_code, 404)

    def test_the_page_list_is_in_navigation_order(self):
        rows = self.client_.get(reverse("v1:admin:page-list")).json()["data"]
        self.assertEqual([row["route"] for row in rows], list(ORDERED_PAGES))


class SectionWriteTests(AdminTestCase):
    def test_a_section_is_created_on_first_write(self):
        response = self.patch("home", {"intro": {"heading": "We shape spaces."}})

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(HomePage.objects.get().intro.heading, "We shape spaces.")

    def test_a_second_write_updates_rather_than_duplicating(self):
        self.patch("home", {"intro": {"heading": "First"}})
        self.patch("home", {"intro": {"heading": "Second"}})

        from archethosbackend.apps.pages.models import HomeIntroSection

        self.assertEqual(HomeIntroSection.objects.count(), 1)
        self.assertEqual(HomePage.objects.get().intro.heading, "Second")

    def test_an_omitted_section_is_left_alone(self):
        self.patch("home", {"intro": {"heading": "Kept"}})
        self.patch("home", {"cta": {"heading": "Talk to us"}})

        self.assertEqual(HomePage.objects.get().intro.heading, "Kept")

    def test_item_order_is_the_array_order(self):
        a = Counter.objects.create(content="40", subtitle="Projects")
        b = Counter.objects.create(content="2", subtitle="Cities")

        self.patch("home", {"stats": {"items": [{"counter": b.pk}, {"counter": a.pk}]}})

        section = StatsSection.objects.get()
        self.assertEqual(
            [item.counter_id for item in section.items.all()], [b.pk, a.pk]
        )

    def test_reordering_is_sending_the_array_again(self):
        a = Counter.objects.create(content="40", subtitle="Projects")
        b = Counter.objects.create(content="2", subtitle="Cities")

        self.patch("home", {"stats": {"items": [{"counter": a.pk}, {"counter": b.pk}]}})
        self.patch("home", {"stats": {"items": [{"counter": b.pk}, {"counter": a.pk}]}})

        section = StatsSection.objects.get()
        self.assertEqual(
            [item.counter_id for item in section.items.all()], [b.pk, a.pk]
        )
        self.assertEqual(section.items.count(), 2, "items were duplicated, not replaced")

    def test_an_empty_list_clears_a_collection(self):
        counter = Counter.objects.create(content="40", subtitle="Projects")
        self.patch("home", {"stats": {"items": [{"counter": counter.pk}]}})
        self.patch("home", {"stats": {"items": []}})

        self.assertEqual(StatsSection.objects.get().items.count(), 0)

    def test_omitting_a_collection_does_not_clear_it(self):
        """The distinction between "unchanged" and "empty" has to survive."""
        counter = Counter.objects.create(content="40", subtitle="Projects")
        self.patch("home", {"stats": {"items": [{"counter": counter.pk}]}})
        self.patch("home", {"stats": {"eyebrow": "At a glance"}})

        self.assertEqual(StatsSection.objects.get().items.count(), 1)

    def test_a_write_is_one_transaction(self):
        """A rejected section must not leave an earlier one written."""
        response = self.patch(
            "home",
            {
                "intro": {"heading": "Should not persist"},
                "stats": {"items": [{"counter": 99999}]},
            },
        )

        self.assertEqual(response.status_code, 400)
        page = HomePage.objects.filter(pk=HomePage.SINGLETON_PK).first()
        self.assertTrue(page is None or page.intro_id is None)


class MasterDataTests(AdminTestCase):
    """Sections reference master data. They never copy it, and never own it."""

    def test_a_section_returns_the_record_not_a_join_row(self):
        service = Service.objects.create(title="Architecture", short_description="…")
        self.patch("home", {"services": {"items": [{"service": service.pk}]}})

        data = self.client_.get(
            page_url("home")
        ).json()["data"]

        self.assertEqual(data["services"]["items"][0]["detail"]["title"], "Architecture")

    def test_the_same_record_can_appear_on_two_pages(self):
        """The reason master data exists at all (§6)."""
        location = Location.objects.create(city="Lucknow")

        self.patch("home", {"locations": {"items": [{"location": location.pk}]}})
        self.patch("about", {"presence": {"items": [{"location": location.pk}]}})

        self.assertEqual(location.home_section_items.count(), 1)
        self.assertEqual(location.about_section_items.count(), 1)

    def test_editing_the_record_changes_every_page_showing_it(self):
        service = Service.objects.create(title="Architecture")
        self.patch("home", {"services": {"items": [{"service": service.pk}]}})

        service.title = "Architecture Design"
        service.save()

        data = self.client_.get(
            page_url("home")
        ).json()["data"]
        self.assertEqual(
            data["services"]["items"][0]["detail"]["title"], "Architecture Design"
        )

    def test_a_record_in_use_cannot_be_deleted(self):
        """PROTECT, so a live page cannot lose its content silently (§18)."""
        service = Service.objects.create(title="Architecture")
        self.patch("home", {"services": {"items": [{"service": service.pk}]}})

        with self.assertRaises(ProtectedError):
            service.delete()

    def test_deleting_a_section_item_does_not_touch_the_record(self):
        service = Service.objects.create(title="Architecture")
        self.patch("home", {"services": {"items": [{"service": service.pk}]}})
        self.patch("home", {"services": {"items": []}})

        self.assertTrue(Service.objects.filter(pk=service.pk).exists())

    def test_a_section_cannot_list_the_same_record_twice(self):
        service = Service.objects.create(title="Architecture")

        response = self.patch(
            "home",
            {"services": {"items": [{"service": service.pk}, {"service": service.pk}]}},
        )
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(HomeServicesSection.objects.count(), 0)


class PublishingTests(AdminTestCase):
    def test_a_page_cannot_be_published_while_a_required_section_is_empty(self):
        response = self.patch("home", {"is_published": True})

        self.assertEqual(response.status_code, 400)
        self.assertIn("hero", response.json()["errors"])

    def test_the_admin_is_told_what_is_missing(self):
        data = self.client_.get(
            page_url("home")
        ).json()["data"]
        self.assertEqual(sorted(data["missing_sections"]), ["cta", "hero", "intro"])

    def test_a_complete_page_publishes(self):
        image = asset()
        self.patch("home", {
            "hero": {"slides": [{"heading": "Archethos", "media": image.pk}]},
            "intro": {"heading": "We shape spaces."},
            "cta": {"heading": "Start a project"},
        })

        response = self.patch("home", {"is_published": True})

        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(HomePage.objects.get().is_published)


class PublicTests(AdminTestCase):
    def publish_home(self):
        image = asset()
        self.patch("home", {
            "hero": {"slides": [{"heading": "Archethos", "media": image.pk}]},
            "intro": {"heading": "We shape spaces."},
            "cta": {"heading": "Start a project"},
        })
        self.patch("home", {"is_published": True})

    def test_an_unpublished_page_is_a_404(self):
        """Indistinguishable from a page that does not exist."""
        response = self.client.get(page_url("home", public=True))
        self.assertEqual(response.status_code, 404)

    def test_a_published_page_is_served_without_authentication(self):
        self.publish_home()

        response = self.client.get(page_url("home", public=True))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["hero"]["slides"][0]["heading"], "Archethos")

    def test_the_public_payload_carries_no_admin_bookkeeping(self):
        self.publish_home()

        data = self.client.get(
            page_url("home", public=True)
        ).json()["data"]

        for key in ("is_published", "missing_sections", "id", "updated_at"):
            self.assertNotIn(key, data)

    def test_items_are_flattened_to_the_record_for_the_frontend(self):
        """§13: a list of join rows is a database detail, not an API."""
        counter = Counter.objects.create(content="40", subtitle="Projects")
        self.patch("home", {"stats": {"items": [{"counter": counter.pk}]}})
        self.publish_home()

        data = self.client.get(
            page_url("home", public=True)
        ).json()["data"]

        item = data["stats"]["items"][0]
        self.assertEqual(item["subtitle"], "Projects")
        self.assertNotIn("detail", item)
        self.assertNotIn("counter", item)

    def test_the_route_index_lists_only_published_pages(self):
        self.publish_home()

        rows = self.client.get(reverse("v1:public:page-index")).json()["data"]

        self.assertEqual([row["route"] for row in rows], ["home"])


class QueryCountTests(AdminTestCase):
    """The cost of a page is its shape, not its size.

    A page is one row plus its sections plus their items plus the master data
    behind them. Fetched naively that is a query per item — the N+1 the
    selector exists to prevent. What matters is not the exact number but that
    it does not move when content is added.
    """

    def populate(self, services=3, counters=3, gallery=3, locations=2):
        image = asset()
        self.patch("home", {
            "hero": {"slides": [{"heading": "Archethos", "media": image.pk}]},
            "intro": {"heading": "We shape spaces."},
            "cta": {"heading": "Start a project"},
            "services": {"items": [
                {"service": Service.objects.create(
                    title=f"Service {i}", status=PublishStatus.PUBLISHED).pk}
                for i in range(services)
            ]},
            "stats": {"items": [
                {"counter": Counter.objects.create(
                    content=str(i), subtitle=f"Stat {i}").pk}
                for i in range(counters)
            ]},
            "gallery": {"items": [
                {"gallery_item": GalleryItem.objects.create(
                    title=f"Image {i}", image=asset(f"g{i}.webp")).pk}
                for i in range(gallery)
            ]},
            "locations": {"items": [
                {"location": Location.objects.create(city=f"City {i}").pk}
                for i in range(locations)
            ]},
        })
        self.patch("home", {"is_published": True})

    def test_reading_a_page_is_flat_in_the_number_of_items(self):
        self.populate(services=3, counters=3, gallery=3, locations=2)
        url = page_url("home", public=True)

        small = self._count(url)

        # Ten times the content, through the same code path.
        self.patch("home", {
            "services": {"items": [
                {"service": s.pk} for s in Service.objects.all()[:3]
            ]},
            "gallery": {"items": [
                {"gallery_item": GalleryItem.objects.create(
                    title=f"Extra {i}", image=asset(f"x{i}.webp")).pk}
                for i in range(30)
            ]},
        })

        large = self._count(url)

        self.assertEqual(
            small,
            large,
            f"query count grew with content: {small} → {large}",
        )

    def _count(self, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
        return len(ctx)
