# Archethos CMS — Task Tracker

Architecture reference: [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked

**Progress:** Phases 1-11, 13, 14 complete · Phase 12 (audit) outstanding ·
302 tests passing

**Standing constraints — apply to every phase**

- Class-based views only. No ViewSets, no routers, no `@action`. (plan §2.8)
- Media is `FK(MediaAsset, PROTECT)`, serialized as a relative path. (plan §2.1)
- `order` is display-only and appears in **no** constraint. (plan §2.3)
- One publish flag: `status` + `published_at`. No `is_active` / `is_published`. (plan §2.6)
- Public serializers are independent classes, never subclasses of admin ones. (plan §12)
- Structure is code, content is data. A page is a model; its fields are its render order.
  Never reintroduce a generic page/section/registry layer. (plan §2.2)
- Master data lives in `content` (Project, Service, BlogPost, FAQ, Counter, GalleryItem,
  Location). Sections live in `pages`, beside the page that renders them. `Company` too.
- A section references master data through an item model and never copies its fields. (plan §5.5)
- The website frontend and the page models are changed together. The admin consumes the API.

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

## Phases 7-9 — Generic sections and page composition `[x] SUPERSEDED`

Built and shipped: `Section` MTI base, `SECTION_REGISTRY`, per-type CRUD, section items with
atomic reorder, `Page` + `PageSection` composition with visibility and ordering.

**Replaced in Phase 13.** The generic layer worked but was the wrong shape for a nine-page
corporate site: the schema described a page builder rather than the website, and the frontend
needed a registry to render it. See Phase 13 below.

---

## Phase 10 — Public page API `[x] COMPLETE, rebuilt in Phase 13`

- [x] `GET /api/v1/public/pages/{route}/` — one request renders a whole route
- [x] `GET /api/v1/public/pages/` — which routes are live, for sitemaps and static builds
- [x] Sections as named keys; master data inlined, not join rows
- [x] Admin bookkeeping stripped from the public payload
- [x] Unpublished page -> 404, indistinguishable from one that does not exist
- [x] Query plan derived from the models in `pages/selectors.py`
- [x] **Query-count test** pinning flatness so it cannot silently regress

---

**Phase 10 notes**

- The original implementation batched one query per distinct section type through
  `SECTION_REGISTRY.public_queryset`, because MTI made section rows polymorphic.
  Phase 13 removed the polymorphism, so the batching went with it: sections are now
  `OneToOneField`s and arrive with the page in **one** query.
- **11 queries** for the eleven-section home page. Flat: thirty gallery images cost
  the same as three, pinned by `QueryCountTests`.
- The N+1 that survived the first cut: joining an item's master record leaves *that
  record's* media unfetched, so thirty gallery items cost thirty extra queries. The
  selector joins two levels for exactly that reason.
- ETag and `Cache-Control` were dropped with the rebuild — worth reinstating, but
  Cloudflare now sits in front and is the more important cache to think about.

---

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
      `credentials: "include"`, the page API contract
- [ ] Deployment notes (gunicorn, static/media serving, migrations)
- [ ] Final full test run

---

## Phase 13 — Explicit page models `[x] COMPLETE`

Replaced the generic CMS with one model per page. Structure is code; content is data.

**Backend**

- [x] Ten page models, each a singleton with SEO, `is_published`, `required_sections`
- [x] Sections as plain tables: shared (Hero, CTA, Process, RichText) plus per-page
- [x] Item models linking sections to master data, `unique(section, record)`
- [x] `GalleryItem` and `Location` master models, lifted out of the frontend data files
- [x] `Service` completed: number, title_lines, hero_heading, hero/index images,
      detail sections, process steps, gallery
- [x] `Project` completed: category, layout, five narrative blocks, materials,
      kind-discriminated media (gallery / floor plan / drawing)
- [x] One endpoint per page, `GET` + `PATCH`, nested section writes in one transaction
- [x] Item order is array order — no `order` on the wire, no reorder endpoints
- [x] Public payload inlines master data, drops admin bookkeeping, 404s while unpublished
- [x] `pages/selectors.py` derives the query plan from the models; joins master data
      **and its media**, two levels deep
- [x] `manage.py ensure_pages`, wired into `deploy.sh`
- [x] Deleted: `sections` app, `Page`, `PageSection`, `SectionType`, `SECTION_REGISTRY`,
      section CRUD and reorder routes, `section_type` / `section_key` everywhere
- [x] Tests: structure invariants, nested writes, publish gating, public visibility,
      and a query-count test proving a page read stays flat as content grows

**Frontend**

- [x] `Pages` menu listing the ten routes; one form per page, sections in render order
- [x] Explicit page composers — no `sections.map()`, no registry
- [x] `RecordPicker` for master-data sections: choose and order, never edit
- [x] Deleted: `components/sections/registry.js`, `section-renderer.jsx`,
      the hero CRUD screen, the runtime section-type menu lookup

**Not done**

- [ ] Admin screens for Gallery and Locations (`/admin/content/gallery`, `/locations`) —
      API is done, UI is not

---

## Phase 14 — Seeding and rate limiting `[x] COMPLETE`

**Seed** — `manage.py seed_site`

- [x] `dump.mjs` exports the frontend's `src/data/*.js` to JSON; the seed reads that
      rather than a hand transcription of 24 captions and 7 project narratives
- [x] `seed_data/pages.py` carries the copy that lives in the page components
- [x] 46 media assets, 5 services, 7 projects, 24 gallery items, 6 journal entries,
      2 locations, 4 figures, Company, and all ten pages
- [x] Idempotent on natural keys; `--pages-only` leaves master data alone
- [x] Placeholders stay placeholders: unverified figures seeded as DRAFT, founder
      left unnamed, location addresses blank, contact details and social links
      omitted (`PLACEHOLDER_CONTACT`), photography marked as stock
- [x] Legal pages seeded unpublished — no copy supplied, and not ours to draft
- [x] Model gaps the real data exposed: `SourceType.EXTERNAL`, `ProjectLayout.WIDE`

**Rate limiting**

- [x] `client_ip` replaces the stock resolver, which raised behind a unix socket
      and was 500ing every enquiry submission in production
- [x] Trusted header is configuration; Cloudflare needs `HTTP_CF_CONNECTING_IP`
- [x] Login limited per IP **and** per account; only failures count
- [x] Refresh and password change limited
- [x] `CACHE_URL` — production refuses to boot on a per-process cache
- [x] Every rate an env var; `django_ratelimit` installed so its checks run
