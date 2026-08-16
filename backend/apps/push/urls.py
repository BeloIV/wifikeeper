from django.urls import path
from .views import (
    VapidPublicKeyView,
    SubscribeView,
    UnsubscribeView,
    HeartbeatView,
    TestPushView,
    GrafanaWebhookView,
    NotificationListView,
    NotificationDetailView,
    NotificationMarkReadView,
    NotificationUnreadCountView,
)

urlpatterns = [
    path('vapid-public-key/', VapidPublicKeyView.as_view(), name='push-vapid-public-key'),
    path('subscribe/', SubscribeView.as_view(), name='push-subscribe'),
    path('unsubscribe/', UnsubscribeView.as_view(), name='push-unsubscribe'),
    path('heartbeat/', HeartbeatView.as_view(), name='push-heartbeat'),
    path('test/', TestPushView.as_view(), name='push-test'),
    path('notifications/', NotificationListView.as_view(), name='push-notification-list'),
    path('notifications/unread-count/', NotificationUnreadCountView.as_view(), name='push-notification-unread-count'),
    path('notifications/<int:pk>/', NotificationDetailView.as_view(), name='push-notification-detail'),
    path('notifications/<int:pk>/read/', NotificationMarkReadView.as_view(), name='push-notification-read'),
    path('webhook/grafana/', GrafanaWebhookView.as_view(), name='push-webhook-grafana'),
]
