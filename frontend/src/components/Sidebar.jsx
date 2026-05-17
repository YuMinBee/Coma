import { Plus } from 'lucide-react'
import { IMPORT_CONTEXTS } from '../constants'

function formatTime(ts) {
  const d = new Date(ts)
  const today = new Date()
  if (d.toDateString() === today.toDateString()) {
    return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
}

function riskDot(level) {
  if (level === '높음') return 'high'
  if (level === '중간') return 'medium'
  return 'low'
}

export default function Sidebar({
  sessions,
  activeId,
  onSelect,
  onNewScan,
  contextLabel,
}) {
  const icon = (id) => IMPORT_CONTEXTS.find((c) => c.id === id)?.icon || '·'

  return (
    <aside className="session-sidebar">
      <div className="sidebar-head">
        <h2>검사 이력</h2>
        <button type="button" className="sidebar-new" onClick={onNewScan} title="새 검사">
          <Plus size={16} />
        </button>
      </div>
      <ul className="session-list">
        {sessions.map((s) => {
          const active = s.id === activeId
          const level = s.lastResult?.risk_level
          return (
            <li key={s.id}>
              <button
                type="button"
                className={`session-item ${active ? 'session-item--active' : ''}`}
                onClick={() => onSelect(s.id)}
              >
                <span className="session-item-top">
                  <span className="session-ctx">{icon(s.contextId)}</span>
                  <span className="session-title">{s.title}</span>
                </span>
                <span className="session-item-meta">
                  <span>{contextLabel(s.contextId)}</span>
                  <span>{formatTime(s.createdAt)}</span>
                  {level && (
                    <span className={`session-risk session-risk--${riskDot(level)}`}>
                      {level}
                    </span>
                  )}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </aside>
  )
}
