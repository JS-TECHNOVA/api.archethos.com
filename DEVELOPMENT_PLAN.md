# Archethos Headless CMS — Architecture & Development Plan

> Backend: Django + Django REST Framework + PostgreSQL
> Frontend: Next.js at `archethos-nextjs/archethos` — **not built here, and never modified
> from this repo.** Read for reference only.
> Auth: JWT in HttpOnly cookies, refresh rotation + blacklist
>
> Status: **approved**. Single source of truth for the build.
> Update this document when a decision changes; update `TASKS.md` as work completes.

---

## 1. Stack & current state

| Item | Value |
|---|---|
| Django | 6.1 — verified working with simplejwt 5.5.1 + `token_blacklist` |
| DRF | 3.18 |
| DB | PostgreSQL 17.11 via Docker on host port **5433**; psycopg 3.3.4 |
| Installed | `django-cors-headers`, `django-filter`, `django-environ`, `drf-spectacular`, `django-ratelimit`, `django-extensions`, `Pillow` |
| To install | (prod) `gunicorn`, `whitenoise`; (test) `pytest-django`, `factory-boy` |
| Progress | Phases 1–4 complete — foundation, cookie JWT auth, users/groups/permissions. 62 tests passing. |

---

## 2. Locked architectural decisions

Reviewed and approved. Do not re-litigate without updating this section.

### 2.1 Media is a ForeignKey, serialized as a relative path

Content and section models store `ForeignKey(MediaAsset, on_delete=PROTECT)`. The API reads
and writes the **relative path**. No CDN domain is ever persisted.

```
DB        HeroSection.background_media_id = 42
API out   "background_media": "/media/uploads/abc123-hero.webp"
API in    accepts 42 (id) OR "/media/uploads/abc123-hero.webp"
Frontend  CDN_BASE + path
```

A single `MediaReferenceField` implements both directions and validates existence. This gives
delete protection, a working "where is this image used?" query, and validation for free —
none of which a bare path string can provide. The CDN-independence requirement is about the
payload, not the storage layer, and is fully satisfied.

### 2.2 Pages compose sections dynamically — no fixed section slots

**Supersedes the original fixed-FK design.** Pages do not own section content; they own an
ordered composition of sections.

```
Page ──1:N──> PageSection ──N:1──> Section (concrete MTI base)
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
        HeroSection             FAQSection            GallerySection …
```

Why this replaced `HomePage.hero_section = FK(...)`:

| | Fixed FK slots | Page → PageSection → Section |
|---|---|---|
| Add a page | new model + migration + serializer + route | insert a row |
| Reorder sections | migration | one PATCH |
| Same type twice on a page (`top_cta`, `bottom_cta`) | **impossible** — the field is singular | natural |
| Aggregate API | one serializer per page | one endpoint, registry-driven |

The frontend routes settled it: `/locations`, `/legal/privacy`, `/legal/terms` and `/gallery`
were four pages the fixed design had not anticipated, each needing new code to support.

### 2.3 `order` is display-order only and appears in no constraint

```python
order = models.PositiveIntegerField(default=0)
class Meta:
    ordering = ["order", "id"]
```

Duplicates tolerated, `id` breaks ties. Applies to `PageSection.order` and every section-item
model.

**`unique(page, order)` is deliberately NOT created.** It would deadlock the atomic bulk
reorder it is meant to protect: swapping items 1↔2 violates the constraint on the very first
UPDATE inside the transaction. `unique(page, section_key)` **is** created — it stops two
sections claiming the same slot on a page, and never conflicts with reordering.

### 2.4 Audit logging records who changed what — nothing else

No `ip_address`, `user_agent`, `request_method`, `request_path`; no context middleware; no
model-level snapshot machinery.

One `AuditLogMixin` on the base admin view classes (`perform_create` / `perform_update` with a
before-snapshot / `perform_destroy`), plus explicit calls for LOGIN and LOGOUT. No audit code
in any individual view. Because it attaches to view base classes rather than to models, it can
land at any point without retrofitting anything.

**Accepted trade-off:** Django Admin edits, shell edits and data migrations go unlogged. The
REST API is the CMS.

A denylist (`password`, `token`, `secret`, `key`, `session`) strips sensitive values from
`changes` before writing.

### 2.5 Response envelope is infrastructure, not per-view code

- `EnvelopeJSONRenderer` — wraps into `{success, message, data}`, hoists pagination to a
  top-level `pagination` key, passes `204` and the schema endpoints through untouched.
- `envelope_exception_handler` — `{success, message, errors, code}`; maps `ProtectedError` to
  **409 naming the referencing objects**, which is what makes `on_delete=PROTECT` usable from
  a UI rather than a 500.
- `EnvelopePageNumberPagination` — the metadata shape the admin data tables consume.

### 2.6 One flag, not many

`PublishableModel` abstract, applied to **Project, Service, BlogPost, FAQ, Counter**:

```python
status       = DRAFT | PUBLISHED | ARCHIVED   # indexed
published_at = DateTimeField(null=True)       # set on first publish

.live() = status=PUBLISHED AND (published_at IS NULL OR published_at <= now())
```

