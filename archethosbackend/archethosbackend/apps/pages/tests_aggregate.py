"""
Aggregate page API tests.

Two things carry the most weight:

  * nothing unpublished may surface — not the page, and not master content
    referenced from inside a section;
  * the query count must stay flat as content grows. That is the entire claim of
    the batched MTI resolution, so it is pinned with assertNumQueries rather than
    left as an aspiration in a comment.
"""

from django.test import Client, TestCase
from django.urls import reverse

from archethosbackend.apps.content.models import FAQ, Counter, Project, Service
from archethosbackend.apps.core.models import PublishStatus
from archethosbackend.apps.media_library.models import MediaAsset, MediaType, SourceType
from archethosbackend.apps.sections.models import (
    CounterSection,
    CounterSectionItem,
    CTASection,
    FAQSection,
    FAQSectionItem,
    FeaturedProjectItem,
    FeaturedProjectsSection,
    GallerySection,
    GallerySectionItem,
    HeroSection,
    HeroSlide,
    IntroSection,
    ServiceSectionItem,
    ServicesSection,
)

from .models import Company, Page, PageSection


def media(name):
    return MediaAsset.objects.create(
        media_type=MediaType.IMAGE,
        source_type=SourceType.UPLOAD,
        file=f"uploads/{name}",
        alt_text=f"alt {name}",
        width=1600,
        height=900,
    )


class AggregateTestCase(TestCase):
    def setUp(self):
        self.page = Page.objects.get(slug="home")
        self.page.status = PublishStatus.PUBLISHED
        self.page.meta_title = "Archethos"
        self.page.meta_description = "Architecture and design studio"
        self.page.save()
        self.order = 0

    def attach(self, section, key):
        self.order += 1
        return PageSection.objects.create(
            page=self.page, section=section, section_key=key, order=self.order
        )

    def get(self, slug="home", **kwargs):
        return Client().get(reverse("v1:public:page-aggregate", args=[slug]), **kwargs)


# ─── Shape ───────────────────────────────────────────────────────────────────


class AggregateShapeTests(AggregateTestCase):
    def test_page_with_no_sections_returns_an_empty_list(self):
        body = self.get().json()["data"]
        self.assertEqual(body["slug"], "home")
        self.assertEqual(body["sections"], [])
        self.assertEqual(body["seo"]["meta_title"], "Archethos")

    def test_sections_carry_key_type_and_data(self):
        hero = HeroSection.objects.create(internal_label="Home - main hero")
        HeroSlide.objects.create(
            section=hero, heading="Spaces shaped around\nthe way you live.",
            label="Architecture", media=media("hero.png"), order=1,
        )
        self.attach(hero, "main_hero")

        section = self.get().json()["data"]["sections"][0]
        self.assertEqual(section["key"], "main_hero")
        self.assertEqual(section["type"], "hero")
        self.assertEqual(
            section["data"]["slides"][0]["heading_lines"],
            ["Spaces shaped around", "the way you live."],
        )
        self.assertEqual(section["data"]["slides"][0]["media"], "/media/uploads/hero.png")

    def test_sections_come_back_in_placement_order(self):
        for index, key in enumerate(["a", "b", "c"]):
            self.attach(
                CTASection.objects.create(internal_label=key, heading="Hi"), key
            )

        keys = [s["key"] for s in self.get().json()["data"]["sections"]]
        self.assertEqual(keys, ["a", "b", "c"])

    def test_reordering_placements_reorders_the_payload(self):
        placements = [
            self.attach(CTASection.objects.create(internal_label=k, heading="Hi"), k)
            for k in ("a", "b", "c")
        ]
        placements[2].order = 0
        placements[2].save()

        keys = [s["key"] for s in self.get().json()["data"]["sections"]]
        self.assertEqual(keys, ["c", "a", "b"])

    def test_the_same_type_twice_renders_twice_with_distinct_keys(self):
        """The capability the fixed-slot design could not express."""
        self.attach(CTASection.objects.create(internal_label="Top", heading="A"), "top_cta")
        self.attach(
            CTASection.objects.create(internal_label="Bottom", heading="B"), "bottom_cta"
        )

        sections = self.get().json()["data"]["sections"]
        self.assertEqual([s["type"] for s in sections], ["cta", "cta"])
        self.assertEqual([s["key"] for s in sections], ["top_cta", "bottom_cta"])
        self.assertEqual([s["data"]["heading"] for s in sections], ["A", "B"])

    def test_internal_label_never_reaches_the_payload(self):
        self.attach(
            HeroSection.objects.create(internal_label="Home - main hero"), "main_hero"
        )
        self.assertNotIn("Home - main hero", self.get().content.decode())

    def test_invisible_placements_are_omitted(self):
        visible = self.attach(
            CTASection.objects.create(internal_label="Shown", heading="A"), "shown"
        )
        hidden = self.attach(
            CTASection.objects.create(internal_label="Hidden", heading="B"), "hidden"
        )
        hidden.is_visible = False
        hidden.save()

        keys = [s["key"] for s in self.get().json()["data"]["sections"]]
        self.assertEqual(keys, ["shown"])
        self.assertTrue(visible.is_visible)


