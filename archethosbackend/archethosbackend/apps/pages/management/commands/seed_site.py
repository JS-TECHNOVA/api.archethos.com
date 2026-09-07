"""
Load the studio's launch content.

    manage.py seed_site

Idempotent. Every record is matched on a natural key — a slug, a city, a URL —
so re-running updates rather than duplicating, and a partial failure can be
fixed and re-run rather than unpicked.

The content is the frontend's, dumped from `src/data/*.js` (see
`pages/seed_data/__init__.py`) plus the copy that lives in the page components.
This command owns the mapping between that shape and the models; it invents
nothing.

Two placeholders are carried across as placeholders, deliberately:

* **Photography** is licensed stock, seeded as `EXTERNAL` assets pointing at
  Unsplash. Replacing them is an upload and a re-point, not a schema change.
* **Two of the four headline figures** ("Projects delivered", "Client
  satisfaction") are marked unverified in `stats.js`. They are seeded as
  **drafts**, so the studio must confirm them before either can reach the site.
  Publishing an unevidenced "100% client satisfaction" is an advertising
  compliance problem, not a cosmetic one.

Nothing is invented for the founder or for location addresses either: both are
blank in the source and stay blank here.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from archethosbackend.apps.content.models import (
    BlogCategory,
    BlogPost,
    Counter,
    GalleryCategory,
    GalleryItem,
    Location,
    Project,
    ProjectCategory,
    ProjectGalleryItem,
    ProjectLayout,
    ProjectMaterial,
    ProjectMediaKind,
    ProjectStatus,
    Service,
    ServiceDetailSection,
    ServiceGalleryItem,
    ServiceProcessStep,
)
from archethosbackend.apps.core.models import PublishStatus
from archethosbackend.apps.media_library.models import (
    MediaAsset,
    MediaLocation,
    MediaType,
    SourceType,
)
from archethosbackend.apps.pages import models as page_models
from archethosbackend.apps.pages.seed_data import load
from archethosbackend.apps.pages.seed_data import pages as copy

PUBLISHED = {"status": PublishStatus.PUBLISHED}


class Command(BaseCommand):
    help = "Load the studio's launch content. Safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument(
            "--pages-only",
            action="store_true",
            help="Skip master data and only rebuild the page sections.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.data = load()
        self.now = timezone.now()
        self.media = {}

        self.say("Media")
        self.seed_media()

        if not options["pages_only"]:
            self.say("Master data")
            self.seed_services()
            self.seed_projects()
            self.seed_gallery()
            self.seed_locations()
            self.seed_counters()
            self.seed_journal()
            self.seed_company()

        self.say("Pages")
        self.seed_pages()

        self.stdout.write(self.style.SUCCESS("\n  Seeded."))

    # ── helpers ──────────────────────────────────────────────────────────────

    def say(self, label):
        self.stdout.write(f"\n\033[1m-- {label}\033[0m")

    def note(self, line):
        self.stdout.write(f"  {line}")

    def asset(self, key):
        """A MediaAsset for a frontend media key, or None if it is unset."""
        if not key:
            return None
        return self.media.get(key)

    def published(self, model, defaults, **lookup):
        obj, created = model.objects.update_or_create(
            defaults={**defaults, **PUBLISHED}, **lookup
        )
        if obj.published_at is None:
            obj.published_at = self.now
            obj.save(update_fields=["published_at"])
        return obj, created

    @staticmethod
    def replace(manager, model, rows):
        """Rewrite an owned collection, position carrying the order."""
        manager.all().delete()
        model.objects.bulk_create(
            [model(order=index, **row) for index, row in enumerate(rows)]
        )

    # ── media ────────────────────────────────────────────────────────────────

    def seed_media(self):
        """One EXTERNAL asset per entry in the frontend's media catalogue.

        Keyed on the URL, so re-running is a no-op and swapping a photograph in
        the frontend creates a new asset rather than silently repointing one
        that other records may already reference.
        """
        created = 0
        for key, entry in self.data["media"]["media"].items():
            asset, made = MediaAsset.objects.update_or_create(
                external_url=entry["src"],
                defaults={
                    "media_type": MediaType.IMAGE,
                    "source_type": SourceType.EXTERNAL,
                    "media_location": MediaLocation.EXTERNAL,
                    "title": _humanise(key),
                    "alt_text": entry["alt"],
                    "description": (
                        "Licensed stock photography standing in for the studio's "
                        "own work. Replace before launch."
                    ),
                    "tags": ["placeholder", "stock"],
                },
            )
            self.media[key] = asset
            created += made

        self.note(f"{len(self.media)} assets ({created} new) - all EXTERNAL placeholders")

    # ── master data ──────────────────────────────────────────────────────────

    def seed_services(self):
        for entry in self.data["services"]["services"]:
            service, _ = self.published(
                Service,
                {
                    "number": entry.get("number") or "",
                    "title": entry["title"],
                    "title_lines": entry.get("titleLines") or [],
                    "hero_heading": entry.get("heroHeading") or "",
                    "short_description": entry.get("shortDescription") or "",
                    "description": entry.get("description") or "",
                    "hero_image": self.asset(_key(entry.get("heroImage"), self.data)),
                    "index_image": self.asset(_key(entry.get("indexImage"), self.data)),
                    "is_featured": bool(entry.get("featured")),
                    "process_label": (entry.get("process") or {}).get("label") or "",
                    "order": int(entry.get("number") or 0),
                },
                slug=entry["slug"],
            )

            self.replace(
                service.detail_sections,
                ServiceDetailSection,
                [
                    {
                        "service": service,
                        "label": section["label"],
                        "heading": section.get("heading") or "",
                        "body": section.get("body") or "",
                        "items": section.get("items") or [],
                        "image": self.asset(_key(section.get("image"), self.data)),
                        "image_ratio": section.get("imageRatio", "16/9"),
                    }
                    for section in entry.get("sections") or []
                ],
            )

            self.replace(
                service.process_steps,
                ServiceProcessStep,
                [
                    {
                        "service": service,
                        "number": step.get("number") or "",
                        "title": step["title"],
                        "body": step.get("body") or "",
                    }
                    for step in (entry.get("process") or {}).get("steps") or []
                ],
            )

            self.replace(
                service.gallery_items,
                ServiceGalleryItem,
                [
                    {"service": service, "media": self.asset(_key(image, self.data))}
                    for image in entry.get("gallery") or []
                    if _key(image, self.data)
                ],
            )

        self.note(f"{Service.objects.count()} services")

    def match_services(self, labels, services_by_title):
        """Resolve the labels a project lists to real Service rows.

        The two vocabularies are close but not identical: a project says
        "Architecture" where the service is titled "Architecture Design". Matched
        on a prefix in either direction, and anything left over is reported —
        an unmatched label means the project loses a link, which is silent
        content loss otherwise.
        """
        resolved, missed = [], []

        for label in labels:
            key = str(label).strip().lower()
            match = next(
                (
                    service
                    for title, service in services_by_title.items()
                    if title.lower() == key
                    or title.lower().startswith(key)
                    or key.startswith(title.lower())
                ),
                None,
            )
            if match:
                resolved.append(match)
            else:
                missed.append(label)

        if missed:
            self.stdout.write(
                self.style.WARNING(
                    f"  No service matches {', '.join(missed)} - link dropped"
                )
            )
        return resolved

    def seed_projects(self):
        services_by_title = {s.title: s for s in Service.objects.all()}

        for entry in self.data["projects"]["projects"]:
            project, _ = self.published(
                Project,
                {
                    "title": entry["title"],
                    "short_description": entry.get("shortDescription") or "",
                    "description": entry.get("description") or "",
                    "location": entry.get("location") or "",
                    "project_year": _year(entry.get("year")),
                    "project_status": _choice(
                        ProjectStatus, entry.get("status"), ProjectStatus.COMPLETED
                    ),
                    "category": _choice(
                        ProjectCategory, entry.get("category"), ProjectCategory.RESIDENTIAL
                    ),
                    "layout": _choice(
                        ProjectLayout, entry.get("layout"), ProjectLayout.HALF
                    ),
                    "cover_image": self.asset(_key(entry.get("coverImage"), self.data)),
                    "design_intent": entry.get("designIntent") or "",
                    "spatial_planning": entry.get("spatialPlanning") or "",
                    "interior_note": entry.get("interiorNote") or "",
                    "construction_note": entry.get("constructionNote") or "",
                    "outcome_note": entry.get("outcomeNote") or "",
                    "is_featured": bool(entry.get("featured")),
                },
                slug=entry["slug"],
            )

            project.services.set(
                self.match_services(entry.get("services") or [], services_by_title)
            )

            self.replace(
                project.materials,
                ProjectMaterial,
                [
                    {
                        "project": project,
                        "name": material["name"],
                        "note": material.get("note") or "",
                    }
                    for material in entry.get("materials") or []
                ],
            )

            rows = []
            for field, kind in (
                ("gallery", ProjectMediaKind.GALLERY),
                ("floorPlans", ProjectMediaKind.FLOOR_PLAN),
                ("drawings", ProjectMediaKind.DRAWING),
            ):
                for image in entry.get(field) or []:
                    asset = self.asset(_key(image, self.data))
                    if asset:
                        rows.append(
                            {"project": project, "media": asset, "kind": kind}
                        )
            self.replace(project.gallery_items, ProjectGalleryItem, rows)

        self.note(f"{Project.objects.count()} projects")

    def seed_gallery(self):
        for entry in self.data["gallery"]["galleryItems"]:
            asset = self.asset(_key(entry.get("image"), self.data))
            if asset is None:
                continue
            self.published(
                GalleryItem,
                {
                    "caption": entry.get("caption") or "",
                    "category": _choice(
                        GalleryCategory,
                        entry.get("category"),
                        GalleryCategory.ARCHITECTURE,
                    ),
                    "image": asset,
                },
                title=entry["title"],
            )
        self.note(f"{GalleryItem.objects.count()} gallery items")

    def seed_locations(self):
        for entry in self.data["locations"]["locations"]:
            self.published(
                Location,
                {
                    "state": entry.get("state") or "",
                    "coordinates": entry.get("coordinates") or "",
                    "blurb": entry.get("blurb") or "",
                    "image": self.asset(_key(entry.get("image"), self.data)),
                    # Unconfirmed in the source and left unconfirmed here. The
                    # frontend omits an empty field; it prints whatever is set.
                    "address": entry.get("address") or "",
                    "phone": entry.get("phone") or "",
                    "email": entry.get("email") or "",
                    "map_url": entry.get("mapUrl") or "",
                },
                city=entry["city"],
            )
        self.note(f"{Location.objects.count()} locations (addresses deliberately blank)")

    def seed_counters(self):
        unverified = []
        for entry in self.data["stats"]["stats"]:
            verified = bool(entry.get("verified"))
            counter, _ = Counter.objects.update_or_create(
                subtitle=entry["label"],
                defaults={
                    "content": str(entry["value"]),
                    "postfix": entry.get("suffix") or "",
                    "description": entry.get("note") or "",
                    "status": (
                        PublishStatus.PUBLISHED if verified else PublishStatus.DRAFT
                    ),
                },
            )
            if verified and counter.published_at is None:
                counter.published_at = self.now
                counter.save(update_fields=["published_at"])
            if not verified:
                unverified.append(entry["label"])

        self.note(f"{Counter.objects.count()} figures")
        if unverified:
            self.stdout.write(
                self.style.WARNING(
                    f"  Left as DRAFT until the studio confirms them: "
                    f"{', '.join(unverified)}"
                )
            )

    def seed_journal(self):
        for name in self.data["journal"]["journalCategories"]:
            BlogCategory.objects.get_or_create(name=name)
        categories = {c.name: c for c in BlogCategory.objects.all()}

        for entry in self.data["journal"]["journalEntries"]:
            post, _ = self.published(
                BlogPost,
                {
                    "title": entry["title"],
                    "excerpt": entry.get("excerpt") or "",
                    "content": _body(entry.get("body")),
                    "featured_image": self.asset(
                        _key(entry.get("coverImage"), self.data)
                    ),
                    "category": categories.get(entry.get("category")),
                    "reading_time": _minutes(entry.get("readingTime")),
                },
                slug=entry["slug"],
            )
            published_on = parse_date(str(entry.get("date") or "")[:10])
            if published_on:
                post.published_at = timezone.make_aware(
                    timezone.datetime.combine(
                        published_on, timezone.datetime.min.time()
                    )
                )
                post.save(update_fields=["published_at"])

        self.note(f"{BlogPost.objects.count()} journal entries")

    def seed_company(self):
        """Confirmed copy only.

        `company.js` sets `PLACEHOLDER_CONTACT = true`: the email, the phone
        number and the social links shipped with the build are stand-ins — the
        social hrefs are bare platform homepages with no handle on them. Seeding
        those would put a working-looking mailto and four dead links on a live
        site, so they are left blank for the studio to fill in through the admin.

        The name, tagline, statement and navigation are the studio's own and are
        carried across.
        """
        info = self.data["company"]["company"]
        placeholder = self.data["company"].get("PLACEHOLDER_CONTACT", True)
        company = page_models.Company.load()

        company.name = info.get("name") or ""
        # Blank today: `addresses` is empty in the source, and the studio has
        # not confirmed a street address for either city.
        company.address = "\n\n".join(
            filter(None, (a.get("label") or "" for a in info.get("addresses") or []))
        )

        if placeholder:
            company.contacts = {"emails": [], "phones": [], "whatsapp": ""}
            company.social_urls = {}
        else:
            company.contacts = {
                "emails": [info["email"]] if info.get("email") else [],
                "phones": [info["phone"]] if info.get("phone") else [],
                "whatsapp": info.get("whatsapp") or "",
            }
            company.social_urls = {
                entry["label"].lower(): entry["href"]
                for entry in info.get("social") or []
                if entry.get("href")
            }

        company.header_links = [
            {"label": link["label"], "url": link["href"]}
            for link in self.data["navigation"]["primaryNav"]
        ]
        company.footer_links = [
            {
                "heading": group.get("heading") or "",
                "links": [
                    {"label": link["label"], "url": link["href"]}
                    for link in group.get("links") or []
                ],
            }
            for group in self.data["navigation"]["footerNav"]
        ]
        company.meta_title = self.data["company"]["siteConfig"].get("title") or ""
        company.meta_description = (
            self.data["company"]["siteConfig"].get("description") or ""
        )
        company.save()

        self.note("Company settings")
        if placeholder:
            self.stdout.write(
                self.style.WARNING(
                    "  Contact details and social links left blank - the source "
                    "marks them PLACEHOLDER_CONTACT."
                )
            )

    # ── pages ────────────────────────────────────────────────────────────────

    def seed_pages(self):
        self.seed_home()
        self.seed_about()
        self.seed_services_page()
        self.seed_projects_page()
        self.seed_gallery_page()
        self.seed_journal_page()
        self.seed_locations_page()
        self.seed_contact()
        self.seed_legal()

    def hero(self, spec):
        section = page_models.HeroSection.objects.create(
            autoplay_seconds=spec.get("autoplay_seconds", "6.5"),
        )
        self.replace(
            section.slides,
            page_models.HeroSlide,
            [
                {
                    "section": section,
                    "eyebrow": slide.get("eyebrow") or "",
                    "heading": slide["heading"],
                    "lead": slide.get("lead") or "",
                    "media": self.asset(slide["media"]),
                }
                for slide in spec["slides"]
            ],
        )
        return section

    def cta(self, overrides=None):
        spec = {**copy.DEFAULT_CTA, **(overrides or {})}
        return page_models.CTASection.objects.create(
            eyebrow=spec.get("eyebrow") or "",
            heading=spec.get("heading") or "",
            body=spec.get("body") or "",
            link_label=spec.get("link_label") or "",
            link_url=spec.get("link_url") or "",
            secondary_label=spec.get("secondary_label") or "",
            secondary_url=spec.get("secondary_url") or "",
            media=self.asset(spec.get("media")),
        )

    def process(self, spec):
        section = page_models.ProcessSection.objects.create(
            eyebrow=spec.get("eyebrow") or "",
            heading=spec.get("heading") or "",
            lead=spec.get("lead") or "",
        )
        self.replace(
            section.steps,
            page_models.ProcessStep,
            [{"section": section, **step} for step in spec["steps"]],
        )
        return section

    def items(self, section, model, field, records):
        self.replace(
            getattr(section, "items"),
            model,
            [{"section": section, field: record} for record in records],
        )

    def page(self, model, **sections):
        """Rewrite a page's sections, discarding whatever it held before.

        Seeding is a reset, not a merge: a half-updated page is harder to reason
        about than one rebuilt from the source of truth.
        """
        page, _ = model.objects.get_or_create(pk=model.SINGLETON_PK)
        old = {
            name: getattr(page, f"{name}_id")
            for name in sections
            if getattr(page, f"{name}_id", None)
        }

        for name, section in sections.items():
            setattr(page, name, section)
        page.is_published = True
        page.save()

        # Detached only after the page points elsewhere, or PROTECT refuses.
        for name, pk in old.items():
            field = model._meta.get_field(name)
            field.related_model.objects.filter(pk=pk).delete()

        self.note(f"/{_route(model)}")
        return page

    def seed_home(self):
        stats = page_models.StatsSection.objects.create(**copy.HOME_STATS)
        self.items(
            stats,
            page_models.StatsSectionItem,
            "counter",
            Counter.objects.filter(status=PublishStatus.PUBLISHED),
        )

        services = page_models.HomeServicesSection.objects.create(**copy.HOME_SERVICES)
        self.items(
            services,
            page_models.HomeServiceItem,
            "service",
            Service.objects.filter(is_featured=True)[:4],
        )

        featured = page_models.FeaturedProjectSection.objects.create(
            eyebrow="Featured project",
            project=Project.objects.filter(is_featured=True).first(),
        )

        projects = page_models.HomeProjectsSection.objects.create(**copy.HOME_PROJECTS)
        self.items(
            projects,
            page_models.HomeProjectItem,
            "project",
            Project.objects.all()[1:5],
        )

        gallery = page_models.HomeGallerySection.objects.create(**copy.HOME_GALLERY)
        self.items(
            gallery,
            page_models.HomeGalleryItem,
            "gallery_item",
            GalleryItem.objects.all()[:5],
        )

        locations = page_models.HomeLocationsSection.objects.create(
            **copy.HOME_LOCATIONS
        )
        self.items(
            locations,
            page_models.HomeLocationItem,
            "location",
            Location.objects.all(),
        )

        intro_spec = dict(copy.HOME_INTRO)
        intro = page_models.HomeIntroSection.objects.create(**intro_spec)

        self.page(
            page_models.HomePage,
            hero=self.hero(copy.HOME_HERO),
            intro=intro,
            stats=stats,
            featured_project=featured,
            services=services,
            projects=projects,
            gallery=gallery,
            locations=locations,
            cta=self.cta(),
        )

    def seed_about(self):
        presence = page_models.AboutPresenceSection.objects.create(
            **copy.ABOUT_PRESENCE
        )
        self.items(
            presence,
            page_models.AboutLocationItem,
            "location",
            Location.objects.all(),
        )

        studio = self.data["studio"]
        mission_vision = page_models.MissionVisionSection.objects.create()
        self.replace(
            mission_vision.blocks,
            page_models.MissionVisionBlock,
            [
                {
                    "section": mission_vision,
                    "numeral": numeral,
                    "eyebrow": block["eyebrow"],
                    "heading": block["heading"],
                    "body": block["body"],
                    "points": block.get("points") or [],
                    "media": self.asset(media_key),
                    "side": side,
                }
                for numeral, block, media_key, side in (
                    ("01", studio["mission"], "curvedFacade", "right"),
                    ("02", studio["vision"], "aerialNeighbourhood", "left"),
                )
            ],
        )

        founder_source = studio["founder"]
        founder = page_models.FounderSection.objects.create(
            eyebrow=founder_source.get("eyebrow") or "",
            heading=founder_source.get("heading") or "",
            message=founder_source.get("message") or [],
            # Unconfirmed by the studio: left blank on purpose. An invented
            # principal is the most damaging thing a practice site can carry.
            name="",
            role="",
            credentials="",
            fallback_attribution=founder_source.get("fallbackAttribution") or "",
            media=self.asset("drawingDesk"),
        )

        story = page_models.StudioStorySection.objects.create(
            eyebrow="The studio",
            heading="Design and build, held together.",
            body=self.data["company"]["company"].get("statement") or "",
            media=self.asset("timberGateway"),
        )

        self.page(
            page_models.AboutPage,
            hero=self.hero(copy.ABOUT_HERO),
            story=story,
            mission_vision=mission_vision,
            founder=founder,
            process=self.process(copy.ABOUT_PROCESS),
            presence=presence,
            cta=self.cta(copy.ABOUT_CTA),
        )

    def seed_services_page(self):
        index = page_models.ServiceIndexSection.objects.create(**copy.SERVICES_INDEX)
        self.items(
            index,
            page_models.ServiceIndexItem,
            "service",
            Service.objects.all(),
        )

        self.page(
            page_models.ServicesPage,
            hero=self.hero(copy.SERVICES_HERO),
            index=index,
            process=self.process(copy.SERVICES_PROCESS),
            cta=self.cta(copy.SERVICES_CTA),
        )

    def seed_projects_page(self):
        index = page_models.ProjectIndexSection.objects.create(
            eyebrow="Archethos / Work",
            heading="Selected projects.",
            lead=(
                "Residential, commercial and interior work, filtered by the kind "
                "of project rather than the year."
            ),
        )
        # Left uncurated: an empty selection means every published project, so a
        # new one appears without anyone remembering this screen.
        self.page(
            page_models.ProjectsPage,
            hero=self.hero(copy.PROJECTS_HERO),
            index=index,
            cta=self.cta(),
        )

    def seed_gallery_page(self):
        grid = page_models.GalleryGridSection.objects.create(
            eyebrow="Archethos / Gallery",
            heading="The full set.",
        )
        self.items(
            grid,
            page_models.GalleryGridItem,
            "gallery_item",
            GalleryItem.objects.all(),
        )

        self.page(
            page_models.GalleryPage,
            hero=self.hero(copy.GALLERY_HERO),
            grid=grid,
            cta=self.cta(),
        )

    def seed_journal_page(self):
        featured = page_models.JournalFeaturedSection.objects.create(
            eyebrow="Featured",
            heading="Worth starting with.",
        )
        self.items(
            featured,
            page_models.JournalFeaturedItem,
            "post",
            BlogPost.objects.all()[:2],
        )

        listing = page_models.JournalListSection.objects.create(
            eyebrow="All entries",
            heading="Everything the studio has written.",
        )

        self.page(
            page_models.JournalPage,
            hero=self.hero(copy.JOURNAL_HERO),
            featured=featured,
            list=listing,
            cta=self.cta(),
        )

    def seed_locations_page(self):
        listing = page_models.LocationsListSection.objects.create(
            eyebrow="Where we work",
            heading="Two cities, one studio.",
        )
        self.items(
            listing,
            page_models.LocationsListItem,
            "location",
            Location.objects.all(),
        )

        visiting = page_models.VisitingSection.objects.create(
            eyebrow="02 / Visiting",
            heading="Come and see us.",
            body=(
                "We have not published a street address yet. Send an enquiry and "
                "we will arrange to meet — on the plot where possible."
            ),
        )

        self.page(
            page_models.LocationsPage,
            hero=self.hero(copy.LOCATIONS_HERO),
            locations=listing,
            visiting=visiting,
            cta=self.cta(),
        )

    def seed_contact(self):
        form_spec = dict(copy.CONTACT_FORM)
        form = page_models.ContactFormSection.objects.create(
            heading=form_spec["heading"],
            media=self.asset(form_spec["media"]),
            submit_label="Send enquiry",
            success_message=(
                "Thank you — your enquiry has been received. We usually reply "
                "within two working days."
            ),
        )

        details = page_models.ContactDetailsSection.objects.create(
            eyebrow="Studio",
            heading="Get in touch.",
            no_details_note=(
                "We have not published a direct line yet. The form reaches the "
                "studio directly."
            ),
        )

        what_happens = page_models.WhatHappensSection.objects.create(
            eyebrow=copy.CONTACT_WHAT_HAPPENS["eyebrow"],
            heading=copy.CONTACT_WHAT_HAPPENS["heading"],
        )
        self.replace(
            what_happens.steps,
            page_models.WhatHappensStep,
            [
                {"section": what_happens, **step}
                for step in copy.CONTACT_WHAT_HAPPENS["steps"]
            ],
        )

        self.page(
            page_models.ContactPage,
            hero=self.hero(copy.CONTACT_HERO),
            form=form,
            details=details,
            what_happens=what_happens,
            cta=self.cta(),
        )

    def seed_legal(self):
        """Structure only.

        The studio has not supplied privacy or terms copy, and legal text is not
        something to draft on their behalf. Both pages are seeded with their
        heading and left **unpublished** until real wording arrives.
        """
        for model, title in (
            (page_models.PrivacyPage, "Privacy policy"),
            (page_models.TermsPage, "Terms of use"),
        ):
            body = page_models.RichTextSection.objects.create(
                eyebrow="Legal",
                heading=title,
                intro="",
            )
            page, _ = model.objects.get_or_create(pk=model.SINGLETON_PK)
            previous = page.body_id
            page.body = body
            page.is_published = False
            page.save()
            if previous:
                page_models.RichTextSection.objects.filter(pk=previous).delete()

            self.note(f"/{_route(model)} (unpublished - awaiting copy)")


# ─── mapping helpers ─────────────────────────────────────────────────────────


def _humanise(key):
    """`heroHouseDusk` -> `Hero house dusk`."""
    spaced = "".join(f" {c.lower()}" if c.isupper() else c for c in key)
    return spaced.strip().capitalize()


_MEDIA_BY_SRC = {}


def _key(entry, data):
    """The media catalogue key for an embedded `{src, alt}` object.

    The dump inlines the object at every use, so it is matched back by `src` —
    the one field guaranteed to be identical.
    """
    if not entry or not isinstance(entry, dict):
        return None
    if not _MEDIA_BY_SRC:
        _MEDIA_BY_SRC.update(
            {value["src"]: name for name, value in data["media"]["media"].items()}
        )
    return _MEDIA_BY_SRC.get(entry.get("src"))


def _minutes(value):
    """`"4 min"` -> `4`. The frontend stores it ready to print."""
    if value in (None, ""):
        return 0
    digits = "".join(c for c in str(value) if c.isdigit())
    return int(digits) if digits else 0


def _year(value):
    try:
        return int(str(value)[:4])
    except (TypeError, ValueError):
        return None


def _choice(choices, value, default):
    """Match the frontend's label to a TextChoices member.

    Tried against values, names and labels, case-insensitively, because the two
    sides do not agree on casing: the frontend writes "Residential" against
    `RESIDENTIAL` but "full" against `full`. An unmatched value falls back to the
    default rather than raising — but see `_warn_unmatched`, because falling back
    silently is how "wide" became "half" for a whole afternoon.
    """
    if not value:
        return default

    wanted = str(value).strip().lower()
    for member in choices:
        if wanted in (
            str(member.value).lower(),
            member.name.lower(),
            str(member.label).lower(),
        ):
            return member.value
    return default


def _body(value):
    if isinstance(value, list):
        return "\n\n".join(str(part) for part in value)
    return value or ""


def _route(model):
    from archethosbackend.apps.pages.models import ORDERED_PAGES

    for route, candidate in ORDERED_PAGES.items():
        if candidate is model:
            return route
    return model._meta.model_name
