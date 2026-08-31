"""
Section tests.

The registry-driven views are generic, so the tests are too: several run across
every registered type rather than naming one, which means a newly registered
section type is covered the moment it is added.
"""

from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.urls import reverse

from archethosbackend.apps.content.models import FAQ, Counter, Project, Service
from archethosbackend.apps.core.models import PublishStatus
from archethosbackend.apps.media_library.models import MediaAsset, MediaType, SourceType

from .models import (
    CounterSection,
    CounterSectionItem,
    CTASection,
    FAQSection,
    FAQSectionItem,
    GallerySection,
    HeroSection,
    HeroSlide,
    Section,
    SectionType,
)
from .registry import SECTION_REGISTRY


class SectionTestCase(TestCase):
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

    def make_media(self, name="img.png"):
        return MediaAsset.objects.create(
            media_type=MediaType.IMAGE,
            source_type=SourceType.UPLOAD,
            file=f"uploads/{name}",
            alt_text="alt",
        )


# ─── The MTI base ────────────────────────────────────────────────────────────


class SectionBaseTests(SectionTestCase):
    def test_section_type_is_derived_from_the_class(self):
        hero = HeroSection.objects.create(internal_label="Home - main hero")
        cta = CTASection.objects.create(internal_label="Global CTA", heading="Hi")

        self.assertEqual(hero.section_type, SectionType.HERO)
        self.assertEqual(cta.section_type, SectionType.CTA)

    def test_section_type_cannot_be_set_by_a_client(self):
        """It is editable=False and overwritten in save(), so a forged value is
        ignored rather than corrupting the aggregate API's type batching."""
        client = self.admin_client()
        response = client.post(
            reverse("v1:admin:section-list", args=["cta"]),
            {"internal_label": "Sneaky", "heading": "Hi", "section_type": "hero"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            CTASection.objects.get(internal_label="Sneaky").section_type,
            SectionType.CTA,
        )

    def test_the_parent_table_sees_every_type(self):
        HeroSection.objects.create(internal_label="Hero")
        CTASection.objects.create(internal_label="CTA", heading="Hi")
        FAQSection.objects.create(internal_label="FAQ")

        self.assertEqual(Section.objects.count(), 3)
        self.assertEqual(
            set(Section.objects.values_list("section_type", flat=True)),
            {SectionType.HERO, SectionType.CTA, SectionType.FAQ},
        )

    def test_deleting_a_concrete_section_removes_its_parent_row(self):
        hero = HeroSection.objects.create(internal_label="Hero")
        hero.delete()
        self.assertEqual(Section.objects.count(), 0)


# ─── The registry ────────────────────────────────────────────────────────────


class RegistryTests(SectionTestCase):
    def test_every_registered_type_matches_its_model(self):
        for section_type, spec in SECTION_REGISTRY.items():
            with self.subTest(section_type=section_type):
                self.assertEqual(spec.model.SECTION_TYPE, section_type)

    def test_every_registered_type_has_all_four_serializers(self):
        for section_type, spec in SECTION_REGISTRY.items():
            with self.subTest(section_type=section_type):
                for attr in (
                    "list_serializer", "detail_serializer",
                    "write_serializer", "public_serializer",
                ):
                    self.assertIsNotNone(getattr(spec, attr), attr)

    def test_url_segments_are_unique(self):
        segments = [spec.url_segment for spec in SECTION_REGISTRY.values()]
        self.assertEqual(len(segments), len(set(segments)))

    def test_every_section_type_choice_is_registered(self):
        """A type in the enum but missing from the registry would 404 on its own
        admin routes and be unrenderable by the aggregate API."""
        self.assertEqual(set(SECTION_REGISTRY), {t for t in SectionType.values})

    def test_type_catalogue_endpoint_lists_the_registry(self):
        body = self.admin_client().get(reverse("v1:admin:section-type-list")).json()
        self.assertEqual(len(body["data"]), len(SECTION_REGISTRY))

        hero = next(r for r in body["data"] if r["section_type"] == "hero")
        self.assertEqual(hero["url_segment"], "hero")
        self.assertTrue(hero["has_items"])

        cta = next(r for r in body["data"] if r["section_type"] == "cta")
        self.assertFalse(cta["has_items"])


# ─── Generic CRUD, run across every type ─────────────────────────────────────


REQUIRED_FIELDS = {
    "cta": {"heading": "Let's build"},
    "rich-text": {},
}


class GenericSectionCRUDTests(SectionTestCase):
    """Runs against every registered type, so new types are covered for free."""

    def setUp(self):
        self.client_ = self.admin_client()

    def test_create_list_retrieve_update_delete_for_every_type(self):
        for section_type, spec in SECTION_REGISTRY.items():
            segment = spec.url_segment
            with self.subTest(section_type=section_type):
                payload = {"internal_label": f"{segment} one"}
                payload.update(REQUIRED_FIELDS.get(segment, {}))

                created = self.client_.post(
                    reverse("v1:admin:section-list", args=[segment]),
                    payload,
                    content_type="application/json",
                )
                self.assertEqual(created.status_code, 201, created.content)
                pk = created.json()["data"]["id"]

                listed = self.client_.get(
                    reverse("v1:admin:section-list", args=[segment])
                )
                self.assertEqual(listed.status_code, 200)
                self.assertIn("pagination", listed.json())

                detail = self.client_.get(
                    reverse("v1:admin:section-detail", args=[segment, pk])
                )
                self.assertEqual(detail.status_code, 200)
                self.assertEqual(detail.json()["data"]["section_type"], section_type)

                patched = self.client_.patch(
                    reverse("v1:admin:section-detail", args=[segment, pk]),
                    {"internal_label": f"{segment} renamed"},
                    content_type="application/json",
                )
                self.assertEqual(patched.status_code, 200)

                deleted = self.client_.delete(
                    reverse("v1:admin:section-detail", args=[segment, pk])
                )
                self.assertEqual(deleted.status_code, 204)

    def test_unknown_segment_is_404(self):
        response = self.client_.get(
            reverse("v1:admin:section-list", args=["not-a-section"])
        )
        self.assertEqual(response.status_code, 404)

    def test_browse_lists_all_types_and_filters_by_type(self):
        HeroSection.objects.create(internal_label="Hero")
        CTASection.objects.create(internal_label="CTA", heading="Hi")
        FAQSection.objects.create(internal_label="FAQ")

        body = self.client_.get(reverse("v1:admin:section-browse")).json()
        self.assertEqual(body["pagination"]["total_items"], 3)

        filtered = self.client_.get(
            reverse("v1:admin:section-browse") + "?section_type=hero"
        ).json()
        self.assertEqual(filtered["pagination"]["total_items"], 1)

    def test_browse_search_matches_internal_label(self):
        HeroSection.objects.create(internal_label="Home - main hero")
        HeroSection.objects.create(internal_label="About - studio hero")

        body = self.client_.get(
            reverse("v1:admin:section-browse") + "?search=About"
        ).json()
        self.assertEqual(body["pagination"]["total_items"], 1)


# ─── Permissions ─────────────────────────────────────────────────────────────


class SectionPermissionTests(SectionTestCase):
    def test_permissions_are_per_concrete_type(self):
        """"May edit FAQ sections" must not also grant hero sections."""
        user = self.make_user(
            "faq@archethos.test", permissions=["view_faqsection", "change_faqsection"]
        )
        client = self.client_for(user)

        self.assertEqual(
            client.get(reverse("v1:admin:section-list", args=["faq"])).status_code, 200
        )
        self.assertEqual(
            client.get(reverse("v1:admin:section-list", args=["hero"])).status_code, 403
        )

    def test_view_permission_does_not_grant_create(self):
        user = self.make_user("viewer@archethos.test", permissions=["view_ctasection"])
        client = self.client_for(user)

        self.assertEqual(
            client.get(reverse("v1:admin:section-list", args=["cta"])).status_code, 200
        )
        self.assertEqual(
            client.post(
                reverse("v1:admin:section-list", args=["cta"]),
                {"internal_label": "Nope", "heading": "Hi"},
                content_type="application/json",
            ).status_code,
            403,
        )

    def test_anonymous_is_rejected(self):
        self.assertEqual(
            Client().get(reverse("v1:admin:section-browse")).status_code, 401
        )


# ─── Section items ───────────────────────────────────────────────────────────


class SectionItemTests(SectionTestCase):
    def setUp(self):
        self.client_ = self.admin_client()
        self.section = FAQSection.objects.create(internal_label="Home FAQ")
        self.faqs = [
            FAQ.objects.create(question=f"Q{i}?", answer=f"A{i}", status=PublishStatus.PUBLISHED)
            for i in range(3)
        ]

    def add(self, faq, order=0):
        return self.client_.post(
            reverse("v1:admin:section-item-list", args=["faq", self.section.pk]),
            {"faq": faq.pk, "order": order},
            content_type="application/json",
        )

    def test_add_and_list_items(self):
        for index, faq in enumerate(self.faqs):
            self.assertEqual(self.add(faq, index).status_code, 201)

        body = self.client_.get(
            reverse("v1:admin:section-item-list", args=["faq", self.section.pk])
        ).json()
        self.assertEqual(len(body["data"]), 3)
        # Never paginated: paginating would break drag-and-drop ordering.
        self.assertNotIn("pagination", body)

    def test_the_same_content_cannot_be_added_twice(self):
        self.add(self.faqs[0])
        response = self.add(self.faqs[0])
        self.assertEqual(response.status_code, 400)
        self.assertIn("faq", response.json()["errors"])

    def test_the_same_faq_can_live_in_two_sections_with_different_orders(self):
        """The whole reason FAQs are master content rather than inline rows."""
        other = FAQSection.objects.create(internal_label="Vastu FAQ")

        FAQSectionItem.objects.create(section=self.section, faq=self.faqs[0], order=1)
        FAQSectionItem.objects.create(section=self.section, faq=self.faqs[1], order=2)
        FAQSectionItem.objects.create(section=other, faq=self.faqs[1], order=1)
        FAQSectionItem.objects.create(section=other, faq=self.faqs[0], order=2)

        self.assertEqual(
            list(self.section.items.values_list("faq_id", flat=True)),
            [self.faqs[0].pk, self.faqs[1].pk],
        )
        self.assertEqual(
            list(other.items.values_list("faq_id", flat=True)),
            [self.faqs[1].pk, self.faqs[0].pk],
        )

    def test_detail_includes_items_but_list_stays_light(self):
        self.add(self.faqs[0])

        detail = self.client_.get(
            reverse("v1:admin:section-detail", args=["faq", self.section.pk])
        ).json()["data"]
        self.assertEqual(len(detail["items"]), 1)

        row = self.client_.get(
            reverse("v1:admin:section-list", args=["faq"])
        ).json()["data"][0]
        self.assertNotIn("items", row)
        self.assertEqual(row["items_count"], 1)

    def test_removing_an_item_leaves_the_master_content(self):
        item_id = self.add(self.faqs[0]).json()["data"]["id"]
        self.client_.delete(
            reverse(
                "v1:admin:section-item-detail",
                args=["faq", self.section.pk, item_id],
            )
        )
        self.assertEqual(FAQSectionItem.objects.count(), 0)
        self.assertEqual(FAQ.objects.count(), 3)

    def test_deleting_a_section_removes_items_but_not_master_content(self):
        self.add(self.faqs[0])
        self.client_.delete(
            reverse("v1:admin:section-detail", args=["faq", self.section.pk])
        )
        self.assertEqual(FAQSectionItem.objects.count(), 0)
        self.assertEqual(FAQ.objects.count(), 3)

    def test_an_faq_in_a_section_cannot_be_deleted(self):
        """PROTECT: removing content out from under a live page must not be possible."""
        self.add(self.faqs[0])
        response = self.client_.delete(
            reverse("v1:admin:faq-detail", args=[self.faqs[0].pk])
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "protected")

    def test_sections_without_items_reject_the_items_route(self):
        cta = CTASection.objects.create(internal_label="CTA", heading="Hi")
        response = self.client_.get(
            reverse("v1:admin:section-item-list", args=["cta", cta.pk])
        )
        self.assertEqual(response.status_code, 404)


class SectionItemReorderTests(SectionTestCase):
    def setUp(self):
        self.client_ = self.admin_client()
        self.section = FAQSection.objects.create(internal_label="Home FAQ")
        self.items = [
            FAQSectionItem.objects.create(
                section=self.section,
                faq=FAQ.objects.create(question=f"Q{i}?", answer="A"),
                order=i,
            )
            for i in range(3)
        ]

    def url(self):
        return reverse("v1:admin:section-item-reorder", args=["faq", self.section.pk])

    def test_reorder_applies(self):
        response = self.client_.patch(
            self.url(),
            {"items": [
                {"id": self.items[2].pk, "order": 1},
                {"id": self.items[0].pk, "order": 2},
                {"id": self.items[1].pk, "order": 3},
            ]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            list(self.section.items.values_list("id", flat=True)),
            [self.items[2].pk, self.items[0].pk, self.items[1].pk],
        )

    def test_reorder_rejects_an_item_from_another_section(self):
        other = FAQSection.objects.create(internal_label="Other")
        foreign = FAQSectionItem.objects.create(
            section=other, faq=FAQ.objects.create(question="X?", answer="Y"), order=1
        )

        response = self.client_.patch(
            self.url(),
            {"items": [
                {"id": self.items[0].pk, "order": 1},
                {"id": foreign.pk, "order": 2},
            ]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        foreign.refresh_from_db()
        self.assertEqual(foreign.order, 1)

    def test_reorder_is_atomic(self):
        """A rejected payload must change nothing at all."""
        before = list(self.section.items.values_list("id", "order"))

        self.client_.patch(
            self.url(),
            {"items": [
                {"id": self.items[0].pk, "order": 9},
                {"id": 999999, "order": 1},
            ]},
            content_type="application/json",
        )
        self.assertEqual(list(self.section.items.values_list("id", "order")), before)

    def test_reorder_rejects_duplicate_ids(self):
        response = self.client_.patch(
            self.url(),
            {"items": [
                {"id": self.items[0].pk, "order": 1},
                {"id": self.items[0].pk, "order": 2},
            ]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_duplicate_order_values_are_allowed(self):
        """`order` carries no unique constraint (plan §2.3); ties break by id, and
        forbidding duplicates would make partial reorders impossible."""
        response = self.client_.patch(
            self.url(),
            {"items": [
                {"id": self.items[0].pk, "order": 1},
                {"id": self.items[1].pk, "order": 1},
            ]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    def test_reorder_rejects_malformed_payloads(self):
        for payload in ({}, {"items": []}, {"items": "x"}, {"items": [{"id": 1}]},
                        {"items": [{"id": 1, "order": -1}]}):
            with self.subTest(payload=payload):
                response = self.client_.patch(
                    self.url(), payload, content_type="application/json"
                )
                self.assertEqual(response.status_code, 400)

    def test_reorder_requires_change_permission_on_the_section(self):
        user = self.make_user("viewer@archethos.test", permissions=["view_faqsection"])
        response = self.client_for(user).patch(
            self.url(),
            {"items": [{"id": self.items[0].pk, "order": 1}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


# ─── Hero slides ─────────────────────────────────────────────────────────────


class HeroSlideTests(SectionTestCase):
    def test_heading_splits_into_lines(self):
        """The design breaks the headline deliberately; the editor writes the
        breaks in a textarea and the API hands the frontend a list."""
        section = HeroSection.objects.create(internal_label="Home hero")
        slide = HeroSlide.objects.create(
            section=section,
            heading="Spaces shaped around\nthe way you live.",
            label="Architecture",
        )
        self.assertEqual(
            slide.heading_lines, ["Spaces shaped around", "the way you live."]
        )

    def test_slides_are_managed_through_the_generic_item_routes(self):
        client = self.admin_client()
        section = HeroSection.objects.create(internal_label="Home hero")
        media = self.make_media()

        response = client.post(
            reverse("v1:admin:section-item-list", args=["hero", section.pk]),
            {"heading": "One\nTwo", "label": "Architecture", "media": media.pk, "order": 1},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)

        detail = client.get(
            reverse("v1:admin:section-detail", args=["hero", section.pk])
        ).json()["data"]
        self.assertEqual(detail["slides"][0]["heading_lines"], ["One", "Two"])
        self.assertEqual(detail["slides"][0]["media"], media.relative_path)


# ─── Public serializers exclude drafts and CMS-only fields ───────────────────


class PublicSectionSerializerTests(SectionTestCase):
    def test_public_serializers_never_expose_internal_label(self):
        for section_type, spec in SECTION_REGISTRY.items():
            with self.subTest(section_type=section_type):
                self.assertNotIn(
                    "internal_label",
                    spec.public_serializer().fields,
                    f"{section_type} leaks internal_label",
                )

    def test_draft_master_content_is_filtered_out_of_a_section(self):
        from .serializers import PublicCounterSectionSerializer

        section = CounterSection.objects.create(internal_label="At a glance")
        live = Counter.objects.create(
            content="40", postfix="+", subtitle="PROJECTS",
            status=PublishStatus.PUBLISHED,
        )
        draft = Counter.objects.create(content="99", subtitle="SECRET")
        CounterSectionItem.objects.create(section=section, counter=live, order=1)
        CounterSectionItem.objects.create(section=section, counter=draft, order=2)

        data = PublicCounterSectionSerializer(section).data
        self.assertEqual([item["subtitle"] for item in data["items"]], ["PROJECTS"])

    def test_draft_projects_are_filtered_out_of_a_featured_section(self):
        from .models import FeaturedProjectItem, FeaturedProjectsSection
        from .serializers import PublicFeaturedProjectsSectionSerializer

        section = FeaturedProjectsSection.objects.create(internal_label="Selected work")
        live = Project.objects.create(title="Live Villa", status=PublishStatus.PUBLISHED)
        draft = Project.objects.create(title="Secret Villa")
        FeaturedProjectItem.objects.create(section=section, project=live, order=1)
        FeaturedProjectItem.objects.create(section=section, project=draft, order=2)

        data = PublicFeaturedProjectsSectionSerializer(section).data
        self.assertEqual([item["title"] for item in data["items"]], ["Live Villa"])

    def test_draft_services_are_filtered_out_of_a_services_section(self):
        from .models import ServiceSectionItem, ServicesSection
        from .serializers import PublicServicesSectionSerializer

        section = ServicesSection.objects.create(internal_label="What we do")
        live = Service.objects.create(title="Architecture", status=PublishStatus.PUBLISHED)
        draft = Service.objects.create(title="Unannounced")
        ServiceSectionItem.objects.create(section=section, service=live, order=1)
        ServiceSectionItem.objects.create(section=section, service=draft, order=2)

        data = PublicServicesSectionSerializer(section).data
        self.assertEqual([item["title"] for item in data["items"]], ["Architecture"])

    def test_label_override_replaces_the_service_title_publicly(self):
        from .models import ServiceSectionItem, ServicesSection
        from .serializers import PublicServicesSectionSerializer

        section = ServicesSection.objects.create(internal_label="What we do")
        service = Service.objects.create(
            title="Construction Consultancy", status=PublishStatus.PUBLISHED
        )
        ServiceSectionItem.objects.create(
            section=section, service=service, label_override="Construction", order=1
        )

        data = PublicServicesSectionSerializer(section).data
        self.assertEqual(data["items"][0]["title"], "Construction")


class GallerySectionTests(SectionTestCase):
    def test_layout_variant_defaults_to_grid_and_accepts_the_choices(self):
        client = self.admin_client()
        response = client.post(
            reverse("v1:admin:section-list", args=["gallery"]),
            {"internal_label": "Home gallery", "layout_variant": "SLIDER"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(GallerySection.objects.first().layout_variant, "SLIDER")

        default = GallerySection.objects.create(internal_label="Another")
        self.assertEqual(default.layout_variant, "GRID")

    def test_the_same_image_cannot_be_added_twice_to_one_gallery(self):
        client = self.admin_client()
        section = GallerySection.objects.create(internal_label="Home gallery")
        media = self.make_media()

        url = reverse("v1:admin:section-item-list", args=["gallery", section.pk])
        self.assertEqual(
            client.post(url, {"media": media.pk}, content_type="application/json").status_code,
            201,
        )
        self.assertEqual(
            client.post(url, {"media": media.pk}, content_type="application/json").status_code,
            400,
        )
