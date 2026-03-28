from django.urls import path
from .views import LiveSessionsView, DisconnectUserView, SessionHistoryView

urlpatterns = [
    path('live/', LiveSessionsView.as_view(), name='live-sessions'),
    path('live/<str:session_id>/disconnect/', DisconnectUserView.as_view(), name='disconnect-user'),
    path('history/', SessionHistoryView.as_view(), name='session-history'),
]
