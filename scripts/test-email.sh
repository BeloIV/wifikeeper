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

result = send_mail(
    subject='[wifikeeper] Test emailu',
    message='Cau Didi, toto je testovací email z wifikeepera. ',
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
