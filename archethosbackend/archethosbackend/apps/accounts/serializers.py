"""Serializers for authentication and the current-user payload."""

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    """One credential field that accepts an email address or a username.

    `email` is a plain CharField, not an EmailField: the same box takes both, and
    an EmailField would reject a username before authentication ever ran.
    `username` is accepted as an alias so either key works from the frontend.
    """

    email = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Email address or username.",
    )
    username = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Alias for `email`; send either.",
    )
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        identifier = (attrs.get("email") or attrs.get("username") or "").strip()
        if not identifier:
            raise serializers.ValidationError(
                {"email": ["Enter your email address or username."]}
            )

        # Passed as `username` because that is the argument Django's auth
        # backends take; EmailOrUsernameBackend decides which column to match.
        user = authenticate(
            request=self.context.get("request"),
            username=identifier,
            password=attrs["password"],
        )

        # One message for every failure mode: unknown account, wrong password and
        # deactivated account are indistinguishable to an attacker.
        if user is None:
            raise serializers.ValidationError(
                {"detail": "Invalid credentials."}, code="invalid_credentials"
            )

        attrs["user"] = user
        return attrs


class GroupSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


class CurrentUserSerializer(serializers.ModelSerializer):
    """Everything the CMS frontend needs to decide what to render.

    `permissions` is the effective set — direct plus group-derived — resolved
    from Django's permission system on every request. Permissions are
    deliberately not baked into the JWT, so revoking one takes effect
    immediately rather than at token expiry (DEVELOPMENT_PLAN.md §8).
    """

    groups = GroupSummarySerializer(many=True, read_only=True)
    permissions = serializers.SerializerMethodField()

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
            "last_login",
            "date_joined",
            "groups",
            "permissions",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_permissions(self, user):
        # Superusers implicitly hold every permission; get_all_permissions()
        # already expands that, so the frontend needs no special case.
        return sorted(user.get_all_permissions())


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """A user editing their own details.

    Needs no `auth.change_user`: changing your own name is not user
    administration, and requiring that permission would mean every editor could
    also edit everyone else.

    `username` is deliberately absent. It is a login identifier — someone may be
    signing in with it right now — so it is shown in the UI and never accepted
    here. Role and status fields are absent for the obvious reason: this
    endpoint would otherwise be a self-service promotion to superuser.
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        extra_kwargs = {"email": {"required": False}}

    def validate_email(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("An email address is required.")

        # Mirrors the case-insensitive unique index so the client gets a field
        # error rather than a database 409.
        clashes = User.objects.filter(email__iexact=value).exclude(
            pk=self.instance.pk
        )
        if clashes.exists():
            raise serializers.ValidationError(
                "Another account already uses this email address."
            )
        return value


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        user = self.context["request"].user
        try:
            validate_password(value, user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
