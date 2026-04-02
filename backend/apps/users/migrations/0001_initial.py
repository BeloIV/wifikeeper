from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='LDAPGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('label', models.CharField(max_length=128)),
                ('vlan', models.PositiveSmallIntegerField()),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS radreply (
                    id        SERIAL PRIMARY KEY,
                    username  VARCHAR(64)  NOT NULL,
                    attribute VARCHAR(64)  NOT NULL,
                    op        CHAR(2)      NOT NULL DEFAULT ':=',
                    value     VARCHAR(253) NOT NULL
                );
                CREATE INDEX IF NOT EXISTS radreply_username ON radreply (username);
            """,
            reverse_sql="DROP TABLE IF EXISTS radreply;",
        ),
    ]
