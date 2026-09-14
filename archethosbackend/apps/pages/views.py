from drf_spectacular.utils import extend_schema
from rest_framework import generics

from .models import Page
from .serializers import PageSerializer


@extend_schema(tags=["Custom pages"])
class PageListCreateAPIView(generics.ListCreateAPIView):
    queryset = Page.objects.select_related("hero_image")
    serializer_class = PageSerializer


@extend_schema(tags=["Custom pages"])
class PageDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Page.objects.select_related("hero_image")
    serializer_class = PageSerializer
