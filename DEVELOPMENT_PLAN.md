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

### 2.2 Every page is its own model — code defines structure, the CMS defines content

**Supersedes the dynamic `Page → PageSection → Section` composition, which is deleted.**

The site is nine fixed routes, not an arbitrary tree, and modelling it as a page builder cost
more than it bought. Reading the schema told you nothing about the website: to learn that the
home page opens with a hero you had to query a join table, and the frontend needed a registry
to turn rows back into components.

Each page is now a named model whose fields, read top to bottom, are its render order:

```
HomePage
    hero · intro · stats · featured_project · services
    design_build · projects · gallery · vastu · locations · cta
```

| | Generic page builder | A model per page |
|---|---|---|
| What the schema tells you | that pages have sections | what the website is |
| Adding a page | insert a row | model + serializer + component |
| Reordering sections | one PATCH | a code change, reviewed |
| Rendering | registry lookup per row | the components, written out |
| Invalid structure | representable | not representable |

Adding a page being harder is the trade, made deliberately. A corporate site gains a page
every few years; the cost of that is a morning, and what it buys is that an editor can never
leave the site in a shape the frontend cannot render.

Two escape hatches survive where they genuinely pay:

* **Shared section models.** Hero, CTA, Process and RichText are one model each, reused
  wherever the structure is *genuinely identical*. Each page still holds its own row.
* **Variants.** A section that has several designs carries `variant` as a field. The frontend
  owns the visual implementation; the CMS only chooses between them. No `HeroVariant1` model.

### 2.3 `order` is display-order only and appears in no constraint

```python
order = models.PositiveIntegerField(default=0)
class Meta:
    ordering = ["order", "id"]
```

Duplicates tolerated, `id` breaks ties. Applies to every section-item model. Page structure
carries no `order` at all - the order sections render in is the order they are declared in on
the page model.

**`unique(section, order)` is deliberately NOT created.** It would deadlock the very rewrite it
is meant to protect: swapping items 1 and 2 violates the constraint on the first UPDATE inside
the transaction. What *is* constrained is `unique(section, record)`, which stops a section
listing the same thing twice and never conflicts with reordering.

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

Consistently, **sections carry no publish flag of their own.** A page is published or it is
not, and a section is part of exactly one page. An empty section renders nothing already, so a
per-section switch would only be a second way to express the same thing.

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
* Operations that would have been `@action` get their own class - `UserDeactivateAPIView`,
  `BlogPostPublishAPIView`, `MediaReplaceAPIView`.
* `get_serializer_class()` dispatches on `request.method`, not `self.action`.

### 2.9 Sections are plain tables — no inheritance, no discriminator

The MTI `Section` base and its `section_type` discriminator are deleted along with the
composition model that needed them. A section is now an ordinary table with ordinary columns,
referenced by exactly one page through a `OneToOneField` declared on the page.

Alternatives rejected, and why they stay rejected:

| Approach | Why not |
|---|---|
| `GenericForeignKey` | no DB-level FK, no `PROTECT`, no cascade — the integrity is imaginary |
| MTI with a `section_type` column | needs runtime resolution to the concrete subclass, which is what forced the registry |
| JSONField blob | loses typing, validation and queryability — the thing this CMS exists to avoid |

The cost MTI existed to pay — resolving a row to its real class — no longer exists, because
nothing is polymorphic. `HomePage.hero` is a column pointing at `HeroSection`, and Django's
`select_related` follows it in the same query as the page.

---

## 3. Django app structure

```
archethosbackend/apps/
    core/            abstract models only - no tables
    accounts/        auth, roles, admin user management
    media_library/   MediaAsset, upload/replace/usage
    content/         MASTER DATA: Service, Project, BlogPost, FAQ,
                     Counter, GalleryItem, Location
    pages/           THE SITE: ten page models, their sections, Company
    enquiries/       the contact form
    audit/           who changed what
    api/             envelope, generics, fields, routing, dashboard
```

There is no `sections` app. A section belongs to the page that renders it, so it lives beside
that page - `pages/models/home.py` holds `HomePage` and every section only the home page has.
Sections shared by several pages are in `pages/models/shared.py`.

