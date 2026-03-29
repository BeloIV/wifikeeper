"""
Testy pre TempKey API endpointy (mockovaný LDAP).
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from unittest.mock import patch, MagicMock


@pytest.mark.django_db
class TestTempKeyList:
    def test_list_requires_auth(self, client):
        res = client.get('/api/keys/')
        assert res.status_code == 401

    def test_list_returns_keys(self, api_client):
        res = api_client.get('/api/keys/')
        assert res.status_code == 200
        assert isinstance(res.data, list)


@pytest.mark.django_db
class TestTempKeyCreate:
    @patch('apps.keys.views.ldap.create_user')
    @patch('apps.keys.views.ldap.generate_temp_username', return_value='guest_xy1234')
    def test_create_with_valid_hours(self, mock_gen, mock_create, api_client):
        mock_create.return_value = {}
        res = api_client.post('/api/keys/', {
            'key_type': 'timed',
            'valid_hours': 24,
            'label': 'Test hosť',
        }, format='json')
        assert res.status_code == 201
        assert res.data['key_type'] == 'timed'
        assert res.data['valid_hours'] == 24
        # expires_at by mal byť cca now + 24h
        from dateutil.parser import parse as parse_dt
        expires = parse_dt(res.data['expires_at'])
        diff = expires - timezone.now()
        assert timedelta(hours=23) < diff < timedelta(hours=25)

    @patch('apps.keys.views.ldap.create_user')
    @patch('apps.keys.views.ldap.generate_temp_username', return_value='guest_ab5678')
    def test_create_with_expires_at(self, mock_gen, mock_create, api_client):
        mock_create.return_value = {}
        future = timezone.now() + timedelta(days=3)
        res = api_client.post('/api/keys/', {
            'key_type': 'timed',
            'expires_at': future.isoformat(),
            'label': 'Tábor',
        }, format='json')
        assert res.status_code == 201
        assert res.data['valid_hours'] is None
        from dateutil.parser import parse as parse_dt
        returned = parse_dt(res.data['expires_at'])
        assert abs((returned - future).total_seconds()) < 5

    @patch('apps.keys.views.ldap.create_user')
    @patch('apps.keys.views.ldap.generate_temp_username', return_value='guest_cd9999')
    def test_create_one_time(self, mock_gen, mock_create, api_client):
        mock_create.return_value = {}
        res = api_client.post('/api/keys/', {
            'key_type': 'one_time',
        }, format='json')
        assert res.status_code == 201
        assert res.data['expires_at'] is None

    def test_create_requires_admin(self, readonly_client):
        res = readonly_client.post('/api/keys/', {
            'key_type': 'one_time',
        }, format='json')
        assert res.status_code == 403

    def test_create_timed_without_hours_or_datetime_fails(self, api_client):
        res = api_client.post('/api/keys/', {
            'key_type': 'timed',
        }, format='json')
        assert res.status_code == 400


@pytest.mark.django_db
class TestTempKeyDelete:
    def _create_key(self, admin_user):
        from apps.keys.models import TempKey
        from apps.keys.crypto import encrypt_password
        return TempKey.objects.create(
            label='del test',
            key_type=TempKey.KeyType.ONE_TIME,
            ldap_username='guest_del001',
            ldap_password=encrypt_password('pass'),
            created_by=admin_user,
        )

    @patch('apps.keys.views.ldap.get_user', return_value=None)
    @patch('apps.keys.views.ldap.delete_user')
    def test_delete_key(self, mock_del, mock_get, api_client, admin_user):
        key = self._create_key(admin_user)
        res = api_client.delete(f'/api/keys/{key.id}/')
        assert res.status_code == 204

    def test_delete_nonexistent(self, api_client):
        import uuid
        res = api_client.delete(f'/api/keys/{uuid.uuid4()}/')
        assert res.status_code == 404
