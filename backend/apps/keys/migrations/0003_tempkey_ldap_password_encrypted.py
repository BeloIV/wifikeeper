from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keys', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tempkey',
            name='ldap_password',
            field=models.CharField(max_length=256, verbose_name='Heslo (šifrované Fernet)'),
        ),
    ]
