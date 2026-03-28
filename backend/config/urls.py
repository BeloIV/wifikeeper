from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework_simplejwt.views import TokenRefreshView
from apps.panel_users.views import LoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth
    path('api/auth/login/', LoginView.as_view(), name='token_obtain'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # API
    re_path(r'^api/users/?', include('apps.users.urls')),
    re_path(r'^api/keys/?', include('apps.keys.urls')),
    re_path(r'^api/sessions/?', include('apps.sessions.urls')),
    re_path(r'^api/audit/?', include('apps.audit.urls')),
    re_path(r'^api/admins/?', include('apps.panel_users.urls')),
]
