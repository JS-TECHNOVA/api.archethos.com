# Archethos CMS — Task Tracker

Architecture reference: [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked

**Progress:** Phases 1–2 complete · Phase 3 next

---

## Blockers

- [x] ~~PostgreSQL credentials~~ — resolved: Dockerised Postgres 17, credentials live in
      `.env` and are shared with `docker-compose.yml`

_No open blockers._

---

## Phase 1 — Architecture `[x] COMPLETE`

- [x] Review brief, identify architectural risks
- [x] Decide media storage strategy (FK + path serialization)
- [x] Decide page→section cardinality (nullable FK, SET_NULL)
- [x] Decide ordering strategy (`order` in no constraint)
- [x] Decide audit scope (who changed what only)
- [x] Decide response envelope approach
- [x] Decide publish semantics (single `status` field)
- [x] Decide refresh-race handling (none — 401)
- [x] Specify `Company` singleton model
- [x] Specify `Enquiry` model
- [x] Full model catalogue + ERD
- [x] Auth / permission / API / serializer architecture
- [x] Write `DEVELOPMENT_PLAN.md` + `TASKS.md`
- [x] `docker-compose.yml` for local PostgreSQL 17

---

## Phase 2 — Foundation `[x] COMPLETE`

### Environment

- [x] Verify Django 6.1 × simplejwt 5.5.1 × `token_blacklist` compatibility **(do this first)**
- [x] Install `psycopg[binary]`
- [x] `docker compose up -d db` and confirm the container reports healthy
- [x] Verify a psql connection from the host on `localhost:${DB_PORT}`
- [x] Create `requirements/base.txt`, `dev.txt`, `prod.txt`
- [x] `.env.example` with every variable from plan §15
- [x] `.env` (gitignored) for local development
- [x] `.gitignore` (`.env`, `.venv`, `__pycache__`, `media/`, `db.sqlite3`)
- [x] `.env` DB_* values match `docker-compose.yml` (same file feeds both)

### Project restructure

- [x] Create `archethosbackend/apps/` package
- [x] Move root `medialibrary/` → `apps/media_library/`
- [x] Split `settings.py` → `settings/{base,development,production,test}.py`
- [x] Point `manage.py`, `wsgi.py`, `asgi.py` at `settings.development`
- [x] Configure PostgreSQL from `.env` via `django-environ` (`DB_HOST=localhost`)
- [x] `MEDIA_URL` / `MEDIA_ROOT` / static config

### Core app

- [x] `TimeStampedModel`
- [x] `SEOModel` (lazy `"media_library.MediaAsset"` ref)
- [x] `SluggedModel` + unique-slug generator utility
- [x] `PublishableModel` + `PublishableQuerySet.live()`
- [x] `OrderedItemModel`
- [x] `SingletonModel` (pinned pk + `CheckConstraint` + `load()`)

### API infrastructure (`apps/api/`)

- [x] `EnvelopeJSONRenderer`
- [x] `envelope_exception_handler` (incl. 409 for `ProtectedError`)
- [x] `EnvelopePageNumberPagination`
- [x] DRF settings: default auth, permissions, renderer, pagination, filter backends
- [x] API versioning + `/api/v1/` router skeleton (`auth/`, `admin/`, `public/`)
- [x] CORS + CSRF configuration
- [x] drf-spectacular config + postprocessing hooks for the envelope
- [x] `/health/` endpoint


**Phase 2 notes**

- Django 6.1 x simplejwt 5.5.1 x `token_blacklist` verified working (migrate, issue,
  rotate, blacklist, reject-reuse). No fallback to 5.2 LTS needed.
- Postgres publishes on host port **5433**, not 5432 — an unrelated `postgres_db`
  container (postgres:16) already owns 5432 on this machine.
- `SECRET_KEY` must contain no `$`: docker-compose reads the same `.env` and would
  interpolate it. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- PyJWT 2.13 warns on HMAC keys under 32 bytes, so keep `SECRET_KEY` long.
- 20/20 infrastructure assertions pass (envelope, pagination metadata, error mapping
  incl. ProtectedError -> 409, live DB health check).
- No migrations run yet — deliberate, the custom User must be in the first one.

---

## Phase 3 — Authentication

- [ ] Custom `User` model (email as `USERNAME_FIELD`) + `UserManager` **— before first migrate**
- [ ] `AUTH_USER_MODEL` set in settings
- [ ] **First `makemigrations` + `migrate`**
- [ ] `createsuperuser` verified
- [ ] `SIMPLE_JWT` config (15 min / 7 days, rotation, blacklist) — all env-driven
- [ ] Add `rest_framework_simplejwt.token_blacklist` to `INSTALLED_APPS`
- [ ] `CookieJWTAuthentication` — cookie read, Bearer fallback, `token_type` assertion, CSRF
      enforcement on unsafe methods
- [ ] Cookie helper (set / clear, env-aware Secure / SameSite / Domain / Path)
- [ ] `POST /api/v1/auth/login/`
- [ ] `POST /api/v1/auth/refresh/` (rotation + blacklist, 401 + clear cookies on any failure)
- [ ] `POST /api/v1/auth/logout/`
- [ ] `GET /api/v1/auth/me/` — effective permissions via `get_all_permissions()`
- [ ] `POST /api/v1/auth/password/change/`
- [ ] Tests: login, refresh rotation, blacklisted-token rejection, refresh-token-cannot-authenticate,
      CSRF enforcement, logout clears cookies

---

## Phase 4 — Users, groups, permissions

- [ ] `StrictDjangoModelPermissions` (requires `view_*` on GET)
- [ ] User management API — list / create / retrieve / update / deactivate / set-password
- [ ] `UserListSerializer` / `UserDetailSerializer` / `UserWriteSerializer`
- [ ] Assign groups + direct permissions
- [ ] Group management API + permission assignment
- [ ] `GET /api/v1/admin/permissions/` grouped by app/model
- [ ] Privilege-escalation guards:
  - [ ] may only grant permissions the actor holds
  - [ ] non-superuser cannot set `is_superuser`
  - [ ] cannot deactivate self
  - [ ] cannot deactivate the last active superuser
- [ ] Bootstrap groups data migration (Administrators / Content Managers / Editors / Media Managers)
- [ ] Tests: permission matrix per role, escalation guards

---

## Phase 5 — Audit

- [ ] `AuditLog` model + indexes
- [ ] `AuditLogMixin` (`perform_create` / `perform_update` with before-snapshot / `perform_destroy`)
- [ ] Field denylist (`password`, `token`, `secret`, `key`, `session`)
- [ ] Diff builder → `{"field": {"old": ..., "new": ...}}`
- [ ] LOGIN / LOGOUT logging in the auth views
- [ ] `GET /api/v1/admin/audit-logs/` — read-only, paginated
- [ ] Filters: `user`, `action`, `content_type`, `object_id`, date range; search; ordering
- [ ] Tests: create/update/delete produce correct diffs; passwords never appear in `changes`

---

## Phase 6 — Media Library

- [ ] `MediaAsset` model + constraints + `checksum` index
- [ ] UUID-prefixed `upload_to` callable
- [ ] `relative_path` property
- [ ] Upload validation: extension allowlist, MIME sniff, max size, Pillow verify, dimension caps
- [ ] Image metadata extraction (width / height / size / mime)
- [ ] YouTube URL validation + video-id extraction + thumbnail URL
- [ ] `MediaReferenceField` (read → path, write → id-or-path, existence validation)
- [ ] `POST /api/v1/admin/media/upload/`
- [ ] `POST /api/v1/admin/media/youtube/`
- [ ] `GET/PATCH/DELETE /api/v1/admin/media/` + `{id}/` (409 on PROTECT violation)
- [ ] `GET /api/v1/admin/media/{id}/usage/` — where an asset is referenced
- [ ] Pagination, `?search=`, `?media_type=`, `?source_type=`, `?ordering=`
- [ ] Tests: rejects non-image `.jpg`, rejects oversize, dedupes by checksum, YouTube parsing,
      delete-in-use returns 409

---

## Phase 7 — Master content

### Models

- [ ] `Service`
- [ ] `Project` + `ProjectGalleryItem`
- [ ] `BlogCategory` + `BlogPost`
- [ ] `FAQ`
- [ ] Indexes: slugs, `(status, published_at)`, `(section_id, order)`
- [ ] `CheckConstraint` for `published_at` consistency
- [ ] `published_at` auto-set on first transition to PUBLISHED

### Per model: `List` / `Detail` / `Write` / `Public` serializers

- [ ] Service
- [ ] Project
- [ ] BlogPost
- [ ] BlogCategory
- [ ] FAQ

### APIs

- [ ] `AdminModelViewSet` base class (envelope + pagination + filters + audit + serializer dispatch)
- [ ] Admin CRUD: projects, services, blogs, blog-categories, faqs
- [ ] `projects/{id}/gallery/` — list / add / update / remove / reorder
- [ ] `blogs/{id}/publish/` and `unpublish/`
- [ ] Public read-only: projects, services, blogs, faqs (list + `{slug}`)
- [ ] Public filters: `?featured=`, `?service=`, `?year=`, `?status=`, `?category=`
- [ ] Tests: unpublished/draft content never reachable publicly; slug uniqueness; permission matrix

---

## Phase 8 — Sections

### Models

- [ ] `SectionBase` (`internal_name`)
- [ ] `HomeHeroSection` · `AboutHeroSection` · `SimpleHeroSection`
- [ ] `StudioIntroSection` + `StudioStatItem`
- [ ] `FeaturedProjectsSection` + `FeaturedProjectItem`
- [ ] `ServicesSection` + `ServiceSectionItem`
- [ ] `GallerySection` + `GallerySectionItem`
- [ ] `FAQSection` + `FAQSectionItem`
- [ ] `CTASection`
- [ ] `ContactInfoSection`
- [ ] `UniqueConstraint(section, content)` on every item model

### APIs

- [ ] `SectionItemViewSet` generic base — list / add / update / remove / reorder
- [ ] Atomic reorder: validate ownership, no duplicate ids, no unknown ids, `bulk_update`
- [ ] CRUD + `List`/`Detail`/`Write` serializers for all 10 section types
- [ ] Detail responses include items; list responses are lightweight + `items_count`
- [ ] Item routes mounted for all 5 ordered relationships
- [ ] Parent-derived permission class for item endpoints
- [ ] Tests: reorder atomicity + validation; duplicate-content rejection; deleting a section
      leaves master content intact

---

## Phase 9 — Pages & Company

- [ ] `SingletonModel` applied to all page models
- [ ] `HomePage` · `AboutPage` · `ContactPage` · `VastuPage`
- [ ] `ProjectsListingPage` · `ServicesListingPage` · `BlogListingPage`
- [ ] `Company` singleton (JSON fields + inject fields + global SEO)
- [ ] JSON schema validators for `social_urls`, `contacts`, `header_links`, `footer_links`
- [ ] Superuser-only guard on `head_inject` / `body_inject`
- [ ] Data migration seeding one row per page + `Company`
- [ ] Admin page APIs: `GET` / `PATCH` per page, assigning sections by id
- [ ] `GET` / `PATCH /api/v1/admin/company/`
- [ ] Tests: singleton enforcement; non-superuser cannot write inject fields

---

## Phase 10 — Aggregate public APIs

- [ ] `PAGE_REGISTRY` + `PageSpec`
- [ ] `for_public()` selector on every page model (full select_related / prefetch_related)
- [ ] Strongly typed aggregate serializer per page
- [ ] `GET /api/v1/public/pages/{slug}/` (404 on unknown slug, never paginated)
- [ ] `GET /api/v1/public/company/`
- [ ] ETag + `Cache-Control` from max `updated_at`
- [ ] `assertNumQueries` test per aggregate endpoint
- [ ] Tests: unpublished content excluded from aggregates; SEO block present

---

## Phase 11 — Search & enquiries

- [ ] `pg_trgm` + `unaccent` extension migration
- [ ] `search_vector` + GIN index on Project and BlogPost
- [ ] Weighted vector population on save
- [ ] `GET /api/v1/public/search/?q=` across projects + services + blogs
- [ ] `Enquiry` model + indexes
- [ ] `POST /api/v1/public/enquiries/` — rate-limited (`django-ratelimit`) + honeypot
- [ ] Admin: list / retrieve / mark-read / delete enquiries, with filters
- [ ] Tests: search returns only live content; rate limit returns 429

---

## Phase 12 — Hardening & delivery

- [ ] Django Admin registration for all models (dev/superuser use only)
- [ ] OpenAPI schema review + endpoint descriptions + `/api/v1/schema/docs/`
- [ ] `seed_demo_data` management command
- [ ] Production settings: `DEBUG=False`, `ALLOWED_HOSTS`, HSTS, SSL redirect, secure cookies
- [ ] Full security checklist pass (plan §14)
- [ ] `README.md`: setup, env vars, CORS/CSRF for Next.js, auth flow, `credentials: "include"`
- [ ] Deployment notes (gunicorn, static/media serving, migrations)
- [ ] Final test suite run
