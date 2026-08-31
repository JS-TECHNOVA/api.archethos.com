"""
Enquiry submission and management.

The public endpoint is the only place on the whole API where an anonymous
visitor writes to the database, so it carries two defences that nothing else
needs: a rate limit and a honeypot.
"""

import django_filters
from django_ratelimit.core import is_ratelimited
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from archethosbackend.apps.api.generics import (
    AdminListAPIView,
    AdminRetrieveUpdateDestroyAPIView,
)

from .models import Enquiry
from .serializers import (
    EnquiryDetailSerializer,
    EnquiryListSerializer,
    EnquirySubmitSerializer,
    EnquiryUpdateSerializer,
)

#: Generous for a person, useless for a script.
RATE = "10/h"


class EnquirySubmitAPIView(APIView):
    """`POST /api/v1/public/enquiries/` — the site's contact forms."""

    authentication_classes = []
    permission_classes = [AllowAny]
    envelope_message = "Thank you — your enquiry has been received."

    @extend_schema(
        tags=["public"],
        summary="Submit an enquiry",
        request=EnquirySubmitSerializer,
        responses={201: None},
        description=(
            "Rate limited per IP. Include an empty `website` field in the form: "
            "it is a honeypot, and a filled one is silently accepted but discarded."
        ),
    )
    def post(self, request):
        if is_ratelimited(
            request, group="enquiry-submit", key="ip", rate=RATE,
            method="POST", increment=True,
        ):
            return Response(
                {
                    "success": False,
                    "message": "Too many enquiries from this address. Please try again later.",
                    "errors": {},
                    "code": "throttled",
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = EnquirySubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # The response is identical whether the honeypot caught it or not, so a
        # bot cannot learn that it was filtered.
        return Response({"received": True}, status=status.HTTP_201_CREATED)


class EnquiryFilterSet(django_filters.FilterSet):
    created_after = django_filters.DateFilter(
        field_name="created_at", lookup_expr="date__gte"
    )
    created_before = django_filters.DateFilter(
        field_name="created_at", lookup_expr="date__lte"
    )

    class Meta:
        model = Enquiry
        fields = ["form_type", "is_read"]


class EnquiryListAPIView(AdminListAPIView):
    """Read-only: enquiries arrive from the public form, never from the admin."""

    ordering = ["-created_at", "-id"]
    queryset = Enquiry.objects.all()
    list_serializer_class = EnquiryListSerializer
    filterset_class = EnquiryFilterSet
    search_fields = ["name", "email", "subject", "message"]
    ordering_fields = ["created_at", "name", "form_type", "is_read"]

    @extend_schema(tags=["admin:enquiries"], summary="List enquiries")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class EnquiryDetailAPIView(AdminRetrieveUpdateDestroyAPIView):
    queryset = Enquiry.objects.all()
    detail_serializer_class = EnquiryDetailSerializer
    #: Only `is_read` is writable — an enquiry is a record of what someone
    #: actually sent, and editing it would destroy that.
    write_serializer_class = EnquiryUpdateSerializer

    @extend_schema(tags=["admin:enquiries"], summary="Retrieve an enquiry")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["admin:enquiries"],
        summary="Mark an enquiry read or unread",
        description="Only `is_read` is writable; the submitted content is immutable.",
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=["admin:enquiries"], summary="Delete an enquiry")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class EnquiryUnreadCountAPIView(APIView):
    """Backs the unread badge in the admin nav."""

    permission_classes = [IsAuthenticated]
    envelope_message = "Unread count retrieved"

    @extend_schema(
        tags=["admin:enquiries"], summary="Count unread enquiries", responses={200: None}
    )
    def get(self, request):
        if not request.user.has_perm("enquiries.view_enquiry"):
            return Response({"unread": 0})
        return Response({"unread": Enquiry.objects.filter(is_read=False).count()})
