"""
Celery tasky pre správu RADIUS sessions.
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


def _get_connected_macs_via_ssh(nas_ip: str) -> set | None:
    """
    SSH na AP a vráti set MAC adries (lowercase, colon) aktuálne pripojených klientov
    na Oratko SSID. Vráti None ak SSH zlyhalo (= netreba zatvárať sessions).
    """
    import paramiko
    from django.conf import settings

    ssh_user = getattr(settings, 'AP_SSH_USER', None)
    ssh_pass = getattr(settings, 'AP_SSH_PASSWORD', None)
    if not ssh_user or not ssh_pass:
        logger.warning('AP_SSH_USER/AP_SSH_PASSWORD nie sú nastavené, preskakujem overenie')
        return None

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(nas_ip, username=ssh_user, password=ssh_pass, timeout=5)

        # Nájdi rozhrania s SSID Oratko
        _, out, _ = ssh.exec_command(
            "for i in $(ls /var/run/hostapd/ | grep -v '\\.pid'); do "
            "  ssid=$(hostapd_cli -p /var/run/hostapd -i $i get_config 2>/dev/null"
            "         | grep '^ssid=' | cut -d= -f2); "
            "  [ \"$ssid\" = 'Oratko' ] && echo $i; "
            "done"
        )
        oratko_ifaces = out.read().decode().split()

        macs = set()
        for iface in oratko_ifaces:
            _, out, _ = ssh.exec_command(
                f'hostapd_cli -p /var/run/hostapd -i {iface} all_sta 2>/dev/null'
            )
            for line in out.read().decode().splitlines():
                line = line.strip()
                # Každá stanica začína riadkom s MAC adresou xx:xx:xx:xx:xx:xx
                if len(line) == 17 and line.count(':') == 5:
                    macs.add(line.lower())

        ssh.close()
        logger.debug(f'verify_sessions: {nas_ip} má {len(macs)} pripojených klientov')
        return macs

    except Exception as e:
        logger.warning(f'SSH get_connected_macs zlyhal pre {nas_ip}: {e}')
        return None


@shared_task
def verify_active_sessions():
    """
    Periodicky overuje či zariadenia s aktívnou RADIUS session sú stále pripojené.
    Zavrie sessions pre zariadenia, ktoré sa odpojili bez Accounting-Stop paketu
    (napr. po reštarte/rekonfigurácii AP alebo UniFi controllera).
    """
    from .models import RadiusSession

    open_sessions = list(
        RadiusSession.objects.filter(acct_stop_time__isnull=True)
        .only('id', 'username', 'nas_ip_address', 'calling_station_id')
    )

    if not open_sessions:
        return 0

    # Zoskup sessions podľa NAS IP aby sme SSH spojenie otvorili len raz na AP
    sessions_by_nas: dict[str, list] = {}
    for session in open_sessions:
        nas_ip = str(session.nas_ip_address)
        sessions_by_nas.setdefault(nas_ip, []).append(session)

    closed = 0
    for nas_ip, sessions in sessions_by_nas.items():
        connected_macs = _get_connected_macs_via_ssh(nas_ip)
        if connected_macs is None:
            # SSH zlyhalo – nechaj sessions otvorené, nefalšujeme stav
            continue

        now = timezone.now()
        for session in sessions:
            mac = session.calling_station_id.replace('-', ':').lower()
            if mac not in connected_macs:
                session.acct_stop_time = now
                session.acct_terminate_cause = 'Lost-Carrier'
                session.save(update_fields=['acct_stop_time', 'acct_terminate_cause'])
                closed += 1
                logger.info(
                    f'verify_sessions: uzavretá stará session '
                    f'{session.username} MAC={mac} NAS={nas_ip}'
                )

    if closed:
        logger.info(f'verify_sessions: celkom uzavretých {closed} starých sessions')
    return closed
