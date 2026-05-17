import { X, Copy, Download, PanelRightOpen } from 'lucide-react'
import { downloadText } from '../utils/export'
import { ARTIFACT_TABS } from '../hooks/useArtifactPanel'
import FindingAccordion from './FindingAccordion'
import ContextActions from './ContextActions'

export default function ArtifactPanel({
  open,
  tab,
  onTabChange,
  onClose,
  result,
  contextId,
  expandedFindingIndices,
  onToggleFinding,
  onCopy,
}) {
  if (!open || !result) return null

  const masked = result.masked_text || ''
  const prompt = result.safe_prompt || ''

  return (
    <aside className="artifact-panel" aria-label="검사 결과 상세">
      <header className="artifact-header">
        <div className="artifact-header-title">
          <PanelRightOpen size={18} />
          <span>검사 결과</span>
          <span className={`artifact-risk artifact-risk--${result.risk_level}`}>
            {result.risk_level}
          </span>
        </div>
        <button type="button" className="icon-btn" onClick={onClose} title="패널 닫기">
          <X size={18} />
        </button>
      </header>

      <nav className="artifact-tabs">
        {ARTIFACT_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`artifact-tab ${tab === t.id ? 'artifact-tab--active' : ''}`}
            onClick={() => onTabChange(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div className="artifact-body">
        {tab === 'masked' && (
          <pre className="artifact-code">{masked || '(내용 없음)'}</pre>
        )}
        {tab === 'prompt' && (
          <>
            {!result.gemma_used && (
              <p className="artifact-note">Gemma 미연결 — 규칙 기반 템플릿으로 생성됨</p>
            )}
            <pre className="artifact-code artifact-code--prose">{prompt || '(내용 없음)'}</pre>
          </>
        )}
        {tab === 'findings' && (
          <FindingAccordion
            findings={result.findings}
            expandedIndices={expandedFindingIndices}
            onToggle={onToggleFinding}
          />
        )}
      </div>

      <footer className="artifact-footer">
        <ContextActions
          contextId={contextId}
          result={result}
          activeTab={tab}
          onCopy={onCopy}
        />
        {tab === 'masked' && (
          <button
            type="button"
            className="msg-btn"
            onClick={() => onCopy(masked, '마스킹 내용')}
          >
            <Copy size={14} /> 복사
          </button>
        )}
        {tab === 'prompt' && (
          <button
            type="button"
            className="msg-btn msg-btn--primary"
            onClick={() => onCopy(prompt, '안전 프롬프트')}
          >
            <Copy size={14} /> 복사
          </button>
        )}
        {tab === 'masked' && (
          <button
            type="button"
            className="msg-btn"
            onClick={() => downloadText('masked_output.txt', masked)}
          >
            <Download size={14} /> 저장
          </button>
        )}
      </footer>
    </aside>
  )
}