# ─── Publication ─────────────────────────────────────────────────────────────


class AggregatePublicationTests(AggregateTestCase):
    def test_draft_page_is_404(self):
        self.page.status = PublishStatus.DRAFT
        self.page.save()
        self.assertEqual(self.get().status_code, 404)

    def test_archived_page_is_404(self):
        self.page.status = PublishStatus.ARCHIVED
        self.page.save()
        self.assertEqual(self.get().status_code, 404)

    def test_unknown_slug_is_404(self):
        self.assertEqual(self.get("does-not-exist").status_code, 404)

    def test_404_body_is_the_error_envelope(self):
        body = self.get("does-not-exist").json()
        self.assertFalse(body["success"])
        self.assertEqual(body["code"], "not_found")

    def test_nested_slugs_resolve(self):
        """`legal/privacy` needs <path:slug>; <slug:slug> would never match."""
        page = Page.objects.get(slug="legal/privacy")
        page.status = PublishStatus.PUBLISHED
        page.save()

        response = self.get("legal/privacy")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["slug"], "legal/privacy")

    def test_needs_no_authentication(self):
        self.assertEqual(self.get().status_code, 200)


class DraftContentInsideSectionsTests(AggregateTestCase):
    """A published section must not become a back door to draft content."""

    def test_draft_faqs_are_filtered_out(self):
        section = FAQSection.objects.create(internal_label="Home FAQ")
        live = FAQ.objects.create(
            question="Live?", answer="Yes", status=PublishStatus.PUBLISHED
        )
        draft = FAQ.objects.create(question="Secret?", answer="Hidden")
        FAQSectionItem.objects.create(section=section, faq=live, order=1)
        FAQSectionItem.objects.create(section=section, faq=draft, order=2)
        self.attach(section, "faq")

        data = self.get().json()["data"]["sections"][0]["data"]
        self.assertEqual([i["question"] for i in data["items"]], ["Live?"])
        self.assertNotIn("Secret?", self.get().content.decode())

    def test_draft_projects_are_filtered_out(self):
        section = FeaturedProjectsSection.objects.create(internal_label="Selected")
        live = Project.objects.create(title="Live Villa", status=PublishStatus.PUBLISHED)
        draft = Project.objects.create(title="Secret Villa")
        FeaturedProjectItem.objects.create(section=section, project=live, order=1)
        FeaturedProjectItem.objects.create(section=section, project=draft, order=2)
        self.attach(section, "featured")

        data = self.get().json()["data"]["sections"][0]["data"]
        self.assertEqual([i["title"] for i in data["items"]], ["Live Villa"])

    def test_draft_services_and_counters_are_filtered_out(self):
        services = ServicesSection.objects.create(internal_label="What we do")
        ServiceSectionItem.objects.create(
            section=services,
            service=Service.objects.create(title="Architecture", status=PublishStatus.PUBLISHED),
            order=1,
        )
        ServiceSectionItem.objects.create(
            section=services, service=Service.objects.create(title="Unannounced"), order=2
        )
        self.attach(services, "services")

        counters = CounterSection.objects.create(internal_label="At a glance")
        CounterSectionItem.objects.create(
            section=counters,
            counter=Counter.objects.create(
                content="40", postfix="+", subtitle="PROJECTS",
                status=PublishStatus.PUBLISHED,
            ),
            order=1,
        )
        CounterSectionItem.objects.create(
            section=counters,
            counter=Counter.objects.create(content="99", subtitle="HIDDEN"),
            order=2,
        )
        self.attach(counters, "counters")

        sections = {s["key"]: s["data"] for s in self.get().json()["data"]["sections"]}
        self.assertEqual([i["title"] for i in sections["services"]["items"]], ["Architecture"])
        self.assertEqual([i["subtitle"] for i in sections["counters"]["items"]], ["PROJECTS"])


