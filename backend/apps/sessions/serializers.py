from rest_framework import serializers
from .models import RadiusSession


class RadiusSessionSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)
    ssid = serializers.CharField(read_only=True)
    ap_mac = serializers.CharField(read_only=True)
    download_mb = serializers.FloatField(read_only=True)
    upload_mb = serializers.FloatField(read_only=True)

    class Meta:
        model = RadiusSession
        fields = [
            'id', 'acct_session_id', 'username', 'nas_ip_address',
            'nas_identifier', 'nas_port_id', 'called_station_id',
            'calling_station_id', 'framed_ip_address',
            'acct_start_time', 'acct_stop_time', 'acct_session_time',
            'acct_terminate_cause', 'connect_info_start',
            'acct_input_octets', 'acct_output_octets',
            'is_active', 'ssid', 'ap_mac', 'download_mb', 'upload_mb',
        ]
