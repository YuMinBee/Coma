import { Copy, PanelRightOpen } from 'lucide-react'
import FindingAccordion from './FindingAccordion'

const PREVIEW_LEN = 1200

export default function ChatBubble({
  message: m,
  onOpenPanel,
  onCopy,
  expandedFindingIndices = [],
  onToggleFinding,
}) {
  const isUser = m.role === 'user'

  if (m.type === 'loading') {
    return (
      <div className="chat-message">
        <div className="avatar">AI</div>
        <div className="bubble">
          <strong>{m.title}</strong>
          <p>{m.step || '\uBD84\uC11D \uC911\u2026'}</p>
          <div className="typing-dots">
            <span />
            <span />
            <span />
          </div>
        </div>
      </div>
    )
  }

  if (m.type === 'risk') {
    return (
      <div className={`chat-message risk-${m.riskClass}`}>
        <div className="avatar">AI</div>
        <div className="bubble">
          <strong>{m.title}</strong>
          <p className={`risk-score-line ${m.riskClass}`}>
            {m.riskLevel} {'\u00B7'} {m.riskScore}/100
          </p>
          {m.recommendations?.map((r, i) => (
            <p key={i} className="rec-line">
              {'\u2192'} {r}
            </p>
          ))}
          <div className="message-tags">
            {m.tags?.map((t) => (
              <span key={t}>{t}</span>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (m.type === 'findings') {
    return (
      <div className="chat-message">
        <div className="avatar">AI</div>
        <div className="bubble bubble--wide">
          <strong>
            {m.title} ({m.total}{'\uAC74'})
          </strong>
          <p className="cta-hint">
            {'\uC544\uB798 \uD56D\uBAA9\uC744 \uB20C\uB7EC \uD3BC\uCE58\uBA74 \uC0AC\uC720\u00B7\uC778\uC6A9\u00B7\uAD8C\uC7A5 \uC870\uCE58\uB97C \uD655\uC778\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4. \uC5EC\uB7EC \uD56D\uBAA9\uC744 \uB3D9\uC2DC\uC5D0 \uD3BC\uCE60 \uC218 \uC788\uC2B5\uB2C8\uB2E4.'}
          </p>
          <FindingAccordion
            findings={m.findings}
            expandedIndices={expandedFindingIndices}
            onToggle={onToggleFinding}
          />
          <button
            type="button"
            className="panel-open-btn"
            onClick={() => onOpenPanel?.('findings')}
          >
            <PanelRightOpen size={14} /> {'\uC624\uB978\uCABD \uD328\uB110\uC5D0\uC11C \uBCF4\uAE30'}
          </button>
        </div>
      </div>
    )
  }

  if (m.type === 'masked' || m.type === 'prompt') {
    return (
      <div className="chat-message">
        <div className="avatar">AI</div>
        <div className="bubble bubble--wide">
          <strong>{m.title}</strong>
          {m.note && <p className="artifact-note">{m.note}</p>}
          <pre className="code-output">{m.body}</pre>
          <div className="message-actions">
            <button
              type="button"
              className="msg-btn msg-btn--primary"
              onClick={() =>
                onCopy?.(
                  m.body,
                  m.type === 'masked' ? '\uB9C8\uC2A4\uD0B9 \uB0B4\uC6A9' : '\uC548\uC804 \uD504\uB86C\uD504\uD2B8',
                )
              }
            >
              <Copy size={12} /> {'\uBCF5\uC0AC'}
            </button>
            <button
              type="button"
              className="panel-open-btn panel-open-btn--inline"
              onClick={() => onOpenPanel?.(m.type === 'masked' ? 'masked' : 'prompt')}
            >
              <PanelRightOpen size={14} /> {'\uD328\uB110\uC5D0\uC11C \uBCF4\uAE30'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (m.type === 'error') {
    return (
      <div className="chat-message risk-high">
        <div className="avatar">!</div>
        <div className="bubble">
          <strong>{m.title}</strong>
          <p>{m.body}</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`chat-message ${isUser ? 'user' : ''}`}>
      <div className="avatar">{isUser ? '\uB098' : 'AI'}</div>
      <div className="bubble">
        <strong>{m.title}</strong>
        {m.preview && (
          <pre className="user-preview">
            {m.preview.length > PREVIEW_LEN
              ? `${m.preview.slice(0, PREVIEW_LEN)}\n\u2026`
              : m.preview}
          </pre>
        )}
        {m.tags?.length > 0 && (
          <div className="message-tags">
            {m.tags.map((t) => (
              <span key={t}>{t}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
