from rest_framework import serializers

from apps.media_library.serializers import MediaAssetSerializer

from .models import HomePage, Slider


class SliderSerializer(serializers.ModelSerializer):
    media_detail = MediaAssetSerializer(source="media", read_only=True)

    class Meta:
        model = Slider
        fields = "__all__"


class HomePageSerializer(serializers.ModelSerializer):
    sliders_detail = SliderSerializer(source="sliders", many=True, read_only=True)
    class Meta:
        model = HomePage
        fields = [
            "id", "sliders", "sliders_detail", "featured_project", "featured_service",
            "home_counters", "design_build_process", "selected_work_title", "selected_work_description",
            "selected_work", "gallery", "meta_title", "meta_description", "meta_keywords",
        ]
