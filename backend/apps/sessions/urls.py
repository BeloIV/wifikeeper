from django.urls import path
from .views import LiveSessionsView, DisconnectUserView, SessionHistoryView, UserDevicesView, UserDeviceDeleteView

urlpatterns = [
    path('live/', LiveSessionsView.as_view(), name='live-sessions'),
    path('live/<str:session_id>/disconnect/', DisconnectUserView.as_view(), name='disconnect-user'),
    path('history/', SessionHistoryView.as_view(), name='session-history'),
    path('devices/<str:username>/', UserDevicesView.as_view(), name='user-devices'),
    path('devices/<str:username>/<str:mac>/', UserDeviceDeleteView.as_view(), name='user-device-delete'),
]
