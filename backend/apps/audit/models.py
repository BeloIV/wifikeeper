from django.db import models


class AuditLog(models.Model):
    """Audit log – každá write akcia v admin paneli."""

    admin_user = models.CharField(max_length=150, verbose_name='Admin')
    action = models.CharField(max_length=100, db_index=True, verbose_name='Akcia')
    target = models.CharField(max_length=200, blank=True, verbose_name='Cieľ')
    details = models.JSONField(default=dict, blank=True, verbose_name='Detaily')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP admina')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Čas')

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit log'
        verbose_name_plural = 'Audit logy'

    def __str__(self):
        return f'[{self.timestamp:%Y-%m-%d %H:%M}] {self.admin_user}: {self.action} → {self.target}'
