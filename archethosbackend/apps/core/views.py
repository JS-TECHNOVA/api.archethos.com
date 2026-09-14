from django.http import JsonResponse
from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import Company, Enquiry, EnquiryReply
from .serializers import CompanySerializer, EnquiryReplyCreateSerializer, EnquiryReplySerializer, EnquirySerializer


def health(request):
    return JsonResponse({"ok": True})


def api_not_found(request, exception):
    return JsonResponse({"detail": "Not found."}, status=404)


def api_server_error(request):
    return JsonResponse({"detail": "Server error."}, status=500)


class CompanyAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = CompanySerializer

    def get_object(self):
        company, _ = Company.objects.get_or_create(pk=Company.SINGLETON_PK)
        return company


class EnquiryListAPIView(generics.ListCreateAPIView):
    queryset = Enquiry.objects.all()
    serializer_class = EnquirySerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return super().get_permissions()


class EnquiryDetailAPIView(generics.RetrieveUpdateAPIView):
    queryset = Enquiry.objects.all()
    serializer_class = EnquirySerializer

    def retrieve(self, request, *args, **kwargs):
        enquiry = self.get_object()
        if enquiry.status == "unread":
            enquiry.status = "read"
            enquiry.save(update_fields=["status", "updated_at"])
        return super().retrieve(request, *args, **kwargs)


class PublicEnquiryCreateAPIView(generics.CreateAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = EnquirySerializer


class EnquiryReplyAPIView(generics.GenericAPIView):
    serializer_class = EnquiryReplyCreateSerializer

    def post(self, request, pk):
        enquiry = get_object_or_404(Enquiry, pk=pk)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company, _ = Company.objects.get_or_create(pk=Company.SINGLETON_PK)
        if not company.smtp_host or not company.smtp_from_email:
            raise ValidationError({"detail": "Configure SMTP host and from email in Company first."})
        if company.smtp_use_tls and company.smtp_use_ssl:
            raise ValidationError({"detail": "SMTP TLS and SSL cannot both be enabled."})

        connection = EmailBackend(
            host=company.smtp_host,
            port=company.smtp_port,
            username=company.smtp_username,
            password=company.smtp_password,
            use_tls=company.smtp_use_tls,
            use_ssl=company.smtp_use_ssl,
            fail_silently=False,
        )
        message = EmailMessage(
            subject=serializer.validated_data["subject"],
            body=serializer.validated_data["message"],
            from_email=company.smtp_from_email,
            to=[enquiry.email],
            connection=connection,
        )
        try:
            message.send()
        except Exception as exc:
            raise ValidationError({"detail": "The email could not be sent. Check the SMTP configuration."}) from exc
        reply = EnquiryReply.objects.create(
            enquiry=enquiry,
            to_email=enquiry.email,
            subject=serializer.validated_data["subject"],
            message=serializer.validated_data["message"],
            sent_by=request.user,
        )
        enquiry.status = "replied"
        enquiry.save(update_fields=["status", "updated_at"])
        return Response(EnquiryReplySerializer(reply).data, status=status.HTTP_201_CREATED)
