import sys
from django.apps import AppConfig


class SessionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sessions'
    label = 'radius_sessions'
    verbose_name = 'RADIUS sessions'

    def ready(self):
        # Nespúšťaj listener pri migrate/makemigrations/shell príkazoch
        noisy_commands = {'migrate', 'makemigrations', 'shell', 'collectstatic', 'test'}
        if noisy_commands.isdisjoint(sys.argv):
            from .listeners import start_device_limit_listener
            start_device_limit_listener()
