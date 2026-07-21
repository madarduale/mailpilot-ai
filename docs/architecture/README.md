# Architecture

MailPilot AI uses a modular monolith for the MVP. Each backend domain is a Django
application with explicit API, service, repository, model, serializer, task, and
permission boundaries where applicable.

## Dependency direction

`api -> services -> repositories -> models`

- API views handle HTTP concerns only.
- Services own use-case orchestration and transaction boundaries.
- Repositories encapsulate persistence queries.
- Celery tasks call services and do not duplicate business rules.
- Integrations isolate Gmail, OpenAI, push notification, and speech providers.

The mobile application is organized by product feature. Shared API transport,
navigation, state, UI, and platform integrations live under `mobile/src`.

## Proactive assistant event flow

`AI analysis committed -> Celery evaluation -> decision engine -> suggestion -> delivery`

The decision engine is deterministic and explainable. It ranks analyzed email
signals against user preferences and learned feedback, enforces quiet hours and
daily interruption limits, suppresses duplicates, and stores the reason for
every recommendation. Acceptance and dismissal are transactional service-layer
operations. Scheduled expiry is handled by Celery Beat.
