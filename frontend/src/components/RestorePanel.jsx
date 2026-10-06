import { useMemo, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { restorePlaceholders } from '../utils/restore'

export default function RestorePanel({ result, draft, onDraftChange }) {
  const entries = result.placeholders || []
  const [showOriginals, setShowOriginals] = useState(false)
  const restored = useMemo(() => restorePlaceholders(draft, entries), [draft, entries])

  if (!entries.length) {
    return (
      <p className="artifact-empty">
        이전 검사 기록에는 원래 값을 저장하지 않아 복원할 수 없습니다. 원문을 다시 검사하세요.
      </p>
    )
  }

  return (
    <div className="restore-panel">
      <p className="artifact-note">
        마스킹된 내용으로 외부 AI에 질문하고 받은 답변을 붙여 넣으면 [MASKED_PHONE_1] 같은 표시를 원래 값으로
        되돌립니다. 브라우저 안에서만 처리하며 원래 값은 서버나 검사 이력에 남지 않습니다.
      </p>
      <textarea
        className="restore-input"
        value={draft}
        onChange={(e) => onDraftChange(e.target.value)}
        placeholder="외부 AI 답변을 여기에 붙여 넣으세요"
        rows={6}
        spellCheck={false}
      />
      {draft.trim() && (
        <>
          <p className={`restore-count ${restored.count ? '' : 'restore-count--none'}`}>
            {restored.count
              ? `${restored.count}곳을 원래 값으로 되돌렸습니다.`
              : '답변에서 가림 표시를 찾지 못했습니다.'}
          </p>
          <pre className="artifact-code artifact-code--prose restore-output">{restored.text}</pre>
        </>
      )}
      <div className="restore-map-head">
        <span>가림 표시 {entries.length}개</span>
        <button type="button" className="msg-btn" onClick={() => setShowOriginals((v) => !v)}>
          {showOriginals ? <EyeOff size={14} /> : <Eye size={14} />}
          {showOriginals ? ' 원래 값 숨기기' : ' 원래 값 보기'}
        </button>
      </div>
      <table className="restore-map">
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.placeholder}>
              <td>
                <code>{entry.placeholder}</code>
              </td>
              <td>{entry.type}</td>
              <td className="restore-original">{showOriginals ? entry.original : '••••••'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function restoredText(result, draft) {
  return restorePlaceholders(draft, result?.placeholders || []).text
}
