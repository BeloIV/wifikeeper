from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ldap3.core.exceptions import LDAPException

from apps.panel_users.permissions import IsAdmin, IsAdminOrReadOnly
from apps.audit.utils import audit_log
from . import ldap_service as ldap
import secrets
import string

from .serializers import (
    LDAPUserSerializer, CreateLDAPUserSerializer,
    UpdateLDAPUserSerializer, ChangePasswordSerializer,
    BulkEmailImportSerializer, LDAPGroupSerializer,
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

        email = d.get('email', '').strip()
        first = d['first_name'].strip()
        last = d['last_name'].strip()

        # Login: email ak je zadaný, inak meno.priezvisko bez diakritiky
        if email:
            username = email
        else:
            username = _slugify_name(first, last)
            if not username:
                return Response({'detail': 'Nepodarilo sa vygenerovať login z mena.'}, status=400)

        if ldap.get_user(username):
            return Response({'detail': f'Používateľ "{username}" už existuje.'}, status=400)

        password = _generate_password(8)

        try:
            ldap.create_user(
                username=username,
                password=password,
                first_name=first,
                last_name=last,
                email=email,
                group=d['group'],
            )
        except LDAPException as e:
            return Response({'detail': str(e)}, status=400)

        if email:
            from .tasks import send_user_credentials_email
            group_label = ldap.get_group_labels().get(d['group'], d['group'])
            send_user_credentials_email.delay(email, username, password, group_label)

        audit_log(request, 'create_user', username, {'group': d['group']})
        return Response({'username': username, 'password': password, 'email': email}, status=201)


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


def _generate_password(length=8) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def _slugify_name(first: str, last: str) -> str:
    import unicodedata
    raw = f'{first}.{last}'.lower().strip()
    normalized = unicodedata.normalize('NFD', raw)
    ascii_str = normalized.encode('ascii', 'ignore').decode('ascii')
    return ''.join(c for c in ascii_str if c.isalnum() or c == '.')


class UserBulkView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = BulkEmailImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        emails = d['emails']
        group = d['group']

        group_label = ldap.get_group_labels().get(group, group)
        # Zisti ďalšie voľné poradové ID raz pre celú dávku
        next_id = ldap.get_next_group_id(group)

        results = []
        created = 0
        failed = 0

        for i, email in enumerate(emails):
            seq_id = str(next_id + i)
            try:
                password = _generate_password(8)
                ldap.create_user(
                    username=email,
                    password=password,
                    first_name=group_label,
                    last_name=seq_id,
                    email=email,
                    group=group,
                )
                # Pošli heslo emailom
                from .tasks import send_user_credentials_email
                send_user_credentials_email.delay(email, email, password, group_label)

                audit_log(request, 'create_user', email, {'group': group, 'bulk': True})
                results.append({'index': i, 'success': True, 'username': email, 'email': email})
                created += 1
            except Exception as e:
                results.append({'index': i, 'success': False, 'email': email, 'error': str(e)})
                failed += 1

        return Response(
            {'results': results, 'created': created, 'failed': failed},
            status=207,
        )


class UserGroupListView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        users = ldap.list_users()
        detail = request.query_params.get('detail') == '1'

        group_names = ldap.get_groups()
        group_labels = ldap.get_group_labels()
        vlan_map = ldap.get_vlan_map()

        groups = {}
        for g in group_names:
            groups[g] = {
                'name': g,
                'label': group_labels.get(g, g),
                'vlan': vlan_map.get(g, 0),
                'member_count': 0,
                'members': [],
            }

        for user in users:
            g = user.get('group')
            if g and g in groups:
                groups[g]['member_count'] += 1
                if detail:
                    groups[g]['members'].append(user)

        return Response(list(groups.values()))

    def post(self, request):
        if not request.user.is_admin():
            return Response({'detail': 'Nedostatočné oprávnenia.'}, status=403)

        serializer = LDAPGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        from apps.users.models import LDAPGroup
        if LDAPGroup.objects.filter(name=d['name']).exists():
            return Response({'detail': 'Skupina s týmto názvom už existuje.'}, status=400)

        try:
            ldap.create_ldap_group(d['name'])
        except Exception as e:
            return Response({'detail': str(e)}, status=400)

        group = LDAPGroup.objects.create(name=d['name'], label=d['label'], vlan=d['vlan'])
        audit_log(request, 'create_group', d['name'], {'label': d['label'], 'vlan': d['vlan']})
        return Response({'name': group.name, 'label': group.label, 'vlan': group.vlan,
                         'member_count': 0, 'members': []}, status=201)


class UserGroupDetailView(APIView):
    permission_classes = [IsAdmin]

    def delete(self, request, name):
        from apps.users.models import LDAPGroup
        try:
            group = LDAPGroup.objects.get(name=name)
        except LDAPGroup.DoesNotExist:
            return Response({'detail': 'Skupina nenájdená.'}, status=404)

        # Skontroluj, či skupina nie je obsadená
        users = ldap.list_users()
        members = [u for u in users if u.get('group') == name]
        if members:
            return Response({'detail': f'Skupinu nie je možné vymazať – obsahuje {len(members)} používateľov.'}, status=400)

        try:
            ldap.delete_ldap_group(name)
        except Exception as e:
            return Response({'detail': str(e)}, status=400)

        group.delete()
        audit_log(request, 'delete_group', name, {})
        return Response(status=204)
