from rest_framework import serializers

from apps.home.models import Counter, HomeContentGroup, HomeCountersGroup, HomeGalleryGroup, HomePage, HomeProjectsGroup, HomeServicesGroup, Slider, WorkProcessGroup, WorkProcessStep

from .gallery_serializer import PublicGalleryItemSerializer
from .projects_serializer import PublicProjectSerializer
from .services_serializer import PublicServiceSerializer
from .shared_serializer import PublicMediaSerializer


class PublicSliderSerializer(serializers.ModelSerializer):
    media_detail = PublicMediaSerializer(source="media", read_only=True)

    class Meta:
        model = Slider
        fields = ["label", "eyebrow", "title", "description", "media", "media_detail", "primary_cta_label", "primary_cta_url", "secondary_cta_label", "secondary_cta_url", "order"]


class PublicWorkProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkProcessStep
        fields = ["number", "title", "description", "order"]


class PublicWorkProcessGroupSerializer(serializers.ModelSerializer):
    steps = PublicWorkProcessStepSerializer(many=True, read_only=True)

    class Meta:
        model = WorkProcessGroup
        fields = ["eyebrow", "title", "description", "steps"]


class PublicHomeServicesGroupSerializer(serializers.ModelSerializer):
    services = serializers.SerializerMethodField()

    def get_services(self, obj):
        return PublicServiceSerializer(obj.services.filter(is_visible=True), many=True, context=self.context).data

    class Meta:
        model = HomeServicesGroup
        fields = ["eyebrow", "title", "description", "services"]


class PublicHomeProjectsGroupSerializer(serializers.ModelSerializer):
    projects = serializers.SerializerMethodField()

    def get_projects(self, obj):
        return PublicProjectSerializer(obj.projects.filter(status="published"), many=True, context=self.context).data

    class Meta:
        model = HomeProjectsGroup
        fields = ["eyebrow", "title", "description", "projects"]


class PublicHomeGalleryGroupSerializer(serializers.ModelSerializer):
    gallery_items = serializers.SerializerMethodField()

    def get_gallery_items(self, obj):
        return PublicGalleryItemSerializer(obj.gallery_items.filter(is_visible=True), many=True, context=self.context).data

    class Meta:
        model = HomeGalleryGroup
        fields = ["eyebrow", "title", "description", "gallery_items"]


class PublicCounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Counter
        fields = ["value", "label", "description", "order"]


class PublicHomeCountersGroupSerializer(serializers.ModelSerializer):
    counters = serializers.SerializerMethodField()

    def get_counters(self, obj):
        return PublicCounterSerializer(obj.counters.filter(is_visible=True), many=True).data

    class Meta:
        model = HomeCountersGroup
        fields = ["eyebrow", "title", "description", "counters"]


class PublicHomeContentGroupSerializer(serializers.ModelSerializer):
    media_detail = PublicMediaSerializer(source="media", read_only=True)
    secondary_media_detail = PublicMediaSerializer(source="secondary_media", read_only=True)

    class Meta:
        model = HomeContentGroup
        fields = ["group_type", "eyebrow", "title", "description", "content", "media", "media_detail", "secondary_media", "secondary_media_detail", "cta_label", "cta_url", "order"]


class PublicHomePageSerializer(serializers.ModelSerializer):
    sliders = serializers.SerializerMethodField()
    services_group = PublicHomeServicesGroupSerializer(read_only=True)
    projects_group = PublicHomeProjectsGroupSerializer(read_only=True)
    gallery_group = PublicHomeGalleryGroupSerializer(read_only=True)
    counters_group = PublicHomeCountersGroupSerializer(read_only=True)
    featured_project_detail = PublicProjectSerializer(source="featured_project", read_only=True)
    featured_service_detail = PublicServiceSerializer(source="featured_service", read_only=True)
    selected_gallery_items = serializers.SerializerMethodField()
    work_process_group_detail = PublicWorkProcessGroupSerializer(source="work_process_group", read_only=True)
    content_groups = PublicHomeContentGroupSerializer(many=True, read_only=True)

    def get_sliders(self, obj):
        return PublicSliderSerializer(obj.sliders.filter(is_visible=True), many=True, context=self.context).data

    def get_selected_gallery_items(self, obj):
        return PublicGalleryItemSerializer(obj.selected_gallery_items.filter(is_visible=True), many=True, context=self.context).data

    class Meta:
        model = HomePage
        fields = ["meta_title", "meta_description", "meta_keywords", "sliders", "featured_project", "featured_project_detail", "featured_service", "featured_service_detail", "selected_gallery_items", "work_process_group", "work_process_group_detail", "services_group", "projects_group", "gallery_group", "counters_group", "content_groups"]
