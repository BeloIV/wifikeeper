from django.apps import AppConfig


class PushConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.push'
    verbose_name = 'Push notifikácie'

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(_register_periodic_tasks, sender=self)


def _register_periodic_tasks(sender, **kwargs):
    """Zaregistruje warn_and_cleanup_stale_push_subscriptions ako periodic task.

    post_migrate namiesto priameho volania v ready() — pozri apps/keys/apps.py
    a apps/sessions/apps.py pre rovnaký (bezpečný) vzor.
    """
    try:
        from django_celery_beat.models import PeriodicTask, IntervalSchedule
        import json

        # Starý názov tasku (pred pridaním varovania) – zmazať, ak existuje z predošlej verzie
        PeriodicTask.objects.filter(
            task='apps.push.tasks.cleanup_stale_push_subscriptions'
        ).delete()

        daily, _ = IntervalSchedule.objects.get_or_create(
            every=1, period=IntervalSchedule.DAYS
        )

        PeriodicTask.objects.get_or_create(
            name='Warn and cleanup stale push subscriptions',
            defaults={
                'task': 'apps.push.tasks.warn_and_cleanup_stale_push_subscriptions',
                'interval': daily,
                'args': json.dumps([]),
            }
        )
    except Exception:
        pass  # django_celery_beat tabuľky ešte nemusia existovať pri prvej migrácii
