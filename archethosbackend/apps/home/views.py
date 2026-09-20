from drf_spectacular.utils import extend_schema
from django.db import transaction
from rest_framework import generics

from .models import HomePage, Slider
from .serializers import HomePageSerializer, SliderSerializer


@extend_schema(tags=["Sliders"])
class SliderListCreateAPIView(generics.ListCreateAPIView):
    queryset = Slider.objects.select_related("media")
    serializer_class = SliderSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        slider = serializer.save()
        homepage, _ = HomePage.objects.get_or_create(pk=HomePage.SINGLETON_PK)
        homepage.sliders.add(slider)


@extend_schema(tags=["Sliders"])
class SliderDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Slider.objects.select_related("media")
    serializer_class = SliderSerializer

    @transaction.atomic
    def perform_destroy(self, instance):
        homepage, _ = HomePage.objects.get_or_create(pk=HomePage.SINGLETON_PK)
        homepage.sliders.remove(instance)
        instance.delete()


@extend_schema(tags=["Home page"])
class HomePageAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = HomePageSerializer

    def get_object(self):
        page, _ = HomePage.objects.prefetch_related("sliders").get_or_create(pk=HomePage.SINGLETON_PK)
        return page

