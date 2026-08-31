"""
Response envelope.

Every API response is wrapped in a consistent shape so the Next.js admin can rely
on one contract:

    {"success": true, "message": "...", "data": {...}}

Paginated responses additionally carry a top-level "pagination" object, which
EnvelopePageNumberPagination puts on the response for us to hoist here.

Wrapping happens in the renderer rather than in each view, so no view ever has to
think about it (DEVELOPMENT_PLAN.md §2.5).
"""

from rest_framework.renderers import JSONRenderer

# Responses that must reach the client byte-for-byte as generated.
_UNWRAPPED_VIEW_NAMES = frozenset(
    {
        "SpectacularAPIView",
        "SpectacularSwaggerView",
        "SpectacularRedocView",
    }
)

_DEFAULT_MESSAGES = {
    "GET": "Retrieved successfully",
    "POST": "Created successfully",
    "PUT": "Updated successfully",
    "PATCH": "Updated successfully",
    "DELETE": "Deleted successfully",
}


class EnvelopeJSONRenderer(JSONRenderer):
    """Wrap successful responses; leave already-enveloped errors alone."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        response = renderer_context.get("response")

        if response is None or self._should_skip(data, renderer_context):
            return super().render(data, accepted_media_type, renderer_context)

        request = renderer_context.get("request")
        method = getattr(request, "method", "GET")

        payload = {
            "success": True,
            "message": self._message(renderer_context, method),
            "data": data,
        }

        # Pagination metadata is attached by EnvelopePageNumberPagination and
        # belongs beside `data`, not inside it.
        pagination = getattr(response, "pagination", None)
        if pagination is not None:
            payload["pagination"] = pagination
            payload["data"] = data.get("results", data) if isinstance(data, dict) else data

        return super().render(payload, accepted_media_type, renderer_context)

    def _should_skip(self, data, renderer_context):
        response = renderer_context["response"]

        # 204 and other empty bodies stay empty.
        if data is None or response.status_code == 204:
            return True

        # The exception handler has already produced the error envelope.
        if response.status_code >= 400:
            return True

        # A view may opt out entirely (schema, file-ish payloads).
        view = renderer_context.get("view")
        if getattr(view, "envelope", True) is False:
            return True
        if type(view).__name__ in _UNWRAPPED_VIEW_NAMES:
            return True

        return False

    @staticmethod
    def _message(renderer_context, method):
        view = renderer_context.get("view")
        # A view can set `envelope_message` for a friendlier string.
        return getattr(view, "envelope_message", None) or _DEFAULT_MESSAGES.get(
            method, "Success"
        )
