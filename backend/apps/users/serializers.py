from rest_framework import serializers

GROUPS = ['sdb', 'animatori', 'fma', 'spolupracovnici', 'hostia', 'docasny']


class LDAPUserSerializer(serializers.Serializer):
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    group = serializers.ChoiceField(choices=GROUPS)
    disabled = serializers.BooleanField(read_only=True, default=False)
    full_name = serializers.CharField(read_only=True, required=False)


class CreateLDAPUserSerializer(serializers.Serializer):
    username = serializers.RegexField(
        r'^[a-z0-9._-]+$',
        max_length=64,
        error_messages={'invalid': 'Meno smie obsahovať len malé písmená, číslice, bodku, podčiarkovník a pomlčku.'},
    )
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    group = serializers.ChoiceField(choices=GROUPS)


class UpdateLDAPUserSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    group = serializers.ChoiceField(choices=GROUPS, required=False)


class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, write_only=True)
