from rest_framework import serializers

from apps.media_library.serializers import MediaAssetSerializer

from .models import Company, Enquiry, EnquiryReply


class CompanySerializer(serializers.ModelSerializer):
    logo_detail = MediaAssetSerializer(source="logo", read_only=True)
    icon_detail = MediaAssetSerializer(source="icon", read_only=True)

    class Meta:
        model = Company
        fields = "__all__"
        extra_kwargs = {"smtp_password": {"write_only": True}}

    def validate(self, attrs):
        if attrs.get("smtp_use_tls", self.instance.smtp_use_tls if self.instance else True) and attrs.get("smtp_use_ssl", self.instance.smtp_use_ssl if self.instance else False):
            raise serializers.ValidationError("SMTP TLS and SSL cannot both be enabled.")
        return attrs


class EnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Enquiry
        fields = ["id", "name", "email", "phone", "project_type", "location", "scope", "source", "services", "message", "status", "created_at", "updated_at"]
        read_only_fields = ["status", "created_at", "updated_at"]

    def to_internal_value(self, data):
        data = data.copy()
        if not data.get("project_type") and data.get("projectType"):
            data["project_type"] = data["projectType"]
        return super().to_internal_value(data)


class EnquiryReplySerializer(serializers.ModelSerializer):
    sent_by_name = serializers.CharField(source="sent_by.username", read_only=True)

    class Meta:
        model = EnquiryReply
        fields = ["id", "enquiry", "to_email", "subject", "message", "sent_by", "sent_by_name", "sent_at"]
        read_only_fields = ["enquiry", "to_email", "sent_by", "sent_at"]


class EnquiryReplyCreateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField()
