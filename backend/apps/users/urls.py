from django.urls import path
from .views import (
    UserListView, UserDetailView, UserPasswordView,
    UserActivateView, UserBulkView, UserGroupListView,
)

urlpatterns = [
    path('', UserListView.as_view(), name='user-list'),
    path('bulk/', UserBulkView.as_view(), name='user-bulk'),
    path('groups/', UserGroupListView.as_view(), name='user-groups'),
    path('<str:username>/', UserDetailView.as_view(), name='user-detail'),
    path('<str:username>/password/', UserPasswordView.as_view(), name='user-password'),
    path('<str:username>/activate/', UserActivateView.as_view(), name='user-activate'),
]
