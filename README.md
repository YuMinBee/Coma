# SafePrompt Guard

**외부 AI(ChatGPT, Gemini 등) 입력 전 유출 위험 검사 · 마스킹 · 안전 프롬프트 생성** 웹앱 MVP

## 기능

- **3단계 탐지**: 정규식 → 코드/로그 규칙 → Gemma(Ollama) 문맥 분석
- **자동 마스킹**: API Key, 비밀번호, DB URL, 내부 IP/도메인 등
- **안전 프롬프트 생성**: 외부 AI에 바로 붙여넣을 수 있는 질문문
- **파일 업로드**: 허용 확장자는 `shared/allowed_extensions.json` 한 곳에서 관리 (프론트·백엔드 공통)
- **검사 이력 (서버)**: SQLite 로컬 DB (`backend/data/safeprompt.db`)
- **에이전트 UI**: 검사 이력·오른쪽 결과 패널·외부 반입 시나리오 5종
- **네이티브 GUI 프로토타입**: 브라우저 없이 실행파일로 패키징 가능한 Tkinter 앱 (`desktop_native/`)

## 실행 방법

### 1. 백엔드 (FastAPI)

> Python **3.10 이상**이 필요합니다. (`int | None` 타입 문법 사용, Docker 이미지는 Python 3.12)

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### 2. 프론트엔드 (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 **http://localhost:5173** 접속

### 3. (선택) Gemma 문맥 분석 — Ollama

```bash
ollama pull gemma2:2b
ollama serve
```

Ollama가 없어도 **정규식 + 규칙 기반** 탐지와 **템플릿 안전 프롬프트**는 동작합니다.

### 4. Docker Compose (백엔드 + 프론트 한 번에)

**개발·로컬 빌드**

```bash
docker compose up --build
```

**심사·데모 (GHCR 이미지 pull, 빌드 없음)**

```bash
# Windows
scripts\install-docker.bat
scripts\start-judge.bat

# Linux / macOS
chmod +x scripts/*.sh
./scripts/install-docker.sh
./scripts/start-judge.sh
```

- 웹 UI: **http://localhost:8080**
- API 직접: **http://localhost:8001**
- 검사 로그 DB: Docker volume `safeprompt-data` (`/data/safeprompt.db`)

**오프라인 번들 (이미지 tar 포함, pull 없음)**

```bash
# 인터넷 가능한 PC에서 번들 생성
./scripts/export-offline-bundle.sh

# 심사 PC에서는 release/safepromptguard-v3 폴더를 받아 실행
./scripts/start-offline.sh      # Linux / macOS
scripts\start-offline.bat       # Windows
```

| 문서 | 대상 |
|------|------|
| [docs/INSTALL_DOCKER.md](docs/INSTALL_DOCKER.md) | 심사위원 설치·실행 |
| [docs/PUBLISH_GHCR.md](docs/PUBLISH_GHCR.md) | 팀 GHCR 빌드·push |

