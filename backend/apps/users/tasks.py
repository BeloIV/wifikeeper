"""
Celery tasky pre správu WiFi používateľov.
"""
import logging
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)


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
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4ff;border:1px solid #c7d7fd;border-radius:8px;margin-bottom:24px;">
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
