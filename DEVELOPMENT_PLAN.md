# Archethos Headless CMS — Architecture & Development Plan

> Backend: Django + Django REST Framework + PostgreSQL
> Frontend: Next.js (separate app — **not** built here)
> Auth: JWT in HttpOnly cookies, refresh rotation + blacklist
>
> Status: **approved Phase 1 output**. This is the single source of truth for the build.
> Update this document when a decision changes; update `TASKS.md` as work completes.

---

## 1. Stack & current state

| Item | Value |
|---|---|
| Django | 6.1 — verified working with simplejwt 5.5.1 + `token_blacklist` (Phase 2) |
| DRF | 3.18 |
| DB | PostgreSQL 17.11 via Docker on host port **5433**; `psycopg` 3.3.4 |
| Auth | `djangorestframework-simplejwt` 5.5.1 + `token_blacklist` |
| Already installed | `django-cors-headers`, `django-filter`, `django-environ`, `drf-spectacular`, `django-ratelimit`, `django-extensions`, `Pillow` |
| To install | (prod) `gunicorn`, `whitenoise`; (test) `pytest-django`, `factory-boy` |
| Existing code | Phase 2 complete: `apps/` structure, split settings, API infrastructure. **No migrations run yet** — the custom User must land in the first one. |

No migrations exist, so the custom user model and the `apps/` restructure are both still free.

---

## 2. Locked architectural decisions

Reviewed and approved. Do not re-litigate without updating this section.

### 2.1 Media is a ForeignKey, serialized as a relative path

Content models store `ForeignKey(MediaAsset, on_delete=PROTECT)`. The API reads and writes the
**relative path**. No CDN domain is ever persisted.

```
DB        Project.featured_image_id = 42
API out   "featured_image": "/media/uploads/abc123-house.webp"
API in    accepts 42 (id) OR "/media/uploads/abc123-house.webp"
Frontend  CDN_BASE + path
```

A single `MediaReferenceField` (`apps/api/fields.py`) implements both directions and validates
existence. Every media field on every model uses it. Where the frontend needs `alt_text` or
dimensions, the serializer also emits `<field>_detail`:

```json
"featured_image": "/media/uploads/abc123-house.webp",
"featured_image_detail": { "id": 42, "alt_text": "Villa exterior", "width": 2400, "height": 1600 }
```

**Why:** referential integrity, delete protection, and a working "where is this image used?"
query — none of which a bare path string can provide. The CDN-independence requirement is about
the payload, not the storage layer, and is fully satisfied.

### 2.2 Page → section is a nullable ForeignKey

`ForeignKey(null=True, blank=True, on_delete=SET_NULL)` for **every** page→section slot,
including heroes. A page has at most one of each section type (the field is singular), a section
instance may be shared across pages, and deleting a section blanks the slot rather than
destroying the page. `related_name` answers "which pages use this section?" — the admin UI must
show that before allowing a delete.

### 2.3 `order` is display-order only and appears in no constraint

```python
order = models.PositiveIntegerField(default=0)

class Meta:
    ordering = ["order", "id"]
```

Duplicate `order` values are tolerated; `id` breaks ties. The **only** constraint on an item
model is `UniqueConstraint(section, <content>)`, preventing the same FAQ/Project/Service being
added twice to one section.

Consequence: bulk reorder is a plain `transaction.atomic()` + `bulk_update` with no
deferred-constraint gymnastics.

### 2.4 Audit logging records who changed what — nothing else

Dropped: `ip_address`, `user_agent`, `request_method`, `request_path`, the contextvar
middleware, and the model-level `from_db` snapshot machinery.

Written by **one** `AuditLogMixin` on `AdminModelViewSet` (`perform_create` / `perform_update`
snapshots the instance before saving / `perform_destroy`), plus two explicit calls in the login
and logout views. No audit code in any individual view.

**Accepted trade-off:** Django Admin edits, shell edits, and data migrations go unlogged.
Acceptable — the REST API is the CMS.

A field denylist (`password`, `token`, `secret`, `key`, `session`) strips sensitive values from
`changes` before writing.

### 2.5 Response envelope is infrastructure, not per-view code

- `EnvelopeJSONRenderer` — wraps into `{success, message, data}`, hoists pagination to a
  top-level `pagination` key, passes `204` and the schema/docs endpoints through untouched.
- `envelope_exception_handler` — `{success: false, message, errors, code}`.
- `EnvelopePageNumberPagination` — emits `{page, page_size, total_items, total_pages, has_next,
  has_previous}`.
- drf-spectacular postprocessing hooks so the OpenAPI schema documents the wrapped shape.

### 2.6 One publish flag, not three

`PublishableModel` abstract, applied to **Project, Service, BlogPost, FAQ**:

```python
status       = DRAFT | PUBLISHED | ARCHIVED   # indexed
published_at = DateTimeField(null=True)       # set on first transition to PUBLISHED

def live(self):   # PublishableQuerySet
    return self.filter(status=PUBLISHED).filter(
        Q(published_at__isnull=True) | Q(published_at__lte=timezone.now())
    )
```

**Removed:** `is_published` (Project), `is_active` + `is_published` (Service), `is_active`
(FAQ), `is_active` (sections — a section not attached to a page simply does not render).
**Retained:** `Project.is_featured`, which is curation, not publishing.

