from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('radius_sessions', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE device_limit_events ALTER COLUMN event_time SET DEFAULT NOW();",
            reverse_sql="ALTER TABLE device_limit_events ALTER COLUMN event_time DROP DEFAULT;",
        ),
    ]
