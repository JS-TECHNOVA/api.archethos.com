from django.urls import path

from .views import HomePageAPIView, HomeSliderManageAPIView, SliderDetailAPIView, SliderListCreateAPIView


urlpatterns = [
    path("sliders/", SliderListCreateAPIView.as_view()),
    path("sliders/<int:pk>/", SliderDetailAPIView.as_view()),
    path("home/page/", HomePageAPIView.as_view()),
    path("home/slider/manage/<int:pk>/", HomeSliderManageAPIView.as_view()),
    path("home/slider/manage/<int:pk>/add/", HomeSliderManageAPIView.as_view()),
    path("home/slider/manage/<int:pk>/delete/", HomeSliderManageAPIView.as_view()),
]
