"""
WSGI config for myserver project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Use production settings if DJANGO_SETTINGS_MODULE is not already set
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    # On production (Railway), DEBUG should be False
    debug = os.getenv('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes')
    settings_module = 'myserver.settings' if debug else 'myserver.settings_production'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
else:
    # If explicitly set, use that
    pass

application = get_wsgi_application()
