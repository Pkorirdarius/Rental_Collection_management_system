from .base import *  # noqa: F401,F403

DEBUG = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Fail closed: production must supply these.
for required in ("DJANGO_SECRET_KEY", "FIELD_ENCRYPTION_KEY"):
    if not env(required, default=""):  # noqa: F405
        raise RuntimeError(f"{required} must be set in production")
