import fileUploadPolicy from '../../shared/allowed_extensions.json'

/** 업로드 허용 확장자 — shared/allowed_extensions.json 과 동기화 */
export const ALLOWED_FILE_EXTENSIONS = fileUploadPolicy.extensions
export const ACCEPT_FILE_TYPES = fileUploadPolicy.extensions.join(',')
export const NOTEBOOK_EXTENSIONS = new Set(fileUploadPolicy.notebook_extensions || ['.ipynb'])

/** 외부 공유 시나리오 — UI 라벨 (검사 로직은 동일) */
export const IMPORT_CONTEXTS = [
  {
    id: 'ai',
    label: '외부 AI 공유',
    hint: 'ChatGPT, Gemini, Copilot 등에 붙여넣기 전',
    icon: '🤖',
  },
  {
    id: 'git',
    label: 'Git / 저장소',
    hint: 'push, PR, public repo 업로드 전',
    icon: '⎇',
  },
  {
    id: 'share',
    label: '파일·문서 공유',
    hint: '이메일, 드라이브, USB 등 외부 전달 전',
    icon: '📁',
  },
  {
    id: 'collab',
    label: '협업·메신저',
    hint: 'Slack, Teams, Discord 등 채널 공유 전',
    icon: '💬',
  },
  {
    id: 'other',
    label: '기타 외부 공유',
    hint: '외부 업체·클라우드·API 연동 전',
    icon: '↗',
  },
]

export const MAX_FOLDER_FILES = 25
export const MAX_FILE_BYTES = 1 * 1024 * 1024
