from rest_framework import serializers

from apps.core.models import Company

from .shared_serializer import PublicMediaSerializer


class PublicCompanySerializer(serializers.ModelSerializer):
    logo_detail = PublicMediaSerializer(source="logo", read_only=True)
    icon_detail = PublicMediaSerializer(source="icon", read_only=True)

    class Meta:
        model = Company
        fields = [
            "name", "tagline", "gst", "address", "whatsapp_link", "header_links", "footer_links", "locations",
            "contacts", "socials", "logo", "logo_detail", "icon", "icon_detail", "meta_title",
            "meta_description", "meta_keywords", "head_inject_code", "body_inject_code",
        ]