The `content` / `pages` split is the load-bearing one:

* **`content` is master data.** A `Service` exists because the studio offers it, whether or
  not any page happens to list it. Edited in one place, referenced from many.
* **`pages` is the website.** A section is meaningless outside the page it renders on.

If the same entity can logically exist on its own and appear in more than one place, it is
master data. Otherwise it is section content.

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

### 5.3 content - master data, owned once and referenced everywhere

| Model | Fields |
|---|---|
| **`Project`** | Slugged + Publishable + SEO + TimeStamped, `short_description`, `description`, `location`, `project_year`, `project_status` (CONCEPT / ONGOING / COMPLETED), `category` (RESIDENTIAL / COMMERCIAL / INTERIOR / RENOVATION), `layout` (full / half / portrait), `cover_image`, the five narrative blocks (`design_intent`, `spatial_planning`, `interior_note`, `construction_note`, `outcome_note`), `is_featured`, `services` M2M, `search_vector` |
| **`ProjectMaterial`** | `project` (CASCADE), `name`, `note`, `order` |
| **`ProjectGalleryItem`** | `project` (CASCADE), `media` (PROTECT), `kind` (GALLERY / FLOOR_PLAN / DRAWING), `title`, `caption`, `description`, `order` |
| **`Service`** | Slugged + Publishable + SEO + TimeStamped, `number`, `title_lines`, `hero_heading`, `short_description`, `description`, `hero_image`, `index_image`, `icon`, `is_featured`, `process_label`, `order`, `search_vector` |
| **`ServiceDetailSection`** | `service` (CASCADE), `label`, `heading`, `body`, `items` (JSON), `image`, `image_ratio`, `order` |
| **`ServiceProcessStep`** | `service` (CASCADE), `number`, `title`, `body`, `order` |
| **`ServiceGalleryItem`** | `service` (CASCADE), `media` (PROTECT), `caption`, `order` |
| **`BlogPost`** | Slugged + Publishable + SEO + TimeStamped, `excerpt`, `content`, `featured_image`, `author` (SET_NULL), `category` (SET_NULL), `reading_time`, `search_vector` |
| **`BlogCategory`** | `name`, `slug`, `description` |
| **`FAQ`** | Publishable + TimeStamped, `question`, `answer`, `category` |
| **`Counter`** | Publishable + TimeStamped, `prefix`, `content`, `postfix`, `subtitle`, `description` |
| **`GalleryItem`** | Publishable + TimeStamped, `title`, `caption`, `category`, `image` (PROTECT) |
| **`Location`** | Publishable + TimeStamped, `city` (unique), `state`, `coordinates`, `blurb`, `image`, `address`, `phone`, `email`, `map_url` |

`Service` and `Project` carry everything their detail routes render, because a detail page is
the record - not a page composed of sections. `ServiceDetailSection` is owned by the service
and travels with it, which is what keeps it out of `pages`: no page composes those, the
service does.

`GalleryItem` and `Location` were hardcoded in the frontend before the refactor. `GalleryItem`
is distinct from `MediaAsset`: an asset is a file, a gallery item is a published piece of work
with a title, a caption and a category. Plenty of assets are never gallery items.

`Location`'s address, phone, email and map URL are deliberately optional and deliberately
blank. The studio has confirmed the cities but not the premises, and the frontend omits an
empty field rather than printing a placeholder.

### 5.4 pages - the ten pages

Every page model is a singleton carrying SEO, `is_published`, and one `OneToOneField` per
section **in render order**. `required_sections` names the ones that must be filled before
the page can be published.

| Route | Model | Sections, in order |
|---|---|---|
| `/` | `HomePage` | hero, intro, stats, featured_project, services, design_build, projects, gallery, vastu, locations, cta |
| `/about` | `AboutPage` | hero, story, mission_vision, founder, process, philosophy, presence, cta |
| `/services` | `ServicesPage` | hero, index, process, cta |
| `/projects` | `ProjectsPage` | hero, index, cta |
| `/gallery` | `GalleryPage` | hero, grid, cta |
| `/journal` | `JournalPage` | hero, featured, list, cta |
| `/locations` | `LocationsPage` | hero, locations, visiting, cta |
| `/contact` | `ContactPage` | hero, form, details, what_happens, cta |
| `/legal/privacy` | `PrivacyPage` | body |
| `/legal/terms` | `TermsPage` | body |

