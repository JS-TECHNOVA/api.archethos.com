"""
Bulk registration for Django's admin.

⚠️ This is a developer and superuser-rescue tool, not the CMS. The admin the
studio uses is the Next.js one, which goes through the serializers — and the
serializers are where the rules live: media is validated on upload, `head_inject`
is superuser-only, a page cannot be published with a required section missing.
**None of that applies here.** Django's admin writes straight to the model, so
treat it as a database browser with a login on it.

Registration is generated rather than hand-written because there are 72 models
and none of them wants a bespoke screen. What the generated `ModelAdmin` adds is
only what makes a list page readable — a couple of identifying columns, a filter
where there is an obvious one, and a search box over the text fields. Anything
beyond that belongs in the real admin.
"""

from django.apps import apps
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from django.db import models

#: Tried in order for the "what is this row" column.
IDENTIFYING = (
    "title",
    "name",
    "heading",
    "city",
    "subtitle",
    "question",
    "label",
    "eyebrow",
)

#: Appended after the identifying columns when the model has them.
CONTEXT = ("status", "is_published", "is_featured", "order", "updated_at")

#: Only offered as filters when the field is a boolean or has choices — a plain
#: CharField filter would list every distinct value in the table.
FILTERABLE = (
    "status",
    "category",
    "kind",
    "media_type",
    "source_type",
    "media_location",
    "is_published",
    "is_featured",
    "is_read",
)

TEXT_FIELDS = (models.CharField, models.TextField)


def _fields(model):
    """Concrete, editable fields by name -> field."""
    return {
        field.name: field
        for field in model._meta.get_fields()
        if getattr(field, "concrete", False) and not field.many_to_many
    }


def _build_admin(model):
    fields = _fields(model)

    identifying = [name for name in IDENTIFYING if name in fields][:2]
    context = [name for name in CONTEXT if name in fields]
    list_display = ["__str__", *identifying, *context]

    list_filter = [
        name
        for name in FILTERABLE
        if name in fields
        and (
            isinstance(fields[name], models.BooleanField)
            or getattr(fields[name], "choices", None)
        )
    ]

    search_fields = [
        name
        for name in (*IDENTIFYING, "slug", "alt_text", "caption")
        if name in fields and isinstance(fields[name], TEXT_FIELDS)
    ]

    return type(
        f"{model.__name__}Admin",
        (admin.ModelAdmin,),
        {
            "list_display": list_display,
            "list_filter": list_filter,
            "search_fields": search_fields,
            # Several __str__ implementations reach through a FK — a project's
            # material prints its project's title. Without this the list page
            # costs one query per row.
            "list_select_related": True,
        },
    )


def register_app(app_label):
    """Register every model in an app, skipping any already registered."""
    for model in apps.get_app_config(app_label).get_models():
        try:
            admin.site.register(model, _build_admin(model))
        except AlreadyRegistered:
            pass
