"""
Page section copy, transcribed from the frontend components.

The `src/data/*.js` dump covers master data. This covers what the dump cannot
reach: headings, leads and step lists that live inside the page components as
literals. Every string below is copied verbatim from the JSX — none of it is
written here.

Media is named by its key in the frontend's media catalogue; the seed resolves
those to `MediaAsset` rows.
"""

# ─── Home ────────────────────────────────────────────────────────────────────
# components/sections/hero/home-hero.jsx

HOME_HERO = {
    "variant": "SLIDER",
    "autoplay_seconds": "6.5",
    "slides": [
        {
            "eyebrow": "Architecture / Interiors / Build",
            "heading": "Spaces shaped around the way you live.",
            "lead": (
                "Architecture, interiors and construction brought together with "
                "thoughtful design and precise execution."
            ),
            "media": "heroHouseDusk",
        },
        {
            "eyebrow": "Interiors / Materials / Detail",
            "heading": "Rooms planned before they are decorated.",
            "lead": (
                "Interiors resolved from space planning through to material, "
                "lighting and the detail of every joint."
            ),
            "media": "livingTimberWall",
        },
        {
            "eyebrow": "Construction / Site / Execution",
            "heading": "The drawing and the building, one studio.",
            "lead": (
                "We run the build against the same drawings we produced, so the "
                "design survives its own execution."
            ),
            "media": "siteRebar",
        },
    ],
}

# components/sections/intro/studio-introduction.jsx
HOME_INTRO = {
    "eyebrow": "Archethos / Studio",
    # Broken by hand in the design — the line breaks carry the sentence.
    "statement_lines": [
        "We don't simply",
        "design buildings.",
        "We shape the spaces",
        "people experience",
        "every day.",
    ],
    "body": (
        "Archethos works across architecture, interior design, Vastu "
        "consultancy, construction and renovation from Lucknow and Kushinagar. "
        "Most projects need more than one of those, and most of what goes wrong "
        "happens in the gaps between them.\n\n"
        "So we hold them together. The people who read the site and drew the "
        "plan are the people coordinating the build — which means a question "
        "raised at the wall gets answered against the design rather than around "
        "it.\n\n"
        "It is a slower way to begin a project, and a considerably faster way to "
        "finish one."
    ),
    "link_label": "About the studio",
    "link_url": "/about",
}

HOME_STATS = {"eyebrow": "Archethos / At a glance", "tone": "ink"}

HOME_SERVICES = {
    "eyebrow": "Services",
    "heading": "From the first sketch to the finished space.",
    "link_label": "All services",
    "link_url": "/services",
    "tone": "bone",
}

HOME_PROJECTS = {
    "eyebrow": "Selected work",
    "link_label": "All projects",
    "link_url": "/projects",
    "tone": "bone",
}

HOME_GALLERY = {"eyebrow": "Archethos / Gallery", "autoplay_seconds": "6.5"}

HOME_LOCATIONS = {
    "eyebrow": "Presence",
    "heading": "Working from Lucknow and Kushinagar.",
    "link_label": "Our locations",
    "link_url": "/locations",
    "layout": "grid",
}

# ─── About ───────────────────────────────────────────────────────────────────
# app/(website)/about/page.js

ABOUT_HERO = {
    "variant": "PHOTOGRAPHIC",
    "slides": [
        {
            "eyebrow": "Archethos / Studio",
            "heading": "Good architecture begins with understanding.",
            "lead": (
                "An architecture, interiors and construction studio working "
                "across Lucknow, Kushinagar and the surrounding region."
            ),
            "media": "timberGateway",
        }
    ],
}

ABOUT_PROCESS = {
    "eyebrow": "Our approach",
    "heading": "Four stages, and the design survives all of them.",
    "tone": "bone-deep",
    "steps": [
        {
            "number": "01",
            "title": "Understand",
            "body": (
                "The site, the brief, the budget direction and how the space has "
                "to work day to day."
            ),
        },
        {
            "number": "02",
            "title": "Design",
            "body": (
                "Concept developed in plan and section together, so structure "
                "and space resolve as one idea."
            ),
        },
        {
            "number": "03",
            "title": "Refine",
            "body": (
                "Drawings, materials and details settled while they are still "
                "cheap to change."
            ),
        },
        {
            "number": "04",
            "title": "Build",
            "body": (
                "Executed against the same drawing set, with the design team "
                "present on site."
            ),
        },
    ],
}

ABOUT_PRESENCE = {
    "eyebrow": "Our presence",
    "heading": "Lucknow and Kushinagar.",
    "lead": (
        "Being close to the site is what makes running design and construction "
        "together possible rather than theoretical."
    ),
    "link_label": "Our locations",
    "link_url": "/locations",
    "layout": "stacked",
    "tone": "bone",
}

ABOUT_CTA = {
    "heading": "Tell us what you're planning.",
    "media": "livingTimberWall",
    "secondary_label": "Our services",
    "secondary_url": "/services",
}