# ─── Query budget ────────────────────────────────────────────────────────────


#: Measured, not guessed: 2 setup queries (page, placements) + 1 per simple
#: section type + 2 per collection type (the section batch and its prefetch).
#: For the 8-section page below: 2 + intro + cta + 3x2 collections + hero 2 = 16.
FULL_PAGE_QUERIES = 16


class AggregateQueryBudgetTests(AggregateTestCase):
    """The batched-by-type claim, pinned.

    If a future serializer change reintroduces N+1, these fail rather than the
    site quietly getting slower.
    """

    def build_full_page(self, gallery_images=4, faqs=3, projects=3):
        hero = HeroSection.objects.create(internal_label="Hero")
        for i in range(3):
            HeroSlide.objects.create(
                section=hero, heading=f"Line {i}", media=media(f"hero{i}.png"), order=i
            )
        self.attach(hero, "main_hero")

        self.attach(
            IntroSection.objects.create(
                internal_label="Intro", heading="Studio", image=media("intro.png")
            ),
            "intro",
        )

        counters = CounterSection.objects.create(internal_label="Counters")
        for i in range(4):
            CounterSectionItem.objects.create(
                section=counters,
                counter=Counter.objects.create(
                    content=str(i), subtitle=f"STAT {i}", status=PublishStatus.PUBLISHED
                ),
                order=i,
            )
        self.attach(counters, "at_a_glance")

        featured = FeaturedProjectsSection.objects.create(internal_label="Featured")
        for i in range(projects):
            FeaturedProjectItem.objects.create(
                section=featured,
                project=Project.objects.create(
                    title=f"Project {i}",
                    status=PublishStatus.PUBLISHED,
                    featured_image=media(f"p{i}.png"),
                ),
                order=i,
            )
        self.attach(featured, "featured_work")

        services = ServicesSection.objects.create(internal_label="Services")
        for i in range(3):
            ServiceSectionItem.objects.create(
                section=services,
                service=Service.objects.create(
                    title=f"Service {i}",
                    status=PublishStatus.PUBLISHED,
                    icon=media(f"s{i}.png"),
                ),
                order=i,
            )
        self.attach(services, "services")

        gallery = GallerySection.objects.create(internal_label="Gallery")
        for i in range(gallery_images):
            GallerySectionItem.objects.create(
                section=gallery, media=media(f"g{i}.png"), order=i
            )
        self.attach(gallery, "gallery")

        faq = FAQSection.objects.create(internal_label="FAQ")
        for i in range(faqs):
            FAQSectionItem.objects.create(
                section=faq,
                faq=FAQ.objects.create(
                    question=f"Q{i}?", answer="A", status=PublishStatus.PUBLISHED
                ),
                order=i,
            )
        self.attach(faq, "faq")

        self.attach(
            CTASection.objects.create(
                internal_label="CTA", heading="Let's build",
                background_media=media("cta.png"),
            ),
            "bottom_cta",
        )

    def test_a_full_eight_section_page_stays_within_budget(self):
        self.build_full_page()

        with self.assertNumQueries(FULL_PAGE_QUERIES):
            response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]["sections"]), 8)

    def test_query_count_is_flat_as_content_grows(self):
        """The whole point: 40 gallery images cost the same as 4."""
        self.build_full_page(gallery_images=4, faqs=3, projects=3)
        with self.assertNumQueries(FULL_PAGE_QUERIES):
            small = self.get()

        Page.objects.filter(slug="about").update(status=PublishStatus.PUBLISHED)
        big_page = Page.objects.get(slug="about")
        self.page = big_page
        self.order = 0
        self.build_full_page(gallery_images=40, faqs=30, projects=25)

        with self.assertNumQueries(FULL_PAGE_QUERIES):
            big = self.get("about")

        self.assertEqual(small.status_code, 200)
        self.assertEqual(big.status_code, 200)
        self.assertEqual(len(big.json()["data"]["sections"][5]["data"]["items"]), 40)

    def test_repeating_a_type_does_not_add_queries(self):
        """Two CTAs are one batch, not two."""
        for key in ("top_cta", "mid_cta", "bottom_cta"):
            self.attach(
                CTASection.objects.create(internal_label=key, heading="Hi"), key
            )

        # page + placements + one CTA batch
        with self.assertNumQueries(3):
            response = self.get()
        self.assertEqual(len(response.json()["data"]["sections"]), 3)

    def test_an_empty_page_costs_two_queries(self):
        with self.assertNumQueries(2):
            self.get()


