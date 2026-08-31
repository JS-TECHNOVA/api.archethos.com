"""
Page composition tests.

The load-bearing behaviours here are the ones the old fixed-slot design could not
express: the same section on several pages, and the same section *type* twice on
one page under different keys.
"""

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from archethosbackend.apps.core.models import PublishStatus
from archethosbackend.apps.media_library.models import MediaAsset, MediaType, SourceType
from archethosbackend.apps.sections.models import CTASection, FAQSection, HeroSection

from .models import Company, Page, PageSection


class PageTestCase(TestCase):
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


# ─── Seeded pages ────────────────────────────────────────────────────────────


class SeededPageTests(PageTestCase):
    def test_one_page_exists_per_frontend_route(self):
        slugs = set(Page.objects.values_list("slug", flat=True))
        self.assertEqual(
            slugs,
            {
                "home", "about", "contact", "gallery", "journal", "projects",
                "services", "locations", "legal/privacy", "legal/terms",
            },
        )

    def test_seeded_pages_start_as_drafts(self):
        """A page with no sections has nothing to render, so publishing is a
        deliberate act once its composition exists."""
        self.assertEqual(Page.objects.exclude(status=PublishStatus.DRAFT).count(), 0)


# ─── Slug rules ──────────────────────────────────────────────────────────────


