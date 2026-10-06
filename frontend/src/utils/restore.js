function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// backend/services/masking.py의 restore_placeholders와 같은 규칙이다.
// [MASKED_PHONE_1]은 그대로, 대괄호를 뺀 MASKED_PHONE_1은 영숫자 경계로 찾는다(뒤에 붙은 한글 조사는 허용).
export function restorePlaceholders(text, entries = []) {
  const mapping = new Map()
  for (const entry of entries) {
    if (entry?.placeholder && entry.original !== undefined) {
      mapping.set(entry.placeholder.slice(1, -1), entry.original)
    }
  }
  if (!text || mapping.size === 0) return { text: text || '', count: 0 }

  const names = [...mapping.keys()]
    .sort((a, b) => b.length - a.length)
    .map(escapeRegExp)
    .join('|')
  const pattern = new RegExp(`\\[(${names})\\]|(?<![A-Za-z0-9_])(${names})(?![A-Za-z0-9_])`, 'g')
  let count = 0
  const restored = text.replace(pattern, (_match, bracketed, bare) => {
    count += 1
    return mapping.get(bracketed || bare)
  })
  return { text: restored, count }
}

// 검사 이력은 localStorage에 남는다. 원문과 찾아낸 원래 값은 빼고 마스킹된 내용만 저장한다.
export function redactResultForStorage(result) {
  if (!result) return result
  return {
    ...result,
    findings: (result.findings || []).map(redactFinding),
    placeholders: [],
    placeholders_dropped: (result.placeholders || []).length || result.placeholders_dropped || 0,
  }
}

export function redactFinding(finding) {
  const hidden = finding.masked_value || `[${finding.type}]`
  return { ...finding, value: hidden, exact_quote: finding.exact_quote ? hidden : finding.exact_quote }
}