# ─── Caching ─────────────────────────────────────────────────────────────────


class AggregateCachingTests(AggregateTestCase):
    def test_response_carries_etag_and_cache_headers(self):
        response = self.get()
        self.assertTrue(response["ETag"])
        self.assertIn("max-age=60", response["Cache-Control"])
        self.assertIn("stale-while-revalidate", response["Cache-Control"])
        self.assertTrue(response["Last-Modified"])

    def test_matching_etag_returns_304(self):
        etag = self.get()["ETag"]
        response = self.get(HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(response.status_code, 304)

    def test_etag_changes_when_the_page_changes(self):
        before = self.get()["ETag"]
        self.page.meta_title = "Changed"
        self.page.save()
        self.assertNotEqual(self.get()["ETag"], before)

    def test_etag_changes_when_a_section_changes(self):
        """Editing a shared CTA must invalidate every page composing it."""
        cta = CTASection.objects.create(internal_label="CTA", heading="Before")
        self.attach(cta, "bottom_cta")
        before = self.get()["ETag"]

        cta.heading = "After"
        cta.save()
        self.assertNotEqual(self.get()["ETag"], before)

    def test_etag_changes_when_a_placement_is_hidden(self):
        placement = self.attach(
            CTASection.objects.create(internal_label="CTA", heading="Hi"), "cta"
        )
        before = self.get()["ETag"]

        placement.is_visible = False
        placement.save()
        self.assertNotEqual(self.get()["ETag"], before)


# ─── Company ─────────────────────────────────────────────────────────────────


class PublicCompanyTests(TestCase):
    def test_company_is_public_and_includes_inject_fields(self):
        company = Company.load()
        company.name = "Archethos"
        company.header_links = [{"label": "Projects", "url": "/projects"}]
        company.head_inject = "<meta name='x' content='y'>"
        company.save()

        response = Client().get(reverse("v1:public:company"))
        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]
        self.assertEqual(data["name"], "Archethos")
        self.assertEqual(data["header_links"][0]["label"], "Projects")
        # The frontend has to render these, so they are deliberately public.
        self.assertIn("meta", data["head_inject"])

    def test_company_needs_no_authentication(self):
        self.assertEqual(Client().get(reverse("v1:public:company")).status_code, 200)
