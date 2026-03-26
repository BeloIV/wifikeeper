from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ['id', 'admin_user', 'action', 'target', 'details', 'ip_address', 'timestamp']
