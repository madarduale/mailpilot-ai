# API conventions

The public API is versioned under `/api/v1/`. New breaking contracts require a
new namespace rather than changing an existing version in place.

## Successful collections

Collection endpoints use page-number pagination and return `count`, `next`,
`previous`, `page`, `page_size`, and `results`.

## Errors

Errors use one stable envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Bad Request",
    "details": {}
  },
  "request_id": "correlation-id"
}
```

Clients may send `X-Request-ID`; unsafe values are replaced. Every response
returns the effective ID in the same header for support and log correlation.

## Discovery and probes

- OpenAPI schema: `/api/schema/`
- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- Liveness: `/api/v1/health/live/`
- Readiness: `/api/v1/health/ready/`

## Proactive assistant

All proactive assistant endpoints require JWT authentication and are scoped to
the current user.

- Today's briefing: `GET /api/v1/assistant/briefing/today/`
- Suggestions: `GET /api/v1/assistant/suggestions/`
- Accept: `POST /api/v1/assistant/suggestions/{uuid}/accept/`
- Dismiss: `POST /api/v1/assistant/suggestions/{uuid}/dismiss/`
- History: `GET /api/v1/assistant/history/`
- Evaluate an analyzed email: `POST /api/v1/assistant/recommendations/generate/`

Suggestion collections support searching, ordering, and filtering by status,
type, and delivery method. Accept and dismiss operations are idempotency-safe:
terminal suggestions return `409 Conflict` rather than executing twice.

## Voice and notifications

- Voice turn: `POST /api/v1/voice/conversations/turn/`
- Notifications: `GET /api/v1/notifications/`
- Mark one read: `POST /api/v1/notifications/{uuid}/read/`
- Mark all read: `POST /api/v1/notifications/read-all/`
- Register Expo device: `POST /api/v1/notifications/devices/`

Voice uploads are limited to 25 MB and supported audio content types. Provider
calls are isolated behind an integration gateway. Push delivery is asynchronous,
retryable, and stores Expo ticket IDs and failure details.
