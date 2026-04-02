from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminUserViewSet, MeView, AdminInvitationView, AdminInvitationTokenView

router = DefaultRouter()
router.register('', AdminUserViewSet, basename='admin-user')

urlpatterns = [
    path('me/', MeView.as_view(), name='admin-me'),
    path('invitations/', AdminInvitationView.as_view(), name='admin-invitations'),
    path('invitations/<str:token>/', AdminInvitationTokenView.as_view(), name='admin-invitation-token'),
    path('', include(router.urls)),
]
