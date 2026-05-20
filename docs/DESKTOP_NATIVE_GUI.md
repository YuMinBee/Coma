# SafePrompt Guard — Native GUI Prototype

브라우저나 Electron 없이 실행파일로 패키징할 수 있는 Python GUI 프로토타입입니다.  
기존 웹 UI의 구조와 색감을 참고하되, 화면은 Tkinter 네이티브 창으로 구성했습니다.

## 방향

- 로컬 PC에서 실행되는 GUI 앱
- 기존 백엔드 스캐너 코드를 직접 호출
- 로컬 Ollama의 `gemma2:2b` 모델 상태 표시
- 파일 열기, 텍스트 검사, 마스킹 결과 복사, 안전 프롬프트 복사
- `.ipynb` 검사 시 마스킹 노트북 저장 지원

## 개발 실행

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cd ..
python desktop_native/safeprompt_gui.py
```

Windows:

```bat
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

cd ..
python desktop_native\safeprompt_gui.py
```

## 로컬 Gemma 준비

```bash
ollama pull gemma2:2b
ollama serve
```

GUI는 기본적으로 `http://localhost:11434`의 Ollama를 확인합니다.

## 실행파일 빌드

Linux/macOS:

```bash
./scripts/build-gui-exe.sh
```

Windows:

```bat
scripts\build-gui-exe.bat
```

결과물은 `dist/SafePromptGuard` 또는 `dist\SafePromptGuard.exe`에 생성됩니다.
