from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import AdminUser, AdminInvitation


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()  # prijíma email aj username
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        login = data['username']
        # Ak obsahuje @, skús nájsť používateľa podľa emailu
        if '@' in login:
            try:
                db_user = AdminUser.objects.get(email=login)
                login = db_user.username
            except AdminUser.DoesNotExist:
                pass
        user = authenticate(username=login, password=data['password'])
        if not user:
            raise serializers.ValidationError('Nesprávne prihlasovacie meno alebo heslo.')
        if not user.is_active:
            raise serializers.ValidationError('Účet je deaktivovaný.')
        data['user'] = user
        return data


class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = AdminUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role', 'is_active', 'password', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = AdminUser(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class AdminUserMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role']


class AdminInvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=AdminUser.Role.choices)


class AdminInvitationAcceptSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True)