### 2.8 Class-based views only — never ViewSets

Every endpoint is a DRF generic class-based view (`ListCreateAPIView`,
`RetrieveUpdateAPIView`, `APIView`) wired with explicit `path()` entries.
`ViewSet`, `ModelViewSet`, `@action` and DRF routers are not used anywhere.

Consequences, all of them deliberate:

* Every URL is written out in a `urls.py`, so the route list is readable without
  mentally expanding a router.
* One class per operation-group rather than one class per resource. A resource is
  typically two classes (list+create, detail) plus one small class per custom
  operation.
* Custom operations that would have been `@action` become their own view class -
  e.g. `BlogPublishAPIView`, `UserDeactivateAPIView`, `SectionItemReorderAPIView`.
* `get_serializer_class()` dispatches on `request.method` instead of on
  `self.action`.
* Generic views still provide `perform_create` / `perform_update` /
  `perform_destroy`, so the audit hooks in §2.4 attach unchanged.

### 2.7a Django's built-in User (no custom user model)

CMS accounts exist only so staff can edit website content — there is no public
registration, no customer accounts, no profile data beyond a name. Django's
`auth.User` already carries everything `/auth/me/` needs, so no custom user model
is introduced.

Two consequences handled explicitly:

* `auth.User` keys on `username`, but login is by email. An `EmailBackend`
  resolves email -> user, and `username` is auto-filled from the email on creation.
* `auth.User.email` is **not unique**, which would make email login ambiguous. A
  case-insensitive partial unique index is added in
  `accounts/migrations/0001_user_email_unique.py`:

  ```sql
  CREATE UNIQUE INDEX auth_user_email_ci_unique
  ON auth_user (LOWER(email)) WHERE email <> '';
  ```

  Enforced in the database, so it holds for the API, Django Admin, the shell and
  `createsuperuser` alike. Blank emails are excluded so they do not collide.

Trade-off accepted: migrating to a custom user model later is painful. Given the
narrow scope (staff editors only), that is unlikely to be needed.

### 2.7b Logout cannot revoke an already-issued access token

Logout blacklists the refresh token and deletes both cookies. The access token is
stateless and stays valid until it expires. Revoking it would require a database
lookup on every request, which defeats the point of stateless JWT. The mitigation
is the short 15-minute lifetime plus cookie deletion — the browser no longer holds
the token to send.

### 2.7 No refresh-token grace window

Expired / invalid / blacklisted / missing refresh token → `401`, both cookies cleared. The
frontend re-authenticates. Concurrent-refresh races are not handled.

---

## 3. Django app structure

```
archethos-backend/
├── .env                     (gitignored)   .env.example
├── docker-compose.yml       PostgreSQL 17 (the only containerised service)
├── requirements/            base.txt  dev.txt  prod.txt
├── DEVELOPMENT_PLAN.md      TASKS.md
├── manage.py
└── archethosbackend/
    ├── settings/            base.py  development.py  production.py  test.py
    ├── urls.py  wsgi.py  asgi.py
    └── apps/
        ├── core/            abstract models, mixins, validators, slug utils
        ├── accounts/        User, UserManager, cookie JWT, auth + user/group/perm APIs
        ├── audit/           AuditLog, AuditLogMixin, read-only API
        ├── media_library/   MediaAsset, upload pipeline, YouTube parsing, validation
        ├── projects/        Project, ProjectGalleryItem
        ├── services/        Service
        ├── blogs/           BlogPost, BlogCategory
        ├── faqs/            FAQ
        ├── sections/        all strongly typed sections + item models
        ├── pages/           HomePage, AboutPage, ContactPage, listing pages, Company
        ├── enquiries/       Enquiry
        └── api/             renderer, exception handler, pagination, base viewsets,
                             SectionItemViewSet, permission classes, MediaReferenceField,
                             v1 routers
```

Each `AppConfig` sets `name = "archethosbackend.apps.projects"` and `label = "projects"` so
permission codenames stay clean (`projects.add_project`).

The existing root-level `medialibrary` app folds into `apps/media_library/` — safe, it has no
models and no migrations.

`sections` is deliberately **one** app: section models are cross-cutting and mutually
referential, and splitting them creates import cycles for no isolation benefit. Internally split
into `models/hero.py`, `models/collections.py`, `models/cta.py`, re-exported from
`models/__init__.py`.

---

## 4. `core` — abstract models (no tables)

| Abstract | Fields / purpose |
|---|---|
| `TimeStampedModel` | `created_at`, `updated_at` (timezone-aware) |
| `SEOModel` | `meta_title`, `meta_description`, `meta_keywords`, `og_title`, `og_description`, `og_image` (FK `"media_library.MediaAsset"`, lazy string ref), `canonical_url`, `robots_index`, `robots_follow` |
| `SluggedModel` | `title`, `slug` (unique, indexed, auto-generated with collision suffix) |
| `PublishableModel` | `status`, `published_at`, `PublishableQuerySet.live()` |
| `OrderedItemModel` | `order`, `Meta.ordering = ["order", "id"]` |
| `SingletonModel` | pinned pk, `CheckConstraint`, `load()` classmethod |

