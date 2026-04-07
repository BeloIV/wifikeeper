import sys
from django.apps import AppConfig


class SessionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sessions'
    label = 'radius_sessions'
    verbose_name = 'RADIUS sessions'

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(_register_periodic_tasks, sender=self)

        # Nespúšťaj listener pri migrate/makemigrations/shell príkazoch
        noisy_commands = {'migrate', 'makemigrations', 'shell', 'collectstatic', 'test'}
        if noisy_commands.isdisjoint(sys.argv):
            from .listeners import start_device_limit_listener
            start_device_limit_listener()


def _register_periodic_tasks(sender, **kwargs):
    """Zaregistruje verify_active_sessions ako periodic task v django_celery_beat."""
    try:
        import json
        from django_celery_beat.models import IntervalSchedule, PeriodicTask

        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=5,
            period=IntervalSchedule.MINUTES,
        )
        PeriodicTask.objects.get_or_create(
            name='Overenie aktívnych sessions',
            defaults={
                'task': 'apps.sessions.tasks.verify_active_sessions',
                'interval': schedule,
                'args': json.dumps([]),
            },
        )
    except Exception:
        pass  # django_celery_beat tabuľky ešte nemusia existovať pri prvej migrácii
