from django.urls import path

from .views import CompanyAPIView, EnquiryDetailAPIView, EnquiryListAPIView, EnquiryReplyAPIView, PublicEnquiryCreateAPIView


urlpatterns = [
    path("company/", CompanyAPIView.as_view()),
    path("enquiries/", EnquiryListAPIView.as_view()),
    path("enquiries/<int:pk>/", EnquiryDetailAPIView.as_view()),
    path("enquiries/<int:pk>/reply/", EnquiryReplyAPIView.as_view()),
    path("public/enquiries/", PublicEnquiryCreateAPIView.as_view()),
]
