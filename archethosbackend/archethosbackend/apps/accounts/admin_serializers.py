"""
Serializers for CMS user, group and permission management.

The escalation guards here are the important part. Django's permission system
happily lets a user with `auth.change_user` grant themselves — or anyone else —
permissions they do not hold, promote an account to superuser, or lock everyone
out by deactivating the last admin. None of that is prevented by
`DjangoModelPermissions`, so it is prevented here.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

User = get_user_model()


# ─── Permissions ─────────────────────────────────────────────────────────────


class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(source="content_type.app_label", read_only=True)
    model = serializers.CharField(source="content_type.model", read_only=True)
    codename_full = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "codename_full", "app_label", "model"]

    def get_codename_full(self, obj) -> str:
        return f"{obj.content_type.app_label}.{obj.codename}"


# ─── Escalation guards ───────────────────────────────────────────────────────


def _actor(context):
    request = context.get("request")
    return getattr(request, "user", None)


def _assert_may_grant(actor, permissions, field):
    """A non-superuser may only hand out permissions they already hold.

    Without this, anyone with `auth.change_user` could grant themselves
    `projects.delete_project` — or any other permission in the system.
    """
    if actor is None or actor.is_superuser:
        return

    held = actor.get_all_permissions()
    over_reach = sorted(
        f"{p.content_type.app_label}.{p.codename}"
        for p in permissions
        if f"{p.content_type.app_label}.{p.codename}" not in held
    )
    if over_reach:
        raise serializers.ValidationError(
            {
                field: [
                    "You cannot grant permissions you do not hold yourself: "
                    + ", ".join(over_reach)
                ]
            }
        )


def _assert_may_assign_groups(actor, groups):
    """Assigning a group grants everything inside it, so the same rule applies."""
    if actor is None or actor.is_superuser or not groups:
        return

    permissions = Permission.objects.filter(group__in=groups).select_related(
        "content_type"
    )
    _assert_may_grant(actor, permissions, "groups")


# ─── Users ───────────────────────────────────────────────────────────────────


class UserListSerializer(serializers.ModelSerializer):
    """Flat row for the admin data table — no nested objects."""

    full_name = serializers.SerializerMethodField()
    groups = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "last_login",
            "date_joined",
        ]

    def get_full_name(self, obj) -> str:
        return obj.get_full_name() or obj.email


class UserDetailSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()
    user_permissions = PermissionSerializer(many=True, read_only=True)
    effective_permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
            "effective_permissions",
            "last_login",
            "date_joined",
        ]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_groups(self, obj):
        return [{"id": g.id, "name": g.name} for g in obj.groups.all()]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_effective_permissions(self, obj):
        return sorted(obj.get_all_permissions())


class UserWriteSerializer(serializers.ModelSerializer):
    """Create and update CMS accounts.

    Accounts are only ever created by an administrator — there is no
    self-registration anywhere in this API.
    """

    password = serializers.CharField(
        write_only=True, required=False, trim_whitespace=False
    )
    groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Group.objects.all(), required=False
    )
    user_permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), required=False
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "password",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        ]

    def validate_email(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("An email address is required.")

        clashes = User.objects.filter(email__iexact=value)
        if self.instance:
            clashes = clashes.exclude(pk=self.instance.pk)
        if clashes.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def validate(self, attrs):
        actor = _actor(self.context)

        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError(
                {"password": ["A password is required when creating a user."]}
            )

        # Staff and superuser flags are the keys to the kingdom: is_superuser
        # bypasses every permission check, is_staff opens Django Admin.
        for flag in ("is_superuser", "is_staff"):
            if flag in attrs and actor is not None and not actor.is_superuser:
                current = getattr(self.instance, flag, False)
                if attrs[flag] != current:
                    raise serializers.ValidationError(
                        {flag: ["Only a superuser can change this flag."]}
                    )

        if "user_permissions" in attrs:
            _assert_may_grant(actor, attrs["user_permissions"], "user_permissions")
        if "groups" in attrs:
            _assert_may_assign_groups(actor, attrs["groups"])

        # Never let an admin lock themselves — or everyone — out.
        if self.instance is not None and attrs.get("is_active") is False:
            if actor is not None and self.instance.pk == actor.pk:
                raise serializers.ValidationError(
                    {"is_active": ["You cannot deactivate your own account."]}
                )
            if self.instance.is_superuser and _is_last_active_superuser(self.instance):
                raise serializers.ValidationError(
                    {"is_active": ["The last active superuser cannot be deactivated."]}
                )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")
        groups = validated_data.pop("groups", [])
        permissions = validated_data.pop("user_permissions", [])

        # auth.User requires a username. Deriving it from the email keeps it
        # unique for free, since email is uniquely indexed.
        email = validated_data["email"]
        user = User(username=email[:150], **validated_data)
        user.set_password(password)
        user.save()

        user.groups.set(groups)
        user.user_permissions.set(permissions)
        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("password", None)  # changed via the dedicated endpoint
        groups = validated_data.pop("groups", None)
        permissions = validated_data.pop("user_permissions", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if groups is not None:
            instance.groups.set(groups)
        if permissions is not None:
            instance.user_permissions.set(permissions)
        return instance


class SetPasswordSerializer(serializers.Serializer):
    """An administrator setting someone else's password.

    The current password is deliberately not required: an admin resetting an
    account does not know it.
    """

    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value):
        try:
            validate_password(value, self.context.get("target_user"))
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


def _is_last_active_superuser(user):
    return (
        not User.objects.filter(is_superuser=True, is_active=True)
        .exclude(pk=user.pk)
        .exists()
    )


# ─── Groups ──────────────────────────────────────────────────────────────────


class GroupListSerializer(serializers.ModelSerializer):
    permissions_count = serializers.IntegerField(read_only=True)
    users_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Group
        fields = ["id", "name", "permissions_count", "users_count"]


class GroupDetailSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    users_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name", "permissions", "users_count"]

    def get_users_count(self, obj) -> int:
        return obj.user_set.count()


class GroupWriteSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), required=False
    )

    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]

    def validate_name(self, value):
        value = value.strip()
        clashes = Group.objects.filter(name__iexact=value)
        if self.instance:
            clashes = clashes.exclude(pk=self.instance.pk)
        if clashes.exists():
            raise serializers.ValidationError("A group with this name already exists.")
        return value

    def validate(self, attrs):
        if "permissions" in attrs:
            _assert_may_grant(_actor(self.context), attrs["permissions"], "permissions")
        return attrs
