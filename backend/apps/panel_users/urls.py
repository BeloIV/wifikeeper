from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminUserViewSet, MeView

router = DefaultRouter()
router.register('', AdminUserViewSet, basename='admin-user')

urlpatterns = [
    path('me/', MeView.as_view(), name='admin-me'),
    path('', include(router.urls)),
]
