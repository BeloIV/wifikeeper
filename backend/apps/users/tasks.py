"""
Celery tasky pre správu WiFi používateľov.
"""
import logging
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)

DEVICE_LIMIT = 2


@shared_task
def send_user_credentials_email(email: str, username: str, password: str, group_label: str, support_email: str = None):
    """
    Pošle vygenerované prihlasovacie údaje novému WiFi používateľovi emailom.
    """
    support = support_email or settings.ADMIN_EMAIL
    subject = 'Prístupové údaje na WiFi – Oratko'

    text_body = (
        f'Dobrý deň,\n\n'
        f'Bol vám vytvorený prístup na WiFi sieť Oratko.\n\n'
        f'  Sieť:   Oratko\n'
        f'  Login:  {username}\n'
        f'  Heslo:  {password}\n\n'
        f'UPOZORNENIE: Heslo je vygenerované výhradne pre vás. Je zakázané ho zdieľať s inými osobami.\n\n'
        f'iOS:\n'
        f'  Vyberte sieť Oratko → zadajte login a heslo → klepnite "Dôverovať" na certifikát.\n\n'
        f'Android:\n'
        f'  Vyberte sieť Oratko, nastavte:\n'
        f'    EAP metóda: PEAP\n'
        f'    Fáza 2: MSCHAPV2\n'
        f'    Certifikát CA: Neoverovat / Do not validate\n'
        f'    Identita: {username}\n'
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
                bol vám vytvorený prístup na WiFi sieť <strong>Oratko</strong>.
              </p>

              <!-- Credentials box -->
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4ff;border:1px solid #c7d7fd;border-radius:8px;margin-bottom:20px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="padding:6px 0;color:#6b7280;font-size:13px;width:80px;">Sieť</td>
                        <td style="padding:6px 0;color:#111827;font-size:15px;font-weight:700;">Oratko</td>
                      </tr>
                      <tr>
                        <td style="padding:6px 0;color:#6b7280;font-size:13px;">Login</td>
                        <td style="padding:6px 0;color:#111827;font-size:15px;font-family:monospace;">{username}</td>
                      </tr>
                      <tr>
                        <td style="padding:6px 0;color:#6b7280;font-size:13px;">Heslo</td>
                        <td style="padding:6px 0;">
                          <span style="background:#1d4ed8;color:#ffffff;font-family:monospace;font-size:18px;font-weight:700;letter-spacing:2px;padding:4px 12px;border-radius:4px;">{password}</span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- No-sharing warning -->
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;margin-bottom:16px;">
                <tr>
                  <td style="padding:12px 16px;">
                    <p style="margin:0;color:#92400e;font-size:13px;line-height:1.5;">
                      <strong>Upozornenie:</strong> Heslo je vygenerované výhradne pre vás. Je <strong>zakázané ho zdieľať</strong> s inými osobami.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- iOS instructions -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">
                <tr>
                  <td style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:16px 20px;">
                    <p style="margin:0 0 8px;color:#166534;font-size:13px;font-weight:700;">🍎 iPhone / iPad (iOS)</p>
                    <p style="margin:0;color:#374151;font-size:13px;line-height:1.7;">
                      1. Otvorte <strong>Nastavenia → Wi-Fi</strong><br>
                      2. Vyberte sieť <strong>Oratko</strong><br>
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
                      2. Vyberte sieť <strong>Oratko</strong><br>
                      3. Nastavte:<br>
                      &nbsp;&nbsp;&nbsp;• EAP metóda: <strong>PEAP</strong><br>
                      &nbsp;&nbsp;&nbsp;• Fáza 2: <strong>MSCHAPV2</strong><br>
                      &nbsp;&nbsp;&nbsp;• Certifikát CA: <strong>Neoverovat</strong> (Do not validate)<br>
                      &nbsp;&nbsp;&nbsp;• Identita: <strong>{username}</strong><br>
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
            <td style="background:#f9fafb;border-top:1px solid #e5e7eb;padding:16px 32px;text-align:center;margin-top:24px;">
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
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send()
    except Exception as exc:
        logger.error(f'Chyba pri odosielaní emailu na {email}: {exc}')
        raise


@shared_task
def send_admin_invitation_email(email: str, role: str, invitation_url: str, expires_days: int = 7):
    """
    Pošle pozvánku novému adminovi s odkazom na registráciu.
    """
    role_labels = {'superadmin': 'Superadmin', 'admin': 'Admin', 'readonly': 'Len čítanie'}
    role_label = role_labels.get(role, role)
    subject = 'Pozvánka do WiFi správcu – Oratko'

    text_body = (
        f'Dobrý deň,\n\n'
        f'Boli ste pozvaní do systému správy WiFi Oratko s rolou: {role_label}.\n\n'
        f'Zaregistrujte sa cez tento odkaz (platný {expires_days} dní):\n'
        f'{invitation_url}\n\n'
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
              <h1 style="margin:8px 0 0;color:#ffffff;font-size:22px;font-weight:700;">Pozvánka do WiFi správcu</h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px;">
              <p style="margin:0 0 24px;color:#374151;font-size:15px;line-height:1.6;">
                Dobrý deň,<br>
                boli ste pozvaní do systému správy WiFi siete <strong>Oratko</strong>.
              </p>

              <!-- Role box -->
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4ff;border:1px solid #c7d7fd;border-radius:8px;margin-bottom:24px;">
                <tr>
                  <td style="padding:16px 24px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="padding:4px 0;color:#6b7280;font-size:13px;width:80px;">Email</td>
                        <td style="padding:4px 0;color:#111827;font-size:14px;font-family:monospace;">{email}</td>
                      </tr>
                      <tr>
                        <td style="padding:4px 0;color:#6b7280;font-size:13px;">Rola</td>
                        <td style="padding:4px 0;color:#111827;font-size:14px;font-weight:700;">{role_label}</td>
                      </tr>
                      <tr>
                        <td style="padding:4px 0;color:#6b7280;font-size:13px;">Platnosť</td>
                        <td style="padding:4px 0;color:#111827;font-size:14px;">{expires_days} dní</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
                <tr>
                  <td align="center">
                    <a href="{invitation_url}" style="display:inline-block;background:#1d4ed8;color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;padding:14px 32px;border-radius:8px;">
                      Zaregistrovať sa
                    </a>
                  </td>
                </tr>
              </table>

              <p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.6;word-break:break-all;">
                Alebo skopíruj odkaz: <a href="{invitation_url}" style="color:#1d4ed8;">{invitation_url}</a>
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
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send()
    except Exception as exc:
        logger.error(f'Chyba pri odosielaní pozvánky na {email}: {exc}')
        raise





def send_device_limit_email(email: str, username: str):
    """Odošle notifikačný email o prekročení limitu zariadení."""
    subject = 'Limit zariadení prekročený – WiFi Oratko'

    text_body = (
        f'Dobrý deň,\n\n'
        f'Pokúsili ste sa pripojiť ďalšie zariadenie na WiFi sieť Oratko, '
        f'no dosiahli ste maximálny limit {DEVICE_LIMIT} súčasne pripojených zariadení.\n\n'
        f'Prístup novému zariadeniu bol zamietnutý. Vaše pôvodné zariadenia zostávajú pripojené.\n\n'
        f'Prekročili ste limit povolených zariadení. '
        f'Kontaktujte support alebo oslovte saleziána v oratku.\n\n'
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
            <td style="background:#dc2626;padding:28px 32px;text-align:center;">
              <p style="margin:0;color:#ffffff;font-size:13px;letter-spacing:1px;text-transform:uppercase;opacity:0.8;">Saleziánske oratórium Prešov</p>
              <h1 style="margin:8px 0 0;color:#ffffff;font-size:22px;font-weight:700;">Limit zariadení prekročený</h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px;">
              <p style="margin:0 0 20px;color:#374151;font-size:15px;line-height:1.6;">
                Dobrý deň,<br>
                pokúsili ste sa pripojiť ďalšie zariadenie na WiFi sieť <strong>Oratko</strong>,
                no dosiahli ste maximálny limit <strong>{DEVICE_LIMIT} súčasne pripojených zariadení</strong>.
              </p>

              <!-- Warning box -->
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;margin-bottom:24px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <p style="margin:0 0 8px;color:#991b1b;font-size:14px;font-weight:700;">Prístup zamietnutý</p>
                    <p style="margin:0;color:#7f1d1d;font-size:14px;line-height:1.6;">
                      Nové zariadenie nebolo pripojené. Vaše pôvodné zariadenia zostávajú funkčné.
                    </p>
                  </td>
                </tr>
              </table>

              <p style="margin:0 0 16px;color:#374151;font-size:15px;line-height:1.6;font-weight:600;">
                Prekročili ste limit povolených zariadení.
              </p>
              <p style="margin:0;color:#6b7280;font-size:14px;line-height:1.6;">
                Kontaktujte support alebo oslovte saleziána v oratku.
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

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send()
