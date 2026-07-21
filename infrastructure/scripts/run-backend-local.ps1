$ErrorActionPreference = 'Stop'

$env:DJANGO_SETTINGS_MODULE = 'config.settings.local'
$env:DJANGO_ALLOWED_HOSTS = 'localhost,127.0.0.1,0.0.0.0,.ngrok-free.dev'
$env:DJANGO_CSRF_TRUSTED_ORIGINS = 'http://localhost:8000,https://*.ngrok-free.dev,http://*.ngrok-free.dev'
$env:DATABASE_URL = 'postgresql://mailpilot:mailpilot@127.0.0.1:5433/mailpilot'
$env:REDIS_URL = 'redis://127.0.0.1:6380/0'
$env:REDIS_CACHE_URL = 'redis://127.0.0.1:6380/1'
$env:CELERY_BROKER_URL = 'redis://127.0.0.1:6380/2'
$env:CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6380/3'

Push-Location (Join-Path $PSScriptRoot '..\..\backend')
try {
    python manage.py migrate --noinput
    python manage.py runserver 0.0.0.0:8000
}
finally {
    Pop-Location
}
