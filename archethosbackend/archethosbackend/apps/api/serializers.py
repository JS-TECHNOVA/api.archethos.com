"""Serializer pieces shared across every content app."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .fields import MediaReferenceField

#: Every field contributed by core.SEOModel.
SEO_FIELDS = [
    "meta_title",
    "meta_description",
    "meta_keywords",
    "og_title",
    "og_description",
    "og_image",
    "canonical_url",
    "robots_index",
    "robots_follow",
]


class SEOWriteMixin(serializers.Serializer):
    """Adds the SEO block to an admin write serializer.

    `og_image` must go through MediaReferenceField like every other media field,
    or SEO images would be the one place a raw path could sneak into the database.
    """

    og_image = MediaReferenceField(required=False, allow_null=True)


class PublicSEOSerializer(serializers.Serializer):
    """The `seo` block the Next.js frontend puts into its metadata export.

    Emitted as a nested object rather than nine flat keys so a page payload keeps
    page content and page metadata visibly separate.
    """

    meta_title = serializers.CharField(allow_blank=True)
    meta_description = serializers.CharField(allow_blank=True)
    meta_keywords = serializers.CharField(allow_blank=True)
    og_title = serializers.CharField(allow_blank=True)
    og_description = serializers.CharField(allow_blank=True)
    og_image = serializers.SerializerMethodField()
    canonical_url = serializers.CharField(allow_blank=True)
    robots_index = serializers.BooleanField()
    robots_follow = serializers.BooleanField()

    def get_og_image(self, obj) -> str | None:
        asset = getattr(obj, "og_image", None)
        return asset.relative_path if asset else None


@extend_schema_field(PublicSEOSerializer)
class SEOBlockField(serializers.Field):
    """Drop-in `seo` key for a public serializer.

    A plain Field with `source="*"` so the whole instance arrives here and no
    serializer using it needs a `get_seo` method of its own.
    """

    def __init__(self, **kwargs):
        kwargs["read_only"] = True
        kwargs["source"] = "*"
        super().__init__(**kwargs)

    def to_representation(self, instance):
        return PublicSEOSerializer(instance).data


class NestedCollectionsMixin:
    """Write ordered child collections wholesale, in one transaction.

    Used wherever a record owns lists that are edited as part of it — a page's
    section items, a project's materials, a service's chapters. Collections are
    replaced rather than diffed, which has three consequences, all wanted:

      * `order` is the array index, so reordering is "send the array in the new
        order" and needs no separate endpoint;
      * removing an item is omitting it, with no tombstone to chase;
      * a save is idempotent — the same payload twice leaves the same rows.

    Only collections actually present in the payload are touched, so a PATCH
    that omits one leaves it alone rather than emptying it. Sending `[]` is how
    you clear one, and that distinction is the whole reason this is explicit.
    """

    #: serializer field name → related_name on the model.
    collections: dict = {}

    def create(self, validated_data):
        from django.db import transaction

        with transaction.atomic():
            payloads = self._extract_collections(validated_data)
            instance = super().create(validated_data)
            self._write_collections(instance, payloads)
            return instance

    def update(self, instance, validated_data):
        from django.db import transaction

        with transaction.atomic():
            payloads = self._extract_collections(validated_data)
            instance = super().update(instance, validated_data)
            self._write_collections(instance, payloads)
            return instance

    def _extract_collections(self, validated_data):
        return {
            field: validated_data.pop(field)
            for field in self.collections
            if field in validated_data
        }

    def _write_collections(self, instance, payloads):
        for field, rows in payloads.items():
            manager = getattr(instance, self.collections[field])
            model = manager.model
            fk_name = manager.field.name

            manager.all().delete()
            model.objects.bulk_create(
                [
                    model(order=index, **{fk_name: instance}, **row)
                    for index, row in enumerate(rows)
                ]
            )
