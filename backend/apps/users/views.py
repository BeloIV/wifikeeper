from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ldap3.core.exceptions import LDAPException

from apps.panel_users.permissions import IsAdmin, IsAdminOrReadOnly
from apps.audit.utils import audit_log
from . import ldap_service as ldap
from .serializers import (
    LDAPUserSerializer, CreateLDAPUserSerializer,
    UpdateLDAPUserSerializer, ChangePasswordSerializer,
)


class UserListView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        users = ldap.list_users()
        # Filtrovanie
        group = request.query_params.get('group')
        search = request.query_params.get('search', '').lower()
        if group:
            users = [u for u in users if u['group'] == group]
        if search:
            users = [u for u in users if search in u['username'].lower()
                     or search in u['full_name'].lower()
                     or search in u['email'].lower()]
        return Response(users)

    def post(self, request):
        self.check_permissions(request)
        if not request.user.is_admin():
            return Response({'detail': 'Nedostatočné oprávnenia.'}, status=403)

        serializer = CreateLDAPUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        # Skontroluj, či user neexistuje
        existing = ldap.get_user(d['username'])
        if existing:
            return Response({'detail': 'Používateľ s týmto menom už existuje.'}, status=400)

        try:
            user = ldap.create_user(
                username=d['username'],
                password=d['password'],
                first_name=d.get('first_name', ''),
                last_name=d.get('last_name', ''),
                email=d.get('email', ''),
                group=d['group'],
            )
        except LDAPException as e:
            return Response({'detail': str(e)}, status=400)

        audit_log(request, 'create_user', d['username'], {'group': d['group']})
        return Response(user, status=201)


class UserDetailView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request, username):
        user = ldap.get_user(username)
        if not user:
            return Response({'detail': 'Používateľ nenájdený.'}, status=404)
        return Response(user)

    def patch(self, request, username):
        if not request.user.is_admin():
            return Response({'detail': 'Nedostatočné oprávnenia.'}, status=403)

        user = ldap.get_user(username)
        if not user:
            return Response({'detail': 'Používateľ nenájdený.'}, status=404)

        serializer = UpdateLDAPUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            updated = ldap.update_user(username, **d)
        except LDAPException as e:
            return Response({'detail': str(e)}, status=400)

        audit_log(request, 'update_user', username, d)
        return Response(updated)

    def delete(self, request, username):
        if not request.user.is_admin():
            return Response({'detail': 'Nedostatočné oprávnenia.'}, status=403)

        user = ldap.get_user(username)
        if not user:
            return Response({'detail': 'Používateľ nenájdený.'}, status=404)

        try:
            ldap.delete_user(username)
        except LDAPException as e:
            return Response({'detail': str(e)}, status=400)

        audit_log(request, 'delete_user', username, {})
        return Response(status=204)


class UserPasswordView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, username):
        user = ldap.get_user(username)
        if not user:
            return Response({'detail': 'Používateľ nenájdený.'}, status=404)

        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            ldap.set_password(username, serializer.validated_data['password'])
        except LDAPException as e:
            return Response({'detail': str(e)}, status=400)

        audit_log(request, 'change_password', username, {})
        return Response({'detail': 'Heslo zmenené.'})


class UserActivateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, username):
        user = ldap.get_user(username)
        if not user:
            return Response({'detail': 'Používateľ nenájdený.'}, status=404)

        active = request.data.get('active', True)
        ldap.set_active(username, active)
        audit_log(request, 'set_active', username, {'active': active})
        return Response({'detail': 'Stav účtu aktualizovaný.'})
