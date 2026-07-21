from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = list(  # noqa: F405
    dict.fromkeys([*ALLOWED_HOSTS, "0.0.0.0", ".ngrok-free.dev"])  # noqa: F405
)
CSRF_TRUSTED_ORIGINS = list(  # noqa: F405
    dict.fromkeys(  # noqa: F405
        [
            *CSRF_TRUSTED_ORIGINS,  # noqa: F405
            "https://*.ngrok-free.dev",
            "http://*.ngrok-free.dev",
        ]
    )
)
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += (  # noqa: F405
    "rest_framework.renderers.BrowsableAPIRenderer",
)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
