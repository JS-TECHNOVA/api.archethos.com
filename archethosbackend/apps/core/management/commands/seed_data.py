from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.about.models import AboutPage
from apps.core.models import Company
from apps.home.models import HomePage, Slider
from apps.projects.models import Project, ProjectCategory
from apps.services.models import Service


def editor(text):
    return {"blocks": [{"type": "paragraph", "data": {"text": text}}]}


class Command(BaseCommand):
    help = "Seed starter CMS content without overwriting existing records."

    def handle(self, *args, **options):
        services = []
        for title, slug, tagline in [
            ("Architecture Design", "architecture-design", "Site, brief and form resolved as one clear architectural direction."),
            ("Interior Design", "interior-design", "Spaces planned around daily use, material character and light."),
            ("Construction", "construction", "The drawings and the build held together by one studio."),
            ("Renovation", "renovation", "Existing spaces carefully reworked for the way they need to perform now."),
            ("Vastu Consultancy", "vastu-consultancy", "Orientation, circulation and spatial planning considered from the first plan."),
        ]:
            service, created = Service.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "eyebrow": "Services",
                    "tagline": tagline,
                    "short_description": tagline,
                    "description": editor(tagline),
                    "is_active": True,
                },
            )
            services.append(service)
            if created:
                self.stdout.write(f"Created service: {title}")

        categories = {}
        for order, name in enumerate(["Residential", "Interior", "Commercial", "Renovation", "Hospitality"]):
            category, created = ProjectCategory.objects.get_or_create(
                name=name,
                defaults={"order": order, "description": editor(f"{name} projects.")},
            )
            categories[name] = category
            if created:
                self.stdout.write(f"Created project category: {name}")

        project_specs = [
            ("Courtyard House", "courtyard-house", "Residential", "Lucknow", 2026, "A calm family home organised around light, shade and a planted courtyard."),
            ("Material-led Apartment", "material-led-apartment", "Interior", "Lucknow", 2026, "An interior shaped through daylight, texture and deliberate storage."),
            ("Neighbourhood Studio", "neighbourhood-studio", "Commercial", "Kushinagar", 2025, "A focused workspace with a clear public edge and quieter working rooms."),
        ]
        projects = []
        for title, slug, category, location, year, description in project_specs:
            project, created = Project.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "category": categories[category],
                    "location": location,
                    "year": year,
                    "project_status": "completed",
                    "short_description": description,
                    "description": editor(description),
                    "is_featured": title == "Courtyard House",
                    "status": "published",
                    "published_at": timezone.now(),
                },
            )
            if created:
                project.services.set(services[:2])
                self.stdout.write(f"Created project: {title}")
            projects.append(project)

        about, _ = AboutPage.objects.get_or_create(pk=AboutPage.SINGLETON_PK)
        about_updates = {
            "hero_eyebrow": "The studio",
            "hero_title": "Architecture shaped around the way people live.",
            "hero_description": "Architecture, interiors and construction brought together through one considered process.",
            "who_we_are_title": "We make spaces that hold up in everyday life.",
            "who_we_are_description": editor("Archethos works across architecture, interiors and construction. We begin with the site, the brief and the decisions that will still matter when the work is built."),
            "sections": [
                {"title": "Our mission", "description": editor("To make thoughtful design practical from the first conversation through to the finished space."), "points": [], "image": "", "image_side": "right"},
                {"title": "Our vision", "description": editor("A built environment where design quality and the realities of construction are never treated as separate concerns."), "points": [], "image": "", "image_side": "left"},
            ],
            "approach": {"title": "Our approach", "description": "A clear sequence keeps every decision connected to the site, the brief and the work on site.", "items": [{"title": "Understand", "description": "Read the site, listen to the brief and identify what matters first."}, {"title": "Develop", "description": "Turn the direction into drawings, materials and details."}, {"title": "Deliver", "description": "Carry those decisions through construction with care."}]},
        }
        changed = []
        for name, value in about_updates.items():
            if not getattr(about, name):
                setattr(about, name, value)
                changed.append(name)
        if changed:
            about.save(update_fields=changed)
            self.stdout.write("Seeded About page content.")

        home, _ = HomePage.objects.get_or_create(pk=HomePage.SINGLETON_PK)
        if not home.sliders.exists():
            for order, (eyebrow, title, description) in enumerate([
                ("Architecture / Interiors / Build", "Spaces shaped around the way you live.", "Architecture, interiors and construction brought together with thoughtful design and careful execution."),
                ("Interiors / Materials / Detail", "Rooms planned before they are decorated.", "Interiors resolved from planning through to material, lighting and the details of everyday use."),
                ("Construction / Site / Execution", "The drawing and the building, one studio.", "We carry the build against the same drawings we produce, so the design holds together on site."),
            ]):
                slider = Slider.objects.create(
                    eyebrow=eyebrow,
                    title=title,
                    description=description,
                    primary_cta_label="Explore our work",
                    primary_cta_url="/projects",
                    secondary_cta_label="Start a project",
                    secondary_cta_url="/contact",
                    order=order,
                )
                home.sliders.add(slider)
            self.stdout.write("Seeded Home hero slides.")

        if not home.home_counters:
            home.home_counters = [
                {"label": "12", "prefix": "", "postfix": "+", "subtitle": "Years of practice", "description": "Across architecture, interiors and construction."},
                {"label": "80", "prefix": "", "postfix": "+", "subtitle": "Spaces shaped", "description": "Homes, workplaces and renovations."},
                {"label": "5", "prefix": "", "postfix": "", "subtitle": "Core disciplines", "description": "Held together by one studio."},
            ]
        if not home.design_build_process:
            home.design_build_process = {"eyebrow": "Design and build", "title": "The drawing and the building come from the same room.", "description": "A connected process means the design is carried carefully from the first plan to the work on site.", "items": [{"title": "Design", "description": "Resolve the site, brief and concept."}, {"title": "Drawings", "description": "Develop the information the site needs."}, {"title": "Detail", "description": "Settle materials and junctions early."}, {"title": "Build", "description": "Deliver against the agreed drawings."}]}
        if not home.selected_work_title:
            home.selected_work_title = "Selected work"
        if not home.selected_work_description:
            home.selected_work_description = "A selection of spaces imagined, shaped and built by the studio."
        if not home.section_content:
            home.section_content = {
                "services": {"eyebrow": "Services", "title": "From the first sketch to the finished space.", "description": "Design decisions and build decisions held together by the same studio."},
                "stats": {"eyebrow": "At a glance"},
                "featured_project": {"eyebrow": "Featured project"},
                "gallery": {"eyebrow": "Studio / Gallery"},
            }
        if not home.featured_project_id and projects:
            home.featured_project = projects[0]
        home.save()
        if not home.selected_work.exists() and projects:
            home.selected_work.set(projects)
        self.stdout.write(self.style.SUCCESS("Seed data is ready. Existing content was preserved."))
