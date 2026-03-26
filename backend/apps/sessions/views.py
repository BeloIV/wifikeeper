import re
import subprocess
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from apps.panel_users.permissions import IsAdminOrReadOnly, IsAdmin
from apps.audit.utils import audit_log
from .models import RadiusSession
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
