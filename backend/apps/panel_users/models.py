from django.contrib.auth.models import AbstractUser
from django.db import models


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
