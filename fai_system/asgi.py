"""
ASGI config for FAI System project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fai_system.settings')

application = get_asgi_application()
