from drf_spectacular.utils import extend_schema
from rest_framework import generics

from .models import Service, ServiceWorkStage, ServicesGallery, ServicesPage
from .serializers import ServiceSerializer, ServiceWorkStageSerializer, ServicesGallerySerializer, ServicesPageSerializer


@extend_schema(tags=["Services"])
class ServiceListCreateAPIView(generics.ListCreateAPIView):
    queryset = Service.objects.select_related("image").prefetch_related("gallery__asset", "work_stages__media")
    serializer_class = ServiceSerializer


@extend_schema(tags=["Services"])
class ServiceDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Service.objects.select_related("image").prefetch_related("gallery__asset", "work_stages__media")
    serializer_class = ServiceSerializer


@extend_schema(tags=["Service work stages"])
class ServiceWorkStageListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ServiceWorkStageSerializer

    def get_queryset(self):
        return ServiceWorkStage.objects.filter(service_id=self.kwargs["service_id"]).select_related("media")

    def perform_create(self, serializer):
        serializer.save(service_id=self.kwargs["service_id"])


@extend_schema(tags=["Service work stages"])
class ServiceWorkStageDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ServiceWorkStageSerializer

    def get_queryset(self):
        return ServiceWorkStage.objects.filter(service_id=self.kwargs["service_id"]).select_related("media")


@extend_schema(tags=["Services gallery"])
class ServicesGalleryListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ServicesGallerySerializer

    def get_queryset(self):
        return ServicesGallery.objects.filter(service_id=self.kwargs["service_id"]).select_related("asset")

    def perform_create(self, serializer):
        serializer.save(service_id=self.kwargs["service_id"])


@extend_schema(tags=["Services gallery"])
class ServicesGalleryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ServicesGallerySerializer

    def get_queryset(self):
        return ServicesGallery.objects.filter(service_id=self.kwargs["service_id"]).select_related("asset")


@extend_schema(tags=["Services page"])
class ServicesPageAPIView(generics.RetrieveUpdateAPIView):
    queryset = ServicesPage.objects.select_related("hero_image")
    serializer_class = ServicesPageSerializer

    def get_object(self):
        page, _ = ServicesPage.objects.get_or_create(pk=ServicesPage.SINGLETON_PK)
        return page
