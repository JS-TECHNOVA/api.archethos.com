from rest_framework import serializers


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)


class LoginResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()


class RefreshResponseSerializer(serializers.Serializer):
    refreshed = serializers.BooleanField()


class MeResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)
    is_staff = serializers.BooleanField()
    is_superuser = serializers.BooleanField()
    groups = serializers.ListField()
    permissions = serializers.ListField(child=serializers.CharField())


class CSRFResponseSerializer(serializers.Serializer):
    csrftoken = serializers.CharField()
