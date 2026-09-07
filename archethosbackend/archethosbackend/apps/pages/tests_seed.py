"""
`seed_site` — that it loads, that it is re-runnable, and that the studio's
placeholders survive as placeholders.

The last of those is the point. The frontend data files carry explicit warnings:
two headline figures are unverified, the founder is unnamed, the locations have
no address, and every photograph is licensed stock. A seed that quietly
published any of that would put unevidenced claims on a live architecture
practice's website, which is a compliance problem rather than a cosmetic one.
"""

from django.core.management import call_command
from django.test import TestCase

from archethosbackend.apps.content.models import (
    BlogPost,
    Counter,
    GalleryItem,
    Location,
    Project,
    ProjectMediaKind,
    Service,
)
from archethosbackend.apps.core.models import PublishStatus
from archethosbackend.apps.media_library.models import MediaAsset, SourceType
from archethosbackend.apps.pages.models import (
    ORDERED_PAGES,
    AboutPage,
    Company,
    HomePage,
    PrivacyPage,
    ServicesPage,
    TermsPage,
)


class SeedTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_site", verbosity=0)


class MasterDataTests(SeedTestCase):
    def test_every_service_arrives_with_its_detail_page(self):
        self.assertEqual(Service.objects.count(), 5)

        architecture = Service.objects.get(slug="architecture-design")
        self.assertEqual(architecture.number, "01")
        self.assertEqual(architecture.title_lines, ["Architecture", "Design"])
        self.assertTrue(architecture.hero_heading)
        self.assertTrue(architecture.detail_sections.exists())
        self.assertTrue(architecture.process_steps.exists())
        self.assertTrue(architecture.gallery_items.exists())

    def test_a_service_chapter_keeps_its_bullet_list(self):
        chapter = (
            Service.objects.get(slug="architecture-design").detail_sections.first()
        )
        self.assertEqual(chapter.label, "Concept & Planning")
        self.assertIn("Site study and orientation", chapter.items)

    def test_every_project_arrives_with_its_narrative(self):
        self.assertEqual(Project.objects.count(), 7)

        courtyard = Project.objects.get(slug="courtyard-house")
        self.assertEqual(courtyard.category, "RESIDENTIAL")
        self.assertEqual(courtyard.layout, "full")
        self.assertEqual(courtyard.project_year, 2024)
        self.assertTrue(courtyard.design_intent)
        self.assertTrue(courtyard.spatial_planning)
        self.assertTrue(courtyard.outcome_note)

    def test_materials_are_rows_rather_than_a_blob(self):
        materials = Project.objects.get(slug="courtyard-house").materials.all()
        self.assertEqual(
            [m.name for m in materials][:2],
            ["Board-marked concrete", "Teak"],
        )
        self.assertEqual(materials[0].note, "Structure, left exposed internally")

    def test_project_media_is_split_by_kind(self):
        courtyard = Project.objects.get(slug="courtyard-house")
        kinds = {item.kind for item in courtyard.gallery_items.all()}

        self.assertIn(ProjectMediaKind.GALLERY, kinds)
        self.assertIn(ProjectMediaKind.DRAWING, kinds)
        self.assertEqual(
            courtyard.gallery_items.filter(kind=ProjectMediaKind.GALLERY).count(), 5
        )

    def test_projects_link_to_the_services_that_delivered_them(self):
        courtyard = Project.objects.get(slug="courtyard-house")
        self.assertEqual(
            sorted(s.title for s in courtyard.services.all()),
            ["Architecture Design", "Interior Design"],
        )

    def test_the_gallery_and_journal_load(self):
        self.assertEqual(GalleryItem.objects.count(), 24)
        self.assertEqual(BlogPost.objects.count(), 6)
        self.assertTrue(BlogPost.objects.exclude(category=None).exists())

    def test_company_settings_come_from_the_frontend(self):
        company = Company.load()
        self.assertTrue(company.name)
        self.assertTrue(company.header_links)
        self.assertTrue(company.footer_links)


