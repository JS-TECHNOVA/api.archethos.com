# Archethos CMS — Task Tracker

Architecture reference: [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked

**Progress:** Phases 1-5 complete · Phase 6 (master content) next · 97 tests passing

**Standing constraints — apply to every phase**

- Class-based views only. No ViewSets, no routers, no `@action`. (plan §2.8)
- Media is `FK(MediaAsset, PROTECT)`, serialized as a relative path. (plan §2.1)
- `order` is display-only and appears in **no** constraint. (plan §2.3)
- One publish flag: `status` + `published_at`. No `is_active` / `is_published`. (plan §2.6)
- Public serializers are independent classes, never subclasses of admin ones. (plan §12)
- Never modify the Next.js UI repo. Read it for reference only.

---

## Blockers

_None._

---

## Phase 1 — Architecture `[x] COMPLETE`

- [x] Critical review of the brief; identify real risks
- [x] Decide media storage (FK + path serialization)
- [x] Decide ordering strategy (`order` in no constraint)
- [x] Decide audit scope (who changed what only)
- [x] Decide response envelope approach
- [x] Decide publish semantics (single `status` field)
- [x] Decide refresh-race handling (none - 401)
- [x] Decide class-based views only, never ViewSets
- [x] **Redesign: dynamic page composition** - `Page` -> `PageSection` -> `Section` (MTI)
      replaces fixed per-page FK slots
- [x] Decide MTI over GenericForeignKey / sparse nullable FKs / JSONField
- [x] Decide `section_type` (component) vs `section_key` (role on a page)
- [x] Specify `Company` singleton, `Enquiry`, `Counter`
- [x] Model catalogue + ERD + deletion rules
- [x] Auth / permission / registry / aggregate-query architecture
- [x] `docker-compose.yml` for local PostgreSQL 17

---

## Phase 2 — Foundation `[x] COMPLETE`

- [x] Verify Django 6.1 x simplejwt 5.5.1 x `token_blacklist`
- [x] Install `psycopg[binary]`
- [x] `docker compose up -d db`, container healthy, host connection verified
- [x] `requirements/{base,dev,prod}.txt`
- [x] `.env` / `.env.example` / `.gitignore`
- [x] Restructure into `archethosbackend/apps/` with an `AppConfig` per app
- [x] Move root `medialibrary/` -> `apps/media_library/`
- [x] Split settings into `base` / `development` / `production` / `test`
- [x] PostgreSQL wired from `.env`
- [x] `core` abstracts: TimeStamped, SEO, Slugged, Publishable, OrderedItem, Singleton
- [x] `EnvelopeJSONRenderer`
- [x] `envelope_exception_handler` (incl. `ProtectedError` -> 409 naming referents)
- [x] `EnvelopePageNumberPagination`
- [x] DRF settings, `/api/v1/` route skeleton, CORS + CSRF, drf-spectacular
- [x] `/health/` endpoint
- [x] JSON `handler404` / `handler500` under `/api/`

**Notes**

- Postgres publishes on host port **5433** - an unrelated `postgres_db` container owns 5432.
- **No `$` in any `.env` value** - docker-compose interpolates it. Use `secrets.token_urlsafe`.
- PyJWT 2.13 warns on HMAC keys under 32 bytes.

---

## Phase 3 — Authentication `[x] COMPLETE`

**Decision:** built-in `auth.User`, not a custom user model. (plan §2.7a)

- [x] `EmailBackend` - login by email, constant-time on unknown emails
- [x] Case-insensitive unique index on `auth_user.email` (migration 0001)
- [x] First `makemigrations` + `migrate` against Docker Postgres
- [x] Superuser created (`admin@archethos.test`)
- [x] `SIMPLE_JWT` config, rotation + blacklist, env-driven lifetimes
- [x] `CookieJWTAuthentication` - cookie read, Bearer fallback, access-only token type,
      CSRF enforced on unsafe methods
- [x] Cookie helpers (env-aware Secure / SameSite / Domain / Path)
- [x] `login/` `refresh/` `logout/` `me/` `password/change/` `csrf/`
- [x] `cookieAuth` OpenAPI security scheme
- [x] 23 tests

**Notes**

- Refresh cookie scoped to `Path=/api/v1/auth/`.
- Logout **cannot** revoke an already-issued access token (stateless JWT); mitigated by the
  15-minute lifetime plus cookie deletion. (plan §2.7b)
- Login/logout are `AllowAny`: an expired access token must never block logging out.

---

## Phase 4 — Users, groups, permissions `[x] COMPLETE`

- [x] `StrictDjangoModelPermissions` (requires `view_*` on GET)
- [x] `AdminListCreateAPIView` / `AdminRetrieveUpdateDestroyAPIView` base classes
- [x] User list / create / retrieve / update, with filters, search, ordering
- [x] `UserDeactivateAPIView` / `UserActivateAPIView` / `UserSetPasswordAPIView`
- [x] Group list / create / detail / update / delete
- [x] `GET /admin/permissions/` grouped by app and model
- [x] Escalation guards: grant-only-what-you-hold · group assignment checked the same way ·
      superuser-only flags · no self-deactivation · last superuser protected
- [x] Bootstrap roles in `accounts/groups.py` + migration + `sync_cms_groups` command
- [x] 39 tests

**Notes**

- Users are **never deleted**, only deactivated - `DELETE /users/{id}/` returns 405.
- `sync_cms_groups` **must be re-run after each content phase**; the roles grant whatever
  models exist when synced.

---

## Phase 5 — Media Library `[x] COMPLETE`

- [x] `MediaAsset` model + `CheckConstraint`s + `checksum` index
- [x] UUID-prefixed `upload_to`; user filename never determines uniqueness
- [x] `relative_path` property
- [x] Upload validation: extension allowlist, MIME sniff, max size, dimension caps,
      Pillow verify (a `.jpg` that is not an image must be rejected)
- [x] Image metadata extraction (width / height / size / mime)
- [x] YouTube URL validation + video-id extraction + thumbnail URL
- [x] **`MediaReferenceField`** - read -> path, write -> id-or-path, existence validated.
      The single place plan §2.1 is enforced; everything later depends on it.
- [x] `POST /admin/media/upload/`
- [x] `POST /admin/media/youtube/`
- [x] `GET/PATCH/DELETE /admin/media/` + `{id}/` (409 on PROTECT violation)
- [x] `GET /admin/media/{id}/usage/` - where an asset is referenced
- [x] Pagination, `?search=`, `?media_type=`, `?source_type=`, `?ordering=`
- [x] Tests: rejects non-image `.jpg`, rejects oversize, dedupes by checksum,
      YouTube parsing, delete-in-use returns 409
- [x] `manage.py sync_cms_groups`

---

**Phase 5 notes**

- `MediaReferenceField` is live and tested both directions: reads as a relative
  path, writes from an id, a `/media/...` path, a bare `uploads/...` path, or a
  YouTube URL. A GET'd payload PATCHes back unchanged, which the frontend relies on.
- Upload validation checks **bytes, not names**. A PHP payload named `evil.jpg` is
  rejected by Pillow's `verify()`, confirmed over real HTTP.
- YouTube host matching is an allowlist, not a substring check - `youtube.evil.example`
  is rejected. The same video is refused twice even via a different URL shape.
- `file` is immutable after upload; only `title` and `alt_text` are editable.
  Swapping bytes under a stable id would silently change every page using it.
- **Fixed:** upload tests were writing into the project's `media/` directory.
  `settings/test.py` now points `MEDIA_ROOT` at a temp dir.
- Deletion relies on `PROTECT` plus the envelope handler's 409; `media/{id}/usage/`
  lets the UI show what would break before offering the delete.

## Phase 6 — Master content

- [ ] `Service`
- [ ] `Project` + `ProjectGalleryItem`
- [ ] `BlogCategory` + `BlogPost`
- [ ] `FAQ`
- [ ] `Counter` (prefix, content, postfix, subtitle, description) - plan §5.5
- [ ] Indexes: slugs, `(status, published_at)`
- [ ] `published_at` auto-set on first transition to PUBLISHED
- [ ] Four serializers each: List / Detail / Write / Public
- [ ] Admin CRUD for all six
- [ ] `projects/{id}/gallery/` list / add / update / remove / reorder
- [ ] `blogs/{id}/publish/` and `unpublish/`
- [ ] Public read-only: projects, services, blogs, faqs (list + `{slug}`)
- [ ] Public filters: `?featured=` `?service=` `?year=` `?status=` `?category=`
- [ ] Tests: draft content unreachable publicly; slug uniqueness; permission matrix
- [ ] `manage.py sync_cms_groups`

---

## Phase 7 — Sections

- [ ] **Prerequisite:** component-level survey of the Next.js UI to derive real fields per
      section type (plan §20). Do not guess.
- [ ] `Section` concrete MTI base: `section_type` (set in `save()`, never client-supplied),
      `internal_label`
- [ ] `SectionType` choices
- [ ] `HeroSection`
- [ ] `IntroSection`
- [ ] `CounterSection`
- [ ] `FeaturedProjectsSection`
- [ ] `ServicesSection`
- [ ] `GallerySection` (layout_variant GRID / MASONRY / SLIDER)
- [ ] `FAQSection`
- [ ] `CTASection`
- [ ] `ContactInfoSection`
- [ ] `RichTextSection` (carries `/legal/privacy` and `/legal/terms`)
- [ ] `SECTION_REGISTRY` with `SectionSpec` (model, 4 serializers, url_segment,
      public_queryset)
- [ ] Admin section URLs **generated from the registry**, not hand-written per type
- [ ] `GET /admin/sections/` - all sections, `?section_type=` filter, paginated
- [ ] Per-type CRUD: `sections/{type}/` and `sections/{type}/{id}/`
- [ ] Tests: `section_type` cannot be set by the client and matches the concrete class
- [ ] `manage.py sync_cms_groups`

---

## Phase 8 — Section items + reorder

- [ ] `FAQSectionItem`
- [ ] `CounterSectionItem`
- [ ] `FeaturedProjectItem` (+ `display_variant`)
- [ ] `ServiceSectionItem` (+ `label_override`)
- [ ] `GallerySectionItem` (+ `caption`)
- [ ] `UniqueConstraint(section, content)` on each; **no** constraint on `order`
- [ ] `SectionItemListCreateAPIView` / `SectionItemDetailAPIView` base classes
- [ ] `ReorderAPIView` base - validates ownership, no duplicate ids, no unknown ids,
      then `transaction.atomic()` + `bulk_update(["order"])`
- [ ] Item routes generated from the registry for every type that has items
- [ ] Parent-derived permissions (`sections.change_faqsection`, not a per-item permission)
- [ ] Detail responses include items; list responses stay light with `items_count`
- [ ] Tests: reorder atomicity + validation; duplicate content rejected; deleting a section
      leaves master content intact (PROTECT)

---

## Phase 9 — Pages + composition

- [ ] `Page` - name, slug (unique), `is_published`, SEO
- [ ] `PageSection` - page, section, `section_key`, `order`, `is_visible`
- [ ] `UniqueConstraint(page, section_key)` - and **no** `unique(page, order)` (plan §2.3)
- [ ] Page CRUD (list light + paginated, detail with composition)
- [ ] `GET /admin/pages/{id}/sections/` - list composition
- [ ] `POST /admin/pages/{id}/sections/` - attach a section
- [ ] `PATCH /admin/pages/{id}/sections/{ps_id}/` - key / visibility / order
- [ ] `DELETE /admin/pages/{id}/sections/{ps_id}/` - detach; **must not delete the Section**
- [ ] `PATCH /admin/pages/{id}/sections/reorder/` - atomic
- [ ] `GET /admin/sections/{type}/{id}/usage/` - which pages use this section
- [ ] Seed the ten `Page` rows matching the frontend routes (plan §18)
- [ ] Tests: same section type twice on one page via different keys; duplicate key rejected;
      detaching leaves the section intact; reorder atomicity
- [ ] `manage.py sync_cms_groups`

---

## Phase 10 — Public aggregate API

- [ ] `GET /api/v1/public/pages/{slug}/`
- [ ] Batched per-type resolution driven by `SECTION_REGISTRY.public_queryset`
      (**not** `InheritanceManager`) - plan §13
- [ ] Only `is_visible=True`, ordered by `PageSection.order`
- [ ] Each entry emits `id` / `key` / `type` / `data`; `internal_label` never exposed
- [ ] Unpublished page -> 404; unknown slug -> 404
- [ ] ETag + `Cache-Control` from max `updated_at`
- [ ] **`assertNumQueries` test** pinning the query count so it cannot silently regress
- [ ] Test: query count is flat as gallery items scale from 4 to 40
- [ ] Test: draft master content never surfaces inside a section

---

## Phase 11 — Search, enquiries, company

- [ ] `pg_trgm` + `unaccent` extension migration
- [ ] `search_vector` + GIN index on Project and BlogPost, weighted
- [ ] `GET /api/v1/public/search/?q=` across projects + services + blogs
- [ ] `Company` singleton + JSON schema validators
- [ ] **Superuser-only guard on `head_inject` / `body_inject`** (stored-XSS vector)
- [ ] `GET/PATCH /admin/company/` · `GET /public/company/`
- [ ] `Enquiry` model
- [ ] `POST /public/enquiries/` - rate-limited + honeypot
- [ ] Admin enquiry list / detail / mark-read / delete
- [ ] Tests: search returns only live content; rate limit returns 429; non-superuser cannot
      write inject fields

---

## Phase 12 — Audit, hardening, delivery

- [ ] `AuditLog` model + indexes
- [ ] `AuditLogMixin` on the admin base view classes (before-snapshot diff)
- [ ] Denylist (`password`, `token`, `secret`, `key`, `session`)
- [ ] LOGIN / LOGOUT / PUBLISH / UNPUBLISH logging
- [ ] `GET /admin/audit-logs/` - read-only, paginated, filter by user / action /
      content_type / object_id / date range
- [ ] Tests: diffs correct; passwords never appear in `changes`
- [ ] Django Admin registration (dev and superuser rescue only)
- [ ] OpenAPI polish + `/api/v1/schema/docs/`
- [ ] `seed_demo_data` management command
- [ ] Production settings pass + full security checklist (plan §15)
- [ ] `README.md`: setup, env vars, CORS/CSRF for Next.js, auth flow,
      `credentials: "include"`, section registry contract
- [ ] Deployment notes (gunicorn, static/media serving, migrations)
- [ ] Final full test run
