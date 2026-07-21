from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

import environ
from corsheaders.defaults import default_headers

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent

env = environ.Env(
    DEBUG=(bool, False),
    DJANGO_SECRET_KEY=(str, "unsafe-development-key-change-me"),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
    DATABASE_URL=(
        str, "postgresql://mailpilot:mailpilot@localhost:5432/mailpilot"),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    CORS_ALLOWED_ORIGINS=(list, []),
    OAUTH_TOKEN_ENCRYPTION_KEYS=(list, []),
)

environment_file = env.str(
    "DJANGO_ENV_FILE", default=str(PROJECT_DIR / ".env"))
if environment_file and Path(environment_file).is_file():
    environ.Env.read_env(environment_file, overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
JWT_SIGNING_KEY = env.str("JWT_SIGNING_KEY", default=SECRET_KEY)
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("DJANGO_CSRF_TRUSTED_ORIGINS")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "channels",
]
LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.dashboard",
    "apps.email_accounts",
    "apps.emails",
    "apps.intelligence",
    "apps.reminders",
    "apps.notifications",
    "apps.voice",
    "apps.preferences",
    "apps.proactive_assistant.apps.ProactiveAssistantConfig",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.common.middleware.RequestIDMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BACKEND_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = 60
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BACKEND_DIR / "locale"]

STATIC_URL = "/static/"
STATIC_ROOT = BACKEND_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BACKEND_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

API_PAGE_SIZE = env.int("API_PAGE_SIZE", default=25)
API_MAX_PAGE_SIZE = env.int("API_MAX_PAGE_SIZE", default=100)
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPageNumberPagination",
    "PAGE_SIZE": API_PAGE_SIZE,
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ("v1",),
    "VERSION_PARAM": "version",
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S.%fZ",
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("JWT_ACCESS_TOKEN_MINUTES", default=15)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int("JWT_REFRESH_TOKEN_DAYS", default=30)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": JWT_SIGNING_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "uuid",
    "USER_ID_CLAIM": "user_id",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "MailPilot AI API",
    "DESCRIPTION": "AI-powered email and voice assistant API.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
    "SERVE_PERMISSIONS": ("rest_framework.permissions.AllowAny",),
    "ENUM_NAME_OVERRIDES": {
        "NotificationChannelEnum": "apps.notifications.models.NotificationChannel.choices",
        "AssistantDeliveryMethodEnum": (
            "apps.proactive_assistant.enums.DeliveryMethod.choices"
        ),
    },
}

REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "auth_register": env.str("AUTH_REGISTER_RATE", default="5/hour"),
    "auth_login": env.str("AUTH_LOGIN_RATE", default="10/minute"),
    "auth_refresh": env.str("AUTH_REFRESH_RATE", default="30/minute"),
    "auth_password_change": env.str("AUTH_PASSWORD_CHANGE_RATE", default="5/hour"),
    "health": env.str("HEALTH_CHECK_RATE", default="60/minute"),
}

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=False)
CORS_ALLOW_HEADERS = (*default_headers, "x-request-id")
CORS_EXPOSE_HEADERS = ("X-Request-ID",)
REDIS_URL = env("REDIS_URL")
REDIS_CACHE_URL = env.str(
    "REDIS_CACHE_URL", default="redis://localhost:6379/1")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "TIMEOUT": 300,
    },
}
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
            "capacity": env.int("CHANNEL_CAPACITY", default=1500),
            "expiry": env.int("CHANNEL_EXPIRY_SECONDS", default=60),
        },
    },
}

CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT_SECONDS", default=900)
CELERY_TASK_SOFT_TIME_LIMIT = env.int(
    "CELERY_TASK_SOFT_TIME_LIMIT_SECONDS", default=840)
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BEAT_SCHEDULE = {
    "expire-stale-assistant-suggestions": {
        "task": "apps.proactive_assistant.tasks.expire_stale_suggestions",
        "schedule": 300.0,
    },
    "sync-connected-gmail-accounts": {
        "task": "apps.email_accounts.tasks.sync_all_gmail_accounts",
        "schedule": 60.0,
    },
    "dispatch-due-reminders": {
        "task": "apps.reminders.tasks.dispatch_due_reminders",
        "schedule": 60.0,
    },
}

EMAIL_BACKEND = env.str(
    "DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = env.str(
    "DEFAULT_FROM_EMAIL", default="MailPilot AI <noreply@localhost>")