Removed: every `is_published` / `is_active` variant. Retained: `Project.is_featured`, which is
curation rather than publishing.

Consistently, **`Section` has no `is_active`.** Visibility lives on `PageSection.is_visible`,
where it means something specific — "hidden on this page". A section attached to no page
already renders nowhere, so a second global flag earns nothing.

### 2.7 No refresh-token grace window

Expired / invalid / blacklisted / missing refresh token → `401`, both cookies cleared.
Concurrent-refresh races are not handled.

### 2.7a Django's built-in User — no custom user model

CMS accounts exist only so staff can edit website content: no public registration, no customer
accounts. `auth.User` carries everything `/auth/me/` needs.

* `auth.User` keys on `username` but login is by email → `EmailBackend` resolves email→user,
  and runs the hasher on unknown emails so timing does not leak which addresses exist.
* `auth.User.email` is not unique, which would make email login ambiguous → a case-insensitive
  partial unique index enforces it **in the database**, so it holds for the API, Django Admin,
  the shell and `createsuperuser` alike.

### 2.7b Logout cannot revoke an already-issued access token

Logout blacklists the refresh token and deletes both cookies. The access token is stateless
and stays valid until it expires; revoking it would need a DB lookup on every request, which
defeats stateless JWT. Mitigated by the 15-minute lifetime plus cookie deletion.

### 2.8 Class-based views only — never ViewSets

Every endpoint is a DRF generic class-based view (`ListCreateAPIView`, `RetrieveUpdateAPIView`,
`APIView`) wired with explicit `path()` entries. `ViewSet`, `ModelViewSet`, `@action` and DRF
routers are not used anywhere.

* Every URL is written out, so the route list is readable without expanding a router.
* Operations that would have been `@action` get their own class — `UserDeactivateAPIView`,
  `SectionItemReorderAPIView`, `PageSectionReorderAPIView`.
* `get_serializer_class()` dispatches on `request.method`, not `self.action`.

### 2.9 Multi-table inheritance for the Section hierarchy

`Section` is a **concrete** parent so `PageSection.section` can be a real ForeignKey with real
integrity. Concrete section models subclass it (Django MTI).

Alternatives rejected:

| Approach | Why not |
|---|---|
| `GenericForeignKey` | no DB-level FK, no `PROTECT`, no cascade — the integrity is imaginary |
| One nullable FK per type on `PageSection` | ~12 sparse columns plus a CHECK constraint to enforce exactly-one |
| JSONField blob | loses typing, validation and queryability — the thing this CMS exists to avoid |

MTI's one real cost is resolving a `Section` row to its concrete subclass. That is solved by
**batching per type** (§13), not by `InheritanceManager`, whose all-subclass LEFT JOIN is
slower and — the deciding point — cannot apply the different prefetches each section type
needs.

`section_type` is set automatically in each concrete model's `save()` and never accepted from
the client, so it cannot drift from the actual class.

---

## 3. Django app structure

```
archethos-backend/
├── .env  .env.example  docker-compose.yml  requirements/
├── DEVELOPMENT_PLAN.md  TASKS.md
├── manage.py
└── archethosbackend/
    ├── settings/            base.py  development.py  production.py  test.py
    ├── urls.py  wsgi.py  asgi.py
    └── apps/
        ├── core/            abstract models, mixins, validators, slug utils
        ├── accounts/        auth, cookie JWT, user/group/permission APIs   [DONE]
        ├── audit/           AuditLog, AuditLogMixin, read-only API
        ├── media_library/   MediaAsset, upload pipeline, YouTube parsing
        │
        ├── content/         ALL master content, split into modules:
        │                      models/project.py  Project, ProjectGalleryItem
        │                      models/service.py  Service
        │                      models/blog.py     BlogPost, BlogCategory
        │                      models/faq.py      FAQ
        │                      models/counter.py  Counter
        │
        │   ── presentation ──
        ├── sections/        Section MTI base, concrete sections, item models,
        │                    SECTION_REGISTRY
        ├── pages/           Page, PageSection, Company
        ├── enquiries/       Enquiry
        └── api/             renderer, exception handler, pagination,
                             generic CBV base classes, permissions,
                             MediaReferenceField, v1 routes
```

Each `AppConfig` sets `name = "archethosbackend.apps.projects"` and `label = "projects"` so
permission codenames stay flat (`projects.add_project`).

Two structural choices worth stating:

* **`sections` is one app.** Section models share the MTI base and are mutually referential;
  splitting them creates import cycles for no isolation benefit. Internally split into
  `models/base.py`, `models/hero.py`, `models/collections.py`, `models/cta.py`.
* **`company` is its own app, not part of `pages`.** `Company` is site-wide configuration, not
  a page, and it deserves its own permission (`company.change_company`) so "may edit site
  settings" can be granted independently of "may edit pages".

---

## 4. `core` — abstract models (no tables)

