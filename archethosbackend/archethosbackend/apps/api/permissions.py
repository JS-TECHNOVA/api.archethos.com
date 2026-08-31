"""DRF permission classes for the admin API."""

from rest_framework.permissions import BasePermission, DjangoModelPermissions


class StrictDjangoModelPermissions(DjangoModelPermissions):
    """DjangoModelPermissions, but GET also requires the `view_*` permission.

    DRF's stock class leaves GET unmapped, so anyone authenticated can read any
    endpoint. That makes "this user may only view Projects" unenforceable in the
    negative direction — they could read Blogs too. The CMS assigns view
    permissions deliberately, so they must actually be checked.
    """

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class HasModelPermission(BasePermission):
    """Require named permissions on a view that has no queryset of its own.

    Used by the small single-purpose views that replace what would have been
    `@action` methods (deactivate, set-password, reorder, publish), where the
    required permission is stated explicitly rather than derived from a model.

        class UserDeactivateAPIView(...):
            required_permissions = ["auth.change_user"]
    """

    def has_permission(self, request, view):
        required = getattr(view, "required_permissions", None)
        if not required:
            return True
        return request.user.is_authenticated and request.user.has_perms(required)


class IsSuperUser(BasePermission):
    message = "This action is restricted to superusers."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)
