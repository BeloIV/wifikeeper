"""
Testy pre TempKeyCreateSerializer – validácia expires_at vs valid_hours.
"""
import pytest
from datetime import timedelta
from django.utils import timezone


class TestTempKeyCreateSerializer:
    def _get_serializer(self, data):
        from apps.keys.serializers import TempKeyCreateSerializer
        return TempKeyCreateSerializer(data=data)

    def test_timed_with_valid_hours_is_valid(self):
        s = self._get_serializer({'key_type': 'timed', 'valid_hours': 24})
        assert s.is_valid(), s.errors

    def test_timed_with_expires_at_future_is_valid(self):
        future = (timezone.now() + timedelta(hours=2)).isoformat()
        s = self._get_serializer({'key_type': 'timed', 'expires_at': future})
        assert s.is_valid(), s.errors

    def test_timed_with_both_is_invalid(self):
        future = (timezone.now() + timedelta(hours=2)).isoformat()
        s = self._get_serializer({'key_type': 'timed', 'valid_hours': 24, 'expires_at': future})
        assert not s.is_valid()

    def test_timed_with_neither_is_invalid(self):
        s = self._get_serializer({'key_type': 'timed'})
        assert not s.is_valid()

    def test_timed_expires_at_in_past_is_invalid(self):
        past = (timezone.now() - timedelta(hours=1)).isoformat()
        s = self._get_serializer({'key_type': 'timed', 'expires_at': past})
        assert not s.is_valid()
        assert 'expires_at' in str(s.errors)

    def test_one_time_no_hours_required(self):
        s = self._get_serializer({'key_type': 'one_time'})
        assert s.is_valid(), s.errors

    def test_timed_valid_hours_min_value(self):
        s = self._get_serializer({'key_type': 'timed', 'valid_hours': 0})
        assert not s.is_valid()

    def test_timed_valid_hours_max_value(self):
        s = self._get_serializer({'key_type': 'timed', 'valid_hours': 721})
        assert not s.is_valid()

    def test_label_optional(self):
        s = self._get_serializer({'key_type': 'one_time'})
        assert s.is_valid()
        assert s.validated_data['label'] == ''