| Abstract | Fields / purpose |
|---|---|
| `TimeStampedModel` | `created_at`, `updated_at` |
| `SEOModel` | `meta_title`, `meta_description`, `meta_keywords`, `og_title`, `og_description`, `og_image` (FK MediaAsset), `canonical_url`, `robots_index`, `robots_follow` |
| `SluggedModel` | `title`, `slug` — unique, generated once, never regenerated (published URLs must not break because someone fixed a typo) |
| `PublishableModel` | `status`, `published_at`, `PublishableQuerySet.live()` |
| `OrderedItemModel` | `order`, `Meta.ordering = ["order", "id"]` |
| `SingletonModel` | pinned pk + `CheckConstraint` + `load()` — used only by `Company` |

---

## 5. Model catalogue

### 5.1 accounts — **DONE**

Uses `auth.User` unchanged; contributes behaviour, not tables: `EmailBackend`,
`CookieJWTAuthentication`, cookie helpers, the `cookieAuth` OpenAPI scheme, and the
case-insensitive unique email index. Role definitions live in `groups.py`, applied by the
bootstrap migration and refreshed by `manage.py sync_cms_groups`.

### 5.2 media_library

**`MediaAsset`** — `media_type` (IMAGE / VIDEO / DOCUMENT), `source_type` (UPLOAD / YOUTUBE),
`file`, `external_url`, `external_id`, `thumbnail_url`, `file_name`, `file_size`, `mime_type`,
`width`, `height`, `duration`, `title`, `alt_text`, `checksum` (sha256, indexed),
`uploaded_by`, timestamps.

`upload_to` produces `uploads/<uuid4>-<slug>.<ext>` — the user filename never determines
uniqueness. `relative_path` returns `/media/uploads/…`, or the external URL for YouTube.
`CheckConstraint`: `file` required for UPLOAD, `external_url` required for YOUTUBE.

### 5.3 content — master content, owns the content itself, reusable everywhere

| Model | Fields |
|---|---|
| **`Project`** | Slugged + Publishable + SEO + TimeStamped · `short_description`, `description`, `location`, `project_year`, `project_status` (CONCEPT / ONGOING / COMPLETED), `featured_image`, `is_featured`, `services` M2M, `search_vector` |
| **`ProjectGalleryItem`** | `project` (CASCADE), `media` (PROTECT), `caption`, `order` |
| **`Service`** | Slugged + Publishable + SEO + TimeStamped · `short_description`, `description`, `featured_image`, `icon`, `order` |
| **`BlogPost`** | Slugged + Publishable + SEO + TimeStamped · `excerpt`, `content`, `featured_image`, `author` (SET_NULL), `category` (SET_NULL), `reading_time`, `search_vector` |
| **`BlogCategory`** | `name`, `slug`, `description` |
| **`FAQ`** | Publishable + TimeStamped · `question`, `answer`, `category` |
| **`Counter`** | Publishable + TimeStamped · `prefix`, `content`, `postfix`, `subtitle`, `description` — see §5.5 |

### 5.4 sections

**`Section`** — the concrete MTI parent, the single table `PageSection` points at.

```python
class Section(TimeStampedModel):
    section_type   = CharField(choices=SectionType, db_index=True)  # set in save()
    internal_label = CharField(max_length=255)
```

`internal_label` is the admin-facing name for a section instance. Section models are master
tables holding many rows; opening the section browser otherwise shows several heroes with no
way to tell them apart from their content alone:

```
id  section_type  internal_label            title
1   hero          "Home - main hero"        "Architecture Beyond Boundaries"
2   hero          "About - studio hero"     "Who We Are"
3   cta           "Global - contact us"     "Let's Build Something Meaningful"
```

Never rendered on the public site, never present in public serializers. Purely for the CMS
section picker and admin tables, where "which hero is this?" is otherwise guesswork.

| Concrete section | Fields | Item model |
|---|---|---|
| `HeroSection` | `title`, `subtitle`, `background_media`, `cta_label`, `cta_url`, `overlay_opacity` | — |
| `IntroSection` | `eyebrow`, `heading`, `body`, `image` | — |
| `CounterSection` | `eyebrow`, `heading`, `description` | `CounterSectionItem` (`counter`, `order`) |
| `FeaturedProjectsSection` | `eyebrow`, `heading`, `subheading` | `FeaturedProjectItem` (`project`, `order`, `display_variant`) |
| `ServicesSection` | `eyebrow`, `heading`, `subheading` | `ServiceSectionItem` (`service`, `order`, `label_override`) |
| `GallerySection` | `eyebrow`, `heading`, `subheading`, `layout_variant` (GRID / MASONRY / SLIDER) | `GallerySectionItem` (`media`, `caption`, `order`) |
| `FAQSection` | `eyebrow`, `heading`, `subheading` | `FAQSectionItem` (`faq`, `order`) |
| `CTASection` | `heading`, `description`, `background_media`, `button_label`, `button_url` | — |
| `ContactInfoSection` | `address`, `phone`, `email`, `map_embed_url`, `office_hours` | — |
| `RichTextSection` | `heading`, `body` (HTML) — carries `/legal/privacy` and `/legal/terms` | — |