호스트 PC에서 Ollama를 쓰려면 기본값 `OLLAMA_BASE=http://host.docker.internal:11434` 를 사용합니다.  
Ollama 없이도 정규식·규칙 탐지는 동작합니다. Linux Docker 환경에서 `Ollama 연결됨 · Gemma 모델 없음` 으로 보이면 Ollama 실행 사용자/모델 저장 경로가 다른 상태일 수 있으니 [Docker 설치 가이드의 Ollama 섹션](docs/INSTALL_DOCKER.md#5-선택-gemma--ollama)을 확인하세요.

환경 변수 예시 (`.env` 또는 `.env.prod`):

```bash
OLLAMA_BASE=http://host.docker.internal:11434
GEMMA_MODEL=gemma2:2b
```

### 5. 네이티브 GUI 프로토타입

브라우저나 Electron 없이 로컬 실행파일로 패키징 가능한 GUI입니다. 기존 백엔드 스캐너를 직접 호출하고, 로컬 Ollama의 `gemma2:2b` 상태를 표시합니다.

```bash
python desktop_native/safeprompt_gui.py
```

실행파일 빌드:

```bash
./scripts/build-gui-exe.sh      # Linux / macOS
scripts\build-gui-exe.bat       # Windows
```

자세한 내용: [docs/DESKTOP_NATIVE_GUI.md](docs/DESKTOP_NATIVE_GUI.md)

## 검사 로그 (SQLite)

검사할 때마다 서버가 **로컬 SQLite**에 기록합니다 (외부 DB·클라우드 미사용 → 폐쇄망 가능).

| 항목 | 설명 |
|------|------|
| 저장 위치 (로컬 개발) | `backend/data/safeprompt.db` |
| 환경 변수 | `SAFE_PROMPT_DB_PATH` 로 경로 변경 |
| 조회 API | `GET /api/logs?limit=50` |

브라우저 `localStorage` 이력(채팅 세션)과 별개로, **감사·통계용 서버 이력**입니다.

## 성능 측정 (팀원 실행 가이드)

과제 정량 목표 **「1MB 이하 텍스트 · 평균 5초 이내 분석」** 를 재현·기록하기 위한 절차입니다.  
**사양이 낮은 PC에서는 Gemma 포함 전체 벤치마크를 한 번에 돌리지 마세요.** (수십 분 이상 걸릴 수 있음)

### 측정 목표

| 항목 | 기준 |
|------|------|
| 응답 시간 | 구간별 **평균 5,000ms 이하** 권장 |
| 입력 크기 | API 상한 **최대 1,048,576자** (약 1MiB) |
| 측정 대상 | `run_scan()` 전체 (정규식 → 규칙 → 선택 Gemma → 마스킹 → 안전 프롬프트), HTTP 업로드 오버헤드 제외 |

### 사전 준비

```bash
cd backend
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

- **1·2차만 측정**: Ollama 불필요  
- **Gemma 포함 측정**: `ollama serve` 실행 후 `ollama pull gemma2:2b`  
- 웹 서버(`uvicorn`)는 **끌 필요 없음** — 스크립트가 `run_scan()` 을 직접 호출합니다.

### 권장 실행 순서 (사양 보통 이상 PC)

**① 정규식+규칙만 (빠름, 1분 내외)**

```bash
cd backend
python scripts/benchmark_scan.py --regex-only --iterations 3
```

**② Gemma 포함 (작은 크기만, Ollama 필요)**

```bash
python scripts/benchmark_scan.py --gemma-only --sizes 10000,50000,100000 --iterations 2
```

**③ (선택) 전체 자동 — 사양 좋은 PC만**

```bash
python scripts/benchmark_scan.py --iterations 3
```

> 50만 자 + Gemma 조합은 매우 오래 걸립니다. 기본 스크립트는 **100,000자 초과 구간은 Gemma ON을 생략**하고 1·2차만 측정합니다.

### 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--iterations N` | 크기·모드별 반복 횟수 | `3` |
| `--sizes` | 쉼표 구분 **문자 수** (예: `10000,100000,500000`) | `10000,50000,100000,500000` |
| `--regex-only` | Gemma 생략 (1·2차만) | - |
| `--gemma-only` | Gemma ON만 (10만 자 이하 크기만) | - |
| `--output PATH` | 결과 Markdown 경로 | `docs/PERFORMANCE.md` |

### 측정 방식 (스크립트 내부)

1. **합성 샘플 텍스트** 생성 — DB URL, 비밀번호, AWS Key, JWT 등이 반복 포함된 블록  
2. 지정 **문자 수**만큼 이어 붙여 입력 생성  
3. 각 구간마다 `run_scan(text, use_gemma=...)` 호출 후 **wall-clock 시간(ms)** 기록  
4. 반복 후 **평균 / 최소 / 최대** 계산, 5초 이내 여부 표시  
5. 결과를 터미널에 출력하고 **`docs/PERFORMANCE.md`** 로 저장  

HTTP(`/api/scan`) 오버헤드는 **포함하지 않습니다.** 실제 API 체감은 네트워크·업로드에 따라 조금 더 길 수 있습니다.

### 결과물 제출

측정 담당자는 실행 후 아래를 공유하면 됩니다.

- `docs/PERFORMANCE.md` (자동 생성)  
- 측정 PC: OS, CPU/RAM 요약, Ollama 연결 여부  
- 사용한 명령어 (`--regex-only` / `--gemma-only` 등)

### 실제 서비스에서 시간 확인 (선택)

SQLite 로그의 `duration_ms` 로도 확인할 수 있습니다.

```bash
# 검사 몇 번 실행한 뒤
curl http://localhost:8001/api/logs?limit=20
```

### 주의

- 벤치마크 도중 터미널에 **출력이 없으면** 진행 중일 수 있습니다. **전체 한 방 실행은 피하고** `--regex-only` → `--gemma-only` 순으로 나누세요.  
- Gemma 문맥 분석 입력은 코드상 **약 12,000자 상한**이라, 대용량 파일도 3차 분석 자체는 일정하지만 **1·2차·프롬프트 생성**은 입력 길이에 비례해 느려질 수 있습니다.

## 데모 시나리오

1. **예시 불러오기** 클릭
2. **유출 위험 검사하기** 클릭
3. 위험도 **높음**, 탐지 항목 확인
4. **안전 프롬프트 복사** → ChatGPT/Gemini에 붙여넣기

## 기술 스택

| 구분 | 기술 |
|------|------|
| Frontend | React, Vite, Lucide Icons |
| Backend | FastAPI, Pydantic |
| 1차 탐지 | 정규식 (AWS Key, JWT, DB URL 등) |
| 2차 탐지 | 개발 문맥 규칙 (prod, internal, .env 등) |
| 3차 탐지 | Gemma via Ollama (로컬) |
| 마스킹 | 위치 기반 + 줄 단위 치환 |

## API

- `GET /api/config` — 허용 확장자·`accept` 속성 (UI 동기화용)
- `GET /api/health` — 서버·Gemma·DB 경로·허용 확장자 상태
- `GET /api/logs` — 최근 검사 이력 (SQLite)
- `POST /api/scan` — 텍스트 검사 `{ "text": "...", "use_gemma": true }`
- `POST /api/scan/file` — 파일 업로드

## 프로젝트 구조

```
├── shared/
│   └── allowed_extensions.json   # 업로드 허용 확장자 (수정 시 여기만 편집)
├── backend/
│   ├── main.py
│   ├── models/schemas.py
│   └── services/
│       ├── regex_scanner.py
│       ├── rule_scanner.py
│       ├── gemma_analyzer.py
│       ├── masking.py
│       ├── audit_log.py
│       ├── notebook_loader.py
│       └── scanner.py
│   └── scripts/
│       └── benchmark_scan.py   # 성능 측정 스크립트
├── docker-compose.yml          # 로컬 빌드
├── docker-compose.prod.yml     # GHCR pull (심사용)
├── docker-compose.offline.yml  # 사전 load 이미지 실행 (오프라인)
├── desktop_native/
│   ├── safeprompt_gui.py       # 네이티브 GUI 프로토타입
│   └── requirements-build.txt
├── .env.prod.example
├── scripts/
│   ├── install-docker.bat / .sh
│   ├── start-judge.bat / .sh
│   ├── start-offline.bat / .sh
│   ├── export-offline-bundle.sh
│   ├── build-gui-exe.bat / .sh
│   └── publish-ghcr.ps1        # 팀 이미지 push
├── docs/
│   ├── INSTALL_DOCKER.md       # 심사위원 가이드
│   ├── PUBLISH_GHCR.md
│   └── PERFORMANCE.md          # 성능 측정 결과 (벤치마크 실행 후 생성)
└── frontend/
    ├── Dockerfile
    └── src/
```
