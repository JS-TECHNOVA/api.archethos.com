from django.urls import path

from .views import (
    ServiceDetailAPIView, ServiceListCreateAPIView, ServicesPageAPIView,
    ServicesWorkProcessDetailAPIView, ServicesWorkProcessListCreateAPIView,
)


urlpatterns = [
    path("services/page/", ServicesPageAPIView.as_view()),
    path("services/", ServiceListCreateAPIView.as_view()),
    path("services/<int:pk>/", ServiceDetailAPIView.as_view()),
    path("services/<int:service_id>/work-processes/", ServicesWorkProcessListCreateAPIView.as_view()),
    path("services/<int:service_id>/work-processes/<int:pk>/", ServicesWorkProcessDetailAPIView.as_view()),
]
