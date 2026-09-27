from rest_framework import serializers

from apps.contact.models import ContactPage
from apps.core.models import Company

from .company_serializer import PublicCompanySerializer
from .shared_serializer import PublicMediaSerializer


class PublicContactPageSerializer(serializers.ModelSerializer):
    hero_media_detail = PublicMediaSerializer(source="hero_media", read_only=True)
    sidebar_image_detail = PublicMediaSerializer(source="sidebar_image", read_only=True)
    company = serializers.SerializerMethodField()

    def get_company(self, obj):
        company, _ = Company.objects.select_related("logo", "icon").get_or_create(pk=Company.SINGLETON_PK)
        return PublicCompanySerializer(company, context=self.context).data

    class Meta:
        model = ContactPage
        fields = [
            "hero_eyebrow", "hero_title", "hero_description", "hero_media", "hero_media_detail",
            "sidebar_image", "sidebar_image_detail",
            "next_section", "meta_title", "meta_description",
            "meta_keywords", "company",
        ]
