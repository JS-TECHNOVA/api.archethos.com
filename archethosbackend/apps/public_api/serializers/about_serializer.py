from rest_framework import serializers

from apps.about.models import AboutPage

from .home_serializer import PublicSliderSerializer
from .home_serializer import PublicWorkProcessGroupSerializer
from .shared_serializer import PublicMediaSerializer


class PublicAboutPageSerializer(serializers.ModelSerializer):
    slider_detail = PublicSliderSerializer(source="slider", read_only=True)
    work_process_group_detail = PublicWorkProcessGroupSerializer(source="work_process_group", read_only=True)
    studio_image_detail = PublicMediaSerializer(source="studio_image", read_only=True)
    founder_image_detail = PublicMediaSerializer(source="founder_image", read_only=True)
    philosophy_image_detail = PublicMediaSerializer(source="philosophy_image", read_only=True)
    cta_image_detail = PublicMediaSerializer(source="cta_image", read_only=True)

    class Meta:
        model = AboutPage
        fields = "__all__"
