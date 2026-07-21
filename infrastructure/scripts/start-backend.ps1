$ErrorActionPreference = 'Stop'

docker compose up --build --detach db redis backend worker scheduler nginx
docker compose ps

Write-Host ''
Write-Host 'MailPilot API: http://localhost:8000/api/v1/'
Write-Host 'Swagger UI:   http://localhost:8000/api/docs/'
Write-Host 'Nginx gateway: http://localhost:8080/'
