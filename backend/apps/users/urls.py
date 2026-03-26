from django.urls import path
from .views import UserListView, UserDetailView, UserPasswordView, UserActivateView

urlpatterns = [
    path('', UserListView.as_view(), name='user-list'),
    path('<str:username>', UserDetailView.as_view(), name='user-detail'),
    path('<str:username>/password', UserPasswordView.as_view(), name='user-password'),
    path('<str:username>/activate', UserActivateView.as_view(), name='user-activate'),
]
