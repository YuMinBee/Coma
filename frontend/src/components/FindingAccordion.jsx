import { ChevronDown } from 'lucide-react'

function severityKo(s) {
  if (s === 'HIGH') return '높음'
  if (s === 'MEDIUM') return '중간'
  return '낮음'
}

function sourceKo(s) {
  if (s === 'regex') return '정규식'
  if (s === 'rule') return '규칙'
  if (s === 'gemma') return 'Gemma'
  return s
}

export default function FindingAccordion({
  findings = [],
  expandedIndices = [],
  onToggle,
}) {
  const expandedSet = new Set(expandedIndices)

  if (!findings.length) {
    return <p className="artifact-empty">탐지된 항목이 없습니다.</p>
  }

  return (
    <ul className="finding-accordion">
      {findings.map((f, i) => {
        const open = expandedSet.has(i)
        return (
          <li key={`${f.source}-${f.type}-${f.line}-${i}`} className={open ? 'is-open' : ''}>
            <button type="button" className="finding-accordion-head" onClick={() => onToggle?.(i)}>
              <span className="finding-accordion-num">{i + 1}</span>
              <div className="finding-accordion-main">
                <span className="finding-accordion-title">
                  {f.type}
                  <span className={`severity-pill severity-pill--${f.severity}`}>
                    {severityKo(f.severity)}
                  </span>
                  <span className="source-pill">{sourceKo(f.source)}</span>
                </span>
                <span className="finding-accordion-meta">
                  {f.line ? `\uC904 ${f.line}` : ''}
                  {typeof f.confidence === 'number'
                    ? ` \u00B7 \uC2E0\uB8B0\uB3C4 ${Math.round(f.confidence * 100)}%`
                    : ''}
                </span>
              </div>
              <ChevronDown size={16} className="finding-chevron" />
            </button>
            {open && (
              <div className="finding-accordion-body">
                {f.reason && (
                  <p className="finding-reason-line">
                    <strong>{'\uC0AC\uC720'}</strong> {f.reason}
                  </p>
                )}
                {f.exact_quote && (
                  <pre className="finding-quote-block">{f.exact_quote}</pre>
                )}
                {f.action && (
                  <p className="finding-action-line">
                    <strong>{'\uAD8C\uC7A5 \uC870\uCE58'}</strong> {f.action}
                  </p>
                )}
              </div>
            )}
          </li>
        )
      })}
    </ul>
  )
}
