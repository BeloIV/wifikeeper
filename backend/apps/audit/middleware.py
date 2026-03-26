"""
Automatický audit log pre všetky write akcie cez API.
Zaznamenáva len POST/PUT/PATCH/DELETE requesty od autentifikovaných adminov.
"""


class AuditMiddleware:
    LOGGED_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Audit sa robí explicitne v views cez audit_log() – tu len zalogujeme
        # neúspešné pokusy (4xx od autentifikovaných userov)
        if (
            request.method in self.LOGGED_METHODS
            and hasattr(request, 'user')
            and request.user.is_authenticated
            and response.status_code >= 400
        ):
            from .models import AuditLog
            ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            if not ip:
                ip = request.META.get('REMOTE_ADDR')
            AuditLog.objects.create(
                admin_user=request.user.username,
                action=f'FAILED_{request.method}',
                target=request.path,
                details={'status': response.status_code},
                ip_address=ip or None,
            )

        return response
