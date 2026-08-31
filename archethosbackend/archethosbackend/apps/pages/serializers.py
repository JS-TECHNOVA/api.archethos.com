"""Page, composition and Company serializers."""

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from archethosbackend.apps.api.fields import MediaDetailField, MediaReferenceField
from archethosbackend.apps.api.serializers import SEO_FIELDS
from archethosbackend.apps.sections.models import Section

from .models import (
    Company,
    Page,
    PageSection,
    validate_contacts,
    validate_footer_groups,
    validate_link_list,
    validate_string_map,
)


# ─── Page composition ────────────────────────────────────────────────────────


class PageSectionSerializer(serializers.ModelSerializer):
    """One row of a page's composition, with just enough of the section to
    render the admin list without a per-row query."""

    section_type = serializers.CharField(source="section.section_type", read_only=True)
    internal_label = serializers.CharField(
        source="section.internal_label", read_only=True
    )

    class Meta:
        model = PageSection
        fields = [
            "id", "section", "section_type", "internal_label",
            "section_key", "order", "is_visible",
        ]


class PageSectionWriteSerializer(serializers.ModelSerializer):
    section = serializers.PrimaryKeyRelatedField(queryset=Section.objects.all())

    class Meta:
        model = PageSection
        fields = ["id", "section", "section_key", "order", "is_visible"]

    def validate_section_key(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A section key is required.")
        return value

    def validate(self, attrs):
        page = self.context["page"]
        key = attrs.get("section_key") or getattr(self.instance, "section_key", None)

        # Mirrors unique(page, section_key) so the client gets a field error
        # rather than a database 409.
        clashes = PageSection.objects.filter(page=page, section_key=key)
        if self.instance:
            clashes = clashes.exclude(pk=self.instance.pk)
        if clashes.exists():
            raise serializers.ValidationError(
                {
                    "section_key": [
                        f"'{key}' is already used on this page. Section keys must be "
                        "unique per page — that is what lets one page carry two CTAs."
                    ]
                }
            )
        return attrs

    def create(self, validated_data):
        validated_data["page"] = self.context["page"]
        return super().create(validated_data)


# ─── Pages ───────────────────────────────────────────────────────────────────


class PageListSerializer(serializers.ModelSerializer):
    sections_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Page
        fields = [
            "id", "name", "slug", "status", "published_at",
            "sections_count", "updated_at",
        ]


class PageDetailSerializer(serializers.ModelSerializer):
    og_image = MediaReferenceField(read_only=True)
    og_image_detail = MediaDetailField("og_image")
    page_sections = PageSectionSerializer(many=True, read_only=True)

    class Meta:
        model = Page
        fields = [
            "id", "name", "slug", "status", "published_at",
            "page_sections", "og_image_detail",
            "created_at", "updated_at",
        ] + SEO_FIELDS


class PageWriteSerializer(serializers.ModelSerializer):
    og_image = MediaReferenceField()

    class Meta:
        model = Page
        fields = ["id", "name", "slug", "status", "published_at"] + SEO_FIELDS


# ─── Company ─────────────────────────────────────────────────────────────────

COMPANY_FIELDS = [
    "name", "address", "logo", "favicon",
    "social_urls", "contacts", "header_links", "footer_links",
    "meta_title", "meta_description", "meta_keywords",
]

INJECT_FIELDS = ["head_inject", "body_inject"]


class CompanySerializer(serializers.ModelSerializer):
    logo = MediaReferenceField(read_only=True)
    logo_detail = MediaDetailField("logo")
    favicon = MediaReferenceField(read_only=True)

    class Meta:
        model = Company
        fields = COMPANY_FIELDS + INJECT_FIELDS + ["logo_detail", "updated_at"]


class CompanyWriteSerializer(serializers.ModelSerializer):
    logo = MediaReferenceField()
    favicon = MediaReferenceField()

    class Meta:
        model = Company
        fields = COMPANY_FIELDS + INJECT_FIELDS

    def validate_social_urls(self, value):
        return self._run(validate_string_map, value)

    def validate_contacts(self, value):
        return self._run(validate_contacts, value)

    def validate_header_links(self, value):
        return self._run(validate_link_list, value)

    def validate_footer_links(self, value):
        return self._run(validate_footer_groups, value)

    def validate(self, attrs):
        # head_inject and body_inject are raw markup rendered on every page of
        # the live site: whoever writes them executes JavaScript for every
        # visitor. That is a different level of trust from editing a phone
        # number, so these two fields alone are superuser-only.
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if user is not None and not user.is_superuser:
            for field in INJECT_FIELDS:
                if field in attrs and attrs[field] != getattr(self.instance, field, ""):
                    raise serializers.ValidationError(
                        {
                            field: [
                                "Only a superuser can change injected code. It runs "
                                "on every page of the live site."
                            ]
                        }
                    )
        return attrs

    @staticmethod
    def _run(validator, value):
        try:
            validator(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def to_representation(self, instance):
        return CompanySerializer(instance, context=self.context).data


class PublicCompanySerializer(serializers.ModelSerializer):
    """Independent of the admin serializer (plan §12).

    The inject fields *are* public: the frontend has to render them. Everything
    else here is already visible on the site.
    """

    logo = MediaReferenceField(read_only=True)
    logo_detail = MediaDetailField("logo")
    favicon = MediaReferenceField(read_only=True)

    class Meta:
        model = Company
        fields = COMPANY_FIELDS + INJECT_FIELDS + ["logo_detail"]


# ─── Section usage (deferred from Phase 7 until PageSection existed) ─────────


class SectionUsageSerializer(serializers.Serializer):
    page_id = serializers.IntegerField()
    page_name = serializers.CharField()
    page_slug = serializers.CharField()
    section_key = serializers.CharField()
    is_visible = serializers.BooleanField()
