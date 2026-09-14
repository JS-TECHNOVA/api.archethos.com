from drf_spectacular.utils import extend_schema
from rest_framework import generics

from .models import Service, ServicesPage, ServicesWorkProcess
from .serializers import ServiceSerializer, ServicesPageSerializer, ServicesWorkProcessSerializer


@extend_schema(tags=["Services"])
class ServiceListCreateAPIView(generics.ListCreateAPIView):
    queryset = Service.objects.select_related("hero_image", "index_image").prefetch_related("gallery", "work_processes")
    serializer_class = ServiceSerializer


@extend_schema(tags=["Services"])
class ServiceDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Service.objects.select_related("hero_image", "index_image").prefetch_related("gallery", "work_processes")
    serializer_class = ServiceSerializer


@extend_schema(tags=["Service work processes"])
class ServicesWorkProcessListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ServicesWorkProcessSerializer

    def get_queryset(self):
        return ServicesWorkProcess.objects.filter(service_id=self.kwargs["service_id"])

    def perform_create(self, serializer):
        serializer.save(service_id=self.kwargs["service_id"])


@extend_schema(tags=["Service work processes"])
class ServicesWorkProcessDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ServicesWorkProcessSerializer

    def get_queryset(self):
        return ServicesWorkProcess.objects.filter(service_id=self.kwargs["service_id"])


@extend_schema(tags=["Services page"])
class ServicesPageAPIView(generics.RetrieveUpdateAPIView):
    queryset = ServicesPage.objects.select_related("hero_image")
    serializer_class = ServicesPageSerializer

    def get_object(self):
        page, _ = ServicesPage.objects.get_or_create(pk=ServicesPage.SINGLETON_PK)
        return page
