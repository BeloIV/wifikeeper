from django.apps import AppConfig


class KeysConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.keys'

    def ready(self):
        # Registruj periodické tasky pri štarte
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
            pass