`SEOModel.og_image` uses a lazy string reference, so `core` carries no import-time dependency on
`media_library`.

---

## 5. Model catalogue

### 5.1 accounts

Uses Django's built-in **`auth.User`** unchanged (see §2.7a) — no model of its own.
The app contributes behaviour, not tables:

| Module | Purpose |
|---|---|
| `backends.EmailBackend` | resolves email -> user for login; constant-time on unknown emails |
| `authentication.CookieJWTAuthentication` | reads the access token from the cookie, enforces CSRF on unsafe methods, accepts a Bearer fallback |
| `cookies.py` | `set_auth_cookies` / `clear_auth_cookies`, env-aware |
| `schema.py` | registers the `cookieAuth` OpenAPI security scheme |
| `migrations/0001` | the case-insensitive unique email index |

### 5.2 media_library

**`MediaAsset`** — `media_type` (IMAGE / VIDEO / DOCUMENT), `source_type` (UPLOAD / YOUTUBE),
`file`, `external_url`, `external_id` (YouTube video id), `thumbnail_url`, `file_name` (original,
display only), `file_size`, `mime_type`, `width`, `height`, `duration`, `title`, `alt_text`,
`checksum` (sha256, indexed — duplicate detection), `uploaded_by`, timestamps.

- `upload_to` callable produces `uploads/<uuid4>-<slugified-name>.<ext>` — the user filename
  never determines uniqueness.
- Property `relative_path` → `/media/uploads/...` for uploads, `external_url` for YouTube.
- `CheckConstraint`: `file` required when `source_type=UPLOAD`; `external_url` required when
  `source_type=YOUTUBE`.

### 5.3 Master content

| Model | Fields |
|---|---|
| **`Project`** | Slugged + Publishable + SEO + TimeStamped, plus `short_description`, `description`, `location`, `project_year`, `project_status` (CONCEPT / ONGOING / COMPLETED), `featured_image`→MediaAsset, `is_featured`, `services` M2M→Service, `search_vector` |
| **`ProjectGalleryItem`** | `project` (CASCADE), `media` (PROTECT), `caption`, `order` |
| **`Service`** | Slugged + Publishable + SEO + TimeStamped, plus `short_description`, `description`, `featured_image`, `icon`→MediaAsset, `order` |
| **`BlogPost`** | Slugged + Publishable + SEO + TimeStamped, plus `excerpt`, `content`, `featured_image`, `author`→User (SET_NULL), `category`→BlogCategory (SET_NULL), `reading_time`, `search_vector` |
| **`BlogCategory`** | `name`, `slug`, `description` |
| **`FAQ`** | Publishable + TimeStamped, plus `question`, `answer`, `category` (GENERAL / VASTU / PROCESS / PRICING) |

### 5.4 sections

All inherit `TimeStampedModel` + `SectionBase`, which provides **`internal_label`** — a
required, admin-facing name for the section instance.

This field exists because section models are master tables holding many rows. Opening the
`HomeHeroSection` table shows several rows with no way to tell them apart from their content
alone. `internal_label` says which page or purpose each row was created for:

```
HeroSection
  id  internal_label              title
  1   "Home - main hero"          "Architecture Beyond Boundaries"
  2   "About - studio hero"       "Who We Are"
  3   "Home - seasonal campaign"  "Monsoon Collection"
```

It is never rendered on the public site and never appears in public serializers. It is purely
for the CMS section picker and admin tables, where "which hero is this?" is otherwise
guesswork.

| Section | Fields | Item model |
|---|---|---|
| `HomeHeroSection` | `title`, `subtitle`, `background_media`, `cta_label`, `cta_url`, `overlay_opacity` | — |
| `AboutHeroSection` | `title`, `description`, `image` | — |
| `SimpleHeroSection` | `title`, `subtitle`, `image` (services / contact / vastu pages) | — |
| `StudioIntroSection` | `heading`, `body`, `image` | `StudioStatItem` (`label`, `value`, `order`) |
| `FeaturedProjectsSection` | `heading`, `subheading` | `FeaturedProjectItem` (`project`, `order`, `display_variant`) |
| `ServicesSection` | `heading`, `subheading` | `ServiceSectionItem` (`service`, `order`, `label_override`) |
| `GallerySection` | `heading`, `subheading`, `layout_variant` (GRID / MASONRY / SLIDER) | `GallerySectionItem` (`media`, `caption`, `order`) |
| `FAQSection` | `heading`, `subheading` | `FAQSectionItem` (`faq`, `order`) |
| `CTASection` | `heading`, `description`, `background_media`, `button_label`, `button_url` | — |
| `ContactInfoSection` | `address`, `phone`, `email`, `map_embed_url`, `office_hours` | — |

Every item model: `section` CASCADE, content FK **PROTECT**, `UniqueConstraint(section,
content)`, `order` unconstrained.

### 5.5 pages

`HomePage`, `AboutPage`, `ContactPage`, `VastuPage`, `ProjectsListingPage`,
`ServicesListingPage`, `BlogListingPage` — each `SingletonModel` + `SEOModel` +
`TimeStampedModel` with nullable FKs to its section slots.

