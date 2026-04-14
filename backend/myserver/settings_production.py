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

import os

# ---------------------------------------------------------------------------
# Basic security settings (overrides for production)
# ---------------------------------------------------------------------------

DEBUG = False

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

# List of hosts/domains your site is allowed to serve.
# Example: "example.com,www.example.com"
ALLOWED_HOSTS = [
    "wonderful-generosity-production.up.railway.app",
    ".railway.app"
]

# Ensure cookies are only sent over HTTPS in production
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

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

if os.environ.get('DJANGO_DB_ENGINE'):
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
# else: keep the database configuration from base settings (SQLite)

# ---------------------------------------------------------------------------
# Email configuration
# ---------------------------------------------------------------------------

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------

# Ensure collectstatic is run and that these directories are writable by the server.
STATIC_ROOT = os.environ.get('DJANGO_STATIC_ROOT', os.path.join(BASE_DIR, 'static'))
MEDIA_ROOT = os.environ.get('DJANGO_MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))

# ---------------------------------------------------------------------------
# Additional production settings (optional)
# ---------------------------------------------------------------------------

# If you want to disable the default admin-facing warning about default credentials,
# you can override that in your login view or disable messages entirely.

# End of production settings.