class PlaceholderTests(SeedTestCase):
    """What the studio has not confirmed must not go live."""

    def test_unverified_figures_are_seeded_as_drafts(self):
        for label in ("Projects delivered", "Client satisfaction"):
            with self.subTest(figure=label):
                counter = Counter.objects.get(subtitle=label)
                self.assertEqual(counter.status, PublishStatus.DRAFT)

    def test_verified_figures_are_published(self):
        for label in ("Cities served", "Disciplines in-house"):
            with self.subTest(figure=label):
                counter = Counter.objects.get(subtitle=label)
                self.assertEqual(counter.status, PublishStatus.PUBLISHED)

    def test_the_stats_band_lists_only_verified_figures(self):
        """A draft figure must not reach the page through a section item."""
        section = HomePage.objects.get().stats
        for item in section.items.all():
            self.assertEqual(item.counter.status, PublishStatus.PUBLISHED)

    def test_the_founder_is_left_unnamed(self):
        founder = AboutPage.objects.get().founder
        self.assertEqual(founder.name, "")
        self.assertEqual(founder.role, "")
        self.assertEqual(founder.credentials, "")
        self.assertFalse(founder.is_attributed)
        self.assertTrue(founder.fallback_attribution)

    def test_locations_keep_their_unconfirmed_fields_blank(self):
        for location in Location.objects.all():
            with self.subTest(city=location.city):
                self.assertEqual(location.address, "")
                self.assertEqual(location.phone, "")
                self.assertEqual(location.email, "")
                self.assertTrue(location.blurb, "the blurb IS confirmed copy")

    def test_photography_is_marked_as_stock(self):
        assets = MediaAsset.objects.all()
        self.assertEqual(assets.count(), 46)
        for asset in assets:
            with self.subTest(asset=asset.title):
                self.assertEqual(asset.source_type, SourceType.EXTERNAL)
                self.assertIn("placeholder", asset.tags)
                self.assertTrue(asset.alt_text, "alt text must survive the import")

    def test_the_legal_pages_are_not_published(self):
        """No copy has been supplied, and legal text is not ours to draft."""
        for model in (PrivacyPage, TermsPage):
            with self.subTest(page=model.__name__):
                page = model.objects.get()
                self.assertFalse(page.is_published)
                self.assertIsNotNone(page.body)


class PageTests(SeedTestCase):
    def test_every_page_except_the_legal_two_is_published(self):
        for route, model in ORDERED_PAGES.items():
            with self.subTest(route=route):
                page = model.objects.get()
                expected = not route.startswith("legal/")
                self.assertEqual(page.is_published, expected)

    def test_no_published_page_is_missing_a_required_section(self):
        for route, model in ORDERED_PAGES.items():
            page = model.objects.get()
            if page.is_published:
                with self.subTest(route=route):
                    self.assertEqual(page.missing_sections(), [])

    def test_the_home_hero_carries_all_three_slides(self):
        """Three slides is the fact. Whether they advance is the component's
        business — there is no `variant` column to assert against."""
        hero = HomePage.objects.get().hero
        slides = list(hero.slides.all())
        self.assertEqual(len(slides), 3)
        self.assertEqual(slides[0].heading, "Spaces shaped around the way you live.")
        self.assertTrue(all(slide.media_id for slide in slides))

    def test_the_intro_keeps_its_hand_broken_headline(self):
        intro = HomePage.objects.get().intro
        self.assertEqual(intro.statement_lines[0], "We don't simply")
        self.assertEqual(len(intro.statement_lines), 5)

    def test_sections_reference_master_data_rather_than_copying_it(self):
        section = ServicesPage.objects.get().index
        item = section.items.first()

        self.assertEqual(item.service, Service.objects.get(slug="architecture-design"))

        # The proof: change the record, and the page shows the change.
        item.service.title = "Architecture"
        item.service.save()
        self.assertEqual(section.items.first().service.title, "Architecture")

    def test_the_project_index_is_left_uncurated(self):
        """Empty means "every published project", so new work appears on its own."""
        self.assertFalse(ORDERED_PAGES["projects"].objects.get().index.items.exists())

    def test_the_about_page_gets_mission_and_vision(self):
        blocks = list(AboutPage.objects.get().mission_vision.blocks.all())
        self.assertEqual([b.eyebrow for b in blocks], ["Mission", "Vision"])
        self.assertEqual([b.side for b in blocks], ["right", "left"])
        self.assertTrue(blocks[0].points)


class IdempotenceTests(TestCase):
    def test_running_it_twice_changes_nothing(self):
        call_command("seed_site", verbosity=0)
        counts = {
            model: model.objects.count()
            for model in (MediaAsset, Service, Project, GalleryItem, Location, BlogPost)
        }

        call_command("seed_site", verbosity=0)

        for model, before in counts.items():
            with self.subTest(model=model.__name__):
                self.assertEqual(model.objects.count(), before)

    def test_a_second_run_does_not_orphan_sections(self):
        """Page sections are rebuilt, so the old rows have to actually go."""
        from archethosbackend.apps.pages.models import HeroSection

        call_command("seed_site", verbosity=0)
        first = HeroSection.objects.count()

        call_command("seed_site", verbosity=0)
        self.assertEqual(HeroSection.objects.count(), first)

    def test_pages_only_leaves_master_data_alone(self):
        call_command("seed_site", verbosity=0)
        Service.objects.filter(slug="architecture-design").update(title="Edited")

        call_command("seed_site", "--pages-only", verbosity=0)

        self.assertEqual(
            Service.objects.get(slug="architecture-design").title, "Edited"
        )
