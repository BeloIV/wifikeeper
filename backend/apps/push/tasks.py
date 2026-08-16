"""Celery tasky pre správu push subscriptions."""
import logging

from celery import shared_task
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

# Ak appku nikto neotvoril (heartbeat) dlhšie, považujeme subscription za orphan
# (napr. appka bola zmazaná z plochy telefónu). Apple Web Push to nevie oznámiť
# spoľahlivo cez chybový status, takže sa to rieši týmto TTL.
# Superadmin appku neotvára denne, preto dlhšie okno + varovanie pred zmazaním,
# ktoré zároveň funguje ako heartbeat (otvorenie appky TTL resetuje).
STALE_AFTER_DAYS = 30
WARN_BEFORE_DAYS = 3


@shared_task
def warn_and_cleanup_stale_push_subscriptions():
    from .models import PushSubscription
    from .views import _send_push

    now = timezone.now()
    delete_cutoff = now - timedelta(days=STALE_AFTER_DAYS)
    warn_cutoff = now - timedelta(days=STALE_AFTER_DAYS - WARN_BEFORE_DAYS)

    # 1. Varovanie – posledné WARN_BEFORE_DAYS dní pred zmazaním príde pripomienka
    # KAŽDÝ deň (nie len raz), aby si mal opakovanú šancu appku otvoriť. Kontrola
    # "warned_at starší ako 20h" zabraňuje duplicitnému odoslaniu v ten istý deň,
    # ak by task bežal viackrát.
    to_warn = PushSubscription.objects.filter(
        last_seen__lt=warn_cutoff,
        last_seen__gte=delete_cutoff,
    ).exclude(warned_at__gte=now - timedelta(hours=20))
    warned = 0
    for sub in to_warn:
        # Počítané od poslednej aktivity, nie ako rozdiel dvoch "now" cutoffov —
        # odčítanie dvoch nezávisle vypočítaných "now" hodnôt (aj keď len pár ms od seba)
        # vedelo pri zaokrúhlení .days nadol posunúť výsledok o celý deň nižšie.
        days_inactive = (now - sub.last_seen).days
        days_left = max(1, STALE_AFTER_DAYS - days_inactive)
        _send_push(sub, {
            'title': 'WiFi Manager',
            'body': f'Toto zariadenie bude o {days_left} {"deň" if days_left == 1 else "dni"} odobraté '
                    f'z notifikácií pre neaktivitu. Otvor appku pre pokračovanie.',
            'data': {'url': '/dashboard/notifications'},
        })
        sub.warned_at = now
        sub.save(update_fields=['warned_at'])
        warned += 1
    if warned:
        logger.info(f'Poslané denné varovanie o odobratí {warned} push subscriptions')

    # 2. Mazanie – zariadenia bez heartbeatu dlhšie ako STALE_AFTER_DAYS (dostali varovanie a nezareagovali)
    stale = PushSubscription.objects.filter(last_seen__lt=delete_cutoff)
    deleted = stale.count()
    if deleted:
        stale.delete()
        logger.info(f'Zmazaných {deleted} neaktívnych push subscriptions (last_seen > {STALE_AFTER_DAYS} dní)')

    return {'warned': warned, 'deleted': deleted}
