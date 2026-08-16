from django.conf import settings
from django.db import models
from django.utils import timezone


class PushSubscription(models.Model):
    """Web Push subscription (PWA) pre admina — endpoint identifikuje jedno zariadenie."""

    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='push_subscriptions',
    )
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    # Apple Web Push nevracia spoľahlivo 404/410 pre zrušené registrácie (endpoint
    # akceptuje aj mŕtve odbery), takže mazanie orphanov rieši heartbeat namiesto toho.
    last_seen = models.DateTimeField(default=timezone.now)
    # Kedy bola poslaná varovná notifikácia "toto zariadenie bude čoskoro odstránené".
    # Resetuje sa na None pri každom novom heartbeate, aby sa cyklus mohol opakovať.
    warned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Push subscription'
        verbose_name_plural = 'Push subscriptions'

    def __str__(self):
        return f'{self.admin_user.username} — {self.endpoint[:50]}...'


class PushNotification(models.Model):
    """História notifikácií (Grafana alerty aj testovacie) na zobrazenie v appke."""

    class Status(models.TextChoices):
        FIRING = 'firing', 'Firing'
        RESOLVED = 'resolved', 'Resolved'
        TEST = 'test', 'Test'

    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TEST)
    alertname = models.CharField(max_length=255, blank=True)
    severity = models.CharField(max_length=50, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Push notifikácia'
        verbose_name_plural = 'Push notifikácie'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.created_at:%Y-%m-%d %H:%M})'
