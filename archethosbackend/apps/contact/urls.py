from django.urls import path

from .views import ContactPageAPIView


urlpatterns = [path("contact/page/", ContactPageAPIView.as_view())]
