from rest_framework import serializers

from apps.home.serializers import SliderSerializer
from apps.media_library.serializers import MediaAssetSerializer

from .models import ContactPage


class ContactPageSerializer(serializers.ModelSerializer):
    slider_detail = SliderSerializer(source="slider", read_only=True)
    sidebar_image_detail = MediaAssetSerializer(source="sidebar_image", read_only=True)

    class Meta:
        model = ContactPage
        fields = "__all__"
