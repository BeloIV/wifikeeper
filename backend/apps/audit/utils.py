from .models import AuditLog


def audit_log(request, action: str, target: str, details: dict):
    """Zapíše záznam do audit logu."""
    ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
    if not ip:
        ip = request.META.get('REMOTE_ADDR')

    AuditLog.objects.create(
        admin_user=request.user.username if request.user.is_authenticated else 'anonymous',
        action=action,
        target=target,
        details=details,
        ip_address=ip or None,
    )
