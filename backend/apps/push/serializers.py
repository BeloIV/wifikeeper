from rest_framework import serializers
from .models import PushNotification


class PushNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushNotification
        fields = ['id', 'title', 'body', 'status', 'alertname', 'severity', 'detail', 'created_at', 'read_at']
