import re
import socket
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from apps.panel_users.permissions import IsAdminOrReadOnly, IsAdmin
from apps.audit.utils import audit_log
from .utils import ssh_deauth_mac
from .models import RadiusSession, UserDevice, UserDeviceLimit
from .serializers import RadiusSessionSerializer

logger = logging.getLogger(__name__)


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

        sessions = list(sessions)
        return Response(RadiusSessionSerializer(
            sessions, many=True, context=_session_display_names(sessions)
        ).data)


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

        # SSH deauth — okamžité odpojenie cez hostapd_cli
        kicked = ssh_deauth_mac(nas_ip, session.calling_station_id)

        # Označ session ako ukončenú v DB
        from django.utils import timezone
        session.acct_stop_time = timezone.now()
        session.acct_terminate_cause = 'Admin-Reset'
        session.save(update_fields=['acct_stop_time', 'acct_terminate_cause'])

        # Zablokuj používateľa (LDAP disabled + zmaž radreply) – zabrání opätovnému pripojeniu
        from apps.users import ldap_service as ldap
        try:
            ldap.set_active(username, False)
        except Exception as exc:
            logger.warning(f'Nepodarilo sa zablokovať LDAP účet {username}: {exc}')

        audit_log(request, 'disconnect_user', username, {'session_id': session_id, 'nas_ip': nas_ip, 'kicked': kicked})
        return Response({'detail': f'Používateľ {username} odpojený a zablokovaný.'})


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
            RadiusSessionSerializer(
                page, many=True, context=_session_display_names(page)
            ).data
        )


def _unifi_hostnames(mac_addresses: list[str]) -> dict[str, str]:
    """
    Vytiahne názvy zariadení (hostname, napr. "iPhone", "Redmi-12-5G") z databázy
    UniFi controllera pre zadané MAC adresy. Vracia {MAC v našom formáte: názov}.

    UniFi je jediný spoľahlivý zdroj – telefóny dnes používajú randomizované MAC
    adresy, takže z MAC sa nedá určiť ani výrobca, a reverzný DNS na WiFi klientov
    nefunguje (nemajú PTR záznam).

    Jeden dotaz pre všetky MAC naraz. Pri akomkoľvek probléme vráti prázdny dict –
    názvy sú len doplnková informácia, výpadok UniFi nesmie rozbiť zoznam zariadení.
    """
    from django.conf import settings

    if not mac_addresses or not settings.UNIFI_MONGO_USER:
        return {}

    # UniFi ukladá MAC malými písmenami s dvojbodkami, my máme veľké s pomlčkami.
    to_unifi = {m.replace('-', ':').lower(): m for m in mac_addresses}

    client = None
    try:
        from pymongo import MongoClient

        client = MongoClient(
            host=settings.UNIFI_MONGO_HOST,
            username=settings.UNIFI_MONGO_USER,
            password=settings.UNIFI_MONGO_PASS,
            authSource='admin',
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
            socketTimeoutMS=2000,
        )
        docs = client['unifi']['user'].find(
            {'mac': {'$in': list(to_unifi)}},
            {'mac': 1, 'hostname': 1, '_id': 0},
        )
        return {
            to_unifi[d['mac']]: d['hostname']
            for d in docs
            if d.get('hostname') and d.get('mac') in to_unifi
        }
    except Exception:
        logger.warning('Nepodarilo sa načítať názvy zariadení z UniFi', exc_info=True)
        return {}
    finally:
        if client is not None:
            client.close()


def _unifi_ap_names() -> dict[str, str]:
    """
    Názvy prístupových bodov z UniFi controllera: {IP adresa: názov}.
    Napr. {'192.168.1.230': 'Kostol'}. AP bez pomenovania v UniFi sa preskočia.
    Pri probléme vráti prázdny dict – zobrazí sa potom holá IP adresa.
    """
    from django.conf import settings

    if not settings.UNIFI_MONGO_USER:
        return {}

    client = None
    try:
        from pymongo import MongoClient

        client = MongoClient(
            host=settings.UNIFI_MONGO_HOST,
            username=settings.UNIFI_MONGO_USER,
            password=settings.UNIFI_MONGO_PASS,
            authSource='admin',
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
            socketTimeoutMS=2000,
        )
        docs = client['unifi']['device'].find({}, {'ip': 1, 'name': 1, '_id': 0})
        return {d['ip']: d['name'] for d in docs if d.get('ip') and d.get('name')}
    except Exception:
        logger.warning('Nepodarilo sa načítať názvy AP z UniFi', exc_info=True)
        return {}
    finally:
        if client is not None:
            client.close()


def _session_display_names(sessions) -> dict:
    """
    Pripraví názvy zariadení a AP pre zoznam sessions – hromadne, nie v cykle,
    aby to nerobilo N+1 dotazov.

    Názvy zariadení berie z user_devices.label (napĺňa sa z UniFi pri prezeraní
    zariadení používateľa), pre zvyšok doplní priamo z UniFi.
    """
    macs = {s.calling_station_id for s in sessions if s.calling_station_id}

    device_names = dict(
        UserDevice.objects.filter(mac_address__in=macs)
        .exclude(label='')
        .values_list('mac_address', 'label')
    )
    # Zariadenia, ktoré ešte nie sú v registri s názvom, skús doplniť z UniFi
    missing = [m for m in macs if m not in device_names]
    if missing:
        device_names.update(_unifi_hostnames(missing))

    return {'device_names': device_names, 'ap_names': _unifi_ap_names()}


def _resolve_device_name(mac_address: str) -> str:
    """
    Záloha, keď UniFi názov nepozná: reverse DNS z poslednej IP adresy zariadenia.
    IP berie z radius_sessions (framed_ip_address) – zapísaná FreeRADIUSom pri accountingu.
    Pri WiFi klientoch to väčšinou nevráti nič (nemajú PTR záznam).
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

        # Doplň/aktualizuj názov zariadenia – najprv hromadne z UniFi (jeden dotaz
        # pre všetky MAC naraz), reverzný DNS len ako záloha pre zvyšok.
        unifi_names = _unifi_hostnames([d.mac_address for d in devices])

        result = []
        for d in devices:
            name = unifi_names.get(d.mac_address) or _resolve_device_name(d.mac_address)
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

        # Samotné zmazanie z registra zariadenie NEODPOJÍ – ostalo by pripojené
        # (a ďalej používalo WiFi) až kým sa samo neodpojí. Preto ho aj reálne
        # deautentifikujeme na AP a uzavrieme jeho otvorené RADIUS sessions.
        from django.utils import timezone

        open_sessions = RadiusSession.objects.filter(
            username=username,
            calling_station_id=mac,
            acct_stop_time__isnull=True,
        )
        disconnected = 0
        for session in open_sessions:
            try:
                if ssh_deauth_mac(str(session.nas_ip_address), session.calling_station_id):
                    disconnected += 1
            except Exception:
                # Odpojenie na AP je best-effort – aj tak session uzavrieme,
                # aby stav v DB nezostal visieť ako "pripojený".
                logger.exception(
                    'Deauth zlyhal pri odstraneni zariadenia %s (%s)', mac, username
                )
            session.acct_stop_time = timezone.now()
            session.acct_terminate_cause = 'Admin-Reset'
            session.save(update_fields=['acct_stop_time', 'acct_terminate_cause'])

        audit_log(request, 'delete_user_device', username,
                  {'mac': mac, 'sessions_closed': len(open_sessions), 'deauthed': disconnected})
        return Response(status=204)
