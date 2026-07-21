# MailPilot backend

## Settings profiles

- `config.settings.local` enables the browsable API and console email backend.
- `config.settings.test` uses in-memory SQLite, cache, channels, email, and Celery.
- `config.settings.production` fails fast when required secrets and service URLs
  are missing and enables Django's HTTPS deployment protections.

Copy the repository-level `.env.example` to `.env` and replace every secret.
Production must provide PostgreSQL, Redis, Gmail OAuth, OpenAI, and versioned
OAuth-token encryption settings through the environment or a secret manager.

## Common commands

Run these commands from this `backend` directory:

```powershell
python -m pip install -e ".[dev]"
python manage.py check --settings=config.settings.local
python manage.py runserver
celery -A config worker --loglevel=INFO
daphne config.asgi:application
```

Use `config.settings.production` explicitly in every deployed web, worker, and
scheduler process.

## Containerized local stack

From the repository root, start PostgreSQL, Redis, Django ASGI, Celery worker,
Celery Beat, and Nginx with:

```powershell
.\infrastructure\scripts\start-backend.ps1
```

The API is available at `http://localhost:8000`, Swagger at
`http://localhost:8000/api/docs/`, and the Nginx gateway at
`http://localhost:8080`. PostgreSQL and Redis are exposed on host ports `5433`
and `6380` by default to avoid colliding with locally installed services.

Run the isolated container test suite with:

```powershell
.\infrastructure\scripts\test-backend.ps1
```

To run Django directly on the host while using the Compose PostgreSQL and Redis
containers, use:

```powershell
.\infrastructure\scripts\run-backend-local.ps1
```

Stop services without deleting database data:

```powershell
docker compose down
```

To also remove local PostgreSQL and Redis volumes, explicitly run
`docker compose down --volumes`.
