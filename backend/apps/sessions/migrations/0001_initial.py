from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='RadiusPostAuth',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=64)),
                ('password_attempt', models.CharField(blank=True, db_column='pass', max_length=64)),
                ('reply', models.CharField(blank=True, max_length=32)),
                ('called_station_id', models.CharField(blank=True, db_column='calledstationid', max_length=50)),
                ('calling_station_id', models.CharField(blank=True, db_column='callingstationid', max_length=50)),
                ('auth_date', models.DateTimeField(blank=True, db_column='authdate', null=True)),
            ],
            options={
                'verbose_name': 'Auth log',
                'db_table': 'radius_postauth',
                'ordering': ['-auth_date'],
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='RadiusSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('acct_session_id', models.CharField(max_length=64, verbose_name='Session ID')),
                ('acct_unique_id', models.CharField(blank=True, max_length=32, verbose_name='Unique ID')),
                ('username', models.CharField(db_index=True, max_length=64, verbose_name='Používateľ')),
                ('realm', models.CharField(blank=True, max_length=64)),
                ('nas_ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='NAS IP')),
                ('nas_port_id', models.CharField(blank=True, max_length=15, verbose_name='NAS Port')),
                ('nas_port_type', models.CharField(blank=True, max_length=32)),
                ('nas_identifier', models.CharField(blank=True, max_length=64, verbose_name='AP meno')),
                ('acct_start_time', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Začiatok')),
                ('acct_update_time', models.DateTimeField(blank=True, null=True, verbose_name='Posledný update')),
                ('acct_stop_time', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Koniec')),
                ('acct_session_time', models.IntegerField(blank=True, null=True, verbose_name='Trvanie (s)')),
                ('acct_authentic', models.CharField(blank=True, max_length=32)),
                ('connect_info_start', models.CharField(blank=True, max_length=50, verbose_name='Rýchlosť pri pripojení')),
                ('connect_info_stop', models.CharField(blank=True, max_length=50)),
                ('acct_input_octets', models.BigIntegerField(blank=True, null=True, verbose_name='Stiahnuté (B)')),
                ('acct_output_octets', models.BigIntegerField(blank=True, null=True, verbose_name='Odoslané (B)')),
                ('called_station_id', models.CharField(blank=True, db_index=True, max_length=50, verbose_name='AP:SSID')),
                ('calling_station_id', models.CharField(blank=True, max_length=50, verbose_name='MAC zariadenia')),
                ('acct_terminate_cause', models.CharField(blank=True, max_length=32, verbose_name='Dôvod ukončenia')),
                ('service_type', models.CharField(blank=True, max_length=32)),
                ('framed_protocol', models.CharField(blank=True, max_length=32)),
                ('framed_ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP zariadenia')),
            ],
            options={
                'verbose_name': 'RADIUS session',
                'verbose_name_plural': 'RADIUS sessions',
                'db_table': 'radius_sessions',
                'ordering': ['-acct_start_time'],
                'managed': True,
                'indexes': [
                    models.Index(fields=['username', 'acct_stop_time'], name='radius_sess_usernam_e847bd_idx'),
                    models.Index(fields=['called_station_id'], name='radius_sess_called__0c4245_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='DeviceLimitEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=64, db_index=True)),
                ('blocked_mac', models.CharField(max_length=50, verbose_name='Zamietnuté MAC')),
                ('registered_macs', models.JSONField(default=list, verbose_name='Registrované MAC adresy')),
                ('event_time', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Čas udalosti')),
                ('notification_sent', models.BooleanField(default=False, db_index=True, verbose_name='Email odoslaný')),
            ],
            options={
                'db_table': 'device_limit_events',
                'ordering': ['-event_time'],
                'verbose_name': 'Udalosť limitu zariadení',
                'verbose_name_plural': 'Udalosti limitu zariadení',
            },
        ),
        migrations.CreateModel(
            name='UserDevice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=64, db_index=True)),
                ('mac_address', models.CharField(max_length=50, verbose_name='MAC adresa')),
                ('label', models.CharField(max_length=100, blank=True, verbose_name='Popis zariadenia')),
                ('first_seen', models.DateTimeField(auto_now_add=True, verbose_name='Prvé pripojenie')),
                ('last_seen', models.DateTimeField(auto_now=True, verbose_name='Posledné pripojenie')),
            ],
            options={
                'db_table': 'user_devices',
                'ordering': ['-last_seen'],
                'verbose_name': 'Zariadenie používateľa',
                'verbose_name_plural': 'Zariadenia používateľov',
                'unique_together': {('username', 'mac_address')},
            },
        ),
        migrations.CreateModel(
            name='UserDeviceLimit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=64, unique=True)),
                ('max_devices', models.PositiveSmallIntegerField(default=2, verbose_name='Max zariadení')),
            ],
            options={
                'db_table': 'user_device_limits',
                'verbose_name': 'Limit zariadení používateľa',
            },
        ),
        migrations.RunSQL(
            sql="""
                CREATE OR REPLACE FUNCTION check_and_register_device(p_username TEXT, p_mac TEXT)
                RETURNS TEXT AS $$
                DECLARE
                    v_max_devices   INTEGER;
                    v_device_count  INTEGER;
                    v_registered    JSONB;
                BEGIN
                    IF p_username IS NULL OR p_username = ''
                       OR p_mac IS NULL OR p_mac = '' THEN
                        RETURN 'OK';
                    END IF;

                    IF EXISTS (
                        SELECT 1 FROM user_devices
                        WHERE username = p_username AND mac_address = p_mac
                    ) THEN
                        UPDATE user_devices
                        SET last_seen = NOW()
                        WHERE username = p_username AND mac_address = p_mac;
                        RETURN 'OK';
                    END IF;

                    SELECT COALESCE(max_devices, 2) INTO v_max_devices
                    FROM user_device_limits WHERE username = p_username;
                    v_max_devices := COALESCE(v_max_devices, 2);

                    SELECT COUNT(*) INTO v_device_count
                    FROM user_devices WHERE username = p_username;

                    IF v_device_count >= v_max_devices THEN
                        SELECT COALESCE(jsonb_agg(mac_address), '[]'::jsonb)
                        INTO v_registered
                        FROM user_devices WHERE username = p_username;

                        INSERT INTO device_limit_events
                            (username, blocked_mac, registered_macs, notification_sent)
                        SELECT p_username, p_mac, v_registered, FALSE
                        WHERE NOT EXISTS (
                            SELECT 1 FROM device_limit_events
                            WHERE username = p_username
                              AND blocked_mac = p_mac
                              AND event_time > NOW() - INTERVAL '5 minutes'
                        );

                        PERFORM pg_notify('device_limit_exceeded', p_username);

                        RETURN 'EXCEEDED';
                    END IF;

                    INSERT INTO user_devices (username, mac_address, first_seen, last_seen)
                    VALUES (p_username, p_mac, NOW(), NOW())
                    ON CONFLICT (username, mac_address) DO UPDATE SET last_seen = NOW();

                    RETURN 'OK';
                END;
                $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS check_and_register_device(TEXT, TEXT);",
        ),
    ]
