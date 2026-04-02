import os
from pathlib import Path
from datetime import timedelta
import ldap
from django_auth_ldap.config import LDAPSearch, GroupOfNamesType

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ['SECRET_KEY']
# Fernet key pre šifrovanie citlivých DB polí (ldap_password v TempKey).
# Generuj: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEY = os.environ['FIELD_ENCRYPTION_KEY']
# RADIUS CoA shared secret – musí súhlasiť s NAS (UniFi AP).
RADIUS_COA_SECRET = os.environ['RADIUS_COA_SECRET']
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')
APPEND_SLASH = False

# ── Aplikácie ──────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Tretie strany
    'rest_framework',
    'corsheaders',
    'django_celery_beat',
    # Lokálne aplikácie
    'apps.panel_users',
    'apps.keys',
    'apps.users',
    'apps.sessions',
    'apps.audit',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit.middleware.AuditMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ── Databáza ───────────────────────────────────────────────────────────────────
import dj_database_url
DATABASES = {
    'default': dj_database_url.parse(
        os.environ['DATABASE_URL'],
        conn_max_age=600,
    )
}

# ── Redis / Celery ─────────────────────────────────────────────────────────────
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = 'Europe/Bratislava'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ── LDAP – správa používateľov ────────────────────────────────────────────────
LDAP_SERVER_URI = os.environ.get('LDAP_SERVER_URI', 'ldap://localhost')
LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN', 'dc=oratko,dc=local')
LDAP_BIND_DN = os.environ.get('LDAP_BIND_DN', 'cn=admin,dc=oratko,dc=local')
LDAP_BIND_PASSWORD = os.environ.get('LDAP_BIND_PASSWORD', '')

# LDAP skupiny → VLAN mapovanie
LDAP_VLAN_MAP = {
    'sdb': 10,
    'animatori': 20,
    'fma': 20,
    'spolupracovnici': 30,
    'hostia': 40,
    'docasny': 40,
}

# ── django-auth-ldap – prihlásenie adminov cez LDAP ───────────────────────────
AUTH_LDAP_SERVER_URI = LDAP_SERVER_URI
AUTH_LDAP_BIND_DN = LDAP_BIND_DN
AUTH_LDAP_BIND_PASSWORD = LDAP_BIND_PASSWORD
AUTH_LDAP_USER_SEARCH = LDAPSearch(
    f'ou=users,{LDAP_BASE_DN}',
    ldap.SCOPE_SUBTREE,
    '(uid=%(user)s)',
)
AUTH_LDAP_USER_ATTR_MAP = {
    'first_name': 'givenName',
    'last_name': 'sn',
    'email': 'mail',
}
AUTH_LDAP_ALWAYS_UPDATE_USER = True

AUTHENTICATION_BACKENDS = [
    'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_USER_MODEL = 'panel_users.AdminUser'

# ── REST Framework ─────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.panel_users.authentication.JWTCookieAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ── CORS ───────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,https://localhost'
).split(',')
CORS_ALLOW_CREDENTIALS = True

# ── Email (Brevo SMTP relay) ───────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp-relay.brevo.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.environ.get('EMAIL_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'

DEFAULT_FROM_EMAIL = os.environ.get('MAIL_FROM', 'no-reply@oratko.sk')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@oratko.sk')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# ── Statické súbory ────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LANGUAGE_CODE = 'sk'
TIME_ZONE = 'Europe/Bratislava'
USE_I18N = True
USE_TZ = True