`ORDERED_PAGES` maps route to model and is the one place that knows the site has ten pages.
`manage.py ensure_pages` creates the rows and runs on every deploy.

Two singletons for the legal pages rather than one table with a slug: they are genuinely two
fixed routes, and a `LegalPage(slug=...)` table would be the same generic-page mistake in
miniature - it would invite a third row that nothing renders.

### 5.5 Sections

**Shared** (`pages/models/shared.py`) - reused where the structure is genuinely identical:

| Model | Fields | Children |
|---|---|---|
| `HeroSection` | variant, autoplay_seconds | `HeroSlide` (eyebrow, heading, lead, media) |
| `CTASection` | heading block, body, media, two links | - |
| `ProcessSection` | heading block, tone | `ProcessStep` (number, title, body) |
| `RichTextSection` | heading block, intro, updated_on | `RichTextBlock` (title, body) |

**Page-specific** - one module per page. Sections that list master data hold an item model and
nothing else for that content:

```
StatsSection           -> StatsSectionItem     -> content.Counter
HomeServicesSection    -> HomeServiceItem      -> content.Service
HomeProjectsSection    -> HomeProjectItem      -> content.Project
HomeGallerySection     -> HomeGalleryItem      -> content.GalleryItem
HomeLocationsSection   -> HomeLocationItem     -> content.Location
ServiceIndexSection    -> ServiceIndexItem     -> content.Service
ProjectIndexSection    -> ProjectIndexItem     -> content.Project
GalleryGridSection     -> GalleryGridItem      -> content.GalleryItem
LocationsListSection   -> LocationsListItem    -> content.Location
AboutPresenceSection   -> AboutLocationItem    -> content.Location
JournalFeaturedSection -> JournalFeaturedItem  -> content.BlogPost
```

An explicit item model rather than a plain `ManyToManyField`, because ordering is per-section
and there is room for per-section configuration later. Each carries a unique constraint on
`(section, record)` so a section cannot list the same thing twice.

### 5.6 Variants

A section with several designs carries `variant` as a `TextChoices` field. `HeroSection` has
`PHOTOGRAPHIC` and `SLIDER`. There is no `HeroVariant1` model and no variant table - the
frontend owns the components, the CMS picks between them, and adding a design is a component
plus a choice member.

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
                            MEDIA LIBRARY
   MediaAsset - media_type, source_type, file/external_url, alt_text
        |
        |  PROTECT everywhere. Referenced by master data, by sections and by
        |  Company; an asset in use cannot be deleted out from under a page.
        v
   ------------------------------------------------------------------
                            MASTER DATA (content)
     Project        Service       BlogPost     FAQ    Counter
      +Materials     +Detail       +Category
      +Gallery       +Process
                     +Gallery
     GalleryItem    Location
   ------------------------------------------------------------------
        |
        |  PROTECT. A record listed on a live page cannot be deleted;
        |  the error names the sections still using it.
        v
                     SECTION ITEMS (ordered intermediates)
     StatsSectionItem, HomeServiceItem, HomeProjectItem, HomeGalleryItem,
     HomeLocationItem, ServiceIndexItem, ProjectIndexItem, GalleryGridItem,
     LocationsListItem, AboutLocationItem, JournalFeaturedItem

     each: UniqueConstraint(section, record)  ·  order in NO constraint
        |
        |  CASCADE (item -> section). An item is meaningless without it.
        v
                              SECTIONS
     shared:  HeroSection (+HeroSlide) · CTASection
              ProcessSection (+ProcessStep) · RichTextSection (+RichTextBlock)

     per page: HomeIntroSection, StatsSection, FeaturedProjectSection,
               HomeServicesSection, DesignBuildSection (+points), ...
               StudioStorySection, MissionVisionSection (+blocks),
               FounderSection, PhilosophySection (+points), ...
        ^
        |  OneToOneField, declared ON THE PAGE, in render order.
        |  PROTECT: a section cannot vanish from under a live page.
        |
                               PAGES
     HomePage · AboutPage · ServicesPage · ProjectsPage · GalleryPage
     JournalPage · LocationsPage · ContactPage · PrivacyPage · TermsPage

     each a singleton (pk=1), each carrying SEO + is_published
        |
        v
   GET /api/v1/public/pages/{route}/   ->   NEXT.JS

   CROSS-CUTTING
     User >-- Group --< Permission      (Django native, no custom RBAC)
     Company (singleton)  ·  Enquiry  ·  AuditLog
