"""
Testy pre TempKey model – is_expired, is_active, šifrovanie hesla.
"""
import pytest
from datetime import timedelta
from django.utils import timezone


@pytest.mark.django_db
class TestTempKeyIsExpired:
    def _make_key(self, **kwargs):
        from apps.keys.models import TempKey
        from apps.keys.crypto import encrypt_password
        from apps.panel_users.models import AdminUser

        user = AdminUser.objects.create_user(username='test_admin_exp', password='pass')
        defaults = dict(
            label='test',
            key_type=TempKey.KeyType.TIMED,
            ldap_username='guest_test01',
            ldap_password=encrypt_password('testpass'),
            created_by=user,
        )
        defaults.update(kwargs)
        return TempKey.objects.create(**defaults)

    def test_not_expired_when_no_expires_at(self):
        key = self._make_key(key_type='one_time', expires_at=None)
        assert key.is_expired is False

    def test_not_expired_when_future(self):
        key = self._make_key(expires_at=timezone.now() + timedelta(hours=1))
        assert key.is_expired is False

    def test_expired_when_past(self):
        key = self._make_key(expires_at=timezone.now() - timedelta(hours=1))
        assert key.is_expired is True


@pytest.mark.django_db
class TestTempKeyIsActive:
    def _make_key(self, **kwargs):
        from apps.keys.models import TempKey
        from apps.keys.crypto import encrypt_password
        from apps.panel_users.models import AdminUser

        AdminUser.objects.filter(username='test_admin_act').delete()
        user = AdminUser.objects.create_user(username='test_admin_act', password='pass')
        defaults = dict(
            label='test',
            key_type=TempKey.KeyType.ONE_TIME,
            ldap_username=f'guest_active_{id(kwargs)}',
            ldap_password=encrypt_password('testpass'),
            created_by=user,
        )
        defaults.update(kwargs)
        return TempKey.objects.create(**defaults)

    def test_active_when_all_clean(self):
        key = self._make_key()
        assert key.is_active is True

    def test_inactive_when_used(self):
        key = self._make_key(used=True)
        assert key.is_active is False

    def test_inactive_when_ldap_deleted(self):
        key = self._make_key(ldap_deleted=True)
        assert key.is_active is False

    def test_inactive_when_expired(self):
        key = self._make_key(
            key_type='timed',
            expires_at=timezone.now() - timedelta(hours=1),
        )
        assert key.is_active is False


class TestPasswordEncryption:
    def test_roundtrip(self):
        from apps.keys.crypto import encrypt_password, decrypt_password
        original = 'MySecret123!'
        encrypted = encrypt_password(original)
        assert encrypted != original
        assert decrypt_password(encrypted) == original

    def test_different_ciphertexts(self):
        from apps.keys.crypto import encrypt_password
        # Fernet používa náhodné IV, každé šifrovanie je odlišné
        pw = 'SamePassword1'
        assert encrypt_password(pw) != encrypt_password(pw)
