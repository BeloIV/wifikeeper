"""
Celery tasky pre správu dočasných kľúčov.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

logger = logging.getLogger(__name__)



@shared_task(bind=True, max_retries=3)
def cleanup_expired_keys(self):
    """Bežný Celery task – spúšťa sa každých 5 minút."""
    from .models import TempKey
    from apps.users import ldap_service as ldap

    now = timezone.now()
    to_cleanup = TempKey.objects.filter(
        ldap_deleted=False,
    ).filter(
        models_q := __import__('django.db.models', fromlist=['Q']).Q(expires_at__lt=now) |
                    __import__('django.db.models', fromlist=['Q']).Q(used=True)
    )

    cleaned = 0
    for key in to_cleanup:
        try:
            user = ldap.get_user(key.ldap_username)
            if user:
                ldap.delete_user(key.ldap_username)
            key.ldap_deleted = True
            key.save(update_fields=['ldap_deleted'])
            cleaned += 1
            logger.info(f'Zmazaný LDAP účet pre kľúč {key.ldap_username}')
        except Exception as exc:
            logger.error(f'Chyba pri mazaní LDAP účtu {key.ldap_username}: {exc}')

    if cleaned:
        logger.info(f'Cleanup: zmazaných {cleaned} dočasných LDAP účtov')
    return cleaned


@shared_task
def cleanup_expired_keys_safe():
    """Bezpečná verzia cleanup_expired_keys bez cyklických importov."""
    from .models import TempKey
    from apps.users import ldap_service as ldap
    from django.db.models import Q

    now = timezone.now()
    to_cleanup = TempKey.objects.filter(
        ldap_deleted=False
    ).filter(
        Q(expires_at__lt=now) | Q(used=True)
    )

    cleaned = 0
    for key in to_cleanup:
        try:
            user = ldap.get_user(key.ldap_username)
            if user:
                ldap.delete_user(key.ldap_username)
            key.ldap_deleted = True
            key.save(update_fields=['ldap_deleted'])
            cleaned += 1
        except Exception as exc:
            logger.error(f'Chyba pri mazaní LDAP účtu {key.ldap_username}: {exc}')

    return cleaned



def _coa_disconnect_user(username: str) -> int:
    """SSH deauth pre všetky aktívne RADIUS sessions daného používateľa."""
    from apps.sessions.models import RadiusSession
    from apps.sessions.utils import ssh_deauth_mac
    from django.utils import timezone

    sessions = RadiusSession.objects.filter(
        username=username,
        acct_stop_time__isnull=True,
    )

    disconnected = 0
    for session in sessions:
        nas_ip = str(session.nas_ip_address)
        kicked = ssh_deauth_mac(nas_ip, session.calling_station_id)
        session.acct_stop_time = timezone.now()
        session.acct_terminate_cause = 'Admin-Reset'
        session.save(update_fields=['acct_stop_time', 'acct_terminate_cause'])
        if kicked:
            disconnected += 1
            logger.info(f'SSH deauth: odpojený {username} zo {nas_ip}')

    return disconnected


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def expire_temp_key(self, key_id: str):
    """
    Spúšťa sa presne v čase expirácie časového kľúča (apply_async eta=expires_at).
    1. Vymaže radreply → RADIUS odmietne nové autentifikácie okamžite
    2. Odošle CoA Disconnect-Request pre všetky aktívne sessions
    3. Vymaže LDAP účet a označí kľúč ako použitý
    """
    from .models import TempKey
    from apps.users import ldap_service as ldap
    from django.db import connection

    try:
        key = TempKey.objects.get(id=key_id)
    except TempKey.DoesNotExist:
        return

    if key.ldap_deleted:
        return

    username = key.ldap_username

    # 1. Vymaž radreply – nové pokusy o autentifikáciu budú odmietnuté
    with connection.cursor() as cur:
        cur.execute('DELETE FROM radreply WHERE username = %s', [username])

    # 2. Odpoj všetkých aktuálne pripojených
    _coa_disconnect_user(username)

    # 3. Vymaž LDAP účet
    try:
        if ldap.get_user(username):
            ldap.delete_user(username)
        update_fields = ['ldap_deleted']
        key.ldap_deleted = True
        if not key.used:
            key.used = True
            key.used_at = timezone.now()
            update_fields += ['used', 'used_at']
        key.save(update_fields=update_fields)
        logger.info(f'expire_temp_key: kľúč {username} expiroval a bol zmazaný')
    except Exception as exc:
        logger.error(f'expire_temp_key: chyba LDAP pre {username}: {exc}')
        raise self.retry(exc=exc)

@shared_task
def send_key_email(key_id: str, recipient_email: str):
    """Pošle kľúč emailom hosťovi s QR kódom a iOS WiFi profilom."""
    from .models import TempKey
    from .crypto import decrypt_password

    try:
        key = TempKey.objects.get(id=key_id)
    except TempKey.DoesNotExist:
        return

    password = decrypt_password(key.ldap_password)
    ssid = 'Oratko'
    support = settings.ADMIN_EMAIL

    if key.key_type == TempKey.KeyType.ONE_TIME:
        validity_label = 'Jednorazový'
        validity_desc = '1 prihlásenie'
    elif key.key_type == TempKey.KeyType.MULTI_USE:
        validity_label = 'N-násobný'
        validity_desc = f'{key.max_uses} prihlásení'
    elif key.valid_hours:
        validity_label = 'Časový'
        validity_desc = f'{key.valid_hours} hodín (do {timezone.localtime(key.expires_at).strftime("%d.%m.%Y %H:%M")})'
    else:
        validity_label = 'Časový'
        validity_desc = f'do {timezone.localtime(key.expires_at).strftime("%d.%m.%Y %H:%M")}'

    text_body = (
        f'Dobrý deň,\n\n'
        f'Bol vám vytvorený prístup na WiFi sieť {ssid}.\n\n'
        f'  Sieť:     {ssid}\n'
        f'  Login:    {key.ldap_username}\n'
        f'  Heslo:    {password}\n'
        f'  Platnosť: {validity_label} – {validity_desc}\n\n'
        f'iOS:\n'
        f'  Vyberte sieť {ssid} → zobrazí sa certifikát → klepnite "Dôverovať".\n\n'
        f'Android:\n'
        f'  Vyberte sieť {ssid}, nastavte:\n'
        f'    EAP metóda: PEAP\n'
        f'    Fáza 2: MSCHAPV2\n'
        f'    Certifikát CA: Neoverovat / Do not validate\n'
        f'    Identita: {key.ldap_username}\n'
        f'    Heslo: {password}\n\n'
        f'Ak máte problém s pripojením, kontaktujte nás na {support}.\n\n'
        f'Saleziánske oratórium Prešov'
    )

    html_body = f'''<!DOCTYPE html>
<html lang="sk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:32px 16px;">
    <tr>
      <td align="center">
        <table width="520" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background:#1d4ed8;padding:28px 32px;text-align:center;">
              <p style="margin:0;color:#ffffff;font-size:13px;letter-spacing:1px;text-transform:uppercase;opacity:0.8;">Saleziánske oratórium Prešov</p>
              <h1 style="margin:8px 0 0;color:#ffffff;font-size:22px;font-weight:700;">Prístup na WiFi</h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px;">
              <p style="margin:0 0 24px;color:#374151;font-size:15px;line-height:1.6;">
                Dobrý deň,<br>
                bol vám vytvorený prístup na WiFi sieť <strong>{ssid}</strong>.
              </p>

              <!-- Credentials -->
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4ff;border:1px solid #c7d7fd;border-radius:8px;margin-bottom:20px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="padding:6px 0;color:#6b7280;font-size:13px;width:90px;">Sieť</td>
                        <td style="padding:6px 0;color:#111827;font-size:15px;font-weight:700;">{ssid}</td>
                      </tr>
                      <tr>
                        <td style="padding:6px 0;color:#6b7280;font-size:13px;">Login</td>
                        <td style="padding:6px 0;color:#111827;font-size:15px;font-family:monospace;">{key.ldap_username}</td>
                      </tr>
                      <tr>
                        <td style="padding:6px 0;color:#6b7280;font-size:13px;">Heslo</td>
                        <td style="padding:6px 0;">
                          <span style="background:#1d4ed8;color:#ffffff;font-family:monospace;font-size:18px;font-weight:700;letter-spacing:2px;padding:4px 12px;border-radius:4px;">{password}</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding:6px 0;color:#6b7280;font-size:13px;">Platnosť</td>
                        <td style="padding:6px 0;color:#374151;font-size:13px;">{validity_label} – {validity_desc}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- iOS instructions -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
                <tr>
                  <td style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:16px 20px;">
                    <p style="margin:0 0 8px;color:#166534;font-size:13px;font-weight:700;">🍎 iPhone / iPad (iOS)</p>
                    <p style="margin:0;color:#374151;font-size:13px;line-height:1.7;">
                      1. Otvorte <strong>Nastavenia → Wi-Fi</strong><br>
                      2. Vyberte sieť <strong>{ssid}</strong><br>
                      3. Zadajte login a heslo<br>
                      4. Zobrazí sa certifikát servera → klepnite <strong>Dôverovať</strong>
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Android instructions -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                <tr>
                  <td style="background:#fefce8;border:1px solid #fde68a;border-radius:8px;padding:16px 20px;">
                    <p style="margin:0 0 8px;color:#854d0e;font-size:13px;font-weight:700;">🤖 Android</p>
                    <p style="margin:0;color:#374151;font-size:13px;line-height:1.7;">
                      1. Otvorte <strong>Nastavenia → Wi-Fi</strong><br>
                      2. Vyberte sieť <strong>{ssid}</strong><br>
                      3. Nastavte:<br>
                      &nbsp;&nbsp;&nbsp;• EAP metóda: <strong>PEAP</strong><br>
                      &nbsp;&nbsp;&nbsp;• Fáza 2: <strong>MSCHAPV2</strong><br>
                      &nbsp;&nbsp;&nbsp;• Certifikát CA: <strong>Neoverovat</strong> (Do not validate)<br>
                      &nbsp;&nbsp;&nbsp;• Identita: <strong>{key.ldap_username}</strong><br>
                      &nbsp;&nbsp;&nbsp;• Heslo: <strong>{password}</strong>
                    </p>
                  </td>
                </tr>
              </table>

              <p style="margin:0;color:#6b7280;font-size:13px;line-height:1.6;">
                Ak máte problém s pripojením, kontaktujte nás na
                <a href="mailto:{support}" style="color:#1d4ed8;text-decoration:none;">{support}</a>.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f9fafb;border-top:1px solid #e5e7eb;padding:16px 32px;text-align:center;">
              <p style="margin:0;color:#9ca3af;font-size:12px;">Saleziánske oratórium Prešov · WiFi správca</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>'''

    try:
        msg = EmailMultiAlternatives(
            subject='Prístupové údaje na WiFi – Oratko',
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send()

        key.email_sent_to = recipient_email
        key.save(update_fields=['email_sent_to'])

    except Exception as exc:
        logger.error(f'Chyba pri odosielaní emailu na {recipient_email}: {exc}')
        raise
