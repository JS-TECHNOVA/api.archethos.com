from drf_spectacular.utils import extend_schema
from rest_framework import generics

from .models import AboutPage
from .serializers import AboutPageSerializer


@extend_schema(tags=["About page"])
class AboutPageAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = AboutPageSerializer

    def get_object(self):
        page, _ = AboutPage.objects.select_related("slider").get_or_create(pk=AboutPage.SINGLETON_PK)
        return page

