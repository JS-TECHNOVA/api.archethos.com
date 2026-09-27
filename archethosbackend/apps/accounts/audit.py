from contextvars import ContextVar

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import AuditLog


audit_actor = ContextVar("audit_actor", default=None)
TRACKED_APP_LABELS = {"about", "auth", "blogs", "contact", "core", "home", "master", "media_library", "pages", "projects", "services"}
PRIVATE_FIELD_NAMES = {"password", "smtp_password"}


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        token = audit_actor.set(user if request.method in {"POST", "PUT", "PATCH", "DELETE"} and user and user.is_authenticated and user.is_staff else None)
        try:
            return self.get_response(request)
        finally:
            audit_actor.reset(token)


def should_audit(sender):
    return audit_actor.get() is not None and sender is not AuditLog and sender._meta.app_label in TRACKED_APP_LABELS


@receiver(pre_save)
def capture_changed_fields(sender, instance, **kwargs):
    if not should_audit(sender) or instance._state.adding:
        return

    previous = sender._default_manager.filter(pk=instance.pk).values().first()
    if previous is None:
        return

    instance._audit_changed_fields = [
        field.name
        for field in sender._meta.concrete_fields
        if not field.primary_key and not getattr(field, "auto_now", False) and not getattr(field, "auto_now_add", False) and field.name not in PRIVATE_FIELD_NAMES
        and previous[field.attname] != getattr(instance, field.attname)
    ]


@receiver(post_save)
def create_audit_log(sender, instance, created, **kwargs):
    if not should_audit(sender):
        return

    AuditLog.objects.create(
        actor=audit_actor.get(),
        action=AuditLog.Action.CREATED if created else AuditLog.Action.UPDATED,
        resource=sender._meta.verbose_name.title(),
        object_id=str(instance.pk),
        object_repr=str(instance),
        changed_fields=[] if created else getattr(instance, "_audit_changed_fields", []),
    )


@receiver(post_delete)
def create_deletion_audit_log(sender, instance, origin, **kwargs):
    if not should_audit(sender) or sender is not origin.__class__:
        return

    AuditLog.objects.create(
        actor=audit_actor.get(),
        action=AuditLog.Action.DELETED,
        resource=sender._meta.verbose_name.title(),
        object_id=str(instance.pk),
        object_repr=str(instance),
    )