AI_TEXT_PROVIDER = env.str("AI_TEXT_PROVIDER", default="openrouter").lower()
AI_AUDIO_PROVIDER = env.str("AI_AUDIO_PROVIDER", default="openrouter").lower()
AI_CONNECT_TIMEOUT_SECONDS = env.float("AI_CONNECT_TIMEOUT_SECONDS", default=5.0)
AI_READ_TIMEOUT_SECONDS = env.float("AI_READ_TIMEOUT_SECONDS", default=60.0)
AI_WRITE_TIMEOUT_SECONDS = env.float("AI_WRITE_TIMEOUT_SECONDS", default=30.0)
AI_MAX_RETRIES = env.int("AI_MAX_RETRIES", default=2)
AI_MAX_OUTPUT_TOKENS = env.int("AI_MAX_OUTPUT_TOKENS", default=512)
NEW_EMAIL_NOTIFICATION_MAX_AGE_SECONDS = env.int(
    "NEW_EMAIL_NOTIFICATION_MAX_AGE_SECONDS", default=900
)

OPENROUTER_API_KEY = env.str("OPENROUTER_API_KEY", default="")
OPENROUTER_BASE_URL = env.str(
    "OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1"
)
OPENROUTER_RESPONSES_MODEL = env.str(
    "OPENROUTER_RESPONSES_MODEL", default="openai/gpt-5.6-terra"
)
OPENROUTER_TRANSCRIPTION_MODEL = env.str(
    "OPENROUTER_TRANSCRIPTION_MODEL", default="openai/whisper-1"
)
OPENROUTER_TTS_MODEL = env.str(
    "OPENROUTER_TTS_MODEL", default="x-ai/grok-voice-tts-1.0"
)
OPENROUTER_TTS_FALLBACK_MODELS = env.list(
    "OPENROUTER_TTS_FALLBACK_MODELS",
    default=["hexgrad/kokoro-82m", "mistralai/voxtral-mini-tts-2603"],
)
OPENROUTER_TTS_VOICE = env.str(
    "OPENROUTER_TTS_VOICE", default="Eve"
)
OPENROUTER_HTTP_REFERER = env.str("OPENROUTER_HTTP_REFERER", default="")
OPENROUTER_APP_TITLE = env.str("OPENROUTER_APP_TITLE", default="MailPilot AI")

# Direct OpenAI remains available as an optional production provider.
OPENAI_API_KEY = env.str("OPENAI_API_KEY", default="")
OPENAI_BASE_URL = env.str("OPENAI_BASE_URL", default="https://api.openai.com/v1")
OPENAI_RESPONSES_MODEL = env.str("OPENAI_RESPONSES_MODEL", default="gpt-5.6-terra")
OPENAI_TRANSCRIPTION_MODEL = env.str(
    "OPENAI_TRANSCRIPTION_MODEL", default="whisper-1")
OPENAI_TTS_MODEL = env.str("OPENAI_TTS_MODEL", default="gpt-4o-mini-tts")
GOOGLE_OAUTH_CLIENT_ID = env.str("GOOGLE_OAUTH_CLIENT_ID", default="")
GOOGLE_OAUTH_CLIENT_SECRET = env.str("GOOGLE_OAUTH_CLIENT_SECRET", default="")
GOOGLE_OAUTH_REDIRECT_URI = env.str("GOOGLE_OAUTH_REDIRECT_URI", default="")
GOOGLE_OAUTH_SCOPES = env.list(
    "GOOGLE_OAUTH_SCOPES",
    default=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/gmail.modify",
    ],
)
GOOGLE_OAUTH_STATE_TTL_SECONDS = env.int("GOOGLE_OAUTH_STATE_TTL_SECONDS", default=600)
GOOGLE_API_TIMEOUT_SECONDS = env.float("GOOGLE_API_TIMEOUT_SECONDS", default=30.0)
GOOGLE_OAUTH_CLOCK_SKEW_SECONDS = env.int(
    "GOOGLE_OAUTH_CLOCK_SKEW_SECONDS", default=30
)
if not 0 <= GOOGLE_OAUTH_CLOCK_SKEW_SECONDS <= 120:
    raise ValueError("GOOGLE_OAUTH_CLOCK_SKEW_SECONDS must be between 0 and 120.")
OAUTH_MOBILE_REDIRECT_SCHEMES = env.list(
    "OAUTH_MOBILE_REDIRECT_SCHEMES", default=["mailpilot"]
)
OAUTH_TOKEN_ENCRYPTION_KEYS = env("OAUTH_TOKEN_ENCRYPTION_KEYS")
EXPO_ACCESS_TOKEN = env.str("EXPO_ACCESS_TOKEN", default="")
PROACTIVE_ASSISTANT_AUTO_EVALUATE = env.bool(
    "PROACTIVE_ASSISTANT_AUTO_EVALUATE",
    default=True,
)
PROACTIVE_ASSISTANT_DAILY_LIMIT = env.int(
    "PROACTIVE_ASSISTANT_DAILY_LIMIT",
    default=4,
)

LOG_LEVEL = env.str("LOG_LEVEL", default="INFO")
LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "apps.common.utils.logging.JSONFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_id"],
        },
    },
    "filters": {
        "request_id": {"()": "apps.common.utils.logging.RequestIDFilter"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "apps": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}
