export function downloadText(filename, content) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function buildCollabSummary(result) {
  const items = result.detected_items?.slice(0, 5).join(', ') || '민감정보'
  return `[보안 검사 완료]
위험도: ${result.risk_level} (${result.risk_score}/100)
탐지: ${result.findings?.length ?? 0}건 (${items})

아래는 마스킹된 내용입니다. 원문의 비밀번호·키·내부 식별자는 제거되었습니다.
---
${result.masked_text?.slice(0, 2000) || ''}`
}

export const GIT_CHECKLIST = `커밋 / PR 전 체크리스트
□ .env, credentials, API Key가 포함되지 않았는지 확인
□ 마스킹된 파일만 저장소에 반영
□ 실제 비밀번호·토큰은 비밀 관리 도구에만 보관
□ PR 설명에 민감한 내부 URL·고객명이 없는지 확인`

export const SHARE_CHECKLIST = `외부 공유 전 체크리스트
□ 마스킹본과 원본을 혼동하지 않기
□ 수신자·채널이 승인된 대상인지 확인
□ 불필요한 로그·설정 파일 전체는 보내지 않기`
