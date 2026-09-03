"""
Company — the site-wide settings block.

Header, footer, contacts and the global SEO defaults. Not a page: every page
renders it, so it belongs beside them rather than inside any one of them.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from archethosbackend.apps.api.fields import MediaDetailField, MediaReferenceField

from ..models import Company
from ..models.company import (
    validate_contacts,
    validate_footer_groups,
    validate_link_list,
    validate_string_map,
)

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
