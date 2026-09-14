from rest_framework import serializers

from apps.media_library.serializers import MediaAssetSerializer

from .models import Counter, HomeContentGroup, HomeCountersGroup, HomeGalleryGroup, HomePage, HomeProjectsGroup, HomeServicesGroup, Slider, WorkProcessGroup, WorkProcessStep


class SliderSerializer(serializers.ModelSerializer):
    media_detail = MediaAssetSerializer(source="media", read_only=True)

    class Meta:
        model = Slider
        fields = "__all__"


class CounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Counter
        fields = "__all__"


class WorkProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkProcessStep
        fields = ["id", "group", "number", "title", "description", "order"]
        read_only_fields = ["group"]


class WorkProcessGroupSerializer(serializers.ModelSerializer):
    steps = WorkProcessStepSerializer(many=True, read_only=True)

    class Meta:
        model = WorkProcessGroup
        fields = ["id", "eyebrow", "title", "description", "is_visible", "steps"]


class HomeServicesGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeServicesGroup
        fields = "__all__"
        read_only_fields = ["page"]


class HomeProjectsGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeProjectsGroup
        fields = "__all__"
        read_only_fields = ["page"]


class HomeGalleryGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeGalleryGroup
        fields = "__all__"
        read_only_fields = ["page"]


class HomeCountersGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeCountersGroup
        fields = "__all__"
        read_only_fields = ["page"]


class HomeContentGroupSerializer(serializers.ModelSerializer):
    media_detail = MediaAssetSerializer(source="media", read_only=True)
    secondary_media_detail = MediaAssetSerializer(source="secondary_media", read_only=True)

    class Meta:
        model = HomeContentGroup
        fields = "__all__"
        read_only_fields = ["page"]


class HomePageSerializer(serializers.ModelSerializer):
    sliders_detail = SliderSerializer(source="sliders", many=True, read_only=True)
    services_group = HomeServicesGroupSerializer(read_only=True)
    projects_group = HomeProjectsGroupSerializer(read_only=True)
    gallery_group = HomeGalleryGroupSerializer(read_only=True)
    counters_group = HomeCountersGroupSerializer(read_only=True)
    work_process_group_detail = WorkProcessGroupSerializer(source="work_process_group", read_only=True)
    content_groups = HomeContentGroupSerializer(many=True, read_only=True)

    class Meta:
        model = HomePage
        fields = ["id", "sliders", "sliders_detail", "featured_project", "featured_service", "selected_gallery_items", "work_process_group", "work_process_group_detail", "meta_title", "meta_description", "meta_keywords", "services_group", "projects_group", "gallery_group", "counters_group", "content_groups"]