**`Company`** (singleton master, TimeStamped):

```
name                CharField
address             TextField
logo                → MediaAsset (SET_NULL)

social_urls         JSONB   {"instagram": "...", "linkedin": "...", "youtube": "..."}
contacts            JSONB   {"emails": [...], "phones": [...], "whatsapp": "..."}
header_links        JSONB   [{"label": "Projects", "url": "/projects"}]
footer_links        JSONB   [{"heading": "Company", "links": [{"label", "url"}]}]

head_inject         TextField   → rendered inside <head>
body_inject         TextField   → rendered before </body>

meta_title          CharField
meta_description    TextField
meta_keywords       CharField
```

- JSON fields use `JSONField` (JSONB), not `TextField` — same JSON over the wire, but validated
  on write and queryable. Each has a light schema validator.
- **`head_inject` / `body_inject` are a stored-XSS vector**: whoever can write them executes
  arbitrary JS on every page of the live site. The write serializer restricts **these two fields
  only** to superusers; the rest of `Company` needs just `pages.change_company`.

### 5.6 enquiries

**`Enquiry`** (TimeStamped) — one table for every form on the site.

```
form_type    CONTACT | CONSULTATION | CAREER | GENERAL   (indexed)
name · email · phone · subject · message
extra        JSONB, default {}     ← form-specific fields; a new form needs no migration
source_page  CharField             ← "/vastu", "/contact"
is_read      BooleanField          (indexed)
```

### 5.7 audit

**`AuditLog`**

```
user          → User (SET_NULL)
action        CREATE | UPDATE | DELETE | LOGIN | LOGOUT
content_type  → ContentType (null for LOGIN / LOGOUT)
object_id     PositiveBigIntegerField (null)
object_repr   CharField
changes       JSONB   {"title": {"old": "...", "new": "..."}}
created_at
```

Indexes: `(content_type, object_id)`, `(user, -created_at)`, `(action, -created_at)`.

**~33 tables total.**

---

## 6. ERD

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              MEDIA LIBRARY                               │
│  MediaAsset — media_type · source_type · file/external_url · alt_text     │
└───┬──────────────────────────────────────────────────────────────────────┘
    │ PROTECT (referenced everywhere; never orphaned)
    ├──────────────┬──────────────┬──────────────┬─────────────┬──────────┐
    ▼              ▼              ▼              ▼             ▼          ▼
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌─────────┐ ┌────────┐
│ Project │  │ Service  │  │ BlogPost │  │  FAQ       │  │ Company │ │SEOModel│
│ featured│  │ featured │  │ featured │  │ (no media) │  │ .logo   │ │.og_img │
│ _image  │  │ _image   │  │ _image   │  │            │  │         │ │(abstr.)│
└────┬────┘  │ .icon    │  └────┬─────┘  └─────┬──────┘  └─────────┘ └────────┘
     │       └────┬─────┘       │              │
     │  Project.services M2M ───┘              │
     │            │  BlogPost.author   → User  │
     │            │  BlogPost.category → BlogCategory
     │            │             │              │
     │  ┌─────────┴─────────────┴──────────────┴───────────────────┐
     │  │   MASTER CONTENT — status: DRAFT | PUBLISHED | ARCHIVED  │
     │  └─────────┬─────────────┬──────────────┬───────────────────┘
     ▼            ▼             ▼              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                  SECTION ITEMS (ordered, content FK = PROTECT)           │
│  FeaturedProjectItem   ServiceSectionItem   GallerySectionItem           │
│  FAQSectionItem        StudioStatItem                                    │
│  ProjectGalleryItem  (belongs to Project, not to a section)              │
│                                                                          │
│  each: UniqueConstraint(section, content)    order = display only,       │
│                                              in NO constraint            │
└───────────────────────────┬──────────────────────────────────────────────┘
                            │ section FK = CASCADE
                            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       SECTIONS (strongly typed)                          │
│  HomeHeroSection   AboutHeroSection   SimpleHeroSection                  │
│  StudioIntroSection   FeaturedProjectsSection   ServicesSection          │
│  GallerySection   FAQSection   CTASection   ContactInfoSection           │
└───────────────────────────┬──────────────────────────────────────────────┘
                            │ FK null=True, on_delete=SET_NULL
                            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                  PAGES (singleton + SEO + TimeStamped)                   │
│                                                                          │
│  HomePage ── hero → HomeHeroSection                                      │
│           ├─ intro → StudioIntroSection                                  │
│           ├─ featured_projects → FeaturedProjectsSection                 │
│           ├─ services → ServicesSection                                  │
│           ├─ gallery → GallerySection      ┐                             │
│           ├─ faq → FAQSection              │ shareable across pages      │
│           └─ cta → CTASection              │                             │
│  AboutPage ─ hero → AboutHeroSection       │                             │
│           ├─ intro → StudioIntroSection    │                             │
│           ├─ gallery → GallerySection  ◄───┤                             │
│           └─ cta → CTASection          ◄───┘                             │
│  ContactPage ─ hero → SimpleHeroSection · contact_info → ContactInfo     │
│  VastuPage · ProjectsListingPage · ServicesListingPage · BlogListingPage │
│  Company (singleton, page-independent)                                   │
└───────────────────────────┬──────────────────────────────────────────────┘
                            ▼
                   AGGREGATE PUBLIC API  →  NEXT.JS

