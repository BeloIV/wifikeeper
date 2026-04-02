from django.contrib import admin
from django.urls import path, include, re_path
from apps.panel_users.views import LoginView, LogoutView, TokenRefreshCookieView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth
    path('api/auth/login/', LoginView.as_view(), name='token_obtain'),
    path('api/auth/logout/', LogoutView.as_view(), name='token_logout'),
    path('api/auth/refresh/', TokenRefreshCookieView.as_view(), name='token_refresh'),
    # API
    re_path(r'^api/users/?', include('apps.users.urls')),
    re_path(r'^api/keys/?', include('apps.keys.urls')),
    re_path(r'^api/sessions/?', include('apps.sessions.urls')),
    re_path(r'^api/audit/?', include('apps.audit.urls')),
    re_path(r'^api/admins/?', include('apps.panel_users.urls')),
]