Every item model: `section` CASCADE, content FK **PROTECT**,
`UniqueConstraint(section, <content>)`, `order` unconstrained.

### 5.5 Counter section — confirmed against the live UI

From the "ARCHETHOS / AT A GLANCE" band. `Counter` is **master content**, not an inline row:
the same stat appears on the home and about pages and must be editable in one place.

```
Counter
  prefix       CharField, blank   "$", "~", usually empty
  content      CharField          "40", "2", "100"
                                  text, not int — "1.5K" and "24/7" must be allowed
  postfix      CharField, blank   "+", "%"
  subtitle     CharField          "PROJECTS DELIVERED"
  description  CharField, blank   "Residential, commercial and interior"
```

| prefix | content | postfix | subtitle | description |
|---|---|---|---|---|
| | 40 | + | PROJECTS DELIVERED | Residential, commercial and interior |
| | 2 | | CITIES SERVED | Lucknow and Kushinagar |
| | 5 | | DISCIPLINES IN-HOUSE | From first sketch to finished space |
| | 100 | % | CLIENT SATISFACTION | From first meeting to handover |

`prefix` / `postfix` are separate fields rather than baked into `content` because the design
styles them differently — the "+" and "%" render in the accent colour at a smaller size than
the number.

### 5.6 pages

Holds `Page`, `PageSection` and the `Company` singleton.

**`Page`** — Publishable + SEO + TimeStamped · `name`, `slug` (unique).

Uses the same `status` / `published_at` pair as every content model rather than a
bespoke `is_published` boolean, so "is this live?" means exactly one thing across the
system (§2.6).

`slug` is a validated `CharField`, **not** a `SlugField`: page slugs mirror frontend
routes, which nest — `legal/privacy` is real, and `SlugField` forbids `/`. The public
route therefore uses `<path:slug>`, not `<slug:slug>`.

No `page_type`. Home, About, Contact, Gallery, Locations and both Legal pages are all just
`Page` rows, created by an administrator without a migration.

**Listing pages** (`/journal`, `/projects`, `/services`) are ordinary `Page` rows too — they
own their hero, SEO and CTA. The list itself comes from `/api/v1/public/blogs/?page=1`, which
needs the pagination the aggregate endpoint deliberately does not have. The frontend route
calls both. No backend concept is required for this, which is why `page_type` stays absent.

**`PageSection`** — the composition table.

```python
class PageSection(TimeStampedModel):
    page        = FK(Page, CASCADE, related_name="page_sections")
    section     = FK(Section, PROTECT, related_name="page_usages")
    section_key = CharField(max_length=100)
    order       = PositiveIntegerField(default=0)
    is_visible  = BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        constraints = [UniqueConstraint(fields=["page", "section_key"],
                                        name="unique_page_section_key")]
```

`section` is **PROTECT**: removing a section from a page deletes only the `PageSection` row,
never the section itself, which may be in use elsewhere. `page_usages` answers "which pages
use this section?" — the admin UI must show that before allowing a delete.

**`section_type` vs `section_key`** — these answer different questions:

```
section_type  →  which component renders this          (on Section)
section_key   →  what role this instance plays on      (on PageSection)
                 this specific page
```

The same type may appear twice on one page — something the fixed-slot design could not express:

```
page   section_key       section_type        order
home   main_hero         hero                1
home   at_a_glance       counter             2
home   featured_work     featured_projects   3
home   top_cta           cta                 4
home   homepage_faq      faq                 5
home   bottom_cta        cta                 6   ← same type, different key
```

#### Company — singleton master

```
name · address · logo (FK MediaAsset)
social_urls    JSONB   {"instagram": "...", "linkedin": "..."}
contacts       JSONB   {"emails": [...], "phones": [...]}
header_links   JSONB   [{"label": "Projects", "url": "/projects"}]
footer_links   JSONB   [{"heading": "Company", "links": [...]}]
head_inject    TextField   → rendered inside <head>
body_inject    TextField   → rendered before </body>
meta_title · meta_description · meta_keywords     global SEO defaults
```

JSON fields use `JSONField` (JSONB), validated on write and queryable — same JSON over the
wire as a `TextField` would give, with none of the downsides.

**`head_inject` / `body_inject` are a stored-XSS vector**: whoever writes them executes
arbitrary JS on every page of the live site. The write serializer restricts **those two fields
only** to superusers; everything else in `Company` needs just `company.change_company`.

### 5.7 enquiries

**`Enquiry`** — one table for every form on the site: `form_type` (CONTACT / CONSULTATION /
CAREER / GENERAL), `name`, `email`, `phone`, `subject`, `message`, `extra` (JSONB — a new form
needs no migration), `source_page`, `is_read`.

### 5.8 audit

**`AuditLog`** — `user` (SET_NULL), `action` (CREATE / UPDATE / DELETE / LOGIN / LOGOUT /
PUBLISH / UNPUBLISH), `content_type`, `object_id`, `object_repr`, `changes` (JSONB),
`created_at`. Indexes on `(content_type, object_id)`, `(user, -created_at)`,
`(action, -created_at)`.

---