┌──────────────────────────────────────────────────────────────────────────┐
│  CROSS-CUTTING                                                           │
│  User ──< Group >── Permission     (Django native — no custom RBAC)      │
│  AuditLog ── user · content_type + object_id · changes JSONB             │
│  Enquiry  ── write-only from public, read + mark-read in admin           │
└──────────────────────────────────────────────────────────────────────────┘
```

### Deletion rules, stated once

| Relationship | `on_delete` | Effect |
|---|---|---|
| content → MediaAsset | **PROTECT** | cannot delete an in-use image; API returns 409 naming the referencing objects |
| item → section | **CASCADE** | deleting a section removes its item rows only, never master content |
| item → master content | **PROTECT** | cannot delete a FAQ placed in a section; error names the sections |
| page → section | **SET_NULL** | deleting a section blanks the slot; the page survives |
| BlogPost → author | **SET_NULL** | deactivating a user never destroys content |
| AuditLog → user | **SET_NULL** | audit history outlives the account |

---

## 7. Authentication architecture

```
┌────────────┐   POST /api/v1/auth/login/  {email, password}
│  Next.js   │   fetch(..., { credentials: "include" })
└─────┬──────┘
      ▼
  authenticate(email, password) → is_active check
      ▼
  RefreshToken.for_user(user) → access (15 min) + refresh (7 days)
      ▼
  Set-Cookie: access_token   HttpOnly Secure SameSite  Path=/api/
  Set-Cookie: refresh_token  HttpOnly Secure SameSite  Path=/api/v1/auth/
  Set-Cookie: csrftoken      (readable — double-submit only)
      ▼
  200 {success, data: {user, groups, permissions}}   ← no token values in the body
  AuditLog(LOGIN)

                 ┌────────────────────────────────────────────┐
   every request │ CookieJWTAuthentication                    │
   ──────────────▶ 1. read access_token cookie                │
                 │ 2. Bearer header fallback (non-browser)    │
                 │ 3. validate signature + expiry             │
                 │ 4. enforce_csrf() on unsafe methods        │
                 │ 5. reject token_type != "access"           │ ← refresh can never authenticate
                 └────────────────────────────────────────────┘

  401 → frontend calls POST /api/v1/auth/refresh/
      ▼
  refresh cookie → validate → blacklist old → issue new pair → reset both cookies → 200
      │
      └─ missing / expired / invalid / blacklisted → 401 + BOTH cookies cleared
         (no grace window — decision 2.7)

  POST /api/v1/auth/logout/ → blacklist refresh → delete both cookies
                            → AuditLog(LOGOUT) → 204
```

`refresh_token` is scoped to `Path=/api/v1/auth/` so it is never transmitted on ordinary API
calls. `token_type` is asserted explicitly so a refresh token can never satisfy a protected
endpoint.

### Cookie / CORS / CSRF configuration

```python
# env-driven
AUTH_COOKIE_SECURE   = env.bool("AUTH_COOKIE_SECURE", False)      # True in production
AUTH_COOKIE_SAMESITE = env("AUTH_COOKIE_SAMESITE", default="Lax")
AUTH_COOKIE_DOMAIN   = env("AUTH_COOKIE_DOMAIN", default=None)
ACCESS_TOKEN_LIFETIME_MINUTES = env.int("ACCESS_TOKEN_LIFETIME_MINUTES", 15)
REFRESH_TOKEN_LIFETIME_DAYS   = env.int("REFRESH_TOKEN_LIFETIME_DAYS", 7)

CORS_ALLOWED_ORIGINS   = env.list("CORS_ALLOWED_ORIGINS")   # never "*" with credentials
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS     = [*default_headers, "x-csrftoken"]
CSRF_TRUSTED_ORIGINS   = env.list("CSRF_TRUSTED_ORIGINS")
CSRF_COOKIE_HTTPONLY   = False          # the frontend must read it to echo it back

