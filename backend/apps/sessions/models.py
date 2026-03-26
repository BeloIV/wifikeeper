from django.db import models


class RadiusSession(models.Model):
    """
    RADIUS accounting záznamy zapísané FreeRADIUSom cez rlm_sql.
    Táto tabuľka je primárne plnená FreeRADIUSom, nie Djangom.
    """
    acct_session_id = models.CharField(max_length=64, verbose_name='Session ID')
    acct_unique_id = models.CharField(max_length=32, blank=True, verbose_name='Unique ID')
    username = models.CharField(max_length=64, db_index=True, verbose_name='Používateľ')
    realm = models.CharField(max_length=64, blank=True)
    nas_ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='NAS IP')
    nas_port_id = models.CharField(max_length=15, blank=True, verbose_name='NAS Port')
    nas_port_type = models.CharField(max_length=32, blank=True)
    nas_identifier = models.CharField(max_length=64, blank=True, verbose_name='AP meno')
    acct_start_time = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='Začiatok')
    acct_update_time = models.DateTimeField(null=True, blank=True, verbose_name='Posledný update')
    acct_stop_time = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='Koniec')
    acct_session_time = models.IntegerField(null=True, blank=True, verbose_name='Trvanie (s)')
    acct_authentic = models.CharField(max_length=32, blank=True)
    connect_info_start = models.CharField(max_length=50, blank=True, verbose_name='Rýchlosť pri pripojení')
    connect_info_stop = models.CharField(max_length=50, blank=True)
    acct_input_octets = models.BigIntegerField(null=True, blank=True, verbose_name='Stiahnuté (B)')
    acct_output_octets = models.BigIntegerField(null=True, blank=True, verbose_name='Odoslané (B)')
    called_station_id = models.CharField(max_length=50, blank=True, db_index=True, verbose_name='AP:SSID')
    calling_station_id = models.CharField(max_length=50, blank=True, verbose_name='MAC zariadenia')
    acct_terminate_cause = models.CharField(max_length=32, blank=True, verbose_name='Dôvod ukončenia')
    service_type = models.CharField(max_length=32, blank=True)
    framed_protocol = models.CharField(max_length=32, blank=True)
    framed_ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP zariadenia')

    class Meta:
        db_table = 'radius_sessions'
        managed = True
        ordering = ['-acct_start_time']
        verbose_name = 'RADIUS session'
        verbose_name_plural = 'RADIUS sessions'
        indexes = [
            models.Index(fields=['username', 'acct_stop_time']),
            models.Index(fields=['called_station_id']),
        ]

    def __str__(self):
        return f'{self.username} @ {self.nas_identifier} ({self.acct_session_id})'

    @property
    def is_active(self):
        return self.acct_stop_time is None

    @property
    def ssid(self):
        """Extrahuje SSID z called_station_id (formát: AA:BB:CC:DD:EE:FF:SSID)"""
        if ':' in self.called_station_id:
            parts = self.called_station_id.split(':')
            if len(parts) > 6:
                return ':'.join(parts[6:])
        return self.called_station_id

    @property
    def ap_mac(self):
        """Extrahuje MAC adresu AP z called_station_id"""
        if ':' in self.called_station_id:
            parts = self.called_station_id.split(':')
            if len(parts) >= 6:
                return ':'.join(parts[:6])
        return self.called_station_id

    @property
    def download_mb(self):
        if self.acct_input_octets:
            return round(self.acct_input_octets / 1024 / 1024, 2)
        return 0

    @property
    def upload_mb(self):
        if self.acct_output_octets:
            return round(self.acct_output_octets / 1024 / 1024, 2)
        return 0


class RadiusPostAuth(models.Model):
    """Log pokusov o autentifikáciu (Accept/Reject)."""
    username = models.CharField(max_length=64)
    password_attempt = models.CharField(max_length=64, blank=True, db_column='pass')
    reply = models.CharField(max_length=32, blank=True)
    called_station_id = models.CharField(max_length=50, blank=True, db_column='calledstationid')
    calling_station_id = models.CharField(max_length=50, blank=True, db_column='callingstationid')
    auth_date = models.DateTimeField(null=True, blank=True, db_column='authdate')

    class Meta:
        db_table = 'radius_postauth'
        managed = True
        ordering = ['-auth_date']
        verbose_name = 'Auth log'