## 6. ERD

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              MEDIA LIBRARY                               │
│  MediaAsset — media_type · source_type · file/external_url · alt_text     │
└───┬──────────────────────────────────────────────────────────────────────┘
    │ PROTECT — referenced by master content AND by sections; never orphaned
    ├────────────┬────────────┬────────────┬──────────┬─────────────────────┐
    ▼            ▼            ▼            ▼          ▼                     ▼
┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ┌─────────┐  ┌───────────────────┐
│ Project │ │ Service  │ │ BlogPost │ │Counter │ │ Company │  │ HeroSection       │
│ +Gallery│ │  .icon   │ │          │ │  FAQ   │ │  .logo  │  │  .background_media│
│  Items  │ │          │ │          │ │(no img)│ │         │  │ CTASection  …     │
└────┬────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ └─────────┘  └───────────────────┘
     │           │            │           │
     │   MASTER CONTENT — status: DRAFT | PUBLISHED | ARCHIVED
     └───────────┴────────────┴───────────┘
                       │ PROTECT
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│               SECTION ITEMS  (ordered intermediates)                     │
│  FAQSectionItem · CounterSectionItem · FeaturedProjectItem                │
│  ServiceSectionItem · GallerySectionItem                                  │
│  each: UniqueConstraint(section, content)  ·  order in NO constraint      │
└───────────────────────────┬──────────────────────────────────────────────┘
                            │ CASCADE (item → section)
                            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   Section   (concrete MTI parent)                        │
│             section_type · internal_label · timestamps                   │
│                                                                          │
│   ┌───────┬───────┬─────────┬──────────┬─────────┬───────┬─────┬──────┐  │
│   ▼       ▼       ▼         ▼          ▼         ▼       ▼     ▼      ▼  │
│  Hero  Intro  Counter  Featured   Services  Gallery   FAQ   CTA  RichText│
│                        Projects                                  Contact │
│   each subclass = its own table, joined to section by pk (Django MTI)    │
└───────────────────────────┬──────────────────────────────────────────────┘
                            │ N:1   PROTECT
                            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                             PageSection                                  │
│      page · section · section_key · order · is_visible                   │
│      UniqueConstraint(page, section_key)       order: NO constraint      │
└───────────────────────────┬──────────────────────────────────────────────┘
                            │ N:1   CASCADE
                            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                                Page                                      │
│         name · slug (unique) · is_published · SEO · timestamps           │
│   home · about · contact · gallery · locations · journal · projects      │
│   services · legal/privacy · legal/terms   —  all just rows              │
└───────────────────────────┬──────────────────────────────────────────────┘
                            ▼
              GET /api/v1/public/pages/{slug}/   →   NEXT.JS

┌──────────────────────────────────────────────────────────────────────────┐
│  CROSS-CUTTING                                                           │
│  User ──< Group >── Permission      (Django native — no custom RBAC)     │
│  Company (singleton)   ·   Enquiry   ·   AuditLog                        │
└──────────────────────────────────────────────────────────────────────────┘
```

### Deletion rules, stated once

| Relationship | `on_delete` | Effect |
|---|---|---|
| content / section → MediaAsset | **PROTECT** | cannot delete an in-use image; 409 names the referents |
| item → section | **CASCADE** | deleting a section drops its item rows only, never master content |
| item → master content | **PROTECT** | cannot delete a FAQ that is placed in a section |
| PageSection → Section | **PROTECT** | removing a section from a page never deletes the section |
| PageSection → Page | **CASCADE** | deleting a page drops its composition rows only |
| concrete section → Section | MTI parent link | deleting a `HeroSection` deletes its `Section` row |
| BlogPost → author | **SET_NULL** | deactivating a user never destroys content |
| AuditLog → user | **SET_NULL** | audit history outlives the account |

---

## 7. Authentication — **DONE**

```
POST /api/v1/auth/login/  →  Set-Cookie: access_token   HttpOnly  Path=/api/
                             Set-Cookie: refresh_token  HttpOnly  Path=/api/v1/auth/
                             Set-Cookie: csrftoken      readable
                             200 { user, groups, permissions }   ← no token values

every request →  CookieJWTAuthentication
                   1. read access_token cookie
                   2. Bearer header fallback (non-browser clients)
                   3. validate signature + expiry
                   4. enforce CSRF on unsafe methods
                   5. AccessToken.verify() rejects a refresh token

401 →  POST /api/v1/auth/refresh/   rotate + blacklist + reset both cookies
       any failure → 401 with both cookies cleared (no grace window)

