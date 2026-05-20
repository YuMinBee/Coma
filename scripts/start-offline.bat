@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

echo [SafePrompt Guard] 오프라인 Docker 실행
echo.

docker version >nul 2>&1
if errorlevel 1 (
    echo Docker가 설치되어 있지 않거나 실행 중이 아닙니다.
    echo Docker Desktop을 켜 주세요.
    exit /b 1
)

if not exist ".env.prod" (
    if exist ".env.prod.example" (
        echo .env.prod 가 없어 예시 파일을 복사합니다...
        copy /Y ".env.prod.example" ".env.prod" >nul
    ) else (
        echo .env.prod 파일이 필요합니다. .env.prod.example 을 복사해 주세요.
        exit /b 1
    )
)

if exist "images\safepromptguard-v3-images.tar" (
    echo 이미지 tar 로드 중: images\safepromptguard-v3-images.tar
    docker load -i "images\safepromptguard-v3-images.tar"
    if errorlevel 1 exit /b 1
) else (
    echo 이미지 tar가 없어 로컬 Docker 이미지 캐시를 사용합니다.
)

echo 컨테이너 시작...
docker compose -f docker-compose.offline.yml --env-file .env.prod up -d
if errorlevel 1 exit /b 1

echo.
echo ========================================
echo  웹 UI:  http://localhost:8080
echo  API:    http://localhost:8001/api/health
echo ========================================
echo.
echo 종료: docker compose -f docker-compose.offline.yml --env-file .env.prod down
endlocal
