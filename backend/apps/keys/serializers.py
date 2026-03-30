from rest_framework import serializers
from .crypto import decrypt_password
from .models import TempKey


class TempKeySerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = TempKey
        fields = [
            'id', 'label', 'key_type', 'ldap_username',
            'valid_hours', 'expires_at', 'used', 'used_at',
            'max_uses', 'use_count',
            'created_by', 'created_by_name', 'created_at',
            'email_sent_to', 'ldap_deleted', 'is_active', 'is_expired',
        ]
        read_only_fields = [
            'id', 'ldap_username', 'used', 'used_at',
            'created_by', 'created_at', 'ldap_deleted',
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None


class TempKeyCreateSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    group = serializers.CharField(max_length=64)
    key_type = serializers.ChoiceField(choices=TempKey.KeyType.choices)
    valid_hours = serializers.IntegerField(min_value=1, max_value=720, required=False, allow_null=True)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    max_uses = serializers.IntegerField(min_value=1, max_value=1000, required=False, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_group(self, value):
        from apps.users.ldap_service import get_groups
        if value not in get_groups():
            raise serializers.ValidationError(f'Skupina "{value}" neexistuje.')
        return value

    def validate(self, data):
        if data['key_type'] == TempKey.KeyType.TIMED:
            has_hours = bool(data.get('valid_hours'))
            has_dt = bool(data.get('expires_at'))
            if has_hours and has_dt:
                raise serializers.ValidationError(
                    'Zadaj buď valid_hours alebo expires_at, nie obe súčasne.'
                )
            if not has_hours and not has_dt:
                raise serializers.ValidationError(
                    {'valid_hours': 'Zadaj platnosť v hodinách alebo konkrétny dátum expirácie.'}
                )
            if has_dt:
                from django.utils import timezone
                if data['expires_at'] <= timezone.now():
                    raise serializers.ValidationError(
                        {'expires_at': 'Dátum expirácie musí byť v budúcnosti.'}
                    )
        if data['key_type'] == TempKey.KeyType.MULTI_USE:
            if not data.get('max_uses'):
                raise serializers.ValidationError(
                    {'max_uses': 'Zadaj maximálny počet použití.'}
                )
        return data


class TempKeyWithPasswordSerializer(TempKeySerializer):
    """Vracia dešifrované heslo – len pri vytvorení kľúča!"""
    ldap_password = serializers.SerializerMethodField()

    class Meta(TempKeySerializer.Meta):
        fields = TempKeySerializer.Meta.fields + ['ldap_password']

    def get_ldap_password(self, obj) -> str:
        return decrypt_password(obj.ldap_password)
