"""Enquiry serializers."""

from rest_framework import serializers

from .models import Enquiry

#: Fields a submitter fills in. `extra` is deliberately open, but capped.
SUBMIT_FIELDS = [
    "form_type", "name", "email", "phone", "subject", "message",
    "extra", "source_page",
]

#: An `extra` payload larger than this is not a real enquiry.
MAX_EXTRA_KEYS = 25
MAX_EXTRA_VALUE_LENGTH = 2000


class EnquirySubmitSerializer(serializers.ModelSerializer):
    """Public submission. Anonymous, so everything is validated hard."""

    #: Honeypot. Real browsers leave it empty because it is hidden; bots that
    #: fill every input reveal themselves. Named plausibly so it is tempting.
    website = serializers.CharField(
        required=False, allow_blank=True, write_only=True,
        help_text="Leave empty. Anti-spam field.",
    )

    class Meta:
        model = Enquiry
        fields = SUBMIT_FIELDS + ["website"]
        extra_kwargs = {
            "name": {"required": True, "allow_blank": False},
            "email": {"required": True},
            "message": {"required": True, "allow_blank": False},
        }

    def validate_extra(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Expected an object.")
        if len(value) > MAX_EXTRA_KEYS:
            raise serializers.ValidationError(
                f"Too many fields (limit {MAX_EXTRA_KEYS})."
            )
        for key, item in value.items():
            if isinstance(item, str) and len(item) > MAX_EXTRA_VALUE_LENGTH:
                raise serializers.ValidationError(f"'{key}' is too long.")
        return value

    def create(self, validated_data):
        caught = bool(validated_data.pop("website", "").strip())
        if caught:
            # Discard it, but return an unsaved instance so the response is
            # byte-identical to a success. Telling a bot it was detected only
            # teaches it to avoid the trap next time.
            return Enquiry(**validated_data)
        return super().create(validated_data)


class EnquiryListSerializer(serializers.ModelSerializer):
    """Flat row for the admin inbox table."""

    class Meta:
        model = Enquiry
        fields = [
            "id", "form_type", "name", "email", "subject",
            "is_read", "source_page", "created_at",
        ]


class EnquiryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enquiry
        fields = [
            "id", "form_type", "name", "email", "phone", "subject", "message",
            "extra", "source_page", "is_read", "created_at", "updated_at",
        ]


class EnquiryUpdateSerializer(serializers.ModelSerializer):
    """Only the read flag. The submission itself is a record of what someone
    actually sent, and editing it would destroy that."""

    class Meta:
        model = Enquiry
        fields = ["is_read"]
