import hmac
import json
import logging

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from pywebpush import webpush, WebPushException
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status

from apps.panel_users.permissions import IsSuperAdmin
from .models import PushSubscription, PushNotification
from .serializers import PushNotificationSerializer

logger = logging.getLogger(__name__)


class VapidPublicKeyView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response({'publicKey': settings.VAPID_PUBLIC_KEY})


class SubscribeView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        data = request.data
        endpoint = data.get('endpoint')
        keys = data.get('keys') or {}
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')

        if not endpoint or not p256dh or not auth:
            return Response({'detail': 'Chýba endpoint alebo keys.'}, status=status.HTTP_400_BAD_REQUEST)

        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'admin_user': request.user,
                'p256dh': p256dh,
                'auth': auth,
                'last_seen': timezone.now(),
                'warned_at': None,
            },
        )
        return Response(status=status.HTTP_201_CREATED)


class HeartbeatView(APIView):
    """Appka volá pri každom otvorení stránky Notifikácie — obnoví last_seen,
    aby vedel cleanup task rozlíšiť aktívne zariadenie od orphana po zmazaní appky z plochy."""
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        endpoint = request.data.get('endpoint')
        if not endpoint:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        updated = PushSubscription.objects.filter(endpoint=endpoint).update(
            last_seen=timezone.now(), warned_at=None
        )
        if not updated:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UnsubscribeView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        endpoint = request.data.get('endpoint')
        if endpoint:
            PushSubscription.objects.filter(endpoint=endpoint).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationListView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        qs = PushNotification.objects.all()
        paginator = PageNumberPagination()
        paginator.page_size = 30
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(PushNotificationSerializer(page, many=True).data)


class NotificationDetailView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk):
        try:
            notif = PushNotification.objects.get(pk=pk)
        except PushNotification.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(PushNotificationSerializer(notif).data)


class NotificationMarkReadView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        PushNotification.objects.filter(pk=pk, read_at__isnull=True).update(read_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationUnreadCountView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        count = PushNotification.objects.filter(read_at__isnull=True).count()
        return Response({'count': count})


def _send_push(subscription, payload):
    try:
        webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {'p256dh': subscription.p256dh, 'auth': subscription.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={'sub': settings.VAPID_CLAIM_EMAIL},
            # pywebpush default ttl=0 = "doruč hneď alebo zahoď" — ak je zariadenie
            # práve zamknuté/offline, push server ho ticho zahodí bez chyby.
            # 24h dáva push serveru priestor doručiť, keď sa zariadenie znova pripojí.
            ttl=86400,
        )
    except WebPushException as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code in (404, 410):
            subscription.delete()
        else:
            logger.warning('Push notifikácia zlyhala: %s', exc)
    except Exception:
        # Sieťové chyby/timeouty z requests (vnútri pywebpush) nie sú WebPushException —
        # nesmú zhodiť celý _broadcast() cyklus a pripraviť ostatných odberateľov o notifikáciu.
        logger.exception('Push notifikácia zlyhala neočakávanou chybou (endpoint=%s)', subscription.endpoint)


def _broadcast(notification: PushNotification):
    payload = {
        'title': notification.title,
        'body': notification.body,
        'data': {'url': f'/dashboard/notifications?id={notification.id}'},
    }
    superadmin_subs = PushSubscription.objects.filter(
        Q(admin_user__role='superadmin') | Q(admin_user__is_superuser=True)
    )
    for sub in superadmin_subs:
        try:
            _send_push(sub, payload)
        except Exception:
            # _send_push si už chyby chytá sama, toto je len posledná poistka,
            # aby jeden zlyhaný odberateľ nikdy nezastavil cyklus pre ostatných.
            logger.exception('Neočakávané zlyhanie _send_push pre endpoint=%s', sub.endpoint)


class TestPushView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        subs = PushSubscription.objects.filter(admin_user=request.user)
        if not subs.exists():
            return Response({'detail': 'Žiadne aktívne prihlásenie na notifikácie.'}, status=status.HTTP_400_BAD_REQUEST)

        notification = PushNotification.objects.create(
            title='WiFi Manager',
            body='Testovacia notifikácia funguje ✅',
            status=PushNotification.Status.TEST,
            detail={'note': 'Manuálny test odoslaný z appky.'},
        )
        _broadcast(notification)
        return Response(PushNotificationSerializer(notification).data, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class GrafanaWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        # Secret ide cez Authorization hlavičku, nie v URL — sekrety v URL cestách
        # sa bežne ocitnú v access logoch (aj v tomto vlastnom Loki/Grafana log
        # pipeline, ktorý tento webhook napája), zatiaľ čo hlavičky nie.
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        expected = f'Bearer {settings.PUSH_WEBHOOK_SECRET}'
        if not hmac.compare_digest(auth_header, expected):
            return Response(status=status.HTTP_404_NOT_FOUND)

        payload = request.data
        alerts = payload.get('alerts', [])

        if not alerts:
            # Fallback pre manuálny test priamo z Grafana UI (Test contact point).
            notification = PushNotification.objects.create(
                title=payload.get('title') or 'WifiKeeper alert',
                body=payload.get('message', 'Stav sa zmenil'),
                status=PushNotification.Status.TEST,
                detail=payload,
            )
            _broadcast(notification)
            return Response(status=status.HTTP_200_OK)

        for alert in alerts:
            labels = alert.get('labels', {})
            annotations = alert.get('annotations', {})
            alert_status = alert.get('status', 'firing')

            notification = PushNotification.objects.create(
                title=labels.get('alertname', payload.get('title') or 'WifiKeeper alert'),
                body=annotations.get('summary', ''),
                status=PushNotification.Status.RESOLVED if alert_status == 'resolved' else PushNotification.Status.FIRING,
                alertname=labels.get('alertname', ''),
                severity=labels.get('severity', ''),
                detail={
                    'labels': labels,
                    'annotations': annotations,
                    'status': alert_status,
                    'startsAt': alert.get('startsAt'),
                    'endsAt': alert.get('endsAt'),
                    'generatorURL': alert.get('generatorURL'),
                },
            )
            _broadcast(notification)

        return Response(status=status.HTTP_200_OK)
