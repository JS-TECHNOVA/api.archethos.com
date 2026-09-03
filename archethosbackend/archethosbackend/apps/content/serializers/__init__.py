"""Admin and public serializers for master content.

Four variants per resource (plan §12):
    List    flat table columns, zero nested objects
    Detail  full record plus nested items
    Write   create/update, media by id-or-path, owns validation
    Public  published fields only, an independent class
"""

from .blog import (
    BlogCategoryDetailSerializer,
    BlogCategoryListSerializer,
    BlogCategoryWriteSerializer,
    BlogPostDetailSerializer,
    BlogPostListSerializer,
    BlogPostWriteSerializer,
    PublicBlogCategorySerializer,
    PublicBlogPostDetailSerializer,
    PublicBlogPostSerializer,
)
from .catalog import (
    GalleryItemDetailSerializer,
    GalleryItemListSerializer,
    GalleryItemWriteSerializer,
    LocationDetailSerializer,
    LocationListSerializer,
    LocationWriteSerializer,
    PublicGalleryItemSerializer,
    PublicLocationSerializer,
)
from .project import (
    ProjectDetailSerializer,
    ProjectGalleryItemSerializer,
    ProjectMaterialSerializer,
    ProjectGalleryItemWriteSerializer,
    ProjectListSerializer,
    ProjectWriteSerializer,
    PublicProjectDetailSerializer,
    PublicProjectSerializer,
)
from .service import (
    PublicServiceDetailSerializer,
    PublicServiceSerializer,
    ServiceDetailSectionSerializer,
    ServiceDetailSerializer,
    ServiceGalleryItemSerializer,
    ServiceListSerializer,
    ServiceProcessStepSerializer,
    ServiceWriteSerializer,
)
from .simple import (
    CounterDetailSerializer,
    CounterListSerializer,
    CounterWriteSerializer,
    FAQDetailSerializer,
    FAQListSerializer,
    FAQWriteSerializer,
    PublicCounterSerializer,
    PublicFAQSerializer,
)

__all__ = [
    "BlogCategoryDetailSerializer", "BlogCategoryListSerializer",
    "BlogCategoryWriteSerializer", "BlogPostDetailSerializer",
    "BlogPostListSerializer", "BlogPostWriteSerializer",
    "CounterDetailSerializer", "CounterListSerializer", "CounterWriteSerializer",
    "FAQDetailSerializer", "FAQListSerializer", "FAQWriteSerializer",
    "ProjectDetailSerializer", "ProjectGalleryItemSerializer",
    "ProjectGalleryItemWriteSerializer", "ProjectListSerializer",
    "ProjectWriteSerializer",
    "PublicBlogCategorySerializer", "PublicBlogPostDetailSerializer",
    "PublicBlogPostSerializer", "PublicCounterSerializer", "PublicFAQSerializer",
    "PublicProjectDetailSerializer", "PublicProjectSerializer",
    "PublicServiceDetailSerializer", "PublicServiceSerializer",
    "ServiceDetailSectionSerializer", "ServiceDetailSerializer",
    "ServiceGalleryItemSerializer", "ServiceListSerializer",
    "ServiceProcessStepSerializer", "ServiceWriteSerializer",
    "GalleryItemDetailSerializer", "GalleryItemListSerializer",
    "GalleryItemWriteSerializer", "PublicGalleryItemSerializer",
    "LocationDetailSerializer", "LocationListSerializer",
    "LocationWriteSerializer", "PublicLocationSerializer",
    "ProjectMaterialSerializer",
]
