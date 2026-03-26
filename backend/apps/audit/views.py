from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q

from apps.panel_users.permissions import IsAdminOrReadOnly
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        qs = AuditLog.objects.all()

        admin = request.query_params.get('admin')
        action = request.query_params.get('action')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        search = request.query_params.get('search', '').strip()

        if admin:
            qs = qs.filter(admin_user__icontains=admin)
        if action:
            qs = qs.filter(action__icontains=action)
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)
        if search:
            qs = qs.filter(
                Q(admin_user__icontains=search) |
                Q(action__icontains=search) |
                Q(target__icontains=search)
            )

        paginator = PageNumberPagination()
        paginator.page_size = 50
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(AuditLogSerializer(page, many=True).data)
