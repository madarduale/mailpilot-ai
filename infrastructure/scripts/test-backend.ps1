$ErrorActionPreference = 'Stop'

docker compose --profile test build test
docker compose --profile test run --rm test
