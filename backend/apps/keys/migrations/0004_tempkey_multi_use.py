from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keys', '0003_tempkey_ldap_password_encrypted'),
    ]

    operations = [
        migrations.AddField(
            model_name='tempkey',
            name='max_uses',
            field=models.PositiveIntegerField(
                blank=True, null=True,
                verbose_name='Max. počet použití',
                help_text='Len pre N-násobný typ.',
            ),
        ),
        migrations.AddField(
            model_name='tempkey',
            name='use_count',
            field=models.PositiveIntegerField(default=0, verbose_name='Počet použití'),
        ),
        migrations.AlterField(
            model_name='tempkey',
            name='key_type',
            field=models.CharField(
                choices=[
                    ('one_time', 'Jednorazový'),
                    ('timed', 'Časový'),
                    ('multi_use', 'N-násobný'),
                ],
                max_length=20,
                verbose_name='Typ kľúča',
            ),
        ),
    ]
