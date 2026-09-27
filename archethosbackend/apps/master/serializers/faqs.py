from rest_framework import serializers

from apps.master.models import FAQ


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "question", "answer", "order", "is_active", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]
