import { useState, useEffect, useRef } from 'react'
import {
  Shield,
  ScanSearch,
  Upload,
  Copy,
  AlertTriangle,
  CheckCircle2,
  FileWarning,
  Sparkles,
  ArrowRight,
  RotateCcw,
} from 'lucide-react'
import './App.css'
import { SAMPLES, DEFAULT_SAMPLE_ID } from './samples'

export default function App() {
  const [text, setText] = useState('')
  const [useGemma, setUseGemma] = useState(true)
  const [loading, setLoading] = useState(false)
  const [loadingStep, setLoadingStep] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [health, setHealth] = useState(null)
  const [toast, setToast] = useState(null)
  const [sampleId, setSampleId] = useState(DEFAULT_SAMPLE_ID)
  const fileRef = useRef(null)

  const loadSample = (id) => {
    const sample = SAMPLES.find((s) => s.id === id)
    if (sample) {
      setSampleId(id)
      setText(sample.text)
      setError(null)
    }
  }

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ gemma_available: false }))
  }, [])

  const copyText = async (content, label) => {
    await navigator.clipboard.writeText(content)
    setToast(`${label} 복사됨`)
    setTimeout(() => setToast(null), 2000)
  }

  const runScan = async (body, isFile = false) => {
    setLoading(true)
    setError(null)
    setResult(null)
    setLoadingStep('1차: 정규식 민감정보 탐지 중...')

    const steps = [
      '2차: 코드/로그 규칙 탐지 중...',
      '3차: Gemma 문맥 분석 중...',
      '마스킹 및 안전 프롬프트 생성 중...',
    ]
    let stepIdx = 0
    const timer = setInterval(() => {
      if (stepIdx < steps.length) {
        setLoadingStep(steps[stepIdx++])
      }
    }, 800)

    try {
      const url = isFile ? `/api/scan/file?use_gemma=${useGemma}` : '/api/scan'
      const options = isFile
        ? { method: 'POST', body }
        : {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, use_gemma: useGemma }),
          }

      const res = await fetch(url, options)
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || '검사 중 오류가 발생했습니다.')
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      clearInterval(timer)
      setLoading(false)
      setLoadingStep('')
    }
  }

  const handleScan = () => {
    if (!text.trim()) {
      setError('검사할 내용을 입력하거나 파일을 업로드해 주세요.')
      return
    }
    runScan()
  }

  const handleFile = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    runScan(fd, true)
    e.target.value = ''
  }

  const riskClass =
    result?.risk_level === '높음'
      ? 'high'
      : result?.risk_level === '중간'
        ? 'medium'
        : 'low'

  return (
    <div className="app">
      <div className="bg-grid" />
      <div className="bg-glow bg-glow--1" />
      <div className="bg-glow bg-glow--2" />

      <div className="container">
        <header className="header">
          <div className="header-badge">
            <Shield size={14} />
            SafePrompt Guard
          </div>
          <h1>외부 AI 입력 전 보안 검사기</h1>
          <p>
            ChatGPT, Gemini에 넣기 전에 코드·로그·문서의 유출 위험을 탐지하고,
            마스킹된 안전 프롬프트를 생성합니다.
          </p>
          <div className="status-bar">
            <div className="status-item">
              <span className={`status-dot ${health ? 'status-dot--on' : ''}`} />
              API 서버
            </div>
            <div className="status-item">
              <span
                className={`status-dot ${health?.gemma_available ? 'status-dot--on' : 'status-dot--off'}`}
              />
              Gemma (Ollama) {health?.gemma_available ? '연결됨' : '오프라인 — 규칙 기반만 동작'}
            </div>
          </div>
        </header>

        <div className="flow">
          <span className="flow-step">붙여넣기</span>
          <ArrowRight size={14} className="flow-arrow" />
          <span className="flow-step">3단계 탐지</span>
          <ArrowRight size={14} className="flow-arrow" />
          <span className="flow-step">자동 마스킹</span>
          <ArrowRight size={14} className="flow-arrow" />
          <span className="flow-step">안전 프롬프트</span>
          <ArrowRight size={14} className="flow-arrow" />
          <span className="flow-step">외부 AI에 복사</span>
        </div>

        {!result && (
          <section className="panel">
            <label className="panel-label">
              외부 AI에 입력하려는 내용
              <span>코드 · 로그 · 설정 · 문서</span>
            </label>
            <textarea
              className="input-area"
              placeholder="여기에 붙여넣으세요. 비밀번호, API Key, DB URL, 내부 도메인 등이 포함될 수 있습니다."
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={loading}
            />
            <div className="actions">
              <button className="btn btn-primary" onClick={handleScan} disabled={loading}>
                <ScanSearch size={18} />
                유출 위험 검사하기
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => fileRef.current?.click()}
                disabled={loading}
              >
                <Upload size={18} />
                파일 업로드
              </button>
              <input
                ref={fileRef}
                type="file"
                className="file-input"
                accept=".txt,.log,.env,.py,.java,.js,.ts,.json,.yml,.yaml,.properties,.md"
                onChange={handleFile}
              />
              <select
                className="sample-select"
                value={sampleId}
                onChange={(e) => loadSample(e.target.value)}
                disabled={loading}
              >
                {SAMPLES.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
              <button
                className="btn btn-secondary"
                onClick={() => loadSample(sampleId)}
                disabled={loading}
              >
                예시 불러오기
              </button>
            </div>
            <p className="sample-hint">
              {SAMPLES.find((s) => s.id === sampleId)?.description}
            </p>
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={useGemma}
                onChange={(e) => setUseGemma(e.target.checked)}
              />
              Gemma 문맥 분석 사용 (Ollama 필요)
            </label>
          </section>
        )}

        {error && <div className="error-box">{error}</div>}

        {loading && (
          <div className="loading panel">
            <div className="spinner" />
            <p>보안 검사 진행 중...</p>
            <p className="loading-steps">{loadingStep}</p>
          </div>
        )}

        {result && !loading && (
          <div className="results">
            <div className={`risk-banner risk-banner--${riskClass}`}>
              <div className="risk-icon">
                {riskClass === 'high' ? (
                  <AlertTriangle size={28} />
                ) : riskClass === 'medium' ? (
                  <FileWarning size={28} />
                ) : (
                  <CheckCircle2 size={28} />
                )}
              </div>
              <div>
                <div className="risk-label">유출 위험도</div>
                <div className="risk-value">{result.risk_level}</div>
              </div>
              <div className="risk-score">
                <div className="risk-score-num">{result.risk_score}</div>
                <div className="risk-score-label">위험 점수 / 100</div>
              </div>
            </div>

            <div className="grid-2">
              <section className="panel">
                <h3 className="card-title">
                  <AlertTriangle size={18} />
                  탐지 항목 ({result.findings.length}건)
                </h3>
                <ul className="finding-list">
                  {result.findings.map((f, i) => (
                    <li key={i} className="finding-item">
                      <span className="finding-num">{i + 1}</span>
                      <div className="finding-body">
                        <strong>
                          {f.type}
                          <span className={`severity severity--${f.severity}`}>
                            {f.severity}
                          </span>
                          <span className="source-tag">{f.source}</span>
                        </strong>
                        <div className="finding-meta">
                          {f.line && <span>줄 {f.line}</span>}
                          {typeof f.confidence === 'number' && (
                            <span>신뢰도 {Math.round(f.confidence * 100)}%</span>
                          )}
                        </div>
                        <span>{f.reason || f.value}</span>
                        {f.exact_quote && <code className="finding-quote">{f.exact_quote}</code>}
                        {f.action && <span className="finding-action">{f.action}</span>}
                      </div>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="panel">
                <h3 className="card-title">
                  <Shield size={18} />
                  권장 조치
                </h3>
                <ul className="rec-list">
                  {result.recommendations.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
                {result.detected_items?.length > 0 && (
                  <>
                    <h3 className="card-title" style={{ marginTop: '1.25rem' }}>
                      요약
                    </h3>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      {result.detected_items.join(' · ')}
                    </p>
                  </>
                )}
              </section>
            </div>

            <section className="panel" style={{ marginTop: '1.5rem' }}>
              <div className="output-header">
                <h3 className="card-title" style={{ marginBottom: 0 }}>
                  마스킹된 내용
                </h3>
                <button
                  className="btn btn-ghost"
                  onClick={() => copyText(result.masked_text, '마스킹 내용')}
                >
                  <Copy size={14} /> 복사
                </button>
              </div>
              <pre className="code-block">{result.masked_text}</pre>
            </section>

            <section className="panel" style={{ marginTop: '1.5rem' }}>
              <div className="output-header">
                <h3 className="card-title" style={{ marginBottom: 0 }}>
                  <Sparkles size={18} style={{ color: 'var(--accent)' }} />
                  안전 프롬프트 — 외부 AI에 붙여넣기
                </h3>
                <button
                  className="btn btn-primary"
                  onClick={() => copyText(result.safe_prompt, '안전 프롬프트')}
                >
                  <Copy size={16} /> 복사해서 ChatGPT/Gemini에 입력
                </button>
              </div>
              <pre className="code-block" style={{ color: 'var(--text)' }}>
                {result.safe_prompt}
              </pre>
              {!result.gemma_used && (
                <p style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Gemma 미연결 — 규칙 기반 템플릿으로 생성됨. Ollama 실행 시 더 자연스러운 프롬프트 생성.
                </p>
              )}
            </section>

            <div className="actions" style={{ marginTop: '1.5rem' }}>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setResult(null)
                  setError(null)
                }}
              >
                <RotateCcw size={18} />
                새로 검사하기
              </button>
            </div>
          </div>
        )}

        <footer className="footer">
          SafePrompt Guard · 정규식 + 규칙 + Gemma 3단계 탐지 · 팀 프로젝트 MVP
        </footer>
      </div>

      {toast && <div className="copy-toast">{toast}</div>}
    </div>
  )
}
