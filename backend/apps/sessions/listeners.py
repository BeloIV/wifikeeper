"""
PostgreSQL LISTEN/NOTIFY listener pre udalosti limitu zariadení.
Štartuje sa automaticky pri spustení Django procesu (AppConfig.ready).
Beží ako daemon vlákno – keď dostane notifikáciu, okamžite pošle email.
"""
import os
import select
import threading
import logging

logger = logging.getLogger(__name__)


def start_device_limit_listener():
    t = threading.Thread(target=_listen, name='device-limit-listener', daemon=True)
    t.start()


def _listen():
    import time
    import psycopg2

    while True:
        conn = None
        try:
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
            conn.set_isolation_level(0)  # AUTOCOMMIT – nutné pre LISTEN
            with conn.cursor() as cur:
                cur.execute('LISTEN device_limit_exceeded;')
            logger.info('Device limit listener: počúvam na notifikácie.')

            while True:
                # Čakáme max 60 s, potom skontrolujeme či je spojenie živé
                ready = select.select([conn], [], [], 60)
                if ready[0]:
                    conn.poll()
                    while conn.notifies:
                        notify = conn.notifies.pop(0)
                        _handle(notify.payload)

        except Exception as exc:
            logger.error(f'Device limit listener zlyhal: {exc}')
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

        time.sleep(5)  # Počkaj pred opätovným pripojením


def _handle(username: str):
    """Pošle email pre najstarší neodoslaný event tohto používateľa."""
    from django.db import transaction
    from apps.sessions.models import DeviceLimitEvent
    from apps.users import ldap_service
    from apps.users.tasks import send_device_limit_email

    try:
        with transaction.atomic():
            event = (
                DeviceLimitEvent.objects
                .select_for_update(skip_locked=True)
                .filter(username=username, notification_sent=False)
                .first()
            )
            if not event:
                return  # Iný worker už spracoval

            user = ldap_service.get_user(username)
            email = (user or {}).get('email', '').strip()

            if email:
                send_device_limit_email(email, username)
                logger.info(f'Odoslaná notifikácia o limite zariadení: {username} → {email}')

            event.notification_sent = True
            event.save(update_fields=['notification_sent'])

    except Exception as exc:
        logger.error(f'Chyba pri spracovaní device limit notifikácie pre {username}: {exc}')
