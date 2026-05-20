# SafePrompt Guard — GHCR 빌드·푸시 (repo 루트에서 실행)
param(
    [string]$Tag = "latest",
    [string]$Owner = $(if ($env:GHCR_OWNER) { $env:GHCR_OWNER } else { "buildguardai" })
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$backend = "ghcr.io/$Owner/safeprompt-guard-v3-backend:$Tag"
$frontend = "ghcr.io/$Owner/safeprompt-guard-v3-frontend:$Tag"

Write-Host "==> Build backend: $backend"
docker build -f backend/Dockerfile -t $backend .

Write-Host "==> Build frontend: $frontend"
docker build -f frontend/Dockerfile -t $frontend .

Write-Host "==> Push"
docker push $backend
docker push $frontend

Write-Host ""
Write-Host "완료. 심사용 .env.prod 예시:"
Write-Host "SAFE_PROMPT_BACKEND_IMAGE=$backend"
Write-Host "SAFE_PROMPT_FRONTEND_IMAGE=$frontend"
Write-Host ""
Write-Host "심사 가이드: docs/INSTALL_DOCKER.md"
