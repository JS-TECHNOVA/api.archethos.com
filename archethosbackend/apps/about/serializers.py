from rest_framework import serializers

from apps.home.serializers import SliderSerializer
from apps.home.serializers import WorkProcessGroupSerializer
from apps.media_library.serializers import MediaAssetSerializer

from .models import AboutPage


class AboutPageSerializer(serializers.ModelSerializer):
    slider_detail = SliderSerializer(source="slider", read_only=True)
    work_process_group_detail = WorkProcessGroupSerializer(source="work_process_group", read_only=True)
    studio_image_detail = MediaAssetSerializer(source="studio_image", read_only=True)
    founder_image_detail = MediaAssetSerializer(source="founder_image", read_only=True)
    philosophy_image_detail = MediaAssetSerializer(source="philosophy_image", read_only=True)
    cta_image_detail = MediaAssetSerializer(source="cta_image", read_only=True)
    class Meta:
        model = AboutPage
        fields = "__all__"
