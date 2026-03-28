#!/usr/bin/env bash
# test-email.sh – odošle testovací email cez Django/Brevo
#
# Použitie:
#   bash scripts/test-email.sh                        # pošle na ADMIN_EMAIL z .env
#   bash scripts/test-email.sh jan@example.com        # pošle na zadanú adresu

set -euo pipefail

# ── Načítaj .env ──────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [[ -f "$ENV_FILE" ]]; then
  set -o allexport
  source "$ENV_FILE"
  set +o allexport
fi

RECIPIENT="${1:-${ADMIN_EMAIL:-}}"
SENDER="${2:-no-reply@${DOMAIN:-salezianipresov.xyz}}"

if [[ -z "$RECIPIENT" ]]; then
  echo "ERROR: Zadaj príjemcu ako argument alebo nastav ADMIN_EMAIL v .env" >&2
  echo "       Použitie: bash scripts/test-email.sh [komu@example.com] [od@example.com]" >&2
  exit 1
fi

echo "========================================"
echo " Test emailu"
echo " Od   : $SENDER"
echo " Komu : $RECIPIENT"
echo "========================================"
echo ""

docker compose -f "$SCRIPT_DIR/../docker-compose.yml" exec backend \
  python manage.py shell -c "
from django.core.mail import send_mail

recipient = '$RECIPIENT'
sender    = '$SENDER'

import datetime
now = datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')

result = send_mail(
    subject='[WiFi Oratko] Test odosielania emailov',
    message=f'''Ahoj,

tento email bol odoslaný automaticky ako overenie SMTP konfigurácie.

  Odosielateľ : {sender}
  Príjemca    : {recipient}
  Čas odoslania: {now}

Ak si dostal tento email, Brevo SMTP relay funguje správne.

--
WiFi správca – Saleziánske oratorium Prešov
''',
    from_email=sender,
    recipient_list=[recipient],
    fail_silently=False,
)
print(f'  Od      : {sender}')
print(f'  Komu    : {recipient}')
print(f'  Výsledok: {\"OK – odoslaný\" if result else \"FAIL – email nebol odoslaný\"}')
"

echo ""
echo "========================================"
