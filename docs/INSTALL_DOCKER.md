# SafePrompt Guard — 심사위원 Docker 설치·실행 가이드

**기본 전제**: 심사 PC에 **인터넷**이 되고, **USB로 파일을 받을 수 없**는 경우를 기준으로 합니다.<br>
앱은 GitHub Container Registry(GHCR)에서 이미지를 받아 실행합니다. (소스 빌드 불필요)<br>
인터넷이 없는 심사 PC는 [4-2. 오프라인 번들 실행](#4-2-오프라인-번들-실행)을 사용합니다.

---

## 1. 필요한 것

| 항목 | 설명 |
|------|------|
| OS | Windows 10/11 64bit, 또는 Linux / macOS |
| RAM | 8GB 이상 권장 (Gemma·Ollama 사용 시 더 필요) |
| 디스크 | Docker 이미지용 여유 2GB 이상 |
| 네트워크 | 온라인 방식: Docker Desktop 설치, `docker pull`, (선택) Ollama 모델 다운로드 / 오프라인 번들 방식: 최초 설치 후 pull 불필요 |
| 권한 | Docker Desktop 설치 시 관리자 권한 |

**Gemma 문맥 분석**은 선택입니다. Ollama 없이도 **정규식·규칙 탐지·마스킹·안전 프롬프트**는 동작합니다.

---

## 2. 저장소 받기

인터넷이 되면 GitHub에서 클론하거나 ZIP을 받습니다.

```bash
git clone https://github.com/BuildGuardAI/SafePromptGuard.git
cd SafePromptGuard
```

ZIP만 받아도 됩니다. 아래 파일이 포함되어 있으면 실행 가능합니다.

- `docker-compose.prod.yml`
- `docker-compose.offline.yml` (오프라인 번들)
- `.env.prod.example`
- `scripts/start-judge.bat` (Windows) 또는 `scripts/start-judge.sh` (Linux/macOS)
- `scripts/start-offline.bat` 또는 `scripts/start-offline.sh` (오프라인 번들)

---

## 3. Docker 설치

### Windows

1. `scripts\install-docker.bat` 실행 — 설치 여부 확인 및 안내  
2. 또는 [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) 설치  
3. 설치 후 **재부팅**, **Docker Desktop 실행** (트레이 고래 아이콘)

### Linux

```bash
chmod +x scripts/install-docker.sh scripts/start-judge.sh
./scripts/install-docker.sh
```

Ubuntu 예: [Docker Engine 설치 문서](https://docs.docker.com/engine/install/ubuntu/)  
`docker compose` 플러그인 포함 버전을 사용하세요.

### macOS

[Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/) 설치 후 실행.

---

## 4. 앱 실행 (심사용)

### 4-1. 온라인 실행 (GHCR pull)

### Windows

```bat
scripts\start-judge.bat
```

### Linux / macOS

```bash
chmod +x scripts/start-judge.sh
./scripts/start-judge.sh
```

스크립트가 하는 일:

1. `.env.prod` 없으면 `.env.prod.example` 복사  
2. `docker compose -f docker-compose.prod.yml pull`  
3. `docker compose ... up -d`  

### 브라우저

| 주소 | 용도 |
|------|------|
| **http://localhost:8080** | 웹 UI (권장) |
| http://localhost:8001/api/health | API 상태 확인 |

### 종료

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod down
```

Windows: 동일 명령을 프로젝트 루트에서 `cmd` 또는 PowerShell에 입력.

---

### 4-2. 오프라인 번들 실행

인터넷 가능한 PC에서 팀원이 먼저 번들을 만듭니다.

```bash
./scripts/export-offline-bundle.sh
```

생성된 `release/safepromptguard-v3` 폴더를 심사 PC로 전달합니다. 심사 PC에서는 네트워크 없이 아래만 실행합니다.

```bash
# Windows
scripts\start-offline.bat

# Linux / macOS
chmod +x scripts/start-offline.sh
./scripts/start-offline.sh
```

오프라인 compose는 `docker-compose.offline.yml`을 사용하며 `pull_policy: never`라서 GHCR에 접속하지 않습니다. 단, Docker Desktop 또는 Docker Engine은 사전에 설치되어 있어야 합니다.

---

## 5. (선택) Gemma — Ollama

호스트 PC에 Ollama를 설치한 뒤:

```bash
ollama pull gemma2:2b
ollama serve
```

Docker 컨테이너는 기본적으로 `http://host.docker.internal:11434` 로 호스트 Ollama에 접속합니다.  
웹 UI 상단 **Gemma 사용 가능** 여부를 `/api/health` 로 확인할 수 있습니다.

### Linux에서 `Ollama 연결됨 · Gemma 모델 없음` 이 보일 때

Docker 컨테이너가 Ollama 서버에는 연결됐지만 모델 목록이 비어 있으면, Ollama 실행 사용자나 모델 저장 경로가 다른 경우입니다. 먼저 호스트에서 확인합니다.

```bash
curl http://127.0.0.1:11434/api/tags
ollama list
```

`gemma2:2b`가 보이지 않으면 모델을 다시 받기보다, 모델이 저장된 Ollama 서비스 기준으로 실행해야 합니다. systemd 서비스에 Docker 접근용 host binding을 추가합니다.

```bash
sudo systemctl edit ollama
```

아래 내용을 추가합니다.

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

적용 후 재시작합니다.

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
docker compose restart backend
curl http://127.0.0.1:8001/api/health
```

성공 기준은 `"ollama_available": true`, `"gemma_available": true` 입니다.

---

## 6. 자주 나는 문제

### `pull` 실패 / image not found

- 팀이 아직 GHCR에 이미지를 올리지 않았을 수 있습니다. → 팀에 `latest` 태그 push 요청  
- `.env.prod` 의 이미지 이름·태그가 push 된 것과 다른지 확인  
- 조직 패키지가 **비공개**이면: `docker login ghcr.io` (GitHub PAT, `read:packages`)

### Docker Desktop이 안 켜짐

- Windows: WSL2 / 가상화 BIOS 설정 확인  
- `docker version` 이 성공하는지 확인

### 포트 충돌 (8080 / 8001 사용 중)

`.env.prod` 에서 변경:

```env
FRONTEND_PORT=9080
BACKEND_PORT=8002
```

이후 `http://localhost:9080` 으로 접속.

### 방화벽 / 회사망

- `ghcr.io`, `docker.io` HTTPS 허용 필요  
- 프록시 환경이면 Docker Desktop 프록시 설정

### 오프라인 실행 실패

- `images/safepromptguard-v3-images.tar`가 번들에 있는지 확인
- `docker load -i images/safepromptguard-v3-images.tar`가 성공하는지 확인
- `.env.prod`의 이미지 이름이 번들에 포함된 이미지 태그와 같은지 확인

---

## 7. 팀(개발자)용

이미지 빌드·GHCR 업로드: [PUBLISH_GHCR.md](./PUBLISH_GHCR.md)

로컬에서 소스 빌드해 실행하려면 (심사와 별도):

```bash
docker compose up --build
```

---

## 8. 체크리스트 (심사 당일)

- [ ] Docker Desktop 실행 중  
- [ ] `scripts/start-judge.bat` (또는 `.sh`) 성공  
- [ ] http://localhost:8080 에서 샘플 텍스트 검사  
- [ ] (선택) Ollama + Gemma 사용 시 health 에 `gemma_available: true`
