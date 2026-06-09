"""Production Django settings for EdTrack3.

This file is intended to be used as the settings module in production
via the DJANGO_SETTINGS_MODULE environment variable (e.g.:

    export DJANGO_SETTINGS_MODULE=myserver.settings_production

This file imports the base settings from `myserver.settings` and then
applies production-safe overrides.

IMPORTANT:
- Do NOT commit your real secrets into source control.
- Use environment variables for all secret values.
- Ensure DEBUG is False and allowed hosts are correctly configured.

"""

from .settings import *  # noqa: F401,F403
from .settings import _get_list_env

import os
from django.core.exceptions import ImproperlyConfigured
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Basic security settings (overrides for production)
# ---------------------------------------------------------------------------

DEBUG = False

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY must be set in production.')

ALLOWED_HOSTS = _get_list_env(
    'DJANGO_ALLOWED_HOSTS',
    'localhost,127.0.0.1,.railway.app'
)

# Ensure cookies are only sent over HTTPS in production
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SAMESITE = 'None'

# Recommended security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', 60 * 60 * 24 * 7))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True') == 'True'
SECURE_HSTS_PRELOAD = os.environ.get('DJANGO_SECURE_HSTS_PRELOAD', 'True') == 'True'
SECURE_REFERRER_POLICY = 'same-origin'

# Redirect all HTTP requests to HTTPS (ensure you have SSL configured)
SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', 'True') == 'True'

# If behind a proxy/load-balancer, ensure this header is set by the proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ---------------------------------------------------------------------------
# Database (override with environment variables)
# ---------------------------------------------------------------------------

database_url = os.environ.get('DATABASE_URL')
if database_url:
    parsed_url = urlparse(database_url)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': parsed_url.path.lstrip('/'),
            'USER': parsed_url.username,
            'PASSWORD': parsed_url.password,
            'HOST': parsed_url.hostname,
            'PORT': parsed_url.port or '5432',
        }
    }
elif os.environ.get('DJANGO_DB_ENGINE'):
    DATABASES = {
        'default': {
            'ENGINE': os.environ['DJANGO_DB_ENGINE'],
            'NAME': os.environ['DJANGO_DB_NAME'],
            'USER': os.environ['DJANGO_DB_USER'],
            'PASSWORD': os.environ['DJANGO_DB_PASSWORD'],
            'HOST': os.environ.get('DJANGO_DB_HOST', ''),
            'PORT': os.environ.get('DJANGO_DB_PORT', ''),
        }
    }

CORS_ALLOWED_ORIGINS = _get_list_env('CORS_ALLOWED_ORIGINS', 'http://localhost:3000')
CSRF_TRUSTED_ORIGINS = _get_list_env('CSRF_TRUSTED_ORIGINS', 'http://localhost:3000')

# ---------------------------------------------------------------------------
# Email configuration
# ---------------------------------------------------------------------------

EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', 10))
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '').strip()
SENDGRID_FROM_EMAIL = os.environ.get('SENDGRID_FROM_EMAIL', '').strip()
DEFAULT_FROM_EMAIL = (os.environ.get('DEFAULT_FROM_EMAIL', '') or SENDGRID_FROM_EMAIL or 'no-reply@edutrack.local').strip()

if SENDGRID_API_KEY:
    EMAIL_BACKEND = 'myserver.email_backends.SendGridEmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------

# Ensure collectstatic is run and that these directories are writable by the server.
STATIC_URL = '/static/'
STATIC_ROOT = os.environ.get('DJANGO_STATIC_ROOT', os.path.join(BASE_DIR, 'static'))
MEDIA_ROOT = os.environ.get('DJANGO_MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))
WHITENOISE_USE_FINDERS = True

# ---------------------------------------------------------------------------
# Additional production settings (optional)
# ---------------------------------------------------------------------------

# If you want to disable the default admin-facing warning about default credentials,
# you can override that in your login view or disable messages entirely.

# End of production settings.
