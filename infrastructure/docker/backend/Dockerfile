FROM python:3.13-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/app/.local/bin:${PATH}"

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system mailpilot \
    && useradd --system --gid mailpilot --home-dir /app --create-home mailpilot

WORKDIR /app

FROM base AS builder
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY . /build
WORKDIR /build
RUN python -m pip wheel --wheel-dir /wheels .

FROM base AS runtime
COPY --from=builder /wheels /wheels
RUN python -m pip install /wheels/* \
    && rm -rf /wheels
COPY --chown=mailpilot:mailpilot . /app
COPY --chown=mailpilot:mailpilot bin/backend-entrypoint.sh /usr/local/bin/backend-entrypoint
RUN chmod 0755 /usr/local/bin/backend-entrypoint \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R mailpilot:mailpilot /app
USER mailpilot
EXPOSE 8000
ENTRYPOINT ["backend-entrypoint"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]

FROM runtime AS development
RUN python -m pip install --user \
      ruff \
      mypy \
      "django-stubs[compatible-mypy]" \
      "djangorestframework-stubs[compatible-mypy]" \
      pytest \
      pytest-django \
      coverage
