"""
Loading a whole page in a bounded number of queries.

A page is one row plus up to eleven section rows plus their item collections
plus the master data those items point at. Fetched naively that is a query per
item — the classic N+1, and the reason the aggregate endpoint needs a selector
rather than a bare `.get()`.

The plan is derived from the models rather than hand-written per page:

  * every section is a `OneToOneField` on the page  → one `select_related` join,
    so the page and all of its sections arrive in a single query;
  * every item collection is a reverse FK on a section → one `prefetch_related`
    each, with the master-data FK joined in;
  * media is joined wherever a section or item references it.

That makes the cost a function of how many *kinds* of thing a page has, not how
many rows are in them. Adding a fiftieth gallery image costs nothing.
"""

from django.db import models


def _media_fields(model):
    """Forward FKs on `model` that point at a MediaAsset."""
    return [
        field.name
        for field in model._meta.get_fields()
        if getattr(field, "many_to_one", False)
        and field.related_model is not None
        and field.related_model._meta.label == "media_library.MediaAsset"
    ]


def _related_fields(model):
    """Forward FKs on an item model, other than its parent section.

    These are the master-data links — `counter`, `service`, `location` — that
    have to be joined or the item list re-queries once per row.
    """
    return [
        field.name
        for field in model._meta.get_fields()
        if getattr(field, "many_to_one", False)
        and field.related_model is not None
        and not field.related_model._meta.label.startswith("pages.")
    ]


def _item_joins(item_model):
    """Everything an item row needs, two levels deep.

    One level is not enough. Joining `gallery_item` still leaves that record's
    own `image` unfetched, so serializing thirty gallery items costs thirty
    extra queries — an N+1 that hides behind a `select_related` that looks
    correct. The master record's media has to be joined too.
    """
    joins = list(_media_fields(item_model))

    for name in _related_fields(item_model):
        joins.append(name)
        related_model = item_model._meta.get_field(name).related_model
        joins.extend(f"{name}__{media}" for media in _media_fields(related_model))

    return joins


def _section_fields(model):
    """The page's sections, in declaration order — which is render order."""
    return [
        field
        for field in model._meta.get_fields()
        if isinstance(field, models.OneToOneField) and field.concrete
    ]


def build_queryset(model):
    """A queryset that pulls an entire page with its sections and items."""
    select = []
    prefetch = []

    for field in _section_fields(model):
        select.append(field.name)
        section_model = field.related_model

        # Media hanging directly off the section.
        select.extend(
            f"{field.name}__{media}" for media in _media_fields(section_model)
        )

        # Each ordered child collection, with its master data and media joined.
        for child in section_model._meta.get_fields():
            if not (child.one_to_many and child.auto_created):
                continue

            item_model = child.related_model
            joins = _item_joins(item_model)
            related = item_model._default_manager.all()
            if joins:
                related = related.select_related(*set(joins))

            prefetch.append(
                models.Prefetch(
                    f"{field.name}__{child.get_accessor_name()}", queryset=related
                )
            )

    return (
        model.objects.select_related(*select).prefetch_related(*prefetch)
        if select
        else model.objects.all()
    )


def load_page(model):
    """The page row, created empty on first access.

    Auto-creating means an editor opening a page for the first time gets a blank
    form rather than a 404 they cannot act on. The row is inert until published:
    `is_published` defaults to False and the public API will not serve it.
    """
    model.objects.get_or_create(pk=model.SINGLETON_PK)
    return build_queryset(model).get(pk=model.SINGLETON_PK)
