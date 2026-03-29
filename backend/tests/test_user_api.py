"""
Testy pre User API endpointy – bulk email import, groups, permissions.
"""
import pytest
from unittest.mock import patch


@pytest.mark.django_db
class TestUserBulkEmailImport:
    EMAILS = ['jan@test.sk', 'anna@test.sk', 'peter@test.sk']

    @patch('apps.users.views.ldap.get_next_group_id', return_value=1)
    @patch('apps.users.views.ldap.create_user', return_value={})
    @patch('apps.users.tasks.send_user_credentials_email.delay')
    def test_bulk_create_success(self, mock_email, mock_create, mock_id, api_client):
        res = api_client.post('/api/users/bulk/', {
            'emails': self.EMAILS,
            'group': 'animatori',
        }, format='json')
        assert res.status_code == 207
        assert res.data['created'] == 3
        assert res.data['failed'] == 0
        assert all(r['success'] for r in res.data['results'])
        # Email odoslaný pre každého
        assert mock_email.call_count == 3

    @patch('apps.users.views.ldap.get_next_group_id', return_value=5)
    @patch('apps.users.views.ldap.create_user', side_effect=[
        {},
        Exception('LDAP nedostupný'),
        {},
    ])
    @patch('apps.users.tasks.send_user_credentials_email.delay')
    def test_bulk_create_partial_failure(self, mock_email, mock_create, mock_id, api_client):
        res = api_client.post('/api/users/bulk/', {
            'emails': self.EMAILS,
            'group': 'animatori',
        }, format='json')
        assert res.status_code == 207
        assert res.data['created'] == 2
        assert res.data['failed'] == 1
        assert res.data['results'][1]['success'] is False
        assert 'error' in res.data['results'][1]

    def test_bulk_create_requires_admin(self, readonly_client):
        res = readonly_client.post('/api/users/bulk/', {
            'emails': self.EMAILS,
            'group': 'animatori',
        }, format='json')
        assert res.status_code == 403

    def test_bulk_create_requires_auth(self, client):
        res = client.post('/api/users/bulk/', {
            'emails': self.EMAILS,
            'group': 'animatori',
        }, format='json')
        assert res.status_code == 401

    @patch('apps.users.views.ldap.get_next_group_id', return_value=1)
    @patch('apps.users.views.ldap.create_user', return_value={})
    @patch('apps.users.tasks.send_user_credentials_email.delay')
    def test_bulk_create_max_exceeded(self, mock_email, mock_create, mock_id, api_client):
        emails = [f'user{i}@test.sk' for i in range(101)]
        res = api_client.post('/api/users/bulk/', {
            'emails': emails,
            'group': 'hostia',
        }, format='json')
        assert res.status_code == 400

    def test_bulk_create_invalid_group(self, api_client):
        res = api_client.post('/api/users/bulk/', {
            'emails': ['a@b.sk'],
            'group': 'neexistujuca',
        }, format='json')
        assert res.status_code == 400

    def test_bulk_create_empty_emails(self, api_client):
        res = api_client.post('/api/users/bulk/', {
            'emails': [],
            'group': 'animatori',
        }, format='json')
        assert res.status_code == 400

    def test_bulk_create_invalid_email(self, api_client):
        res = api_client.post('/api/users/bulk/', {
            'emails': ['nie-je-email'],
            'group': 'animatori',
        }, format='json')
        assert res.status_code == 400

    @patch('apps.users.views.ldap.get_next_group_id', return_value=3)
    @patch('apps.users.views.ldap.create_user', return_value={})
    @patch('apps.users.tasks.send_user_credentials_email.delay')
    def test_sequential_ids_start_after_existing(self, mock_email, mock_create, mock_id, api_client):
        """Poradové čísla začínajú po poslednom existujúcom ID v skupne."""
        res = api_client.post('/api/users/bulk/', {
            'emails': ['a@test.sk', 'b@test.sk'],
            'group': 'animatori',
        }, format='json')
        assert res.status_code == 207
        # create_user by mal byť volaný s last_name='3' a '4'
        calls = mock_create.call_args_list
        assert calls[0].kwargs.get('last_name') == '3'
        assert calls[1].kwargs.get('last_name') == '4'

    @patch('apps.users.views.ldap.get_next_group_id', return_value=1)
    @patch('apps.users.views.ldap.create_user', return_value={})
    @patch('apps.users.tasks.send_user_credentials_email.delay')
    def test_username_equals_email(self, mock_email, mock_create, mock_id, api_client):
        """Login (username) musí byť emailová adresa."""
        res = api_client.post('/api/users/bulk/', {
            'emails': ['jan@oratko.sk'],
            'group': 'sdb',
        }, format='json')
        assert res.status_code == 207
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs['username'] == 'jan@oratko.sk'
        assert call_kwargs['email'] == 'jan@oratko.sk'


@pytest.mark.django_db
class TestUserGroupList:
    @patch('apps.users.views.ldap.list_users', return_value=[
        {'username': 'jan@test.sk', 'full_name': 'Animátori 1', 'first_name': 'Animátori',
         'last_name': '1', 'email': 'jan@test.sk', 'disabled': False, 'group': 'animatori'},
        {'username': 'peter@test.sk', 'full_name': 'SDB 1', 'first_name': 'SDB',
         'last_name': '1', 'email': 'peter@test.sk', 'disabled': False, 'group': 'sdb'},
    ])
    def test_group_list_returns_all_groups(self, mock_list, api_client):
        res = api_client.get('/api/users/groups/')
        assert res.status_code == 200
        assert len(res.data) == 6
        animatori = next(g for g in res.data if g['name'] == 'animatori')
        assert animatori['member_count'] == 1
        assert animatori['vlan'] == 20

    @patch('apps.users.views.ldap.list_users', return_value=[
        {'username': 'jan@test.sk', 'full_name': 'Animátori 1', 'first_name': 'Animátori',
         'last_name': '1', 'email': 'jan@test.sk', 'disabled': False, 'group': 'animatori'},
    ])
    def test_group_list_with_detail(self, mock_list, api_client):
        res = api_client.get('/api/users/groups/?detail=1')
        assert res.status_code == 200
        animatori = next(g for g in res.data if g['name'] == 'animatori')
        assert len(animatori['members']) == 1
        assert animatori['members'][0]['username'] == 'jan@test.sk'

    def test_group_list_requires_auth(self, client):
        res = client.get('/api/users/groups/')
        assert res.status_code == 401