POST /api/v1/auth/logout/  →  blacklist refresh, delete both cookies, 204
```

The refresh cookie is scoped to `Path=/api/v1/auth/` so it is not transmitted on ordinary API
calls. Cookie auth is CSRF-relevant in a way a Bearer header is not, so CSRF is enforced on
unsafe methods and never disabled.

**Default topology `SameSite=Lax`** — works in development, since `localhost:3000` →
`localhost:8000` is same-site. In production keep the admin and the API on the same
registrable domain. Only if genuinely cross-site, switch to `SameSite=None; Secure` with the
double-submit token.

---

## 8. Permission architecture — **DONE**

```
/api/v1/public/*  →  AllowAny · read-only · .live() querysets only
/api/v1/auth/*    →  AllowAny (login, refresh) · IsAuthenticated (me, logout)
/api/v1/admin/*   →  IsAuthenticated AND StrictDjangoModelPermissions
                        GET → view_*       POST → add_*
                        PUT/PATCH → change_*   DELETE → delete_*
                     superuser bypasses (Django convention)
```

`StrictDjangoModelPermissions` adds the `view_*` requirement on GET that DRF's stock class
omits — without it, "this user may only view Projects" is unenforceable in the negative
direction.

**Section-item and page-section permissions derive from the parent.** Editing a
`FAQSectionItem` checks `sections.change_faqsection`; editing a `PageSection` checks
`pages.change_page`. Per-item permission rows would make the group picker unusable.

**Escalation guards** (Django provides none of these): grant only permissions you hold · group
assignment checked the same way, since a group grants everything inside it · only superusers
set `is_superuser` / `is_staff` · nobody deactivates themselves · the last active superuser
cannot be deactivated · `head_inject` / `body_inject` are superuser-only.

`/auth/me/` resolves permissions via `get_all_permissions()`. **Never stored in the JWT
payload**, so a revocation takes effect on the next request rather than at token expiry.

### Default roles

Defined in `accounts/groups.py`, applied by the bootstrap migration, refreshed with
`manage.py sync_cms_groups` — which **must be re-run after each content phase**, since the
roles grant whatever models exist when they are synced.

| Group | Scope |
|---|---|
| `Administrators` | all content + users + audit + company |
| `Content Managers` | all content; no users, no audit |
| `Editors` | view + change content; no delete |
| `Media Managers` | the media library only |

---

## 9. Section registry

One centralised mapping, in `sections/registry.py`. No `if section_type == …` anywhere else in
the codebase.

```python
@dataclass(frozen=True)
class SectionSpec:
    model: type[Section]
    list_serializer: type[Serializer]
    detail_serializer: type[Serializer]
    write_serializer: type[Serializer]
    public_serializer: type[Serializer]
    url_segment: str                              # "hero", "faq", …
    #: applied when the aggregate API batch-loads this type
    public_queryset: Callable[[QuerySet], QuerySet]

SECTION_REGISTRY: dict[str, SectionSpec] = {
    "hero": SectionSpec(HeroSection, …,
                        public_queryset=lambda qs: qs.select_related("background_media")),
    "faq":  SectionSpec(FAQSection, …,
                        public_queryset=lambda qs: qs.prefetch_related("items__faq")),
    …
}
```

Adding a section type:

```
1. model subclassing Section       4. register in SECTION_REGISTRY
2. its four serializers            5. admin URLs — generated from the registry, so free
3. add to SectionType choices      6. frontend adds its component to its own registry
```

Admin section routes are generated by iterating the registry, so step 5 costs nothing.

---

## 10. API surface

### `/api/v1/auth/` — **DONE**
```
login/   refresh/   logout/   me/   password/change/   csrf/
```

### `/api/v1/admin/` — every list paginated, searchable, filterable, orderable
```
users/ · users/{id}/ · users/{id}/{deactivate,activate,set-password}/      [DONE]
groups/ · groups/{id}/ · permissions/                                      [DONE]
audit-logs/ · audit-logs/{id}/                                (read-only)

media/ · media/{id}/ · media/upload/ · media/youtube/ · media/{id}/usage/

projects/ · projects/{id}/
    projects/{id}/gallery/ · gallery/{item_id}/ · gallery/reorder/
services/ · services/{id}/
blogs/ · blogs/{id}/ · blogs/{id}/{publish,unpublish}/
blog-categories/ · faqs/ · counters/
enquiries/ · enquiries/{id}/
company/                                        GET · PATCH (singleton)

# sections — routes generated from SECTION_REGISTRY
sections/                                       all sections, ?section_type= filter
sections/{type}/                                list + create    e.g. sections/hero/
sections/{type}/{id}/                           detail · update · delete
sections/{type}/{id}/items/                     list + add       (types that have items)
sections/{type}/{id}/items/{item_id}/           update · remove
sections/{type}/{id}/items/reorder/             atomic bulk reorder

# page composition
pages/ · pages/{id}/
pages/{id}/sections/                            list + attach a section
pages/{id}/sections/{page_section_id}/          update key / visibility / order
pages/{id}/sections/reorder/                    atomic bulk reorder
```

### `/api/v1/public/` — read-only, `.live()` only
```
pages/{slug}/           the aggregate endpoint — never paginated
projects/ · projects/{slug}/      ?featured=&service=&year=&status=
services/ · services/{slug}/
blogs/ · blogs/{slug}/            ?category=&search=
faqs/ · company/
search/?q=                        projects + services + blogs
enquiries/                        POST only — rate-limited, honeypot
```

### Meta
```
/api/v1/schema/   /api/v1/schema/docs/   /health/
```

### Standard admin list parameters
```
?page=1&page_size=20&search=villa&ordering=-created_at
+ resource filters: ?status=PUBLISHED  ?media_type=IMAGE  ?section_type=hero  ?is_active=true
```

---

## 11. Response format

```json
{ "success": true, "message": "Projects retrieved successfully", "data": [] }
```
```json
{ "success": true, "message": "…",
  "pagination": { "page": 1, "page_size": 20, "total_items": 156,
                  "total_pages": 8, "has_next": true, "has_previous": false },
  "data": [] }
```
```json
{ "success": false, "message": "Validation failed",
  "errors": { "slug": ["This slug is already in use."] }, "code": "validation_error" }
```

`200` · `201` · `204` (empty, unwrapped) · `400` · `401` · `403` · `404` · `409` (PROTECT
violations, slug and section_key conflicts) · `429`.

---

## 12. Serializer strategy

Four variants per admin resource:

| Serializer | Purpose |
|---|---|
| `XListSerializer` | flat data-table columns, **zero nested objects** |
| `XDetailSerializer` | full record + nested items |
| `XWriteSerializer` | create / update, media by id-or-path, owns validation |
| `PublicXSerializer` | published fields only |

**Public serializers are independent classes, never subclasses of the admin ones** — that is
exactly how admin fields leak into public payloads six months later.

```
Models       fields, constraints, PublishableQuerySet
Selectors    live(), for_public(), for_admin_list()  ← all prefetch logic lives here
Serializers  shape + validation
Services     only where genuinely multi-step: upload pipeline, publish transitions,
             atomic reorder, user creation, audit writes
Views        thin CBVs, ~5-15 lines
Permissions  declarative classes
```

Shared base classes in `apps/api/generics.py`: `AdminListCreateAPIView`,
`AdminRetrieveUpdateDestroyAPIView` (both **done**), plus `SectionItemListCreateAPIView`,
`SectionItemDetailAPIView`, `ReorderAPIView` — written once, subclassed per section type and
reused for page composition.

**Reorder** validates: all ids belong to this parent · no duplicate ids · no unknown ids. Then
`transaction.atomic()` + `bulk_update(["order"])`. No deferrable-constraint juggling is needed,
because `order` carries no constraint (§2.3).

---

## 13. Aggregate page API

`GET /api/v1/public/pages/{slug}/`

```json
{
  "id": 1, "name": "Home", "slug": "home",
  "seo": { "meta_title": "…", "meta_description": "…", "og_image": "/media/…",
           "canonical_url": "", "robots_index": true, "robots_follow": true },
  "sections": [
    { "id": 1, "key": "main_hero", "type": "hero",
      "data": { "title": "Architecture Beyond Boundaries",
                "background_media": "/media/uploads/hero.webp",
                "cta_label": "Explore Projects", "cta_url": "/projects" } },

    { "id": 2, "key": "at_a_glance", "type": "counter",
      "data": { "eyebrow": "ARCHETHOS / AT A GLANCE",
                "items": [ { "content": "40", "postfix": "+",
                             "subtitle": "PROJECTS DELIVERED",
                             "description": "Residential, commercial and interior" } ] } }
  ]
}
```

`sections` is ordered by `PageSection.order`, filtered to `is_visible=True`, and each entry
carries `key` + `type` so the frontend registry can select a component. `internal_label` is
never exposed.

### Query strategy — batch by type, not by section

The one real cost of MTI is resolving `Section` rows to concrete subclasses. Naive resolution
is N+1; `InheritanceManager`'s all-subclass LEFT JOIN is slower and cannot apply per-type
prefetches. So:

```
1  Page by slug                                                         1 query
2  PageSection + section parent, visible, ordered                       1 query
3  group the ids by section_type, then ONE batch per DISTINCT type,
   each with the prefetches that type needs (from SECTION_REGISTRY):

     HeroSection.filter(pk__in=[…]).select_related("background_media")        1
     CounterSection.filter(pk__in=[…]).prefetch_related("items__counter")     2
     FAQSection.filter(pk__in=[…]).prefetch_related("items__faq")             2
     GallerySection.filter(pk__in=[…]).prefetch_related("items__media")       2
     FeaturedProjectsSection…prefetch_related("items__project__featured_image") 2
     ServicesSection…prefetch_related("items__service__featured_image")       2
     CTASection.filter(pk__in=[…]).select_related("background_media")         1
```

**Measured at 16 queries** for an 8-section page: 2 setup + 1 per simple type + 2 per
collection type. Bounded by the number of distinct section *types* present, not by content
volume. A page with 40 gallery images costs the same as one with 4. Pinned with
`assertNumQueries` so a future serializer change cannot silently regress it.

`ETag` + `Cache-Control: public, max-age=60, stale-while-revalidate=300` derived from the max
`updated_at` in the graph. Never paginated.

---

## 14. Database & search

- Unique + indexed slug on every slugged model and on `Page`.
- `UniqueConstraint(page, section_key)`. **No** constraint on any `order` column.
- `UniqueConstraint(section, content)` on every section-item model.
- Composite index `(status, published_at)` on all publishable models.
- Index on `Section.section_type` — the aggregate API groups by it.
- `search_vector` (`SearchVectorField` + GIN) on Project and BlogPost, weighted title=A,
  excerpt / short_description=B, body=C. Extensions `pg_trgm` and `unaccent` via migration.
- `CheckConstraint`s: `published_at` consistency; `MediaAsset` source/file/url consistency.
- **Search stays inside PostgreSQL.** No Elasticsearch.

---

## 15. Security checklist

- Secrets, DB credentials and origins from `.env`, never committed
- `DEBUG=False` and `ALLOWED_HOSTS` asserted at boot in production
- HttpOnly + Secure + SameSite cookies; refresh cookie path-scoped
- CSRF enforced on unsafe methods by `CookieJWTAuthentication`; never disabled
- `CORS_ALLOW_CREDENTIALS = True` with an explicit origin list, never `*`
- Refresh rotation + blacklist
- Upload validation: extension allowlist, MIME sniff, max size, dimension caps, Pillow verify
  (an uploaded `.jpg` that is not an image is rejected)
- YouTube URL allowlist + video-id extraction
- Escalation guards on the user and group APIs
- `head_inject` / `body_inject` restricted to superusers
- Public enquiry endpoint rate-limited + honeypot
- Audit denylist strips passwords and tokens from `changes`
- HSTS, SSL redirect, `X_FRAME_OPTIONS`, referrer policy

---

## 16. Environment variables

```
DEBUG  SECRET_KEY  ALLOWED_HOSTS
DB_NAME  DB_USER  DB_PASSWORD  DB_HOST  DB_PORT
CORS_ALLOWED_ORIGINS  CSRF_TRUSTED_ORIGINS
AUTH_COOKIE_SECURE  AUTH_COOKIE_SAMESITE  AUTH_COOKIE_DOMAIN
ACCESS_TOKEN_LIFETIME_MINUTES  REFRESH_TOKEN_LIFETIME_DAYS
MEDIA_URL  MAX_UPLOAD_SIZE_MB
```

**No `$` in any value** — docker-compose reads the same `.env` and interpolates `$VAR`, which
silently mangles the value. Generate keys with
`python -c "import secrets; print(secrets.token_urlsafe(48))"`.

---

## 17. Local PostgreSQL via Docker

Only PostgreSQL is containerised; Django runs on the host venv, so `runserver`, the debugger
and migrations behave normally.

```bash
docker compose up -d db      docker compose ps       docker compose down
docker compose down -v       # destroys the volume — wipes the database
```

**Host port 5433** — an unrelated `postgres_db` container owns 5432 on this machine. The
container still listens on 5432 internally; only the published port differs.

---

## 18. Frontend routes

The Next.js UI is at `archethos-nextjs/archethos`. Read for reference; **never modified from
this repo.**

```
(website)/                home           (website)/locations       locations
(website)/about           about          (website)/legal/privacy   legal/privacy
(website)/contact         contact        (website)/legal/terms     legal/terms
(website)/gallery         gallery
(website)/journal         journal    ┐   (website)/journal/[slug]   BlogPost detail
(website)/projects        projects   │   (website)/projects/[slug]  Project detail
(website)/services        services   ┘   (website)/services/[slug]  Service detail
(admin)/admin, /admin/login    the CMS frontend, same Next.js app
```

Every one of these is a `Page` row. No `/vastu` route exists — Vastu is a `Service`, not a
page. The `/legal/*` pages are composed from a `RichTextSection`.

---

## 19. Roadmap

| Phase | Goal | Status |
|---|---|---|
| 1 | Architecture | **done** |
| 2 | Foundation: `apps/`, settings, Postgres, envelope + pagination + exceptions, core abstracts | **done** |
| 3 | Cookie JWT auth on `auth.User` | **done** |
| 4 | Users, groups, permissions, escalation guards | **done** |
| 5 | Media Library + `MediaReferenceField` | **done** |
| 6 | Master content: FAQ, Counter, Project, Service, BlogPost, BlogCategory | **done** |
| 7 | `Section` MTI base + concrete sections + `SECTION_REGISTRY` + section CRUD | **done** |
| 8 | Section items + atomic bulk reorder | **done** |
| 9 | `Page` + `PageSection` + composition, visibility, reorder APIs | **done** |
| 10 | Public aggregate `/pages/{slug}/` with batched resolution + `assertNumQueries` | **done** |
| 11 | PostgreSQL search + `Enquiry` + `Company` | **done** |
| 12 | Audit, Django Admin, OpenAPI polish, seed command, deployment notes | |

Audit sits late deliberately: `AuditLogMixin` attaches to the view base classes rather than to
models, so nothing needs retrofitting when it lands. (This reverses the Phase 1 plan, which
front-loaded audit on the mistaken assumption it would be model-level.)

---

## 20. Open items

| Item | Status |
|---|---|
| Production deployment topology (same registrable domain vs cross-site) | default `SameSite=Lax`; revisit before production |
| Field-level survey of the UI components, per section type | do at the start of Phase 7 |
| `/locations` — a `Location` master model, or just sections? | decide at Phase 9 |
