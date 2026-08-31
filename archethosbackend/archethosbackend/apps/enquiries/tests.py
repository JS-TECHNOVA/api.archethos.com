"""
Search and enquiry tests.

The public enquiry endpoint is the only place an anonymous visitor writes to the
database, so its defences get the most attention.
"""

from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from archethosbackend.apps.content.models import BlogPost, Project, Service
from archethosbackend.apps.core.models import PublishStatus

from .models import Enquiry, EnquiryType


class EnquiryTestCase(TestCase):
    password = "correct-horse-battery-staple"

    def make_user(self, email, *, superuser=False, permissions=()):
        user = User.objects.create_user(
            username=email, email=email, password=self.password
        )
        if superuser:
            user.is_superuser = user.is_staff = True
            user.save(update_fields=["is_superuser", "is_staff"])
        if permissions:
            user.user_permissions.add(
                *Permission.objects.filter(codename__in=permissions)
            )
        return User.objects.get(pk=user.pk)

    def client_for(self, user):
        client = Client()
        response = client.post(
            reverse("v1:auth:login"),
            {"email": user.email, "password": self.password},
            content_type="application/json",
        )
        assert response.status_code == 200, response.content
        return client

    def admin_client(self):
        return self.client_for(self.make_user("root@archethos.test", superuser=True))

    def submit(self, client=None, **overrides):
        payload = {
            "name": "Asha Verma",
            "email": "asha@example.test",
            "message": "We are planning a house in Lucknow.",
        }
        payload.update(overrides)
        return (client or Client()).post(
            reverse("v1:public:enquiry-submit"), payload, content_type="application/json"
        )


# ─── Public submission ───────────────────────────────────────────────────────


# Rate limiting is disabled by default here so it does not bleed between tests;
# the tests that exercise it re-enable it explicitly.
@override_settings(RATELIMIT_ENABLE=False)
class EnquirySubmitTests(EnquiryTestCase):
    def test_anonymous_can_submit(self):
        response = self.submit()
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Enquiry.objects.count(), 1)

        enquiry = Enquiry.objects.first()
        self.assertEqual(enquiry.name, "Asha Verma")
        self.assertEqual(enquiry.form_type, EnquiryType.CONTACT)
        self.assertFalse(enquiry.is_read)

    def test_name_email_and_message_are_required(self):
        for missing in ("name", "email", "message"):
            with self.subTest(missing=missing):
                payload = {
                    "name": "A", "email": "a@example.test", "message": "Hi"
                }
                payload.pop(missing)
                response = Client().post(
                    reverse("v1:public:enquiry-submit"),
                    payload,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn(missing, response.json()["errors"])

    def test_invalid_email_is_rejected(self):
        self.assertEqual(self.submit(email="not-an-email").status_code, 400)

    def test_extra_carries_form_specific_fields_without_a_migration(self):
        response = self.submit(
            form_type="PROJECT",
            extra={"budget": "50-75L", "plot_size": "2400 sqft", "timeline": "2027"},
        )
        self.assertEqual(response.status_code, 201)

        enquiry = Enquiry.objects.first()
        self.assertEqual(enquiry.extra["budget"], "50-75L")
        self.assertEqual(enquiry.form_type, EnquiryType.PROJECT)

    def test_oversized_extra_is_rejected(self):
        response = self.submit(extra={f"k{i}": "v" for i in range(40)})
        self.assertEqual(response.status_code, 400)
        self.assertIn("extra", response.json()["errors"])

        response = self.submit(extra={"note": "x" * 5000})
        self.assertEqual(response.status_code, 400)

    def test_source_page_is_recorded(self):
        self.submit(source_page="/vastu")
        self.assertEqual(Enquiry.objects.first().source_page, "/vastu")

    # ── honeypot ──

    def test_honeypot_submission_is_discarded_silently(self):
        response = self.submit(website="http://spam.example")

        # Identical to a success: telling a bot it was caught only teaches it to
        # avoid the trap next time.
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["success"])
        self.assertEqual(Enquiry.objects.count(), 0)

    def test_an_empty_honeypot_is_fine(self):
        self.assertEqual(self.submit(website="").status_code, 201)
        self.assertEqual(Enquiry.objects.count(), 1)

    def test_the_honeypot_value_is_never_echoed_back(self):
        response = self.submit(website="http://spam.example")
        self.assertNotIn("spam.example", response.content.decode())

    # ── the endpoint is write-only ──

    def test_the_public_endpoint_does_not_list_enquiries(self):
        self.submit()
        self.assertEqual(
            Client().get(reverse("v1:public:enquiry-submit")).status_code, 405
        )


