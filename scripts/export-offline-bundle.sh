#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env.prod ]]; then
  cp .env.prod.example .env.prod
fi

set -a
. ./.env.prod
set +a

BUNDLE_DIR="release/safepromptguard-v3"
IMAGE_TAR="$BUNDLE_DIR/images/safepromptguard-v3-images.tar"

rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR/images" "$BUNDLE_DIR/scripts"

docker compose -f docker-compose.prod.yml --env-file .env.prod pull
docker save -o "$IMAGE_TAR" "$SAFE_PROMPT_BACKEND_IMAGE" "$SAFE_PROMPT_FRONTEND_IMAGE"

cp docker-compose.offline.yml "$BUNDLE_DIR/docker-compose.offline.yml"
cp .env.prod.example "$BUNDLE_DIR/.env.prod.example"
cp scripts/start-offline.sh "$BUNDLE_DIR/scripts/start-offline.sh"
cp scripts/start-offline.bat "$BUNDLE_DIR/scripts/start-offline.bat"
cp docs/INSTALL_DOCKER.md "$BUNDLE_DIR/INSTALL_DOCKER.md"

chmod +x "$BUNDLE_DIR/scripts/start-offline.sh"

echo "오프라인 번들 생성 완료: $BUNDLE_DIR"
echo "공유 전 압축 예: tar -czf release/safepromptguard-v3.tar.gz -C release safepromptguard-v3"
