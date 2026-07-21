from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False
required_settings = {
    "DATABASE_URL": env.str("DATABASE_URL", default=""),  # noqa: F405
    "DJANGO_ALLOWED_HOSTS": env.list("DJANGO_ALLOWED_HOSTS", default=[]),  # noqa: F405
    "GOOGLE_OAUTH_CLIENT_ID": GOOGLE_OAUTH_CLIENT_ID,  # noqa: F405
    "GOOGLE_OAUTH_CLIENT_SECRET": GOOGLE_OAUTH_CLIENT_SECRET,  # noqa: F405
    "GOOGLE_OAUTH_REDIRECT_URI": GOOGLE_OAUTH_REDIRECT_URI,  # noqa: F405
    "REDIS_URL": env.str("REDIS_URL", default=""),  # noqa: F405
}
if "openrouter" in {AI_TEXT_PROVIDER, AI_AUDIO_PROVIDER}:  # noqa: F405
    required_settings["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY  # noqa: F405
if "openai" in {AI_TEXT_PROVIDER, AI_AUDIO_PROVIDER}:  # noqa: F405
    required_settings["OPENAI_API_KEY"] = OPENAI_API_KEY  # noqa: F405
missing_settings = [name for name, value in required_settings.items() if not value]
if SECRET_KEY == "unsafe-development-key-change-me":  # noqa: F405
    missing_settings.append("DJANGO_SECRET_KEY")
if not OAUTH_TOKEN_ENCRYPTION_KEYS:  # noqa: F405
    missing_settings.append("OAUTH_TOKEN_ENCRYPTION_KEYS")
if missing_settings:
    missing = ", ".join(sorted(set(missing_settings)))
    raise ImproperlyConfigured(f"Missing required production settings: {missing}")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31_536_000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
