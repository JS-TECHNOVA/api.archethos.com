"""
Error envelope.

    {"success": false, "message": "Validation failed",
     "errors": {"slug": ["This slug is already in use."]},
     "code": "validation_error"}

Also translates two database-level failures that DRF does not handle into the
HTTP semantics the plan calls for:

  * ProtectedError -> 409, naming what still references the object. This is what
    makes on_delete=PROTECT usable from a UI: "you cannot delete this image, it is
    used by 3 projects" instead of a 500.
  * IntegrityError  -> 409 for uniqueness collisions, 400 otherwise.
"""

import logging

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.db.models import ProtectedError, RestrictedError
from django.db.utils import IntegrityError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)

_MESSAGES = {
    status.HTTP_400_BAD_REQUEST: "Validation failed",
    status.HTTP_401_UNAUTHORIZED: "Authentication required",
    status.HTTP_403_FORBIDDEN: "You do not have permission to perform this action",
    status.HTTP_404_NOT_FOUND: "Not found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "Method not allowed",
    status.HTTP_409_CONFLICT: "Conflict",
    status.HTTP_429_TOO_MANY_REQUESTS: "Too many requests",
}


def envelope_exception_handler(exc, context):
    exc = _normalise(exc)

    response = drf_exception_handler(exc, context)
    if response is None:
        # Genuinely unhandled: let Django's 500 machinery deal with it so the
        # traceback still reaches the logs and error tracking.
        return None

    detail = response.data
    code = getattr(exc, "default_code", None) or "error"

    if isinstance(detail, dict) and set(detail) == {"detail"}:
        message = str(detail["detail"])
        errors = {}
        code = getattr(detail["detail"], "code", code)
    elif isinstance(detail, list):
        message = _MESSAGES.get(response.status_code, "Request failed")
        errors = {"non_field_errors": detail}
    else:
        message = _MESSAGES.get(response.status_code, "Request failed")
        errors = detail

    response.data = {
        "success": False,
        "message": message,
        "errors": errors,
        "code": code,
    }
    return response


def _normalise(exc):
    """Map non-DRF exceptions onto DRF ones so they render consistently."""
    if isinstance(exc, Http404):
        return exceptions.NotFound()

    if isinstance(exc, PermissionDenied):
        return exceptions.PermissionDenied()

    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
        return exceptions.ValidationError(detail)

    if isinstance(exc, (ProtectedError, RestrictedError)):
        return _Conflict(_protected_detail(exc), code="protected")

    if isinstance(exc, IntegrityError):
        text = str(exc)
        if "unique" in text.lower():
            return _Conflict("That value is already in use.", code="unique_conflict")
        logger.warning("Unhandled IntegrityError: %s", text)
        return exceptions.ValidationError("The request violates a database constraint.")

    return exc


def _protected_detail(exc):
    referencing = list(getattr(exc, "protected_objects", None) or [])
    if not referencing:
        return "This item is still referenced elsewhere and cannot be deleted."

    shown = ", ".join(str(obj) for obj in referencing[:5])
    if len(referencing) > 5:
        shown += f", and {len(referencing) - 5} more"
    return (
        f"This item is still referenced by {len(referencing)} object(s) "
        f"and cannot be deleted: {shown}."
    )


class _Conflict(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflict"
    default_code = "conflict"

    def __init__(self, detail=None, code=None):
        super().__init__(detail=detail, code=code)
        if code:
            self.default_code = code
