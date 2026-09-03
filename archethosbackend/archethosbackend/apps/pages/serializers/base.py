"""
How a page and its sections are read and written.

One endpoint per page, not one per section. A page's admin screen is a single
form — SEO at the top, then each section in render order — so the API mirrors
that: `GET /api/v1/admin/pages/home/` returns the whole thing and a `PATCH`
writes back whatever the editor touched, atomically.

That shape is only possible because the structure is fixed. There is nothing to
discover at runtime, so the serializer can name every section as a field and
Django can validate the lot in one transaction.
"""

from django.db import transaction
from rest_framework import serializers

from archethosbackend.apps.api.serializers import NestedCollectionsMixin


class SectionSerializer(NestedCollectionsMixin, serializers.ModelSerializer):
    """A section, with its ordered child collections written wholesale.

    All of the mechanics live in `NestedCollectionsMixin`, which a project's
    materials and a service's chapters use too — a section is not a special case
    of owning a list, it is just the most common one.

    Subclasses declare `collections` so the mixin knows which fields are child
    lists rather than ordinary values.
    """


class PageSerializer(serializers.ModelSerializer):
    """A whole page: publish state, SEO, and every section in render order.

    Sections are declared as nested `SectionSerializer` fields on the subclass.
    A section row is created on first write and updated in place after that, so
    an editor never has to create anything before they can type into it.
    """

    def _section_fields(self):
        return [
            (name, field)
            for name, field in self.fields.items()
            if isinstance(field, SectionSerializer)
        ]

    @transaction.atomic
    def update(self, instance, validated_data):
        for name, field in self._section_fields():
            if name not in validated_data:
                continue

            payload = validated_data.pop(name)
            row = getattr(instance, name)

            if row is None:
                # First edit of this section: create the row and hang it off the
                # page. `super().update()` below is what persists the new FK.
                setattr(instance, name, field.create(payload))
            else:
                field.update(row, payload)

        return super().update(instance, validated_data)

    def validate(self, attrs):
        """Refuse to publish a page that is missing a required section (§17).

        Checked here rather than only in `Model.clean()` because the API is the
        only way this ever gets set, and a 400 naming the field is more use to
        the admin than a 500 from a later integrity error.
        """
        attrs = super().validate(attrs)

        publishing = attrs.get(
            "is_published",
            getattr(self.instance, "is_published", False),
        )
        if not publishing:
            return attrs

        model = self.Meta.model
        missing = [
            name
            for name in model.required_sections
            # Present in this payload, or already on the row.
            if name not in attrs
            and (
                self.instance is None
                or getattr(self.instance, f"{name}_id", None) is None
            )
        ]
        if missing:
            raise serializers.ValidationError(
                {
                    name: "This section is required before the page can be published."
                    for name in missing
                }
            )
        return attrs