class EnquiryRateLimitTests(EnquiryTestCase):
    @override_settings(RATELIMIT_ENABLE=True)
    def test_repeated_submissions_are_throttled(self):
        from django.core.cache import cache

        cache.clear()
        client = Client()

        accepted = 0
        for _ in range(15):
            response = self.submit(client)
            if response.status_code == 201:
                accepted += 1
            else:
                self.assertEqual(response.status_code, 429)
                self.assertEqual(response.json()["code"], "throttled")
                break

        self.assertEqual(accepted, 10, "the limit is 10/h per IP")
        self.assertEqual(Enquiry.objects.count(), 10)
        cache.clear()


# ─── Admin ───────────────────────────────────────────────────────────────────


@override_settings(RATELIMIT_ENABLE=False)
class EnquiryAdminTests(EnquiryTestCase):
    def setUp(self):
        self.client_ = self.admin_client()
        for i in range(3):
            Enquiry.objects.create(
                name=f"Person {i}",
                email=f"p{i}@example.test",
                message="Hello",
                form_type=EnquiryType.CONTACT if i < 2 else EnquiryType.CAREER,
                is_read=(i == 0),
            )

    def test_list_is_paginated_and_filterable(self):
        body = self.client_.get(reverse("v1:admin:enquiry-list")).json()
        self.assertEqual(body["pagination"]["total_items"], 3)

        unread = self.client_.get(
            reverse("v1:admin:enquiry-list") + "?is_read=false"
        ).json()
        self.assertEqual(unread["pagination"]["total_items"], 2)

        career = self.client_.get(
            reverse("v1:admin:enquiry-list") + "?form_type=CAREER"
        ).json()
        self.assertEqual(career["pagination"]["total_items"], 1)

    def test_search_matches_name_and_message(self):
        body = self.client_.get(
            reverse("v1:admin:enquiry-list") + "?search=Person 1"
        ).json()
        self.assertEqual(body["pagination"]["total_items"], 1)

    def test_mark_read(self):
        enquiry = Enquiry.objects.filter(is_read=False).first()
        response = self.client_.patch(
            reverse("v1:admin:enquiry-detail", args=[enquiry.pk]),
            {"is_read": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        enquiry.refresh_from_db()
        self.assertTrue(enquiry.is_read)

    def test_submitted_content_is_immutable(self):
        """An enquiry is a record of what someone actually sent."""
        enquiry = Enquiry.objects.first()
        self.client_.patch(
            reverse("v1:admin:enquiry-detail", args=[enquiry.pk]),
            {"is_read": True, "message": "rewritten", "email": "hacked@example.test"},
            content_type="application/json",
        )
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.message, "Hello")
        self.assertNotEqual(enquiry.email, "hacked@example.test")

    def test_enquiries_cannot_be_created_through_the_admin_api(self):
        response = self.client_.post(
            reverse("v1:admin:enquiry-list"),
            {"name": "X", "email": "x@example.test", "message": "Y"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 405)

    def test_delete(self):
        enquiry = Enquiry.objects.first()
        self.assertEqual(
            self.client_.delete(
                reverse("v1:admin:enquiry-detail", args=[enquiry.pk])
            ).status_code,
            204,
        )

    def test_unread_count(self):
        body = self.client_.get(reverse("v1:admin:enquiry-unread-count")).json()
        self.assertEqual(body["data"]["unread"], 2)

    def test_unread_count_is_zero_without_permission(self):
        user = self.make_user("nobody@archethos.test")
        body = self.client_for(user).get(
            reverse("v1:admin:enquiry-unread-count")
        ).json()
        self.assertEqual(body["data"]["unread"], 0)

    def test_listing_requires_permission(self):
        user = self.make_user("nobody@archethos.test")
        self.assertEqual(
            self.client_for(user).get(reverse("v1:admin:enquiry-list")).status_code, 403
        )

    def test_anonymous_cannot_read_enquiries(self):
        self.assertEqual(Client().get(reverse("v1:admin:enquiry-list")).status_code, 401)


# ─── Search ──────────────────────────────────────────────────────────────────


class SearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.villa = Project.objects.create(
            title="Courtyard Villa",
            short_description="A courtyard house in Lucknow",
            description="Brick and concrete, planned around a central court.",
            location="Lucknow",
            status=PublishStatus.PUBLISHED,
        )
        cls.draft = Project.objects.create(
            title="Secret Courtyard Project",
            description="Unannounced courtyard scheme.",
        )
        cls.service = Service.objects.create(
            title="Vastu Consultancy",
            short_description="Vastu guidance for residential architecture",
            status=PublishStatus.PUBLISHED,
        )
        cls.post = BlogPost.objects.create(
            title="Designing for Light",
            excerpt="How daylight shapes an architecture practice",
            content="Long article about light in architecture and courtyards.",
            status=PublishStatus.PUBLISHED,
        )

    def search(self, q, **params):
        query = f"?q={q}"
        for key, value in params.items():
            query += f"&{key}={value}"
        return Client().get(reverse("v1:public:search") + query).json()["data"]

    def test_finds_matches_across_all_three_types(self):
        body = self.search("architecture")
        self.assertGreaterEqual(body["counts"]["services"], 1)
        self.assertGreaterEqual(body["counts"]["blogs"], 1)

    def test_matches_a_project_by_title_and_location(self):
        self.assertEqual(
            [p["title"] for p in self.search("courtyard")["results"]["projects"]],
            ["Courtyard Villa"],
        )
        self.assertEqual(
            [p["title"] for p in self.search("Lucknow")["results"]["projects"]],
            ["Courtyard Villa"],
        )

    def test_draft_content_is_never_returned(self):
        body = self.search("courtyard")
        titles = [p["title"] for p in body["results"]["projects"]]
        self.assertNotIn("Secret Courtyard Project", titles)

    def test_stemming_works(self):
        """"designing" and "designs" must both find "Designing for Light"."""
        for term in ("design", "designs", "designing"):
            with self.subTest(term=term):
                self.assertGreaterEqual(self.search(term)["counts"]["blogs"], 1)

    def test_a_misspelling_falls_back_to_trigram_similarity(self):
        """Full-text tokenises, so "courtyrd" matches no token at all."""
        body = self.search("courtyrd")
        self.assertEqual(
            [p["title"] for p in body["results"]["projects"]], ["Courtyard Villa"]
        )

    def test_a_short_query_returns_nothing(self):
        body = self.search("a")
        self.assertEqual(body["counts"], {"projects": 0, "services": 0, "blogs": 0})

    def test_a_missing_query_returns_empty_results(self):
        body = Client().get(reverse("v1:public:search")).json()["data"]
        self.assertEqual(body["query"], "")
        self.assertEqual(body["counts"]["projects"], 0)

    def test_nonsense_returns_no_results_rather_than_an_error(self):
        body = self.search("zzzzqqqxyzzy")
        self.assertEqual(body["counts"], {"projects": 0, "services": 0, "blogs": 0})

    def test_websearch_operators_do_not_crash(self):
        """`websearch_to_tsquery` tolerates whatever a person types."""
        for query in ['"exact phrase"', "architecture -villa", "a or b", "((("]:
            with self.subTest(query=query):
                response = Client().get(reverse("v1:public:search") + f"?q={query}")
                self.assertEqual(response.status_code, 200)

    def test_limit_is_honoured_and_capped(self):
        for i in range(12):
            Project.objects.create(
                title=f"Courtyard House {i}", status=PublishStatus.PUBLISHED
            )
        self.assertEqual(len(self.search("courtyard", limit=3)["results"]["projects"]), 3)
        # Default caps at 10 even though 13 match.
        self.assertEqual(len(self.search("courtyard")["results"]["projects"]), 10)

    def test_search_needs_no_authentication(self):
        self.assertEqual(
            Client().get(reverse("v1:public:search") + "?q=villa").status_code, 200
        )

    def test_the_vector_updates_when_content_changes(self):
        self.assertEqual(self.search("brutalist")["counts"]["projects"], 0)

        self.villa.description = "A brutalist courtyard house."
        self.villa.save()

        self.assertEqual(self.search("brutalist")["counts"]["projects"], 1)

    def test_rebuild_command_repairs_vectors_after_a_bulk_update(self):
        """`update()` bypasses save(), so the vector goes stale by design.

        Tested against `description` rather than `title`: a stale title is
        masked by the trigram fallback, which reads the live column, so only a
        body-only term actually exposes the staleness.
        """
        from io import StringIO

        from django.core.management import call_command

        Project.objects.filter(pk=self.villa.pk).update(
            description="Finished in terracotta screens."
        )
        self.assertEqual(self.search("terracotta")["counts"]["projects"], 0)

        call_command("rebuild_search_index", stdout=StringIO())
        self.assertEqual(self.search("terracotta")["counts"]["projects"], 1)

    def test_a_stale_title_is_still_found_via_the_trigram_fallback(self):
        """A useful side effect: bulk-renaming stays searchable by title even
        before the index is rebuilt."""
        Project.objects.filter(pk=self.villa.pk).update(title="Terracotta Pavilion")
        self.assertEqual(
            [p["title"] for p in self.search("terracotta")["results"]["projects"]],
            ["Terracotta Pavilion"],
        )