# ─── Services ────────────────────────────────────────────────────────────────
# app/(website)/services/page.js

SERVICES_HERO = {
    "variant": "PHOTOGRAPHIC",
    "slides": [
        {
            "eyebrow": "Archethos / Services",
            "heading": "Design, drawn and built by one studio.",
            "lead": (
                "Five disciplines that most projects have to assemble from "
                "separate parties, held together here so the design survives the "
                "build."
            ),
            "media": "cortenHouse",
        }
    ],
}

SERVICES_INDEX = {
    "eyebrow": "Service index",
    "heading": "What we do.",
    "lead": (
        "Each discipline stands on its own, and most projects use more than one. "
        "Where they overlap is usually where the value is."
    ),
    "tone": "bone",
}

SERVICES_PROCESS = {
    "eyebrow": "How a project moves",
    "heading": "The same four stages, whichever service opens the work.",
    "tone": "ink",
    "steps": [
        {
            "number": "01",
            "title": "Understand",
            "body": "The site, the brief and the way the space has to work.",
        },
        {
            "number": "02",
            "title": "Design",
            "body": "Concept tested in plan and section at the same time.",
        },
        {
            "number": "03",
            "title": "Refine",
            "body": "Drawings, materials and detail resolved before pricing.",
        },
        {
            "number": "04",
            "title": "Build",
            "body": "Executed against the same set the studio drew.",
        },
    ],
}

SERVICES_CTA = {
    "eyebrow": "Start a project",
    "media": "drawingDesk",
    "secondary_label": "See our work",
    "secondary_url": "/projects",
}

# ─── Contact ─────────────────────────────────────────────────────────────────
# app/(website)/contact/page.js

CONTACT_HERO = {
    "variant": "PHOTOGRAPHIC",
    "slides": [
        {
            # The eyebrow is built from Company.cities in the component.
            "eyebrow": "Lucknow / Kushinagar / India",
            "heading": "Let's shape your next space.",
            "lead": (
                "Tell us about the site, the brief and where you are in the "
                "process. We'll tell you what the work actually involves."
            ),
            "media": "interiorPoolView",
        }
    ],
}

CONTACT_FORM = {
    "heading": "Start a project",
    "tone": "bone",
    "media": "archAlcove",
}

CONTACT_WHAT_HAPPENS = {
    "eyebrow": "After you send it",
    "heading": "What happens next.",
    "tone": "ink",
    "steps": [
        {
            "number": "01",
            "title": "We read the site",
            "body": (
                "Before we reply we look at where the project is — orientation, "
                "access and what the plot will allow."
            ),
        },
        {
            "number": "02",
            "title": "We come back with questions",
            "body": (
                "Usually within two working days, and usually about the site "
                "rather than the budget."
            ),
        },
        {
            "number": "03",
            "title": "We meet",
            "body": (
                "On the plot where possible. Most of what matters is decided "
                "standing on it."
            ),
        },
    ],
}

# ─── The index pages ─────────────────────────────────────────────────────────
# Each opens with a single-frame hero, transcribed from its page.js.

PROJECTS_HERO = {
    "variant": "PHOTOGRAPHIC",
    "slides": [
        {
            "eyebrow": "Archethos / Projects",
            "heading": "Spaces we've imagined, shaped and built.",
            "lead": (
                "An index of the studio's work — residential, commercial and "
                "interior, from first drawing to finished space."
            ),
            "media": "curvedFacade",
        }
    ],
}

GALLERY_HERO = {
    "variant": "PHOTOGRAPHIC",
    "slides": [
        {
            "eyebrow": "Archethos / Gallery",
            "heading": "Every frame we've kept.",
            "lead": (
                "Buildings, rooms, sites and the details in between — the "
                "pictures the studio takes while the work is happening, and "
                "after it is finished."
            ),
            "media": "angularBuilding",
        }
    ],
}

JOURNAL_HERO = {
    "variant": "PHOTOGRAPHIC",
    "slides": [
        {
            "eyebrow": "Archethos / Journal",
            "heading": "Notes from the studio.",
            "lead": (
                "Working notes on how buildings get planned, drawn, detailed and "
                "built — written for people about to start one."
            ),
            "media": "drawingDesk",
        }
    ],
}

LOCATIONS_HERO = {
    "variant": "PHOTOGRAPHIC",
    "slides": [
        {
            "eyebrow": "Lucknow / Kushinagar / India",
            "heading": "Close enough to be on the site.",
            "lead": (
                "Running design and construction together only works when the "
                "studio can actually get to the work. That is what decides where "
                "we take projects."
            ),
            "media": "apartmentFacade",
        }
    ],
}

#: The closing call to action, used wherever a page does not override it.
DEFAULT_CTA = {
    "eyebrow": "Start a project",
    "heading": "Let's shape your next space.",
    "body": (
        "Tell us about the site, the brief and where you are in the process. "
        "We'll take it from there."
    ),
    "link_label": "Start the conversation",
    "link_url": "/contact",
    "media": "cortenHouse",
}