```

Read the arrows in the middle carefully: the OneToOne points **from the page to the section**,
which is what makes a page's field list its structure. Sections point at nothing; items point
at master data. There is no table in this diagram whose job is to say which sections a page
has.

### Deletion rules, stated once

| Relationship | `on_delete` | Effect |
|---|---|---|
| content / section -> MediaAsset | **PROTECT** | cannot delete an in-use image; 409 names the referents |
| item -> section | **CASCADE** | deleting a section drops its item rows only, never master data |
| item -> master data | **PROTECT** | cannot delete a Service that a section lists |
| page -> section | **PROTECT** | a section cannot vanish out from under a live page |
| child -> parent record | **CASCADE** | a project's materials and gallery go with the project |
| BlogPost -> author | **SET_NULL** | deactivating a user never destroys content |
| AuditLog -> user | **SET_NULL** | audit history outlives the account |

Pages themselves are never deleted - there is no endpoint for it. The site has ten, declared
in code.

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

**Section and item permissions derive from the page.** Everything on a page is written
through that page's endpoint, so the check is `pages.change_homepage` - one permission per
page, not one per section. Per-section permission rows would make the group picker unusable
and would not describe how anyone actually works.

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

## 9. What replaced the section registry

`SECTION_REGISTRY` is deleted, on both sides. Nothing dispatches on a type string.

What remains is `ORDERED_PAGES` - a route to model map, and its serializer twin
`PAGE_SERIALIZERS`. The two are asserted equal at import, so a page without a serializer fails
at boot rather than 404-ing in production with no clue why.

The difference matters. A registry resolved *content* to a renderer at runtime, which meant
the set of section types was data and the frontend had to be generic. This maps a *route* to a
component, over a closed set of ten, all of which are written out. A missing key is a bug, not
a content problem.

The frontend mirror is `PAGE_EDITORS` in the admin, and nothing at all on the website: the
public pages import their sections directly.

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

# pages - one endpoint each, no create, no delete
pages/                                          the ten pages with publish state
pages/{route}/                                  GET the whole page - PATCH any of it
                                                <path:> converter: "legal/privacy" has a slash

# master data added by the page refactor
gallery/ · gallery/{id}/
locations/ · locations/{id}/

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
+ resource filters: ?status=PUBLISHED  ?media_type=IMAGE  ?category=INTERIOR  ?media_location=local
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
violations and slug conflicts) · `429`.

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

## 13. Page API

One endpoint per page, addressed by its public route:

```
GET   /api/v1/admin/pages/            the ten pages with publish state
GET   /api/v1/admin/pages/home/       the whole page, every section
PATCH /api/v1/admin/pages/home/       partial write, one transaction
GET   /api/v1/public/pages/home/      published only, 404 otherwise
GET   /api/v1/public/pages/           which routes are live
```

No create, no delete. The site has ten pages, declared in code.

**Write semantics.** A PATCH is partial at every level: an omitted section is untouched, an
omitted item collection is left alone, and `[]` clears one. That distinction is the reason
collections are explicit rather than inferred. Item order is array order, which removes the
reorder endpoints entirely - reordering is sending the array again.

**Read shape.** The public payload is what the frontend renders: sections as named keys,
master data inlined, no join rows and no admin bookkeeping. The admin payload keeps
`{id, detail}` on items because the form needs the id it will send back.

### Query strategy - derived from the models, not hand-written

`pages/selectors.py` builds the plan by walking the model:

* every section is a `OneToOneField` on the page, so one `select_related` brings the page and
  all eleven sections back in **one query**;
* every item collection is a reverse FK on a section, so one `prefetch_related` each;
* each prefetch joins the item's master record **and that record's own media** - one level is
  not enough, and missing the second is an N+1 hiding behind a `select_related` that looks
  correct.

The cost is therefore a function of how many *kinds* of thing a page has, not how many rows.
Pinned by a test: an eleven-section home page costs the same whether it carries three gallery
images or thirty.

---

## 14. Database & search

- Unique + indexed slug on every slugged model; `Location.city` unique.
- `UniqueConstraint(section, record)` on every section-item model. **No** constraint on any
  `order` column - see §2.3.
- `UniqueConstraint(project, media, kind)` on `ProjectGalleryItem`: the same drawing may appear
  once in the gallery and once among the drawings, but not twice in either.
- Composite index `(status, published_at)` on all publishable models, plus
  `(category, status)` on Project and `(is_featured, status)` on Project and Service.
- Index `(section, order)` on every item model - the page selector reads them in that order.
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

The Next.js UI is at `archethos-nextjs/archethos`. The website routes and this repo's page
models are two halves of one statement and are changed together; the admin under `(admin)/`
consumes the API.

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

Each website route above has a page model of the same name, and the `[slug]` routes are
master data rather than pages. No `/vastu` route exists — Vastu is a `Service`, and the home
page teaser is `VastuSection`.

The frontend renders explicitly:

```jsx
export default function HomePage() {
  return (
    <>
      <HomeHero /> <StudioIntroduction /> <StatsBand /> …
    </>
  );
}
```

No `sections.map()`, no registry lookup. The page component, the page serializer and the page
model list the same sections in the same order — three files that have to agree, and will fail
visibly if they stop agreeing.

---

## 19. History

| Phase | Goal | Status |
|---|---|---|
| 1 | Architecture | **done** |
| 2 | Foundation: `apps/`, settings, Postgres, envelope + pagination + exceptions, core abstracts | **done** |
| 3 | Cookie JWT auth on `auth.User` | **done** |
| 4 | Users, groups, permissions, escalation guards | **done** |
| 5 | Media Library + `MediaReferenceField` | **done** |
| 6 | Master content: FAQ, Counter, Project, Service, BlogPost, BlogCategory | **done** |
| 7-9 | Generic section + page composition layer | **replaced** - see below |
| 10 | Public aggregate page API + `assertNumQueries` | **done**, rebuilt |
| 11 | PostgreSQL search + `Enquiry` + `Company` | **done** |
| 12 | Audit, OpenAPI polish, deployment | in progress |
| 13 | **Refactor: explicit page models** | **done** |

### Phase 13 - what changed and why

Phases 7 to 9 built a generic CMS: `Page -> PageSection -> Section`, MTI, a section registry,
per-type CRUD routes and a dynamic renderer on the frontend. It worked, and it was the wrong
shape for this site. Reading the schema told you nothing about the website, and the frontend
needed a registry to turn rows back into components.

Replaced with a model per page, sections as plain tables, and master data referenced through
item models. Deleted: the `sections` app, `Page`, `PageSection`, `SectionType`,
`SECTION_REGISTRY`, the section CRUD and reorder endpoints, and the frontend's section
registry and renderer.

The existing data was development scaffolding - three page sections, one hero, one project -
so the schema was rebuilt rather than migrated. The real site content still lives in the
frontend's `src/data/*.js` files.

---

## 20. Open items

| Item | Status |
|---|---|
| Production cookie scope (`AUTH_COOKIE_DOMAIN=.archethos.com`) | set; CSRF and session cookies now track it |
| Rate limiting | done. Login (per IP and per account), refresh, password change, enquiries. Rates from env; needs `CACHE_URL` and `RATELIMIT_TRUSTED_IP_HEADER` set in production |
| Seeding | done — `manage.py seed_site`. **Not** in deploy.sh: it rebuilds page sections wholesale, so re-running would discard an editor's work. Launch-time and staging only |
| Admin screens for Gallery and Locations | API done, `/admin/content/gallery` and `/admin/content/locations` not built |
| Cloudflare caching vs `media/replace/` | replace keeps the filename, so a cached image survives it - needs a purge or a checksum query param |
