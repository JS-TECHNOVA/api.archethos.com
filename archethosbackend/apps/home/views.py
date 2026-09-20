from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response

from .models import HomePage, Slider
from .serializers import HomePageSerializer, SliderSerializer


@extend_schema(tags=["Sliders"])
class SliderListCreateAPIView(generics.ListCreateAPIView):
    queryset = Slider.objects.select_related("media")
    serializer_class = SliderSerializer


@extend_schema(tags=["Sliders"])
class SliderDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Slider.objects.select_related("media")
    serializer_class = SliderSerializer


@extend_schema(tags=["Home page"])
class HomePageAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = HomePageSerializer

    def get_object(self):
        page, _ = HomePage.objects.prefetch_related("sliders").get_or_create(pk=HomePage.SINGLETON_PK)
        return page


@extend_schema(tags=["Home sliders"])
class HomeSliderManageAPIView(generics.GenericAPIView):
    serializer_class = HomePageSerializer

    def post(self, request, pk):
        page, _ = HomePage.objects.get_or_create(pk=HomePage.SINGLETON_PK)
        page.sliders.add(Slider.objects.get(pk=pk))
        return Response(HomePageSerializer(page, context={"request": request}).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        page, _ = HomePage.objects.get_or_create(pk=HomePage.SINGLETON_PK)
        page.sliders.remove(Slider.objects.get(pk=pk))
        return Response(status=status.HTTP_204_NO_CONTENT)
