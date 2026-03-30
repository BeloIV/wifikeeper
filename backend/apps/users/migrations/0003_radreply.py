from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_seed_groups'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS radreply (
                    id        SERIAL PRIMARY KEY,
                    username  VARCHAR(64) NOT NULL,
                    attribute VARCHAR(64) NOT NULL,
                    op        CHAR(2)     NOT NULL DEFAULT ':=',
                    value     VARCHAR(253) NOT NULL
                );
                CREATE INDEX IF NOT EXISTS radreply_username ON radreply (username);
            """,
            reverse_sql="DROP TABLE IF EXISTS radreply;",
        ),
    ]
