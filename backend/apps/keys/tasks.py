"""
Celery tasky pre správu dočasných kľúčov.
"""
import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def cleanup_expired_keys(self):
    """
    Bežný Celery task – spúšťa sa každých 5 minút.
    Maže LDAP účty expirovaných/použitých kľúčov.
    """
    from .models import TempKey
    from apps.users import ldap_service as ldap

    now = timezone.now()
    to_cleanup = TempKey.objects.filter(
        ldap_deleted=False,
    ).filter(
        # Expirované alebo použité
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
    """
    Bezpečná verzia cleanup_expired_keys bez cyklických importov.
    """
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


@shared_task
def notify_expiring_keys():
    """
    Pošle email adminovi o kľúčoch expirujúcich o menej ako 1 hodinu.
    Spúšťa sa každých 30 minút.
    """
    from .models import TempKey

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

    message = (
        f'Nasledujúce dočasné kľúče expirujú do 1 hodiny:\n\n'
        + '\n'.join(lines)
    )

    send_mail(
        subject='[wifi-manager] Blížiaca sa expirácia kľúčov',
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],
        fail_silently=True,
    )


@shared_task
def send_key_email(key_id: str, recipient_email: str):
    """
    Pošle kľúč emailom hosťovi.
    Zavolá sa priamo z API view po vytvorení kľúča.
    """
    from .models import TempKey

    from .crypto import decrypt_password

    try:
        key = TempKey.objects.get(id=key_id)
    except TempKey.DoesNotExist:
        return

    if key.key_type == TempKey.KeyType.ONE_TIME:
        validity_text = 'jednorazový (platný na jedno prihlásenie)'
    elif key.valid_hours:
        validity_text = f'časový (platný {key.valid_hours} hodín do {key.expires_at.strftime("%d.%m.%Y %H:%M")})'
    else:
        validity_text = f'časový (platný do {key.expires_at.strftime("%d.%m.%Y %H:%M")})'

    message = (
        f'Dobrý deň,\n\n'
        f'Vaše prihlasovacie údaje pre WiFi sieť Oratko:\n\n'
        f'  Sieť:   Oratko\n'
        f'  Meno:   {key.ldap_username}\n'
        f'  Heslo:  {decrypt_password(key.ldap_password)}\n'
        f'  Typ:    {validity_text}\n\n'
        f'Ak potrebujete pomoc s pripojením, kontaktujte správcu siete.\n\n'
        f'Saleziánske oratórium'
    )

    send_mail(
        subject='Prístupové údaje na WiFi – Oratko',
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient_email],
        fail_silently=False,
    )

    key.email_sent_to = recipient_email
    key.save(update_fields=['email_sent_to'])
