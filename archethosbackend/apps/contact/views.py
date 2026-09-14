from drf_spectacular.utils import extend_schema
from rest_framework import generics

from .models import ContactPage
from .serializers import ContactPageSerializer


@extend_schema(tags=["Contact page"])
class ContactPageAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = ContactPageSerializer

    def get_object(self):
        page, _ = ContactPage.objects.get_or_create(pk=ContactPage.SINGLETON_PK)
        return page