class PageSlugTests(PageTestCase):
    def test_nested_slugs_are_allowed(self):
        """`legal/privacy` is a real frontend route, and a plain SlugField would
        reject it — which the seed migration would have hidden, because RunPython
        skips validation."""
        page = Page(name="Cookies", slug="legal/cookies")
        page.full_clean()  # must not raise

    def test_malformed_slugs_are_rejected(self):
        for slug in ["Bad Slug", "/leading", "trailing/", "double//slash", "UPPER"]:
            with self.subTest(slug=slug):
                with self.assertRaises(ValidationError):
                    Page(name="X", slug=slug).full_clean()

    def test_slug_is_unique(self):
        response = self.admin_client().post(
            reverse("v1:admin:page-list"),
            {"name": "Another Home", "slug": "home"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("slug", response.json()["errors"])


# ─── Composition ─────────────────────────────────────────────────────────────


class PageCompositionTests(PageTestCase):
    def setUp(self):
        self.client_ = self.admin_client()
        self.page = Page.objects.get(slug="home")
        self.hero = HeroSection.objects.create(internal_label="Home - main hero")
        self.cta = CTASection.objects.create(
            internal_label="Global - start a project", heading="Let's build"
        )
        self.faq = FAQSection.objects.create(internal_label="Home FAQ")

    def attach(self, section, key, order=0, page=None):
        return self.client_.post(
            reverse("v1:admin:page-section-list", args=[(page or self.page).pk]),
            {"section": section.pk, "section_key": key, "order": order},
            content_type="application/json",
        )

    def test_attach_and_list(self):
        self.assertEqual(self.attach(self.hero, "main_hero", 1).status_code, 201)
        self.assertEqual(self.attach(self.faq, "homepage_faq", 2).status_code, 201)

        body = self.client_.get(
            reverse("v1:admin:page-section-list", args=[self.page.pk])
        ).json()
        self.assertEqual([row["section_key"] for row in body["data"]],
                         ["main_hero", "homepage_faq"])
        # Composition is short and always shown whole; paginating would break
        # drag-and-drop ordering.
        self.assertNotIn("pagination", body)

    def test_the_same_section_type_can_appear_twice_under_different_keys(self):
        """The capability the fixed-slot design could not express at all."""
        second_cta = CTASection.objects.create(
            internal_label="Home - top CTA", heading="Talk to us"
        )
        self.assertEqual(self.attach(self.cta, "bottom_cta", 9).status_code, 201)
        self.assertEqual(self.attach(second_cta, "top_cta", 1).status_code, 201)

        types = list(
            PageSection.objects.filter(page=self.page).values_list(
                "section__section_type", flat=True
            )
        )
        self.assertEqual(types, ["cta", "cta"])

    def test_a_section_key_cannot_be_reused_on_one_page(self):
        self.attach(self.cta, "bottom_cta")
        response = self.attach(
            CTASection.objects.create(internal_label="Other", heading="Hi"), "bottom_cta"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("section_key", response.json()["errors"])

    def test_the_same_section_can_be_shared_across_pages(self):
        """Editing it once updates every page that composes it."""
        about = Page.objects.get(slug="about")
        self.assertEqual(self.attach(self.cta, "bottom_cta").status_code, 201)
        self.assertEqual(
            self.attach(self.cta, "bottom_cta", page=about).status_code, 201
        )
        self.assertEqual(self.cta.page_usages.count(), 2)

    def test_detaching_leaves_the_section_intact(self):
        placement = self.attach(self.cta, "bottom_cta").json()["data"]["id"]
        self.client_.delete(
            reverse("v1:admin:page-section-detail", args=[self.page.pk, placement])
        )
        self.assertEqual(PageSection.objects.count(), 0)
        self.assertTrue(CTASection.objects.filter(pk=self.cta.pk).exists())

    def test_deleting_a_page_removes_placements_but_not_sections(self):
        self.attach(self.hero, "main_hero")
        self.attach(self.cta, "bottom_cta")
        self.client_.delete(reverse("v1:admin:page-detail", args=[self.page.pk]))

        self.assertEqual(PageSection.objects.filter(page_id=self.page.pk).count(), 0)
        self.assertTrue(HeroSection.objects.filter(pk=self.hero.pk).exists())
        self.assertTrue(CTASection.objects.filter(pk=self.cta.pk).exists())

    def test_a_section_attached_to_a_page_cannot_be_deleted(self):
        """PROTECT: a section in use must not vanish from under a live page."""
        self.attach(self.cta, "bottom_cta")
        response = self.client_.delete(
            reverse("v1:admin:section-detail", args=["cta", self.cta.pk])
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "protected")

    def test_visibility_is_per_placement(self):
        about = Page.objects.get(slug="about")
        home_placement = self.attach(self.cta, "bottom_cta").json()["data"]["id"]
        self.attach(self.cta, "bottom_cta", page=about)

        self.client_.patch(
            reverse("v1:admin:page-section-detail", args=[self.page.pk, home_placement]),
            {"is_visible": False},
            content_type="application/json",
        )

        self.assertFalse(PageSection.objects.get(pk=home_placement).is_visible)
        self.assertTrue(PageSection.objects.filter(page=about, is_visible=True).exists())

    def test_page_detail_includes_composition(self):
        self.attach(self.hero, "main_hero", 1)
        data = self.client_.get(
            reverse("v1:admin:page-detail", args=[self.page.pk])
        ).json()["data"]

        self.assertEqual(len(data["page_sections"]), 1)
        self.assertEqual(data["page_sections"][0]["section_type"], "hero")
        self.assertEqual(
            data["page_sections"][0]["internal_label"], "Home - main hero"
        )

    def test_page_list_stays_light(self):
        self.attach(self.hero, "main_hero")
        row = self.client_.get(reverse("v1:admin:page-list")).json()["data"]
        home = next(r for r in row if r["slug"] == "home")
        self.assertEqual(home["sections_count"], 1)
        self.assertNotIn("page_sections", home)


class PageSectionReorderTests(PageTestCase):
    def setUp(self):
        self.client_ = self.admin_client()
        self.page = Page.objects.get(slug="home")
        self.placements = []
        for index in range(3):
            section = CTASection.objects.create(
                internal_label=f"CTA {index}", heading="Hi"
            )
            self.placements.append(
                PageSection.objects.create(
                    page=self.page, section=section,
                    section_key=f"cta_{index}", order=index,
                )
            )

    def url(self):
        return reverse("v1:admin:page-section-reorder", args=[self.page.pk])

    def test_reorder_applies(self):
        response = self.client_.patch(
            self.url(),
            {"sections": [
                {"id": self.placements[2].pk, "order": 1},
                {"id": self.placements[0].pk, "order": 2},
                {"id": self.placements[1].pk, "order": 3},
            ]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            list(self.page.page_sections.values_list("id", flat=True)),
            [self.placements[2].pk, self.placements[0].pk, self.placements[1].pk],
        )

    def test_reorder_rejects_a_placement_from_another_page(self):
        about = Page.objects.get(slug="about")
        foreign = PageSection.objects.create(
            page=about,
            section=CTASection.objects.create(internal_label="X", heading="Hi"),
            section_key="cta", order=1,
        )
        response = self.client_.patch(
            self.url(),
            {"sections": [
                {"id": self.placements[0].pk, "order": 1},
                {"id": foreign.pk, "order": 2},
            ]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        foreign.refresh_from_db()
        self.assertEqual(foreign.order, 1)

    def test_reorder_is_atomic(self):
        before = list(self.page.page_sections.values_list("id", "order"))
        self.client_.patch(
            self.url(),
            {"sections": [
                {"id": self.placements[0].pk, "order": 9},
                {"id": 999999, "order": 1},
            ]},
            content_type="application/json",
        )
        self.assertEqual(
            list(self.page.page_sections.values_list("id", "order")), before
        )

    def test_reorder_rejects_malformed_payloads(self):
        for payload in ({}, {"sections": []}, {"sections": "x"},
                        {"sections": [{"id": 1}]}, {"sections": [{"id": 1, "order": -1}]}):
            with self.subTest(payload=payload):
                self.assertEqual(
                    self.client_.patch(
                        self.url(), payload, content_type="application/json"
                    ).status_code,
                    400,
                )


# ─── Section usage (deferred from Phase 7) ───────────────────────────────────


class SectionUsageTests(PageTestCase):
    def test_usage_lists_the_pages_composing_a_section(self):
        client = self.admin_client()
        cta = CTASection.objects.create(internal_label="Global CTA", heading="Hi")

        for slug, key in [("home", "bottom_cta"), ("about", "closing_cta")]:
            PageSection.objects.create(
                page=Page.objects.get(slug=slug), section=cta, section_key=key
            )

        body = client.get(
            reverse("v1:admin:section-usage", args=["cta", cta.pk])
        ).json()["data"]

        self.assertEqual(body["count"], 2)
        self.assertEqual(
            {row["page_slug"] for row in body["used_by"]}, {"home", "about"}
        )

    def test_browse_reports_how_many_pages_use_each_section(self):
        client = self.admin_client()
        used = CTASection.objects.create(internal_label="Used", heading="Hi")
        CTASection.objects.create(internal_label="Unused", heading="Hi")
        PageSection.objects.create(
            page=Page.objects.get(slug="home"), section=used, section_key="cta"
        )

        rows = client.get(
            reverse("v1:admin:section-browse") + "?section_type=cta"
        ).json()["data"]
        counts = {row["internal_label"]: row["used_by_count"] for row in rows}
        self.assertEqual(counts, {"Used": 1, "Unused": 0})


# ─── Permissions ─────────────────────────────────────────────────────────────


class PagePermissionTests(PageTestCase):
    def test_composition_requires_change_page(self):
        user = self.make_user("viewer@archethos.test", permissions=["view_page"])
        client = self.client_for(user)
        page = Page.objects.get(slug="home")

        self.assertEqual(client.get(reverse("v1:admin:page-list")).status_code, 200)
        self.assertEqual(
            client.post(
                reverse("v1:admin:page-section-list", args=[page.pk]),
                {"section": 1, "section_key": "x"},
                content_type="application/json",
            ).status_code,
            403,
        )

    def test_anonymous_is_rejected(self):
        self.assertEqual(Client().get(reverse("v1:admin:page-list")).status_code, 401)


# ─── Company ─────────────────────────────────────────────────────────────────


class CompanyTests(PageTestCase):
    def test_singleton_is_created_on_first_load_and_never_duplicated(self):
        Company.objects.all().delete()
        first = Company.load()
        second = Company.load()
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Company.objects.count(), 1)

    def test_get_and_patch_without_an_id_in_the_url(self):
        client = self.admin_client()

        self.assertEqual(client.get(reverse("v1:admin:company-detail")).status_code, 200)
        response = client.patch(
            reverse("v1:admin:company-detail"),
            {"name": "Archethos", "social_urls": {"instagram": "https://ig.test/a"}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Company.load().name, "Archethos")

    def test_json_fields_are_validated(self):
        client = self.admin_client()
        for field, bad in [
            ("social_urls", ["not", "an", "object"]),
            ("contacts", "a string"),
            ("header_links", [{"label": "No url"}]),
            ("footer_links", [{"heading": "No links"}]),
        ]:
            with self.subTest(field=field):
                response = client.patch(
                    reverse("v1:admin:company-detail"),
                    {field: bad},
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json()["errors"])

    def test_valid_json_shapes_are_accepted(self):
        response = self.admin_client().patch(
            reverse("v1:admin:company-detail"),
            {
                "social_urls": {"instagram": "https://ig.test/a"},
                "contacts": {"emails": ["hi@archethos.test"], "whatsapp": "+91"},
                "header_links": [{"label": "Projects", "url": "/projects"}],
                "footer_links": [
                    {"heading": "Company", "links": [{"label": "About", "url": "/about"}]}
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_inject_fields_are_superuser_only(self):
        """They render on every page of the live site, so writing them is a
        different level of trust from editing a phone number."""
        editor = self.make_user(
            "editor@archethos.test", permissions=["view_company", "change_company"]
        )
        client = self.client_for(editor)

        response = client.patch(
            reverse("v1:admin:company-detail"),
            {"head_inject": "<script>alert(1)</script>"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("head_inject", response.json()["errors"])
        self.assertEqual(Company.load().head_inject, "")

    def test_a_non_superuser_can_still_edit_everything_else(self):
        editor = self.make_user(
            "editor@archethos.test", permissions=["view_company", "change_company"]
        )
        response = self.client_for(editor).patch(
            reverse("v1:admin:company-detail"),
            {"name": "Archethos Studio"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    def test_a_superuser_can_write_inject_fields(self):
        response = self.admin_client().patch(
            reverse("v1:admin:company-detail"),
            {"head_inject": "<meta name='x' content='y'>"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("meta", Company.load().head_inject)

    def test_logo_uses_the_media_reference_field(self):
        media = MediaAsset.objects.create(
            media_type=MediaType.IMAGE, source_type=SourceType.UPLOAD,
            file="uploads/logo.png",
        )
        response = self.admin_client().patch(
            reverse("v1:admin:company-detail"),
            {"logo": media.relative_path},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Company.load().logo, media)
        self.assertEqual(response.json()["data"]["logo"], "/media/uploads/logo.png")
