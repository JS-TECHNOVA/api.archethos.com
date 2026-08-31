"""Shared serializer pieces for sections."""

from rest_framework import serializers

from ..models import Section

#: Fields every section carries, in every admin serializer.
SECTION_BASE_FIELDS = ["id", "section_type", "internal_label"]
SECTION_META_FIELDS = ["created_at", "updated_at"]


class SectionBrowseSerializer(serializers.ModelSerializer):
    """One flat row per section, whatever its type.

    Backs `GET /admin/sections/`, the picker the page-composition UI opens when
    an editor attaches a section to a page. Deliberately type-agnostic: it reads
    the parent table only, so it needs no per-type query.
    """

    section_type_display = serializers.CharField(
        source="get_section_type_display", read_only=True
    )

    class Meta:
        model = Section
        # `used_by_count` joins this row once PageSection exists (Phase 9).
        fields = SECTION_BASE_FIELDS + ["section_type_display", "created_at"]


class BaseSectionListSerializer(serializers.ModelSerializer):
    """Per-type list row. Subclasses only set `Meta.model`."""

    class Meta:
        fields = SECTION_BASE_FIELDS + ["created_at"]


class ItemCountMixin(serializers.Serializer):
    """Adds `items_count` so list rows stay light while still being informative.

    The count comes from an annotation on the view's queryset, not from a
    property, so listing N sections costs one query rather than N.
    """

    items_count = serializers.IntegerField(read_only=True)
