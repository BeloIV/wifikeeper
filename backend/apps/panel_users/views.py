from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from django.conf import settings
from django.utils import timezone
from .models import AdminUser, AdminInvitation
from .serializers import (
    LoginSerializer, AdminUserSerializer, AdminUserMeSerializer,
    AdminInvitationCreateSerializer, AdminInvitationAcceptSerializer,
)
from .permissions import IsSuperAdmin


def _set_auth_cookies(response, refresh):
    is_secure = not settings.DEBUG
    response.set_cookie(
        'access_token',
        str(refresh.access_token),
        httponly=True,
        secure=is_secure,
        samesite='Strict',
        max_age=int(jwt_settings.ACCESS_TOKEN_LIFETIME.total_seconds()),
    )
    response.set_cookie(
        'refresh_token',
        str(refresh),
        httponly=True,
        secure=is_secure,
        samesite='Strict',
        max_age=int(jwt_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
    )


def _clear_auth_cookies(response):
    response.delete_cookie('access_token', samesite='Strict')
    response.delete_cookie('refresh_token', samesite='Strict')


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        response = Response({'user': AdminUserMeSerializer(user).data})
        _set_auth_cookies(response, refresh)
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        response = Response({'detail': 'Odhlásený.'})
        _clear_auth_cookies(response)
        return response


class TokenRefreshCookieView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get('refresh_token')
        if not raw_refresh:
            return Response({'detail': 'Chýba refresh token.'}, status=401)
        try:
            refresh = RefreshToken(raw_refresh)
            if jwt_settings.ROTATE_REFRESH_TOKENS:
                if jwt_settings.BLACKLIST_AFTER_ROTATION:
                    try:
                        refresh.blacklist()
                    except AttributeError:
                        pass
                refresh.set_jti()
                refresh.set_exp()
                refresh.set_iat()
            response = Response({'detail': 'OK'})
            _set_auth_cookies(response, refresh)
            return response
        except Exception:
            response = Response({'detail': 'Neplatný refresh token.'}, status=401)
            _clear_auth_cookies(response)
            return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(AdminUserMeSerializer(request.user).data)


class AdminUserViewSet(ModelViewSet):
    queryset = AdminUser.objects.all().order_by('username')
    serializer_class = AdminUserSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        return qs


class AdminInvitationView(APIView):
    """POST: vytvor pozvánku (IsSuperAdmin). GET: zoznam pozvánok."""
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        invitations = AdminInvitation.objects.order_by('-created_at')[:50]
        data = [
            {
                'id': inv.id,
                'email': inv.email,
                'role': inv.role,
                'created_at': inv.created_at,
                'expires_at': inv.expires_at,
                'used': inv.used,
                'is_valid': inv.is_valid,
            }
            for inv in invitations
        ]
        return Response(data)

    def post(self, request):
        serializer = AdminInvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        invitation = AdminInvitation(
            email=d['email'],
            role=d['role'],
            created_by=request.user,
        )
        invitation.save()

        from django.conf import settings
        origin = request.headers.get('Origin', '').rstrip('/')
        frontend_base = origin if origin else settings.FRONTEND_URL
        invitation_url = f'{frontend_base}/invite/{invitation.token}'

        from apps.users.tasks import send_admin_invitation_email
        send_admin_invitation_email.delay(
            email=invitation.email,
            role=invitation.role,
            invitation_url=invitation_url,
        )

        return Response({
            'id': invitation.id,
            'email': invitation.email,
            'role': invitation.role,
            'expires_at': invitation.expires_at,
            'invitation_url': invitation_url,
        }, status=201)


class AdminInvitationTokenView(APIView):
    """GET: overí token (public). POST: prijme pozvánku (public)."""
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            inv = AdminInvitation.objects.get(token=token)
        except AdminInvitation.DoesNotExist:
            return Response({'detail': 'Pozvánka nenájdená.'}, status=404)
        if not inv.is_valid:
            return Response({'detail': 'Pozvánka vypršala alebo bola už použitá.'}, status=410)
        return Response({'email': inv.email, 'role': inv.role, 'expires_at': inv.expires_at})

    def post(self, request, token):
        try:
            inv = AdminInvitation.objects.get(token=token)
        except AdminInvitation.DoesNotExist:
            return Response({'detail': 'Pozvánka nenájdená.'}, status=404)
        if not inv.is_valid:
            return Response({'detail': 'Pozvánka vypršala alebo bola už použitá.'}, status=410)

        serializer = AdminInvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        if AdminUser.objects.filter(username=inv.email).exists():
            return Response({'detail': 'Účet s týmto emailom už existuje.'}, status=400)

        user = AdminUser(
            username=inv.email,
            email=inv.email,
            first_name=d.get('first_name', ''),
            last_name=d.get('last_name', ''),
            role=inv.role,
        )
        user.set_password(d['password'])
        user.save()

        inv.used = True
        inv.used_at = timezone.now()
        inv.save(update_fields=['used', 'used_at'])

        return Response({'detail': 'Účet bol úspešne vytvorený.'}, status=201)
