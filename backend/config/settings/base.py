"""Base Django settings shared by every environment."""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    DATABASE_URL=(str, f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
    REDIS_URL=(str, ""),
    CELERY_TASK_ALWAYS_EAGER=(bool, False),
    FIELD_ENCRYPTION_KEY=(str, ""),
    MPESA_ENABLED=(bool, False),
    MPESA_ENV=(str, "sandbox"),
    MPESA_CONSUMER_KEY=(str, ""),
    MPESA_CONSUMER_SECRET=(str, ""),
    MPESA_SHORTCODE=(str, ""),
    MPESA_PASSKEY=(str, ""),
    MPESA_CALLBACK_TOKEN=(str, ""),
    MPESA_VALIDATION_TOKEN=(str, ""),
    MPESA_CALLBACK_BASE_URL=(str, ""),
    MPESA_IP_ALLOWLIST=(list, []),
    MPESA_INITIATOR_NAME=(str, ""),
    MPESA_SECURITY_CREDENTIAL=(str, ""),
    MPESA_STK_TRANSACTION_TYPE=(str, "CustomerPayBillOnline"),
    AT_USERNAME=(str, ""),
    AT_API_KEY=(str, ""),
    AT_SENDER_ID=(str, ""),
    SMS_ENABLED=(bool, False),
    FRONTEND_URL=(str, "http://localhost:8081"),
)

environ.Env.read_env(PROJECT_ROOT / ".env")
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-insecure-secret-key-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "axes",
    "django_filters",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.properties",
    "apps.tenants",
    "apps.leases",
    "apps.ledger",
    "apps.payments",
    "apps.notifications",
    "apps.reports",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
    "apps.core.middleware.AuditContextMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = 60

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "apps.accounts.backends.EmailOrPhoneBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "rent-manager",
    }
}
if env("REDIS_URL"):
    CACHES["default"] = {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
    }

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/min",
        "user": "240/min",
        "login": "8/min",
        "mpesa": "120/min",
        "sms": "30/min",
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Rent Manager Kenya API",
    "DESCRIPTION": (
        "Rent management for Kenyan landlords: properties, leases, immutable ledger, "
        "M-Pesa C2B/STK, cash receipts, arrears and reporting."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SECURITY": [{"jwtAuth": []}],
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": True},
    "TAGS": [
        {"name": "auth", "description": "Authentication and 2FA"},
        {"name": "properties", "description": "Properties and units"},
        {"name": "tenants", "description": "Tenant records"},
        {"name": "leases", "description": "Lease lifecycle"},
        {"name": "ledger", "description": "Immutable ledger"},
        {"name": "payments", "description": "Cash and M-Pesa payments"},
        {"name": "webhooks", "description": "M-Pesa callbacks"},
        {"name": "notifications", "description": "Reminders and SMS"},
        {"name": "reports", "description": "Dashboard and reports"},
    ],
}

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=not DEBUG)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

AXES_ENABLED = env.bool("AXES_ENABLED", default=True)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = [["ip_address", "username"]]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_CALLABLE = None

FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY")

MPESA = {
    "ENABLED": env("MPESA_ENABLED"),
    "ENV": env("MPESA_ENV"),
    "CONSUMER_KEY": env("MPESA_CONSUMER_KEY"),
    "CONSUMER_SECRET": env("MPESA_CONSUMER_SECRET"),
    "SHORTCODE": env("MPESA_SHORTCODE"),
    "PASSKEY": env("MPESA_PASSKEY"),
    "CALLBACK_TOKEN": env("MPESA_CALLBACK_TOKEN"),
    "VALIDATION_TOKEN": env("MPESA_VALIDATION_TOKEN"),
    "CALLBACK_BASE_URL": env("MPESA_CALLBACK_BASE_URL"),
    "IP_ALLOWLIST": env("MPESA_IP_ALLOWLIST"),
    "INITIATOR_NAME": env("MPESA_INITIATOR_NAME"),
    "SECURITY_CREDENTIAL": env("MPESA_SECURITY_CREDENTIAL"),
    "STK_TRANSACTION_TYPE": env("MPESA_STK_TRANSACTION_TYPE"),
}

AFRICASTALKING = {
    "USERNAME": env("AT_USERNAME"),
    "API_KEY": env("AT_API_KEY"),
    "SENDER_ID": env("AT_SENDER_ID"),
    "ENABLED": env("SMS_ENABLED"),
}

FRONTEND_URL = env("FRONTEND_URL")

CELERY_BROKER_URL = env("REDIS_URL") or "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = env("REDIS_URL") or "redis://localhost:6379/0"
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER")
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "generate-rent-charges": {
        "task": "apps.ledger.tasks.generate_rent_charges_task",
        "schedule": 60 * 60 * 24,
    },
    "apply-late-fees": {
        "task": "apps.ledger.tasks.apply_late_fees_task",
        "schedule": 60 * 60 * 24,
    },
    "send-reminders": {
        "task": "apps.notifications.tasks.send_rent_reminders_task",
        "schedule": 60 * 60 * 24,
    },
    "reconcile-mpesa": {
        "task": "apps.payments.tasks.reconcile_mpesa_task",
        "schedule": 60 * 60,
    },
    "expire-leases": {
        "task": "apps.leases.tasks.expire_leases_task",
        "schedule": 60 * 60 * 24,
    },
    "retry-failed-sms": {
        "task": "apps.notifications.tasks.retry_failed_sms_task",
        "schedule": 60 * 15,
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@rentmanager.local")
