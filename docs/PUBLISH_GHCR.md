# GHCR 이미지 빌드·배포 (팀용)

심사 PC는 **이 문서대로 올린 이미지**를 `docker-compose.prod.yml` 로 pull 합니다.

---

## 1. 사전 준비

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) 실행  
2. GitHub 로그인 (패키지 소유 org/계정과 일치)

```bash
docker login ghcr.io -u YOUR_GITHUB_USERNAME
# Password: GitHub Personal Access Token (classic)
#   scopes: write:packages, read:packages (repo는 private 이미지 시)
```

3. `.env.prod.example` 의 이미지 경로를 **실제 push 대상**과 맞춥니다.

기본 예시 (조직 `BuildGuardAI`):

```text
ghcr.io/buildguardai/safeprompt-guard-v3-backend:latest
ghcr.io/buildguardai/safeprompt-guard-v3-frontend:latest
```

> GHCR 이름은 **소문자**입니다. `BuildGuardAI` → `buildguardai`

---

## 2. 한 번에 빌드·푸시 (Windows)

프로젝트 **루트**에서:

```powershell
.\scripts\publish-ghcr.ps1
```

태그 지정:

```powershell
.\scripts\publish-ghcr.ps1 -Tag "demo-2026-05-19"
```

환경 변수로 레지스트리 prefix 변경:

```powershell
$env:GHCR_OWNER = "yeoul0520"
.\scripts\publish-ghcr.ps1 -Tag "latest"
```

푸시 후 `.env.prod` / `.env.prod.example` 의 이미지 태그를 동일하게 맞추고 심사위원에게 안내합니다.

---

## 3. 수동 빌드·푸시

```bash
cd /path/to/SafePromptGuard   # repo 루트

export OWNER=buildguardai
export TAG=latest

docker build -f backend/Dockerfile -t ghcr.io/${OWNER}/safeprompt-guard-v3-backend:${TAG} .
docker build -f frontend/Dockerfile -t ghcr.io/${OWNER}/safeprompt-guard-v3-frontend:${TAG} .

docker push ghcr.io/${OWNER}/safeprompt-guard-v3-backend:${TAG}
docker push ghcr.io/${OWNER}/safeprompt-guard-v3-frontend:${TAG}
```

---

## 4. 패키지 공개 설정 (심사 pull 간소화)

심사위원이 `docker login` 없이 pull 하려면:

1. GitHub → **Packages** → 해당 container package  
2. **Package settings** → **Change visibility** → **Public**

비공개로 두면 심사 PC에서 PAT로 `docker login ghcr.io` 필요합니다.

---

## 5. 심사 전 검증

팀 PC에서 로컬 빌드 없이 prod compose만 테스트:

```bash
cp .env.prod.example .env.prod
# .env.prod 에 방금 push 한 태그 반영

docker compose -f docker-compose.prod.yml --env-file .env.prod pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
curl http://localhost:8080/api/health
```

브라우저: http://localhost:8080

---

## 6. 재배포 (기능 수정 후)

1. 코드 수정  
2. `.\scripts\publish-ghcr.ps1 -Tag <새태그>`  
3. `.env.prod.example` / 심사 안내 문서의 태그 갱신  
4. 심사 PC: `scripts/start-judge.bat` 재실행 (`pull` + `up -d`)

오프라인 ZIP 번들은 별도 스크립트(추후 `build-offline-bundle.ps1`)로 다시 만들면 됩니다.

---

## 7. 관련 파일

| 파일 | 용도 |
|------|------|
| `docker-compose.prod.yml` | GHCR image pull 전용 |
| `.env.prod.example` | 이미지 URL·포트 템플릿 |
| `scripts/start-judge.*` | 심사 실행 |
| `docs/INSTALL_DOCKER.md` | 심사위원 설치 가이드 |
