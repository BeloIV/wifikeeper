"""
Celery tasky pre správu dočasných kľúčov.
"""
import base64
import io
import logging
from datetime import timedelta

import qrcode
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

logger = logging.getLogger(__name__)


def _generate_wifi_qr_base64(ssid: str, password: str) -> str:
    wifi_string = f'WIFI:T:WPA;S:{ssid};P:{password};;'
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(wifi_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()



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
    """Odošle CoA Disconnect-Request pre všetky aktívne RADIUS sessions daného používateľa."""
    import re
    import subprocess
    from django.conf import settings
    from apps.sessions.models import RadiusSession

    secret = settings.RADIUS_COA_SECRET
    sessions = RadiusSession.objects.filter(
        username=username,
        acct_stop_time__isnull=True,
    )

    disconnected = 0
    for session in sessions:
        nas_ip = str(session.nas_ip_address)
        if not re.fullmatch(r'[A-Fa-f0-9\-]{8,64}', session.acct_session_id):
            logger.warning(f'CoA: neplatný acct_session_id pre {username}, preskakujem')
            continue
        cmd = ['radclient', '-x', f'{nas_ip}:3799', 'disconnect', secret]
        input_data = (
            f'Acct-Session-Id = {session.acct_session_id}\n'
            f'User-Name = {username}\n'
            f'NAS-IP-Address = {nas_ip}\n'
        )
        try:
            result = subprocess.run(cmd, input=input_data, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                disconnected += 1
                logger.info(f'CoA: odpojený {username} zo {nas_ip}')
            else:
                logger.warning(f'CoA zlyhalo pre {username} na {nas_ip}: {result.stderr.strip()}')
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f'CoA výnimka pre {username} na {nas_ip}: {e}')

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
def notify_expiring_keys():
    """Pošle email adminovi o kľúčoch expirujúcich o menej ako 1 hodinu."""
    from .models import TempKey
    from django.core.mail import send_mail

    now = timezone.now()
    soon = now + timedelta(hours=1)

    expiring = TempKey.objects.filter(
        ldap_deleted=False,
        used=False,
        expires_at__gt=now,
        expires_at__lte=soon,
    )

    if not expiring.exists():
        return

    lines = []
    for key in expiring:
        lines.append(
            f'- {key.ldap_username} ({key.label or "bez popisu"}) '
            f'expiruje {key.expires_at.strftime("%d.%m.%Y %H:%M")}'
        )

    send_mail(
        subject='[wifi-manager] Blížiaca sa expirácia kľúčov',
        message='Nasledujúce dočasné kľúče expirujú do 1 hodiny:\n\n' + '\n'.join(lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],
        fail_silently=True,
    )


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
        validity_desc = f'{key.valid_hours} hodín (do {key.expires_at.strftime("%d.%m.%Y %H:%M")})'
    else:
        validity_label = 'Časový'
        validity_desc = f'do {key.expires_at.strftime("%d.%m.%Y %H:%M")}'

    qr_b64 = _generate_wifi_qr_base64(ssid, password)

    text_body = (
        f'Dobrý deň,\n\n'
        f'Bol vám vytvorený prístup na WiFi sieť {ssid}.\n\n'
        f'  Sieť:     {ssid}\n'
        f'  Login:    {key.ldap_username}\n'
        f'  Heslo:    {password}\n'
        f'  Platnosť: {validity_label} – {validity_desc}\n\n'
        f'iOS: otvorte priloženú prílohu oratko-wifi.mobileconfig\n'
        f'Android: naskenujte QR kód fotoaparátom\n\n'
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
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4ff;border:1px solid #c7d7fd;border-radius:8px;margin-bottom:8px;">
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

              <!-- QR code -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
                <tr>
                  <td align="center">
                    <p style="margin:0 0 12px;color:#374151;font-size:13px;font-weight:600;">QR kód pre automatické pripojenie</p>
                    <img src="data:image/png;base64,{qr_b64}"
                         alt="WiFi QR kód"
                         width="180" height="180"
                         style="border-radius:8px;border:1px solid #e5e7eb;" />
                    <p style="margin:8px 0 0;color:#9ca3af;font-size:11px;">
                      iOS 11+ a Android 10+: naskenuj fotoaparátom → automaticky sa pripojí
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
