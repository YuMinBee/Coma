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
  const tabs = ARTIFACT_TABS.filter((t) => t.id !== 'prompt' || prompt.trim())
  const activeTab = prompt.trim() || tab !== 'prompt' ? tab : 'masked'

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
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`artifact-tab ${activeTab === t.id ? 'artifact-tab--active' : ''}`}
            onClick={() => onTabChange(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div className="artifact-body">
        {activeTab === 'masked' && (
          <>
            {result.source_kind === 'notebook' && (
              <p className="artifact-note">
                입력 셀(source)을 검사·마스킹하고 다운로드 파일에서는 outputs·metadata를 제거합니다.
              </p>
            )}
            <pre className="artifact-code">{masked || '(내용 없음)'}</pre>
          </>
        )}
        {activeTab === 'prompt' && (
          <>
            {!result.gemma_used && (
              <p className="artifact-note">Gemma 미연결 — 규칙 기반 템플릿으로 생성됨</p>
            )}
            <pre className="artifact-code artifact-code--prose">{prompt || '(내용 없음)'}</pre>
          </>
        )}
        {activeTab === 'findings' && (
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
        {activeTab === 'masked' && (
          <button
            type="button"
            className="msg-btn"
            onClick={() => onCopy(masked, '마스킹 내용')}
          >
            <Copy size={14} /> 복사
          </button>
        )}
        {activeTab === 'prompt' && (
          <button
            type="button"
            className="msg-btn msg-btn--primary"
            onClick={() => onCopy(prompt, '안전 프롬프트')}
          >
            <Copy size={14} /> 복사
          </button>
        )}
        {activeTab === 'masked' && (
          <button
            type="button"
            className="msg-btn"
            onClick={() => downloadText('masked_output.txt', masked)}
          >
            <Download size={14} /> 저장
          </button>
        )}
        {activeTab === 'masked' && result.masked_notebook_json && (
          <button
            type="button"
            className="msg-btn msg-btn--primary"
            onClick={() => downloadText('masked_notebook.ipynb', result.masked_notebook_json)}
          >
            <Download size={14} /> 마스킹 노트북 (.ipynb)
          </button>
        )}
      </footer>
    </aside>
  )
}
