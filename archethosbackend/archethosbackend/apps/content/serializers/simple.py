"""FAQ and Counter — small models with no media and no SEO of their own."""

from rest_framework import serializers

from ..models import FAQ, Counter


# ─── FAQ ─────────────────────────────────────────────────────────────────────


class FAQListSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "question", "category", "status", "published_at", "created_at"]


class FAQDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = [
            "id", "question", "answer", "category",
            "status", "published_at", "created_at", "updated_at",
        ]


class FAQWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "question", "answer", "category", "status", "published_at"]


class PublicFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "question", "answer", "category"]


# ─── Counter ─────────────────────────────────────────────────────────────────


class CounterListSerializer(serializers.ModelSerializer):
    display = serializers.SerializerMethodField()

    class Meta:
        model = Counter
        fields = [
            "id", "display", "prefix", "content", "postfix", "subtitle",
            "status", "published_at", "created_at",
        ]

    def get_display(self, obj) -> str:
        """The assembled value, so the admin table shows "40+" not three columns."""
        return f"{obj.prefix}{obj.content}{obj.postfix}"


class CounterDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Counter
        fields = [
            "id", "prefix", "content", "postfix", "subtitle", "description",
            "status", "published_at", "created_at", "updated_at",
        ]


class CounterWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Counter
        fields = [
            "id", "prefix", "content", "postfix", "subtitle", "description",
            "status", "published_at",
        ]


class PublicCounterSerializer(serializers.ModelSerializer):
    """prefix / postfix stay separate fields: the design renders them in the
    accent colour at a smaller size than the number, so the frontend needs them
    apart rather than pre-joined."""

    class Meta:
        model = Counter
        fields = ["id", "prefix", "content", "postfix", "subtitle", "description"]
