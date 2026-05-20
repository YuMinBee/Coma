#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[SafePrompt Guard] 오프라인 Docker 실행"
echo

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker가 설치되어 있지 않습니다."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker 데몬이 실행 중이 아닙니다. Docker Desktop / docker 서비스를 켜 주세요."
  exit 1
fi

if [[ ! -f .env.prod ]]; then
  if [[ -f .env.prod.example ]]; then
    echo ".env.prod 가 없어 예시 파일을 복사합니다..."
    cp .env.prod.example .env.prod
  else
    echo ".env.prod 파일이 필요합니다."
    exit 1
  fi
fi

IMAGE_TAR="images/safepromptguard-v3-images.tar"
if [[ -f "$IMAGE_TAR" ]]; then
  echo "이미지 tar 로드 중: $IMAGE_TAR"
  docker load -i "$IMAGE_TAR"
else
  echo "이미지 tar가 없어 로컬 Docker 이미지 캐시를 사용합니다."
fi

echo "컨테이너 시작..."
docker compose -f docker-compose.offline.yml --env-file .env.prod up -d

echo
echo "========================================"
echo " 웹 UI:  http://localhost:8080"
echo " API:    http://localhost:8001/api/health"
echo "========================================"
echo
echo "종료: docker compose -f docker-compose.offline.yml --env-file .env.prod down"
