from django.db import migrations

INITIAL_GROUPS = [
    {'name': 'sdb', 'label': 'SDB', 'vlan': 10},
    {'name': 'animatori', 'label': 'Animátori', 'vlan': 20},
    {'name': 'fma', 'label': 'FMA', 'vlan': 20},
    {'name': 'spolupracovnici', 'label': 'Spolupracovníci', 'vlan': 30},
    {'name': 'hostia', 'label': 'Hostia', 'vlan': 40},
    {'name': 'docasny', 'label': 'Dočasný', 'vlan': 40},
]


def seed(apps, schema_editor):
    LDAPGroup = apps.get_model('users', 'LDAPGroup')
    for g in INITIAL_GROUPS:
        LDAPGroup.objects.get_or_create(name=g['name'], defaults={'label': g['label'], 'vlan': g['vlan']})


def unseed(apps, schema_editor):
    LDAPGroup = apps.get_model('users', 'LDAPGroup')
    LDAPGroup.objects.filter(name__in=[g['name'] for g in INITIAL_GROUPS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
