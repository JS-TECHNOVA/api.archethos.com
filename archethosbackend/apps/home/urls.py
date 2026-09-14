from django.urls import path

from .views import CounterDetailAPIView, CounterListCreateAPIView, HomeContentGroupDetailAPIView, HomeContentGroupListCreateAPIView, HomeCountersGroupAPIView, HomeGalleryGroupAPIView, HomePageAPIView, HomeProjectsGroupAPIView, HomeServicesGroupAPIView, HomeSliderManageAPIView, SliderDetailAPIView, SliderListCreateAPIView, WorkProcessGroupDetailAPIView, WorkProcessGroupListCreateAPIView, WorkProcessStepDetailAPIView, WorkProcessStepListCreateAPIView


urlpatterns = [
    path("sliders/", SliderListCreateAPIView.as_view()),
    path("sliders/<int:pk>/", SliderDetailAPIView.as_view()),
    path("counters/", CounterListCreateAPIView.as_view()),
    path("counters/<int:pk>/", CounterDetailAPIView.as_view()),
    path("work-process-groups/", WorkProcessGroupListCreateAPIView.as_view()),
    path("work-process-groups/<int:pk>/", WorkProcessGroupDetailAPIView.as_view()),
    path("work-process-groups/<int:group_id>/steps/", WorkProcessStepListCreateAPIView.as_view()),
    path("work-process-groups/<int:group_id>/steps/<int:pk>/", WorkProcessStepDetailAPIView.as_view()),
    path("home/page/", HomePageAPIView.as_view()),
    path("home/services-group/", HomeServicesGroupAPIView.as_view()),
    path("home/projects-group/", HomeProjectsGroupAPIView.as_view()),
    path("home/gallery-group/", HomeGalleryGroupAPIView.as_view()),
    path("home/counters-group/", HomeCountersGroupAPIView.as_view()),
    path("home/content-groups/", HomeContentGroupListCreateAPIView.as_view()),
    path("home/content-groups/<int:pk>/", HomeContentGroupDetailAPIView.as_view()),
    path("home/slider/manage/<int:pk>/", HomeSliderManageAPIView.as_view()),
    path("home/slider/manage/<int:pk>/add/", HomeSliderManageAPIView.as_view()),
    path("home/slider/manage/<int:pk>/delete/", HomeSliderManageAPIView.as_view()),
]
