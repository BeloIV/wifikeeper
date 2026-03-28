from django.urls import path
from .views import TempKeyListView, TempKeyDetailView, TempKeyQRView, TempKeyResendEmailView

urlpatterns = [
    path('', TempKeyListView.as_view(), name='key-list'),
    path('<uuid:pk>/', TempKeyDetailView.as_view(), name='key-detail'),
    path('<uuid:pk>/qr/', TempKeyQRView.as_view(), name='key-qr'),
    path('<uuid:pk>/send-email/', TempKeyResendEmailView.as_view(), name='key-send-email'),
]
