import secrets
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta


class AdminUser(AbstractUser):
    """
    Používateľ admin panelu. Prihlasuje sa cez LDAP (django-auth-ldap)
    alebo lokálnym účtom (pre bootstrapping superadmina).
    """

    class Role(models.TextChoices):
        SUPERADMIN = 'superadmin', 'Superadmin'
        ADMIN = 'admin', 'Admin'
        READONLY = 'readonly', 'Len čítanie'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.READONLY,
        verbose_name='Rola',
    )

    class Meta:
        verbose_name = 'Admin'
        verbose_name_plural = 'Admini'

    def is_superadmin(self):
        return self.role == self.Role.SUPERADMIN or self.is_superuser

    def is_admin(self):
        return self.role in (self.Role.SUPERADMIN, self.Role.ADMIN) or self.is_superuser

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


class AdminInvitation(models.Model):
    token = models.CharField(max_length=64, unique=True, editable=False)
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=AdminUser.Role.choices, default=AdminUser.Role.ADMIN)
    created_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True, related_name='sent_invitations')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Pozvánka'
        verbose_name_plural = 'Pozvánky'

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at

    def __str__(self):
        return f'Pozvánka pre {self.email} ({self.get_role_display()})'
