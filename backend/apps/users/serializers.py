from rest_framework import serializers
from . import ldap_service as ldap


def _group_choices():
    return ldap.get_groups()


class _DynamicGroupMixin:
    def validate_group(self, value):
        if value not in ldap.get_groups():
            raise serializers.ValidationError(f'Neplatná skupina: {value}')
        return value


class LDAPUserSerializer(serializers.Serializer):
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    group = serializers.CharField()
    disabled = serializers.BooleanField(read_only=True, default=False)
    full_name = serializers.CharField(read_only=True, required=False)

    def validate_group(self, value):
        if value not in ldap.get_groups():
            raise serializers.ValidationError(f'Neplatná skupina: {value}')
        return value


class CreateLDAPUserSerializer(_DynamicGroupMixin, serializers.Serializer):
    first_name = serializers.CharField(max_length=64)
    last_name = serializers.CharField(max_length=64)
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    group = serializers.CharField()


class UpdateLDAPUserSerializer(_DynamicGroupMixin, serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    group = serializers.CharField(required=False)


class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, write_only=True)


class BulkEmailImportSerializer(_DynamicGroupMixin, serializers.Serializer):
    emails = serializers.ListField(
        child=serializers.EmailField(),
        min_length=1,
        max_length=100,
    )
    group = serializers.CharField()


class LDAPGroupSerializer(serializers.Serializer):
    name = serializers.RegexField(
        r'^[a-z0-9_-]+$',
        max_length=64,
        error_messages={'invalid': 'Názov smie obsahovať len malé písmená, číslice, podčiarkovník a pomlčku.'},
    )
    label = serializers.CharField(max_length=128)
    vlan = serializers.IntegerField(min_value=1, max_value=4094)
