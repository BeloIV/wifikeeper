import re
import socket
import subprocess
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from apps.panel_users.permissions import IsAdminOrReadOnly, IsAdmin
from apps.audit.utils import audit_log
from .models import RadiusSession, UserDevice, UserDeviceLimit
from .serializers import RadiusSessionSerializer


class LiveSessionsView(APIView):
    """Aktívne pripojenia (bez acct_stop_time)."""
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        sessions = RadiusSession.objects.filter(
            acct_stop_time__isnull=True
        ).order_by('-acct_start_time')

        ssid_filter = request.query_params.get('ssid')
        if ssid_filter:
            sessions = sessions.filter(called_station_id__icontains=ssid_filter)

        return Response(RadiusSessionSerializer(sessions, many=True).data)


class DisconnectUserView(APIView):
    """
    RADIUS CoA – odošle Disconnect-Request na NAS (UniFi AP).
    Vyžaduje: radiusclient alebo echo do /dev/udp (závislosť na nástroji `radclient`).
    """
    permission_classes = [IsAdmin]

    def post(self, request, session_id):
        try:
            session = RadiusSession.objects.get(
                acct_session_id=session_id,
                acct_stop_time__isnull=True,
            )
        except RadiusSession.DoesNotExist:
            return Response({'detail': 'Aktívna session nenájdená.'}, status=404)

        nas_ip = str(session.nas_ip_address)
        username = session.username

        # Validácia hodnôt z DB pred vložením do radclient stdin (C5)
        if not re.fullmatch(r'[A-Fa-f0-9\-]{8,64}', session.acct_session_id):
            return Response({'detail': 'Neplatný formát acct_session_id.'}, status=500)
        if not re.fullmatch(r'[a-zA-Z0-9._@\-]{1,64}', username):
            return Response({'detail': 'Neplatný formát username.'}, status=500)

        # Pošli CoA Disconnect-Request cez radclient
        from django.conf import settings
        radius_secret = settings.RADIUS_COA_SECRET  # Chýbajúci env var = fail loud (C4)

        cmd = [
            'radclient', '-x',
            f'{nas_ip}:3799',
            'disconnect',
            radius_secret,
        ]
        input_data = (
            f'Acct-Session-Id = {session.acct_session_id}\n'
            f'User-Name = {username}\n'
            f'NAS-IP-Address = {nas_ip}\n'
        )

        try:
            result = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=10,
            )
            success = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return Response({'detail': f'Chyba pri CoA: {e}'}, status=500)

        if success:
            audit_log(request, 'disconnect_user', username, {'session_id': session_id, 'nas_ip': nas_ip})
            return Response({'detail': f'Používateľ {username} odpojený.'})
        else:
            return Response({'detail': f'CoA zlyhalo: {result.stderr}'}, status=500)


class SessionHistoryView(APIView):
    """História pripojení s filtrovaním."""
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        qs = RadiusSession.objects.all()

        # Filtre
        username = request.query_params.get('username')
        ssid = request.query_params.get('ssid')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        search = request.query_params.get('search', '').strip()

        if username:
            qs = qs.filter(username__icontains=username)
        if ssid:
            qs = qs.filter(called_station_id__icontains=ssid)
        if date_from:
            qs = qs.filter(acct_start_time__date__gte=date_from)
        if date_to:
            qs = qs.filter(acct_start_time__date__lte=date_to)
        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(framed_ip_address__icontains=search) |
                Q(calling_station_id__icontains=search) |
                Q(called_station_id__icontains=search) |
                Q(nas_identifier__icontains=search)
            )

        # Stránkovanie cez DRF
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 50
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            RadiusSessionSerializer(page, many=True).data
        )


def _resolve_device_name(mac_address: str) -> str:
    """
    Zistí sieťové meno zariadenia cez reverse DNS z jeho poslednej IP adresy.
    IP berie z radius_sessions (framed_ip_address) – zapísaná FreeRADIUSom pri accountingu.
    """
    session = RadiusSession.objects.filter(
        calling_station_id__iexact=mac_address,
        framed_ip_address__isnull=False,
    ).order_by('-acct_start_time').first()

    if not session or not session.framed_ip_address:
        return ''

    try:
        hostname, _, _ = socket.gethostbyaddr(str(session.framed_ip_address))
        # Vráť len krátky hostname (bez domény)
        return hostname.split('.')[0]
    except (socket.herror, socket.gaierror):
        return ''


class UserDevicesView(APIView):
    """
    GET   /sessions/devices/<username>/  – zoznam registrovaných zariadení + limit
    PATCH /sessions/devices/<username>/  – zmena limitu zariadení
    """
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request, username):
        devices = list(UserDevice.objects.filter(username=username))
        limit_obj = UserDeviceLimit.objects.filter(username=username).first()

        # Doplň/aktualizuj sieťové meno pre každé zariadenie
        result = []
        for d in devices:
            name = _resolve_device_name(d.mac_address)
            if name and name != d.label:
                d.label = name
                d.save(update_fields=['label'])
            result.append({
                'mac_address': d.mac_address,
                'label': d.label,
                'first_seen': d.first_seen,
                'last_seen': d.last_seen,
            })

        return Response({
            'username': username,
            'max_devices': limit_obj.max_devices if limit_obj else 2,
            'devices': result,
        })

    def patch(self, request, username):
        if not request.user.is_admin():
            return Response({'detail': 'Nedostatočné oprávnenia.'}, status=403)
        max_devices = request.data.get('max_devices')
        if max_devices is None or not str(max_devices).isdigit() or int(max_devices) < 1:
            return Response({'detail': 'Neplatná hodnota max_devices.'}, status=400)
        limit_obj, _ = UserDeviceLimit.objects.get_or_create(username=username)
        limit_obj.max_devices = int(max_devices)
        limit_obj.save()
        audit_log(request, 'update_device_limit', username, {'max_devices': int(max_devices)})
        return Response({'max_devices': limit_obj.max_devices})


class UserDeviceDeleteView(APIView):
    """
    DELETE /sessions/devices/<username>/<mac>/ – odstrání zariadenie z registra
    (používateľ sa môže pripojiť s novým zariadením na uvoľnený slot)
    """
    permission_classes = [IsAdmin]

    def delete(self, request, username, mac):
        deleted, _ = UserDevice.objects.filter(username=username, mac_address=mac).delete()
        if not deleted:
            return Response({'detail': 'Zariadenie nenájdené.'}, status=404)
        audit_log(request, 'delete_user_device', username, {'mac': mac})
        return Response(status=204)
