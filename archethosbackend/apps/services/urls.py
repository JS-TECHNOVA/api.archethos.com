from django.urls import path

from .views import (
    ServiceDetailAPIView, ServiceListCreateAPIView, ServiceWorkStageDetailAPIView,
    ServiceWorkStageListCreateAPIView, ServicesGalleryDetailAPIView,
    ServicesGalleryListCreateAPIView, ServicesPageAPIView,
)


urlpatterns = [
    path("services/page/", ServicesPageAPIView.as_view()),
    path("services/", ServiceListCreateAPIView.as_view()),
    path("services/<int:pk>/", ServiceDetailAPIView.as_view()),
    path("services/<int:service_id>/work-stages/", ServiceWorkStageListCreateAPIView.as_view()),
    path("services/<int:service_id>/work-stages/<int:pk>/", ServiceWorkStageDetailAPIView.as_view()),
    path("services/<int:service_id>/gallery/", ServicesGalleryListCreateAPIView.as_view()),
    path("services/<int:service_id>/gallery/<int:pk>/", ServicesGalleryDetailAPIView.as_view()),
]
