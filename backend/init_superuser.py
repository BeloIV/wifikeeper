import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.panel_users.models import AdminUser

email = os.environ.get('ADMIN_EMAIL')
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

if not email or not password:
    print('init_superuser: ADMIN_EMAIL alebo DJANGO_SUPERUSER_PASSWORD nie je nastavený, preskakujem.')
else:
    obj, created = AdminUser.objects.get_or_create(email=email, defaults={'username': username, 'role': 'superadmin'})
    if created:
        obj.set_password(password)
        obj.save()
        print('init_superuser: vytvorený', email)
    else:
        changed = False
        if obj.role != 'superadmin':
            obj.role = 'superadmin'
            changed = True
        if not obj.check_password(password):
            obj.set_password(password)
            changed = True
        if changed:
            obj.save()
        print('init_superuser: OK', email)
