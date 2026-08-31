# Archethos CMS — Task Tracker

Architecture reference: [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked

**Progress:** Phases 1-11 complete · Phase 12 (audit, hardening) next · 269 tests passing

**Standing constraints — apply to every phase**

- Class-based views only. No ViewSets, no routers, no `@action`. (plan §2.8)
- Media is `FK(MediaAsset, PROTECT)`, serialized as a relative path. (plan §2.1)
- `order` is display-only and appears in **no** constraint. (plan §2.3)
- One publish flag: `status` + `published_at`. No `is_active` / `is_published`. (plan §2.6)
- Public serializers are independent classes, never subclasses of admin ones. (plan §12)
- Never modify the Next.js UI repo. Read it for reference only.
- All master content lives in the single `content` app (Project, Service, BlogPost,
  FAQ, Counter), split into modules under `content/models/`. `Company` lives in `pages`.

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

## Phase 6 — Master content `[x] COMPLETE`

- [x] `Service`
- [x] `Project` + `ProjectGalleryItem`
- [x] `BlogCategory` + `BlogPost`
- [x] `FAQ`
- [x] `Counter` (prefix, content, postfix, subtitle, description) - plan §5.5
- [x] Indexes: slugs, `(status, published_at)`
- [x] `published_at` auto-set on first transition to PUBLISHED
- [x] Four serializers each: List / Detail / Write / Public
- [x] Admin CRUD for all six
- [x] `projects/{id}/gallery/` list / add / update / remove / reorder
- [x] `blogs/{id}/publish/` and `unpublish/`
- [x] Public read-only: projects, services, blogs, faqs (list + `{slug}`)
- [x] Public filters: `?featured=` `?service=` `?year=` `?status=` `?category=`
- [x] Tests: draft content unreachable publicly; slug uniqueness; permission matrix
- [x] `manage.py sync_cms_groups`

---

**Phase 6 notes**

- **The five content apps were merged into one `content` app**, models split into
  modules under `content/models/`. `Company` moved into `pages`. Permission
  codenames are now `content.add_project` etc.
- `MediaReferenceField` proven end to end: create by id, create by path, and a
  GET'd payload PATCHes back unchanged.
- Public exposure is enforced in `get_queryset()` via `.live()`, never in a
  serializer. Drafts return **404, not 403** - a 403 would confirm the record
  exists. A draft Service linked from a live Project is filtered out too.
- Public blog detail exposes `author_name`, never `author_email`.
- Slugs are generated once and never regenerated on title change, so published
  URLs survive typo fixes.
- **Fixed:** `annotate(Count(...))` silently clears `Meta.ordering`, which made
  two paginated lists non-deterministic. Every list view now declares an explicit
  `ordering`.
- `MediaDetailField` / `SEOBlockField` rewritten as plain `Field` subclasses with
  `source="*"`; as `SerializerMethodField`s they needed a `get_<name>` method on
  every serializer, which was the duplication they existed to remove.

## Phase 7 — Sections `[x] COMPLETE`

- [x] Read-only survey of the Next.js UI to derive real fields
- [x] `Section` concrete MTI base: `section_type` (set in `save()`, `editable=False`),
      `internal_label`
- [x] `SectionType` choices - one value per frontend component
- [x] `HeroSection` **+ `HeroSlide`** (the live hero is a 3-frame slider, not a
      single headline - the UI survey caught this)
- [x] `IntroSection`
- [x] `CounterSection`
- [x] `FeaturedProjectsSection`
- [x] `ServicesSection`
- [x] `GallerySection` (GRID / MASONRY / SLIDER)
- [x] `FAQSection`
- [x] `CTASection`
- [x] `ContactInfoSection`
- [x] `RichTextSection` (carries `/legal/privacy` and `/legal/terms`)
- [x] `SECTION_REGISTRY` with `SectionSpec` + `ItemSpec`
- [x] Admin section URLs **generated from the registry** - one route set serves
      all 10 types via `<segment>`
- [x] `GET /admin/sections/` - type-agnostic browser, one query
- [x] `GET /admin/sections/types/` - the registry as data, so the admin menu
      cannot drift from the backend
- [x] Per-type CRUD
- [x] Tests: `section_type` cannot be forged; permissions are per concrete type

---

## Phase 8 — Section items + reorder `[x] COMPLETE`

- [x] `FAQSectionItem` · `CounterSectionItem` · `FeaturedProjectItem`
      (+ `display_variant`) · `ServiceSectionItem` (+ `label_override`) ·
      `GallerySectionItem` (+ `caption`) · `HeroSlide`
- [x] `UniqueConstraint(section, content)` on each; **no** constraint on `order`
- [x] Generic item list / add / update / remove, registry-driven
- [x] `SectionItemReorderAPIView` - ownership checked, duplicate and unknown ids
      rejected, then `bulk_update` in one transaction
- [x] Item routes generated for every type that declares items
- [x] Parent-derived permissions (`sections.change_faqsection`)
- [x] Detail includes items; list stays light with `items_count`
- [x] Tests: reorder atomicity, duplicate content rejected, PROTECT on master content

**Phases 7-8 notes**

- **The hero is a slider.** The UI survey found three frames each with their own
  `eyebrow`, `headingLines`, `lead` and media. A single-headline hero model could
  not have expressed it. `heading` is stored as text with one line per row and
  split into `heading_lines` by the serializer - the breaks are a typographic
  decision the editor makes in a textarea.
- One route set serves all 10 section types. Adding a type = model + serializers +
  registry entry; **no new URL, view or test file**.
- Several tests iterate `SECTION_REGISTRY`, so a newly registered type is covered
  the moment it is added. One asserts every `SectionType` value is registered -
  an unregistered type would 404 on its own routes.
- Public serializers filter draft master content out of every section, and none of
  them expose `internal_label` (asserted for all 10).
- **Deferred to Phase 9:** section `usage` endpoint and `used_by_count`. Both need
  `PageSection`, which does not exist yet - written a phase early and removed
  rather than faked.
- More section types exist in the UI than are modelled (design-build, vastu-preview,
  philosophy, mission-vision, founder-message, studio-story, service-process,
  location). Most are `intro`- or `rich_text`-shaped; add them as needed.

---

## Phase 9 — Pages + composition `[x] COMPLETE`

- [x] `Page` - name, slug (unique), `is_published`, SEO
- [x] `PageSection` - page, section, `section_key`, `order`, `is_visible`
- [x] `UniqueConstraint(page, section_key)` - and **no** `unique(page, order)` (plan §2.3)
- [x] Page CRUD (list light + paginated, detail with composition)
- [x] `GET /admin/pages/{id}/sections/` - list composition
- [x] `POST /admin/pages/{id}/sections/` - attach a section
- [x] `PATCH /admin/pages/{id}/sections/{ps_id}/` - key / visibility / order
- [x] `DELETE /admin/pages/{id}/sections/{ps_id}/` - detach; **must not delete the Section**
- [x] `PATCH /admin/pages/{id}/sections/reorder/` - atomic
- [x] `GET /admin/sections/{type}/{id}/usage/` - which pages use this section
- [x] Seed the ten `Page` rows matching the frontend routes (plan §18)
- [x] Tests: same section type twice on one page via different keys; duplicate key rejected;
      detaching leaves the section intact; reorder atomicity
- [x] `manage.py sync_cms_groups`

---

**Phase 9 notes**

- `Page` uses `status` / `published_at` like every content model, not a bespoke
  `is_published`. One meaning of "live" across the system (plan §2.6).
- **Bug caught:** `legal/privacy` is a real frontend route, but `SlugField` forbids
  `/`. The seed migration created it anyway because `RunPython` skips validation,
  so the API would have rejected editing a row that already existed. `slug` is now
  a validated `CharField`; Phase 10's public route must use `<path:slug>`.
- The 10 seeded pages start as DRAFT: a page with no sections has nothing to
  render, so publishing is deliberate.
- Tested and working: the same section on several pages, and the same section
  *type* twice on one page under different keys - the two things the old
  fixed-slot design could not express at all.
- `is_visible` is per placement, so hiding a shared CTA on one page leaves it
  visible elsewhere.
- Section `usage` and `used_by_count` restored now that `PageSection` exists.
- `Company` inject fields are superuser-only, tested both ways; JSON fields have
  shape validators.

## Phase 10 — Public aggregate API `[x] COMPLETE`

- [x] `GET /api/v1/public/pages/{slug}/`
- [x] Batched per-type resolution driven by `SECTION_REGISTRY.public_queryset`
      (**not** `InheritanceManager`) - plan §13
- [x] Only `is_visible=True`, ordered by `PageSection.order`
- [x] Each entry emits `id` / `key` / `type` / `data`; `internal_label` never exposed
- [x] Unpublished page -> 404; unknown slug -> 404
- [x] ETag + `Cache-Control` from max `updated_at`
- [x] **`assertNumQueries` test** pinning the query count so it cannot silently regress
- [x] Test: query count is flat as gallery items scale from 4 to 40
- [x] Test: draft master content never surfaces inside a section

---

**Phase 10 notes**

- **Measured: 16 queries** for an 8-section homepage, not the 18 estimated.
  The shape is 2 setup + 1 per simple type + 2 per collection type. Three CTAs on
  one page cost **one** batch, not three. Pinned with `assertNumQueries`.
- Flatness proven directly: a page with 40 gallery images, 30 FAQs and 25 projects
  costs the same 16 queries as one with 4/3/3.
- `InheritanceManager` was rejected for this: its all-subclass LEFT JOIN is slower
  *and* cannot apply per-type prefetches, which is what makes batching work.
- Unresolvable section types are logged and skipped rather than 500ing the page.
- ETag covers the whole graph, so editing a shared CTA invalidates every page
  composing it. Verified 304 over real HTTP.
- Verified live: `/pages/legal/privacy/` resolves through `<path:slug>`; draft
  pages 404; CORS headers correct for `localhost:3000`.

## Phase 11 — Search, enquiries, company `[x] COMPLETE`

- [x] `pg_trgm` + `unaccent` extension migration
- [x] `search_vector` + GIN index on Project and BlogPost, weighted
- [x] `GET /api/v1/public/search/?q=` across projects + services + blogs
- [x] `Company` singleton + JSON schema validators
- [x] **Superuser-only guard on `head_inject` / `body_inject`** (stored-XSS vector)
- [x] `GET/PATCH /admin/company/` · `GET /public/company/`
- [x] `Enquiry` model
- [x] `POST /public/enquiries/` - rate-limited + honeypot
- [x] Admin enquiry list / detail / mark-read / delete
- [x] Tests: search returns only live content; rate limit returns 429; non-superuser cannot
      write inject fields

---

**Phase 11 notes**

- Search is **two passes**: weighted full-text against the tsvector, then trigram
  similarity on `title` as a fallback. They fail differently - full-text tokenises,
  so a misspelling produces a token matching nothing at all, while trigram distance
  still finds it. Verified live: `?q=courtyrd` returns "Courtyard Villa".
- The fallback only runs when full-text returns nothing, so it never dilutes good
  results.
- `websearch_to_tsquery` is used rather than `plainto_tsquery`: it accepts quoted
  phrases, `OR` and `-word`, and never raises on malformed input. Tested with `"(((".`
- The vector is maintained in `save()` as a follow-up UPDATE, because the stemming
  and weighting are Postgres's job. `update()` / `bulk_update()` bypass it by
  design - `manage.py rebuild_search_index` repairs that.
- **Found while testing:** a stale vector after a bulk *title* change is masked by
  the trigram fallback, which reads the live column. Only a body-only term exposes
  the staleness. Both behaviours are now pinned by tests.
- `pg_trgm` and `unaccent` live in their own migration: they are database-wide and
  need superuser on first install, so on a managed host that is the one migration
  to run by hand.
- The public enquiry endpoint is the only place an anonymous visitor writes to the
  database. It carries a 10/h per-IP rate limit (429) and a honeypot whose response
  is byte-identical to a success - telling a bot it was caught only teaches it to
  avoid the trap.
- Enquiries are read-only in the admin apart from `is_read`: a submission is a
  record of what someone actually sent.

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
