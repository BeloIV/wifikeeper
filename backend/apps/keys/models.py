import uuid
from django.db import models
from django.utils import timezone


class TempKey(models.Model):
    """
    Jednorazový alebo časovo obmedzený prístupový kľúč.
    Po vygenerovaní sa vytvorí LDAP účet v skupine 'docasny'.
    Celery task ho zmaže po expirácii / použití.
    """

    class KeyType(models.TextChoices):
        ONE_TIME = 'one_time', 'Jednorazový'
        TIMED = 'timed', 'Časový'
        MULTI_USE = 'multi_use', 'N-násobný'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=200, blank=True, verbose_name='Popis / meno hosťa')
    key_type = models.CharField(max_length=20, choices=KeyType.choices, verbose_name='Typ kľúča')

    # LDAP prihlasovacie údaje (generované automaticky)
    ldap_username = models.CharField(max_length=64, unique=True, verbose_name='LDAP meno')
    ldap_password = models.CharField(max_length=256, verbose_name='Heslo (šifrované Fernet)')

    # Platnosť
    valid_hours = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name='Platnosť (hodiny)',
        help_text='Len pre časový typ. Null = ručne definovaná expirácia.',
    )
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='Expiruje')
    used = models.BooleanField(default=False, verbose_name='Použitý / vyčerpaný')
    used_at = models.DateTimeField(null=True, blank=True, verbose_name='Čas posledného použitia')
    max_uses = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name='Max. počet použití',
        help_text='Len pre N-násobný typ.',
    )
    use_count = models.PositiveIntegerField(default=0, verbose_name='Počet použití')

    # Metadata
    created_by = models.ForeignKey(
        'panel_users.AdminUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_keys',
        verbose_name='Vytvoril',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Vytvorený')
    email_sent_to = models.EmailField(blank=True, verbose_name='Email odoslaný na')
    ldap_deleted = models.BooleanField(default=False, verbose_name='LDAP účet zmazaný')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Dočasný kľúč'
        verbose_name_plural = 'Dočasné kľúče'

    def __str__(self):
        return f'{self.ldap_username} ({self.get_key_type_display()}) – {self.label or "bez popisu"}'

    @property
    def is_expired(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

    @property
    def is_active(self):
        if self.ldap_deleted:
            return False
        if self.key_type == self.KeyType.MULTI_USE:
            return not self.used and (self.max_uses is None or self.use_count < self.max_uses)
        return not self.used and not self.is_expired
