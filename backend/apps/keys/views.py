import io
import base64
import secrets
import string
from datetime import timedelta

import qrcode
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ldap3.core.exceptions import LDAPException

from apps.panel_users.permissions import IsAdmin, IsAdminOrReadOnly
from apps.audit.utils import audit_log
from apps.users import ldap_service as ldap
from .crypto import decrypt_password, encrypt_password
from .models import TempKey
from .serializers import TempKeySerializer, TempKeyCreateSerializer, TempKeyWithPasswordSerializer


def _generate_password(length=12) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class TempKeyListView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        qs = TempKey.objects.select_related('created_by')
        # Filtre
        key_type = request.query_params.get('type')
        active_only = request.query_params.get('active') == '1'
        if key_type:
            qs = qs.filter(key_type=key_type)
        if active_only:
            now = timezone.now()
            qs = qs.filter(
                ldap_deleted=False,
                used=False,
            ).exclude(expires_at__lt=now)
        return Response(TempKeySerializer(qs, many=True).data)

    def post(self, request):
        if not request.user.is_admin():
            return Response({'detail': 'Nedostatočné oprávnenia.'}, status=403)

        serializer = TempKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        # Vygeneruj LDAP prihlasovacie údaje
        username = ldap.generate_temp_username('g')
        password = _generate_password()

        # Vytvor LDAP účet
        try:
            ldap.create_user(
                username=username,
                password=password,
                first_name=d.get('label', '') or 'Host',
                last_name='',
                email=d.get('email', ''),
                group=d['group'],
            )
        except LDAPException as e:
            return Response({'detail': f'Chyba LDAP: {e}'}, status=400)

        # Vypočítaj expiráciu
        expires_at = None
        if d['key_type'] == TempKey.KeyType.TIMED:
            if d.get('expires_at'):
                expires_at = d['expires_at']
            elif d.get('valid_hours'):
                expires_at = timezone.now() + timedelta(hours=d['valid_hours'])

        key = TempKey.objects.create(
            label=d.get('label', ''),
            key_type=d['key_type'],
            ldap_username=username,
            ldap_password=encrypt_password(password),
            valid_hours=d.get('valid_hours'),
            expires_at=expires_at,
            max_uses=d.get('max_uses') if d['key_type'] == TempKey.KeyType.MULTI_USE else None,
            created_by=request.user,
        )

        # Pre časový kľúč naplánuj presný čas expirácie
        if key.key_type == TempKey.KeyType.TIMED and key.expires_at:
            from .tasks import expire_temp_key
            expire_temp_key.apply_async(args=[str(key.id)], eta=key.expires_at)

        # Pošli email ak zadaný
        email = d.get('email', '').strip()
        if email:
            from .tasks import send_key_email
            send_key_email.delay(str(key.id), email)

        audit_log(request, 'create_key', username, {'type': d['key_type']})
        return Response(TempKeyWithPasswordSerializer(key).data, status=201)


class TempKeyDetailView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request, pk):
        try:
            key = TempKey.objects.get(pk=pk)
        except TempKey.DoesNotExist:
            return Response({'detail': 'Kľúč nenájdený.'}, status=404)
        return Response(TempKeyWithPasswordSerializer(key).data)

    def delete(self, request, pk):
        if not request.user.is_admin():
            return Response({'detail': 'Nedostatočné oprávnenia.'}, status=403)
        try:
            key = TempKey.objects.get(pk=pk)
        except TempKey.DoesNotExist:
            return Response({'detail': 'Kľúč nenájdený.'}, status=404)

        # Zmaž LDAP účet
        if not key.ldap_deleted:
            try:
                user = ldap.get_user(key.ldap_username)
                if user:
                    ldap.delete_user(key.ldap_username)
                key.ldap_deleted = True
                key.save(update_fields=['ldap_deleted'])
            except LDAPException as e:
                return Response({'detail': f'Chyba LDAP: {e}'}, status=400)

        key.delete()
        audit_log(request, 'delete_key', key.ldap_username, {})
        return Response(status=204)


class TempKeyQRView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request, pk):
        try:
            key = TempKey.objects.get(pk=pk)
        except TempKey.DoesNotExist:
            return Response({'detail': 'Kľúč nenájdený.'}, status=404)

        # QR kód vo formáte WiFi: WIFI:T:WPA;S:Oratko;P:heslo;H:false;;
        wifi_string = f'WIFI:T:WPA;S:Oratko;P:{decrypt_password(key.ldap_password)};;'
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(wifi_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        return Response({
            'qr_code': f'data:image/png;base64,{img_base64}',
            'wifi_string': wifi_string,
            'username': key.ldap_username,
        })


class TempKeyResendEmailView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            key = TempKey.objects.get(pk=pk)
        except TempKey.DoesNotExist:
            return Response({'detail': 'Kľúč nenájdený.'}, status=404)

        email = request.data.get('email', '').strip()
        if not email:
            return Response({'detail': 'Zadaj emailovú adresu.'}, status=400)

        from .tasks import send_key_email
        send_key_email.delay(str(key.id), email)
        return Response({'detail': f'Email odoslaný na {email}.'})