SIMPLE_JWT = {
    "ROTATE_REFRESH_TOKENS":    True,
    "BLACKLIST_AFTER_ROTATION": True,
    ...
}
```

**Default topology: `SameSite=Lax`.** Works in development because `localhost:3000` →
`localhost:8000` is same-site (ports are irrelevant to SameSite). In production, deploy the admin
and the API on the same registrable domain (`admin.archethos.com` / `api.archethos.com`) to keep
`Lax`.

**Only if truly cross-site:** switch to `SameSite=None; Secure` and rely on the double-submit
CSRF token. CSRF is never disabled.

---

## 8. Permission architecture

```
Request
  │
  ├─ /api/v1/public/*  → AllowAny · read-only · .live() querysets only
  │
  ├─ /api/v1/auth/*    → AllowAny (login, refresh) · IsAuthenticated (me, logout)
  │
  └─ /api/v1/admin/*   → IsAuthenticated  AND  StrictDjangoModelPermissions
                             GET       → app_label.view_<model>
                             POST      → app_label.add_<model>
                             PUT/PATCH → app_label.change_<model>
                             DELETE    → app_label.delete_<model>
                          superuser bypasses (Django convention)
```

Three deliberate choices:

1. **`StrictDjangoModelPermissions`** — DRF's stock `DjangoModelPermissions` does *not* require
   `view_*` for GET. We subclass to require it, otherwise "can only view Projects" is
   unenforceable in the negative direction.
2. **Section-item permissions derive from the parent section.** Editing a `FAQSectionItem` checks
   `sections.change_faqsection`, not `sections.change_faqsectionitem`. "Can this person edit the
   FAQ section" is the real mental model, and 10 extra permission rows per section type would
   make the group-assignment UI unusable.
3. **Privilege-escalation guards** (Django provides none of these):
   - a non-superuser may only grant permissions they themselves hold
   - a non-superuser may never set `is_superuser`
   - nobody may deactivate themselves
   - the last active superuser may not be deactivated
   - `Company.head_inject` / `body_inject` are superuser-only

`/auth/me/` resolves permissions via `user.get_all_permissions()` (direct ∪ group-derived).
**Permissions are never stored in the JWT payload** — a revocation takes effect on the next
request rather than at token expiry.

### Bootstrap groups (data migration)

| Group | Scope |
|---|---|
| `Administrators` | everything except superuser-only fields |
| `Content Managers` | all content + sections + pages; no users, no audit |
| `Editors` | view + change content; no delete, no publish |
| `Media Managers` | media library only |

---

## 9. API surface

### `/api/v1/auth/`

```
POST   login/          POST   refresh/       POST   logout/       GET  me/
POST   password/change/
```

### `/api/v1/admin/` — all list endpoints paginated, searchable, filterable, orderable

```
users/   users/{id}/   users/{id}/set-password/   users/{id}/deactivate/
groups/  groups/{id}/  permissions/                (grouped by app/model)
audit-logs/  audit-logs/{id}/                      (read-only)

media/   media/{id}/   media/upload/   media/youtube/   media/{id}/usage/

projects/  projects/{id}/
           projects/{id}/gallery/   projects/{id}/gallery/{item_id}/
           projects/{id}/gallery/reorder/
services/  services/{id}/
blogs/     blogs/{id}/   blogs/{id}/publish/   blogs/{id}/unpublish/
blog-categories/   faqs/
enquiries/  enquiries/{id}/                     (list, retrieve, PATCH is_read, DELETE)

home-hero-sections/       about-hero-sections/       simple-hero-sections/
studio-intro-sections/    featured-project-sections/ services-sections/
gallery-sections/         faq-sections/              cta-sections/
contact-info-sections/
    └─ each: GET list · POST · GET/PATCH/DELETE {id}

# ordered relationships — ONE reusable set of base classes, subclassed per section
{section-type}/{id}/items/               GET list · POST add
{section-type}/{id}/items/{item_id}/     PATCH · DELETE
{section-type}/{id}/items/reorder/       PATCH  (atomic)

pages/home/  pages/about/  pages/contact/  pages/vastu/
pages/projects/  pages/services/  pages/blog/       (GET · PATCH — singletons)
company/                                            (GET · PATCH — singleton)
```

### `/api/v1/public/` — read-only, `.live()` only

```
projects/   projects/{slug}/     ?featured=true&service=<slug>&year=&status=
services/   services/{slug}/
blogs/      blogs/{slug}/        ?category=&search=
faqs/                            ?category=
pages/{slug}/                    home|about|contact|vastu|projects|services|blog
company/
search/?q=                       projects + services + blogs
enquiries/                       POST only — rate-limited, honeypot
```

### Meta

```
/api/v1/schema/   /api/v1/schema/docs/   (drf-spectacular)   /health/
```

### Standard admin list query parameters

```
?page=1&page_size=20&search=villa&ordering=-created_at
+ resource-specific filters: ?status=PUBLISHED  ?media_type=IMAGE  ?is_active=true
```

---

## 10. Response format

**Success**

```json
{ "success": true, "message": "Projects retrieved successfully", "data": [] }
```

**Paginated list**

```json
{
  "success": true,
  "message": "Projects retrieved successfully",
  "pagination": { "page": 1, "page_size": 20, "total_items": 156,
                  "total_pages": 8, "has_next": true, "has_previous": false },
  "data": []
}
```

**Error**

```json
{ "success": false, "message": "Validation failed",
  "errors": { "slug": ["This slug is already in use."] }, "code": "validation_error" }
```

Status codes: `200` · `201` · `204` (empty body, not wrapped) · `400` · `401` · `403` · `404` ·
`409` (PROTECT violations, slug conflicts) · `429` (rate limit).

---

## 11. Serializer strategy

Four variants per admin resource:

| Serializer | Purpose |
|---|---|
| `XListSerializer` | flat, data-table columns only, **zero nested objects** |
| `XDetailSerializer` | full record + nested items + expanded media detail |
| `XWriteSerializer` | create/update; media by id-or-path; owns validation |
| `PublicXSerializer` | published fields only |

**Public serializers are independent classes, never subclasses of the admin ones.** Inheritance
is how admin fields leak into public payloads six months later.

Layering (thin views):

```
Models       fields, constraints, PublishableQuerySet, computed properties
Selectors    for_public(), for_admin_list(), .live()   ← ALL prefetch logic lives here
Serializers  shape + validation
Services     only where genuinely multi-step: media upload pipeline, publish transitions,
             atomic reorder, user creation with permissions, audit writes
Views        thin class-based views — ~5-15 lines, get_serializer_class() dispatch
Permissions  declarative classes
```

Shared infrastructure in `apps/api/generics.py`:

- `AdminListCreateAPIView` — list + create: envelope, pagination, filter/search/order, audit,
  serializer dispatch by method.
- `AdminRetrieveUpdateDestroyAPIView` — detail, update, delete.
- `SectionItemListCreateAPIView` / `SectionItemDetailAPIView` / `SectionItemReorderAPIView` —
  configured per section type, covering list / add / update / remove / **reorder** for all
  ordered relationships. Written once, subclassed per section.
- `MediaReferenceField` — the single place decision 2.1 is enforced.

Reorder validates: all ids belong to this section · no duplicate ids · no unknown ids. Then
`transaction.atomic()` + `bulk_update(["order"])`.

---

## 12. Aggregate page API

`GET /api/v1/public/pages/{slug}/` resolves through a **page registry** — the one place slugs map
to typed models:

```python
PAGE_REGISTRY = {
    "home":    PageSpec(HomePage,    HomePageSerializer),
    "about":   PageSpec(AboutPage,   AboutPageSerializer),
    "contact": PageSpec(ContactPage, ContactPageSerializer),
    "vastu":   PageSpec(VastuPage,   VastuPageSerializer),
    ...
}
```

Unknown slug → 404. Each page has its **own strongly typed serializer** with explicitly named
keys (`hero`, `featured_projects`, `faq`, `cta`) — never a generic loop. Each page model owns a
`for_public()` classmethod carrying its full `select_related` / `prefetch_related` chain, so the
view stays three lines.

**Query budget for `pages/home/` — 8 queries, flat regardless of content volume:**

```
1  HomePage + all 6 section FKs + og_image        select_related (single JOIN)
2  FeaturedProjectItem → Project → featured_image prefetch, ordered
3  Project.services (M2M on featured projects)    prefetch
4  ServiceSectionItem → Service → featured_image  prefetch
5  FAQSectionItem → FAQ                           prefetch
6  GallerySectionItem → MediaAsset                prefetch
7  StudioStatItem                                 prefetch
8  Company                                        cached singleton
```

Guarded by `assertNumQueries` in tests so a future serializer change cannot silently reintroduce
N+1.

Response carries `ETag` + `Cache-Control: public, max-age=60, stale-while-revalidate=300` derived
from the max `updated_at` in the graph — Next.js ISR then costs almost nothing.

Aggregate page endpoints are **never paginated**.

---

## 13. Database & search

- Unique + indexed slug on every slugged model.
- Composite index `(status, published_at)` on Project, Service, BlogPost, FAQ.
- Index `(section_id, order)` on every item table.
- `search_vector` (`SearchVectorField` + GIN index) on Project and BlogPost, populated on save
  with weighted fields — `title` = A, `excerpt`/`short_description` = B, `content`/`description`
  = C.
- Postgres extensions via migration: `pg_trgm`, `unaccent`.
- `CheckConstraint`s: `published_at` consistency; `MediaAsset` source_type/file/external_url
  consistency.
- **Search stays inside PostgreSQL.** No Elasticsearch.

---

## 14. Security checklist

- `SECRET_KEY`, DB credentials, allowed origins — all from `.env`, never committed
- `DEBUG=False` + `ALLOWED_HOSTS` in production
- HttpOnly + Secure + SameSite cookies; `refresh_token` path-scoped
- CSRF enforced on unsafe methods by `CookieJWTAuthentication` (never disabled)
- `CORS_ALLOW_CREDENTIALS = True` with an explicit origin list (never `*`)
- Refresh rotation + blacklist enabled
- Upload validation: extension allowlist, MIME sniffing, max size, image dimension caps, Pillow
  verification (an uploaded `.jpg` that is not an image is rejected)
- YouTube URL format allowlist + video-id extraction
- Privilege-escalation guards on user/group APIs
- `head_inject` / `body_inject` restricted to superusers
- Public enquiry endpoint rate-limited + honeypot
- Audit denylist strips passwords and tokens from `changes`
- Security headers: HSTS, `SECURE_SSL_REDIRECT`, `X_FRAME_OPTIONS`, referrer policy

---

## 15. Environment variables

```
DEBUG                          SECRET_KEY                 ALLOWED_HOSTS
DB_NAME  DB_USER  DB_PASSWORD  DB_HOST  DB_PORT      # shared by Django and docker-compose
CORS_ALLOWED_ORIGINS           CSRF_TRUSTED_ORIGINS
AUTH_COOKIE_SECURE             AUTH_COOKIE_SAMESITE       AUTH_COOKIE_DOMAIN
ACCESS_TOKEN_LIFETIME_MINUTES  REFRESH_TOKEN_LIFETIME_DAYS
MEDIA_URL  MEDIA_ROOT          MAX_UPLOAD_SIZE_MB
```

---

## 16. Phased development plan

Task-level tracking lives in **`TASKS.md`**. This section states each phase's intent and
dependencies.

| Phase | Goal | Depends on |
|---|---|---|
| **1** | DONE - Architecture (this document) | — |
| **2** | DONE - Foundation: restructure to `apps/`, split settings, `.env`, PostgreSQL + psycopg, DRF / spectacular / CORS config, `core` abstracts, envelope + pagination + exception infrastructure, health check | — |
| **3** | DONE - Authentication: built-in `auth.User` + email backend + unique email index, `CookieJWTAuthentication` + CSRF enforcement, login / refresh / logout / me / password-change / csrf, rotation + blacklist | 2 |
| **4** | Users, groups, permissions: management APIs, `StrictDjangoModelPermissions`, escalation guards, bootstrap groups migration | 3 |
| **5** | Audit: `AuditLog`, `AuditLogMixin`, denylist, read-only filtered API. **Deliberately before content** so every later model is audited from birth rather than retrofitted | 3 |
| **6** | Media Library: upload pipeline, validation, YouTube parsing, `MediaReferenceField`, usage endpoint, list / search / filter | 2, 5 |
| **7** | Master content: Project, Service, BlogPost, BlogCategory, FAQ — models, four serializer variants each, admin + public APIs | 6 |
| **8** | Sections + item models + `SectionItemViewSet` + reorder | 7 |
| **9** | Pages, singletons, `Company`, page registry, admin page APIs | 8 |
| **10** | Aggregate public page APIs + `for_public()` selectors + `assertNumQueries` tests + ETag caching | 9 |
| **11** | PostgreSQL full-text search; `Enquiry` model + rate-limited public submit endpoint | 7 |
| **12** | Django Admin config, OpenAPI polish, seed command, security checklist pass, deployment notes | all |

**One reordering vs. the original brief:** audit moves ahead of content, so no model needs
retrofitting later.

---

## 16b. Local PostgreSQL via Docker

PostgreSQL is the only containerised service — Django itself runs on the host venv, so the
normal `runserver` / debugger / migration workflow is unchanged.

```bash
docker compose up -d db          # start (reads DB_* from .env)
docker compose ps                # confirm healthy
docker compose logs -f db        # tail
docker compose down              # stop, keeps data
docker compose down -v           # stop AND destroy the volume (wipes the database)
```

`docker-compose.yml` reads `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_PORT` from the same
`.env` Django uses, so the two can never drift.

**This machine uses host port 5433** — an unrelated `postgres_db` container already owns
5432. The container still listens on 5432 internally; only the published port differs.

**No `$` in any `.env` value.** Compose interpolates `$VAR` when it reads the file, so a
`SECRET_KEY` containing `$` is silently mangled. Generate keys with
`python -c "import secrets; print(secrets.token_urlsafe(48))"` — url-safe, and PyJWT 2.13
warns below 32 bytes anyway.

Django connects with `DB_HOST=localhost` (the container publishes `5432` to the host). Data
persists in the named volume `archethos_pgdata`.

A healthcheck is defined so Phase 2 can wait for readiness before the first `migrate`.

---

## 16c. Frontend routes (source of truth for pages)

The Next.js UI lives at `archethos-nextjs/archethos`. Its actual routes differ from
the Phase 1 assumptions and take precedence:

```
(website)/                     -> HomePage
(website)/about                -> AboutPage
(website)/contact              -> ContactPage
(website)/gallery              -> GalleryPage        (a page, not just a section)
(website)/journal              -> BlogListingPage    ("journal", not "blog")
(website)/journal/[slug]       -> BlogPost detail
(website)/projects             -> ProjectsListingPage
(website)/projects/[slug]      -> Project detail
(website)/services             -> ServicesListingPage
(website)/services/[slug]      -> Service detail
(website)/locations            -> LocationsPage      (not yet modelled)
(website)/legal/privacy        -> LegalPage
(website)/legal/terms          -> LegalPage
(admin)/admin, /admin/login    -> the CMS frontend, same Next.js app
```

Deltas to resolve **before Phase 7 modelling**:

* No `/vastu` route exists — `VastuPage` is probably not needed; Vastu is likely
  just a `Service`.
* `/locations` is unmodelled. Needs a decision: a `Location` master model, or a
  page with static sections.
* `/legal/[slug]` needs a simple `LegalPage` model (title + rich body + SEO); two
  instances, so a slug-keyed model rather than two singletons.
* `/gallery` is a full page, so `GallerySection` must be reusable at page level too.
* Public blog routes are `/journal/...`; the model can stay `BlogPost` but the
  public route naming should match the frontend.

**Phase 7 must begin with a component-level survey of that repo** to derive the
real field list for each section, rather than guessing.

---

## 17. Open items

| Item | Status |
|---|---|
| PostgreSQL connection credentials | **resolved** — Dockerised Postgres 17, credentials from `.env` (see §16b) |
| Django 6.1 × simplejwt 5.5.1 × `token_blacklist` compatibility | **resolved** — verified working in Phase 2 |
| Production deployment topology (same registrable domain vs. cross-site) | default `SameSite=Lax`; revisit before production |
| `/locations` and `/legal/*` page models | **decide before Phase 7** — see §16c |
| Whether `VastuPage` is needed at all | likely not; no such route in the UI (§16c) |
