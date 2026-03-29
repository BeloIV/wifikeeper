"""
Spoločné fixtures pre pytest-django testy.
"""
import os
import pytest
from cryptography.fernet import Fernet
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


# Nastav testovacie env premenné pred importom Django
os.environ.setdefault('FIELD_ENCRYPTION_KEY', Fernet.generate_key().decode())
os.environ.setdefault('SECRET_KEY', 'test-secret-key-not-for-production')
os.environ.setdefault('DATABASE_URL', 'sqlite:///test_db.sqlite3')
os.environ.setdefault('LDAP_SERVER_URI', 'ldap://localhost:389')
os.environ.setdefault('LDAP_BASE_DN', 'dc=test,dc=local')
os.environ.setdefault('LDAP_BIND_DN', 'cn=admin,dc=test,dc=local')
os.environ.setdefault('LDAP_BIND_PASSWORD', 'testpass')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('BREVO_SMTP_HOST', 'smtp-relay.brevo.com')
os.environ.setdefault('BREVO_SMTP_PORT', '587')
os.environ.setdefault('BREVO_SMTP_USER', 'test@example.com')
os.environ.setdefault('BREVO_SMTP_PASS', 'testpass')
os.environ.setdefault('DEFAULT_FROM_EMAIL', 'wifi@test.local')
os.environ.setdefault('RADIUS_SECRET', 'testing123')
os.environ.setdefault('RADIUS_COA_SECRET', 'testing123')
os.environ.setdefault('ALLOWED_HOSTS', 'localhost')


@pytest.fixture
def admin_user(db):
    from apps.panel_users.models import AdminUser
    user = AdminUser.objects.create_user(
        username='admin_test',
        password='adminpass123',
        role=AdminUser.Role.ADMIN,
    )
    return user


@pytest.fixture
def readonly_user(db):
    from apps.panel_users.models import AdminUser
    user = AdminUser.objects.create_user(
        username='readonly_test',
        password='readpass123',
        role=AdminUser.Role.READONLY,
    )
    return user


@pytest.fixture
def api_client(admin_user):
    client = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client


@pytest.fixture
def readonly_client(readonly_user):
    client = APIClient()
    refresh = RefreshToken.for_user(readonly_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client


@pytest.fixture
def mock_ldap(mocker):
    """Mock všetky volania do ldap_service."""
    mocker.patch('apps.users.ldap_service.create_user', return_value={'username': 'test.user', 'group': 'animatori'})
    mocker.patch('apps.users.ldap_service.get_user', return_value=None)
    mocker.patch('apps.users.ldap_service.delete_user')
    mocker.patch('apps.users.ldap_service.get_next_group_id', return_value=1)
    mocker.patch('apps.users.ldap_service.generate_temp_username', return_value='guest_abc123')
    mocker.patch('apps.keys.views.ldap.create_user', return_value={'username': 'guest_abc123'})
    mocker.patch('apps.keys.views.ldap.get_user', return_value=None)
    mocker.patch('apps.keys.views.ldap.delete_user')
    mocker.patch('apps.keys.views.ldap.generate_temp_username', return_value='guest_abc123')
