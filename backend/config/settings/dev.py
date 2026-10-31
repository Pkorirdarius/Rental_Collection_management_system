from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
AXES_ENABLED = env.bool("AXES_ENABLED", default=False)  # noqa: F405

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
