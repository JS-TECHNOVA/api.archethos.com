from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response

from .models import Counter, HomeContentGroup, HomeCountersGroup, HomeGalleryGroup, HomePage, HomeProjectsGroup, HomeServicesGroup, Slider, WorkProcessGroup, WorkProcessStep
from .serializers import CounterSerializer, HomeContentGroupSerializer, HomeCountersGroupSerializer, HomeGalleryGroupSerializer, HomePageSerializer, HomeProjectsGroupSerializer, HomeServicesGroupSerializer, SliderSerializer, WorkProcessGroupSerializer, WorkProcessStepSerializer


@extend_schema(tags=["Sliders"])
class SliderListCreateAPIView(generics.ListCreateAPIView):
    queryset = Slider.objects.select_related("media")
    serializer_class = SliderSerializer


@extend_schema(tags=["Sliders"])
class SliderDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Slider.objects.select_related("media")
    serializer_class = SliderSerializer


@extend_schema(tags=["Counters"])
class CounterListCreateAPIView(generics.ListCreateAPIView):
    queryset = Counter.objects.all()
    serializer_class = CounterSerializer


@extend_schema(tags=["Counters"])
class CounterDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Counter.objects.all()
    serializer_class = CounterSerializer


@extend_schema(tags=["Work process groups"])
class WorkProcessGroupListCreateAPIView(generics.ListCreateAPIView):
    queryset = WorkProcessGroup.objects.prefetch_related("steps")
    serializer_class = WorkProcessGroupSerializer


@extend_schema(tags=["Work process groups"])
class WorkProcessGroupDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorkProcessGroup.objects.prefetch_related("steps")
    serializer_class = WorkProcessGroupSerializer


@extend_schema(tags=["Work process steps"])
class WorkProcessStepListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = WorkProcessStepSerializer

    def get_queryset(self):
        return WorkProcessStep.objects.filter(group_id=self.kwargs["group_id"])

    def perform_create(self, serializer):
        serializer.save(group_id=self.kwargs["group_id"])


@extend_schema(tags=["Work process steps"])
class WorkProcessStepDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = WorkProcessStepSerializer

    def get_queryset(self):
        return WorkProcessStep.objects.filter(group_id=self.kwargs["group_id"])


@extend_schema(tags=["Home page"])
class HomePageAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = HomePageSerializer

    def get_object(self):
        page, _ = HomePage.objects.prefetch_related("sliders").get_or_create(pk=HomePage.SINGLETON_PK)
        return page


class HomeGroupAPIView(generics.RetrieveUpdateAPIView):
    group_model = None
    serializer_class = None

    def get_object(self):
        page, _ = HomePage.objects.get_or_create(pk=HomePage.SINGLETON_PK)
        group, _ = self.group_model.objects.get_or_create(page=page)
        return group


@extend_schema(tags=["Home groups"])
class HomeServicesGroupAPIView(HomeGroupAPIView):
    group_model = HomeServicesGroup
    serializer_class = HomeServicesGroupSerializer


@extend_schema(tags=["Home groups"])
class HomeProjectsGroupAPIView(HomeGroupAPIView):
    group_model = HomeProjectsGroup
    serializer_class = HomeProjectsGroupSerializer


@extend_schema(tags=["Home groups"])
class HomeGalleryGroupAPIView(HomeGroupAPIView):
    group_model = HomeGalleryGroup
    serializer_class = HomeGalleryGroupSerializer


@extend_schema(tags=["Home groups"])
class HomeCountersGroupAPIView(HomeGroupAPIView):
    group_model = HomeCountersGroup
    serializer_class = HomeCountersGroupSerializer


@extend_schema(tags=["Home groups"])
class HomeContentGroupListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = HomeContentGroupSerializer

    def get_queryset(self):
        return HomeContentGroup.objects.filter(page_id=HomePage.SINGLETON_PK).select_related("media", "secondary_media")

    def perform_create(self, serializer):
        page, _ = HomePage.objects.get_or_create(pk=HomePage.SINGLETON_PK)
        serializer.save(page=page)


@extend_schema(tags=["Home groups"])
class HomeContentGroupDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = HomeContentGroupSerializer

    def get_queryset(self):
        return HomeContentGroup.objects.filter(page_id=HomePage.SINGLETON_PK).select_related("media", "secondary_media")


@extend_schema(tags=["Home sliders"])
class HomeSliderManageAPIView(generics.GenericAPIView):
    def post(self, request, pk):
        page, _ = HomePage.objects.get_or_create(pk=HomePage.SINGLETON_PK)
        page.sliders.add(Slider.objects.get(pk=pk))
        return Response(HomePageSerializer(page, context={"request": request}).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        page, _ = HomePage.objects.get_or_create(pk=HomePage.SINGLETON_PK)
        page.sliders.remove(Slider.objects.get(pk=pk))
        return Response(status=status.HTTP_204_NO_CONTENT)
