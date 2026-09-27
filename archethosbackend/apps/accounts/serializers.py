from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from .models import AuditLog


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


class StaffUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    groups = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), many=True, required=False)

    class Meta:
        model = get_user_model()
        fields = ["id", "username", "email", "first_name", "last_name", "is_active", "is_staff", "groups", "date_joined", "password"]
        read_only_fields = ["id", "is_staff", "date_joined"]

    def create(self, validated_data):
        groups = validated_data.pop("groups", [])
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "A password is required when creating a user."})
        user = self.Meta.model(is_staff=True, **validated_data)
        user.set_password(password)
        user.save()
        user.groups.set(groups)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        groups = validated_data.pop("groups", None)
        validated_data.pop("is_staff", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.is_staff = True
        instance.save()
        if groups is not None:
            instance.groups.set(groups)
        return instance


class GroupSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(queryset=Permission.objects.all(), many=True, required=False)

    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]


class PermissionSerializer(serializers.ModelSerializer):
    content_type_label = serializers.CharField(source="content_type.app_label", read_only=True)

    class Meta:
        model = Permission
        fields = ["id", "codename", "name", "content_type", "content_type_label"]


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    def get_actor(self, obj):
        return obj.actor.username if obj.actor_id else "System"

    class Meta:
        model = AuditLog
        fields = ["id", "actor", "action", "resource", "object_id", "object_repr", "changed_fields", "created_at"]
