from django.urls import path

from .views import HomePageAPIView, SliderDetailAPIView, SliderListCreateAPIView


urlpatterns = [
    path("home/slider/", SliderListCreateAPIView.as_view()),
    path("home/slider/<int:pk>/", SliderDetailAPIView.as_view()),
    path("home/page/", HomePageAPIView.as_view()),
]
