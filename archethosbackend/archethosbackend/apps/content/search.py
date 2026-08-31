"""
Public site search.

PostgreSQL full-text, deliberately not Elasticsearch: the corpus is a few hundred
rows of an architecture studio's own content, and a second datastore to run,
sync and keep consistent would cost far more than it returns here.

Two passes, because they fail differently:

  * **Full-text** against the weighted tsvector. Handles stemming, so "designs"
    finds "design", and ranks a title match above a body mention.
  * **Trigram similarity** on the title, as a fallback. Full-text tokenises, so a
    misspelling like "architectre" produces a token that matches nothing at all;
    trigram distance still finds "Architecture". Only consulted when full-text
    returns nothing, so it never dilutes good results.
"""

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Q

from .models import BlogPost, Project, Service

#: Below this, a query is too short to be meaningful and matches almost anything.
MIN_QUERY_LENGTH = 2

#: How similar a title must be to count as a typo of the query, 0-1.
TRIGRAM_THRESHOLD = 0.3

DEFAULT_LIMIT = 10
MAX_LIMIT = 50


def search_all(query, limit=DEFAULT_LIMIT):
    """Search live content across all three types.

    Returns `{"projects": [...], "services": [...], "blogs": [...]}` of model
    instances, ranked. Never returns draft, scheduled or archived rows: every
    queryset starts from `.live()`.
    """
    query = (query or "").strip()
    if len(query) < MIN_QUERY_LENGTH:
        return {"projects": [], "services": [], "blogs": []}

    limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))

    return {
        "projects": _search(
            Project.objects.live().select_related("featured_image"), query, limit
        ),
        "services": _search(
            Service.objects.live().select_related("featured_image", "icon"), query, limit
        ),
        "blogs": _search(
            BlogPost.objects.live().select_related("featured_image", "category"),
            query,
            limit,
        ),
    }


def _search(queryset, query, limit):
    # `websearch` accepts what people actually type — quoted phrases, OR, -word —
    # and never raises on malformed input, unlike `plainto_tsquery`.
    search_query = SearchQuery(query, search_type="websearch", config="english")

    ranked = (
        queryset.filter(search_vector=search_query)
        .annotate(rank=SearchRank(F("search_vector"), search_query))
        .order_by("-rank", "-published_at", "-id")
    )

    results = list(ranked[:limit])
    if results:
        return results

    return _fuzzy(queryset, query, limit)


def _fuzzy(queryset, query, limit):
    """Trigram fallback for misspellings full-text cannot reach."""
    from django.contrib.postgres.search import TrigramSimilarity

    return list(
        queryset.annotate(similarity=TrigramSimilarity("title", query))
        .filter(similarity__gt=TRIGRAM_THRESHOLD)
        .order_by("-similarity", "-id")[:limit]
    )
