from django.apps import AppConfig


class KeysConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.keys'

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(_register_periodic_tasks, sender=self)


def _register_periodic_tasks(sender, **kwargs):
    """Zaregistruje cleanup_expired_keys_safe ako periodic task v django_celery_beat.

    post_migrate namiesto priameho volania v ready() — beží iba po skutočnom
    `manage.py migrate`, takže sa nikdy nespustí skôr, než existujú tabuľky
    django_celery_beat (na rozdiel od ready(), ktoré beží pri KAŽDOM štarte
    procesu vrátane celery workera/beatu, ktoré migrate nikdy nespúšťajú).
    """
    try:
        from django_celery_beat.models import PeriodicTask, IntervalSchedule
        import json

        every5, _ = IntervalSchedule.objects.get_or_create(
            every=5, period=IntervalSchedule.MINUTES
        )

        PeriodicTask.objects.get_or_create(
            name='Cleanup expired keys',
            defaults={
                'task': 'apps.keys.tasks.cleanup_expired_keys_safe',
                'interval': every5,
                'args': json.dumps([]),
            }
        )
    except Exception:
        pass  # django_celery_beat tabuľky ešte nemusia existovať pri prvej migrácii
