import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('radius_sessions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TempKey',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('label', models.CharField(blank=True, max_length=200, verbose_name='Popis / meno hosťa')),
                ('key_type', models.CharField(
                    choices=[
                        ('one_time',  'Jednorazový'),
                        ('timed',     'Časový'),
                        ('multi_use', 'N-násobný'),
                    ],
                    max_length=20,
                    verbose_name='Typ kľúča',
                )),
                ('ldap_username', models.CharField(max_length=64, unique=True, verbose_name='LDAP meno')),
                ('ldap_password', models.CharField(max_length=256, verbose_name='Heslo (šifrované Fernet)')),
                ('valid_hours', models.PositiveIntegerField(
                    blank=True, null=True,
                    help_text='Len pre časový typ. Null = ručne definovaná expirácia.',
                    verbose_name='Platnosť (hodiny)',
                )),
                ('expires_at', models.DateTimeField(blank=True, null=True, verbose_name='Expiruje')),
                ('max_uses', models.PositiveIntegerField(
                    blank=True, null=True,
                    verbose_name='Max. počet použití',
                    help_text='Len pre N-násobný typ.',
                )),
                ('use_count', models.PositiveIntegerField(default=0, verbose_name='Počet použití')),
                ('used', models.BooleanField(default=False, verbose_name='Použitý / vyčerpaný')),
                ('used_at', models.DateTimeField(blank=True, null=True, verbose_name='Čas posledného použitia')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Vytvorený')),
                ('email_sent_to', models.EmailField(blank=True, max_length=254, verbose_name='Email odoslaný na')),
                ('ldap_deleted', models.BooleanField(default=False, verbose_name='LDAP účet zmazaný')),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_keys',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Vytvoril',
                )),
            ],
            options={
                'verbose_name': 'Dočasný kľúč',
                'verbose_name_plural': 'Dočasné kľúče',
                'ordering': ['-created_at'],
            },
        ),
        migrations.RunSQL(
            sql="""
                CREATE OR REPLACE FUNCTION fn_postauth_key_usage()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF NEW.reply != 'Access-Accept' THEN
                        RETURN NEW;
                    END IF;

                    UPDATE keys_tempkey
                    SET
                        use_count = use_count + 1,
                        used      = (use_count + 1 >= max_uses),
                        used_at   = CASE
                                        WHEN use_count + 1 >= max_uses THEN NOW()
                                        ELSE used_at
                                    END
                    WHERE ldap_username = NEW.username
                      AND max_uses IS NOT NULL
                      AND NOT used;

                    DELETE FROM radreply
                    WHERE username = NEW.username
                      AND EXISTS (
                          SELECT 1 FROM keys_tempkey
                          WHERE ldap_username = NEW.username
                            AND used = TRUE
                            AND max_uses IS NOT NULL
                      );

                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER trg_postauth_key_usage
                    AFTER INSERT ON radius_postauth
                    FOR EACH ROW
                    EXECUTE FUNCTION fn_postauth_key_usage();
            """,
            reverse_sql="""
                DROP TRIGGER IF EXISTS trg_postauth_key_usage ON radius_postauth;
                DROP FUNCTION IF EXISTS fn_postauth_key_usage();
            """,
        ),
    ]
