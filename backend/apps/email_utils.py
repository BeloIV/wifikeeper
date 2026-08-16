"""Zdieľané pomôcky pre HTML emaily – logo vkladané ako inline (CID) príloha."""
from email.mime.image import MIMEImage
from pathlib import Path

from django.conf import settings

LOGO_PATH = Path(settings.BASE_DIR) / 'assets' / 'email-logo.png'
LOGO_CID = 'wifikeeper-logo'

# Vlož do <head>/<body> emailu namiesto textového nadpisu.
LOGO_HTML_TAG = (
    f'<img src="cid:{LOGO_CID}" alt="WiFi Manager" width="56" height="56" '
    f'style="display:block;margin:0 auto 12px;border-radius:12px;">'
)


def attach_logo(msg):
    """Pripojí logo appky ako inline obrázok (cid) k EmailMultiAlternatives správe."""
    if not LOGO_PATH.exists():
        return
    with open(LOGO_PATH, 'rb') as f:
        logo = MIMEImage(f.read())
    logo.add_header('Content-ID', f'<{LOGO_CID}>')
    logo.add_header('Content-Disposition', 'inline', filename='logo.png')
    msg.mixed_subtype = 'related'
    msg.attach(logo)
