import logging

logger = logging.getLogger(__name__)


def ssh_deauth_mac(nas_ip: str, mac: str) -> bool:
    """
    SSH na AP a deautentifikuje klienta cez hostapd_cli na všetkých Oratko rozhraniach.
    mac: formát 06-39-C2-CB-91-F5 alebo 06:39:c2:cb:91:f5
    Vráti True ak aspoň jedno rozhranie hlásilo úspech.
    """
    import paramiko
    from django.conf import settings

    ssh_user = settings.AP_SSH_USER
    ssh_pass = settings.AP_SSH_PASSWORD
    if not ssh_user or not ssh_pass:
        return False

    mac_colon = mac.replace('-', ':').lower()

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(nas_ip, username=ssh_user, password=ssh_pass, timeout=5)

        _, out, _ = ssh.exec_command(
            "for i in $(ls /var/run/hostapd/ | grep -v '\\.pid'); do "
            "  ssid=$(hostapd_cli -p /var/run/hostapd -i $i get_config 2>/dev/null | grep '^ssid=' | cut -d= -f2); "
            "  [ \"$ssid\" = 'Oratko' ] && echo $i; "
            "done"
        )
        oratko_ifaces = out.read().decode().split()

        success = False
        for iface in oratko_ifaces:
            # Flush PMKSA cache – forces full EAP re-auth on reconnect (no AP-side PMK cache)
            ssh.exec_command(f'hostapd_cli -p /var/run/hostapd -i {iface} pmksa_flush')
            _, out, _ = ssh.exec_command(
                f'hostapd_cli -p /var/run/hostapd -i {iface} deauthenticate {mac_colon}'
            )
            result = out.read().decode().strip()
            if 'OK' in result:
                success = True
                logger.info(f'SSH deauth: {mac_colon} odpojený cez {iface} na {nas_ip}')

        ssh.close()
        return success
    except Exception as e:
        logger.warning(f'SSH deauth zlyhal pre {mac_colon} na {nas_ip}: {e}')
        return False
