"""
Pagination for admin data tables.

Emits the metadata shape the Next.js table components consume:

    "pagination": {"page": 1, "page_size": 20, "total_items": 156,
                   "total_pages": 8, "has_next": true, "has_previous": false}

The metadata is stashed on the response so EnvelopeJSONRenderer can hoist it to a
sibling of `data` rather than nesting it inside.
"""

from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class EnvelopePageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        paginator = self.page.paginator
        response = Response(OrderedDict([("results", data)]))
        response.pagination = {
            "page": self.page.number,
            "page_size": self.get_page_size(self.request),
            "total_items": paginator.count,
            "total_pages": paginator.num_pages,
            "has_next": self.page.has_next(),
            "has_previous": self.page.has_previous(),
        }
        return response

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean", "example": True},
                "message": {"type": "string", "example": "Retrieved successfully"},
                "pagination": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "integer", "example": 1},
                        "page_size": {"type": "integer", "example": 20},
                        "total_items": {"type": "integer", "example": 156},
                        "total_pages": {"type": "integer", "example": 8},
                        "has_next": {"type": "boolean", "example": True},
                        "has_previous": {"type": "boolean", "example": False},
                    },
                },
                "data": schema,
            },
        }
