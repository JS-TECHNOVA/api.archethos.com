"""
Two small read-only endpoints the admin chrome needs on every screen.

`counts` feeds the sidebar badges, `stats` feeds the dashboard. Both are cheap
aggregate queries, and both return zeros rather than 403 for anything the user
cannot see — a badge is decoration, and failing the whole request because one
number is off-limits would blank the navigation.
"""

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from archethosbackend.apps.content.models import BlogPost, FAQ, Counter, Project, Service
from archethosbackend.apps.core.models import PublishStatus
from archethosbackend.apps.enquiries.models import Enquiry
from archethosbackend.apps.media_library.models import MediaAsset
from archethosbackend.apps.pages.models import Page
from archethosbackend.apps.sections.models import Section

User = get_user_model()


class AdminCountsAPIView(APIView):
    """Badge numbers for the sidebar.

    Permission-aware but never fatal: a user who cannot read enquiries gets 0
    rather than an error, because this response decorates navigation that must
    render regardless.
    """

    permission_classes = [IsAuthenticated]
    envelope_message = "Counts retrieved"

    @extend_schema(tags=["admin"], summary="Sidebar badge counts", responses={200: None})
    def get(self, request):
        user = request.user
        counts = {}

        if user.has_perm("enquiries.view_enquiry"):
            counts["unread_enquiries"] = Enquiry.objects.filter(is_read=False).count()
        else:
            counts["unread_enquiries"] = 0

        return Response(counts)


class DashboardStatsAPIView(APIView):
    """The dashboard's at-a-glance figures.

    One aggregate query per model rather than a count per status, so adding a
    status to the display costs nothing extra.
    """

    permission_classes = [IsAuthenticated]
    envelope_message = "Dashboard statistics retrieved"

    @extend_schema(tags=["admin"], summary="Dashboard statistics", responses={200: None})
    def get(self, request):
        user = request.user

        def publishable(model, perm):
            """Total and published, in one query, or None when not permitted."""
            if not user.has_perm(perm):
                return None
            row = model.objects.aggregate(
                total=Count("id"),
                published=Count("id", filter=Q(status=PublishStatus.PUBLISHED)),
            )
            return {"total": row["total"], "published": row["published"]}

        content = {
            "projects": publishable(Project, "content.view_project"),
            "services": publishable(Service, "content.view_service"),
            "journal": publishable(BlogPost, "content.view_blogpost"),
            "faqs": publishable(FAQ, "content.view_faq"),
            "counters": publishable(Counter, "content.view_counter"),
        }

        return Response(
            {
                # Drop anything this user may not see, rather than sending nulls
                # the dashboard would have to filter again.
                "content": {k: v for k, v in content.items() if v is not None},
                "structure": {
                    "pages": Page.objects.count()
                    if user.has_perm("pages.view_page")
                    else None,
                    "sections": Section.objects.count()
                    if user.has_perm("sections.view_section")
                    else None,
                },
                "media": (
                    MediaAsset.objects.count()
                    if user.has_perm("media_library.view_mediaasset")
                    else None
                ),
                "enquiries": (
                    {
                        "total": Enquiry.objects.count(),
                        "unread": Enquiry.objects.filter(is_read=False).count(),
                    }
                    if user.has_perm("enquiries.view_enquiry")
                    else None
                ),
                "users": (
                    User.objects.filter(is_active=True).count()
                    if user.has_perm("auth.view_user")
                    else None
                ),
            }
        )
