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
    key_type = serializers.ChoiceField(choices=TempKey.KeyType.choices)
    valid_hours = serializers.IntegerField(min_value=1, max_value=720, required=False, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate(self, data):
        if data['key_type'] == TempKey.KeyType.TIMED and not data.get('valid_hours'):
            raise serializers.ValidationError({'valid_hours': 'Zadaj platnosť v hodinách pre časový kľúč.'})
        return data


class TempKeyWithPasswordSerializer(TempKeySerializer):
    """Vracia dešifrované heslo – len pri vytvorení kľúča!"""
    ldap_password = serializers.SerializerMethodField()

    class Meta(TempKeySerializer.Meta):
        fields = TempKeySerializer.Meta.fields + ['ldap_password']

    def get_ldap_password(self, obj) -> str:
        return decrypt_password(obj.ldap_password)
