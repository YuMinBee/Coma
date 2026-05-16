import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Shield,
  ScanSearch,
  Upload,
  Copy,
  FolderOpen,
  Sun,
  Moon,
  RotateCcw,
} from 'lucide-react'
import './App.css'
import { SAMPLES, DEFAULT_SAMPLE_ID } from './samples'
import { useTheme } from './hooks/useTheme'
import { IMPORT_CONTEXTS, MAX_FOLDER_FILES, MAX_FILE_BYTES } from './constants'

let msgId = 0
const nextId = () => `m-${++msgId}`

function riskClass(level) {
  if (level === '높음') return 'high'
  if (level === '중간') return 'medium'
  return 'low'
}

async function readFileText(file) {
  const buf = await file.arrayBuffer()
  try {
    return new TextDecoder('utf-8').decode(buf)
  } catch {
    return new TextDecoder('utf-8', { fatal: false }).decode(buf)
  }
}

async function mergeFiles(files) {
  const slice = files.slice(0, MAX_FOLDER_FILES)
  const parts = []
  for (const file of slice) {
    if (file.size > MAX_FILE_BYTES) continue
    const path = file.webkitRelativePath || file.name
    const text = await readFileText(file)
    parts.push(`--- ${path} ---\n${text}`)
  }
  return parts.join('\n\n')
}

export default function App() {
  const { theme, toggle, isDark } = useTheme()
  const [text, setText] = useState('')
  const [useGemma, setUseGemma] = useState(true)
  const [loading, setLoading] = useState(false)
  const [loadingStep, setLoadingStep] = useState('')
  const [messages, setMessages] = useState([])
  const [lastResult, setLastResult] = useState(null)
  const [error, setError] = useState(null)
  const [health, setHealth] = useState(null)
  const [toast, setToast] = useState(null)
  const [sampleId, setSampleId] = useState(DEFAULT_SAMPLE_ID)
  const [importContext, setImportContext] = useState('ai')
  const [dragActive, setDragActive] = useState(false)

  const fileRef = useRef(null)
  const folderRef = useRef(null)
  const streamRef = useRef(null)

  const activeContext = IMPORT_CONTEXTS.find((c) => c.id === importContext) || IMPORT_CONTEXTS[0]

  const scrollBottom = useCallback(() => {
    requestAnimationFrame(() => {
      if (streamRef.current) {
        streamRef.current.scrollTop = streamRef.current.scrollHeight
      }
    })
  }, [])

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ gemma_available: false }))
  }, [])

  useEffect(() => {
    scrollBottom()
  }, [messages, loading, scrollBottom])

  const copyText = async (content, label) => {
    await navigator.clipboard.writeText(content)
    setToast(`${label} 복사됨`)
    setTimeout(() => setToast(null), 2000)
  }

  const addMessage = (msg) => {
    setMessages((prev) => [...prev, { id: nextId(), ...msg }])
  }

  const runScanWithContent = async (content, label = '붙여넣기', filename = null) => {
    if (!content.trim()) {
      setError('검사할 내용이 없습니다.')
      return
    }

    setLoading(true)
    setError(null)
    setLastResult(null)
    setLoadingStep('1차: 정규식 민감정보 탐지 중...')

    addMessage({
      role: 'user',
      title: label,
      preview: content.slice(0, 1200) + (content.length > 1200 ? '\n…' : ''),
      tags: [activeContext.label, filename || '텍스트'].filter(Boolean),
    })

    const agentId = nextId()
    setMessages((prev) => [
      ...prev,
      { id: agentId, role: 'assistant', type: 'loading', title: '보안 에이전트', step: loadingStep },
    ])

    const steps = [
      '2차: 코드/로그 규칙 탐지 중...',
      '3차: Gemma 문맥 분석 중...',
      '마스킹 및 안전 프롬프트 생성 중...',
    ]
    let stepIdx = 0
    const timer = setInterval(() => {
      if (stepIdx < steps.length) {
        const step = steps[stepIdx++]
        setLoadingStep(step)
        setMessages((prev) =>
          prev.map((m) => (m.id === agentId ? { ...m, step } : m)),
        )
      }
    }, 900)

    try {
      const res = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: content, use_gemma: useGemma }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || '검사 중 오류가 발생했습니다.')

      setLastResult(data)
      setText('')

      setMessages((prev) => prev.filter((m) => m.id !== agentId))

      const rc = riskClass(data.risk_level)
      addMessage({
        role: 'assistant',
        type: 'risk',
        riskClass: rc,
        title: '유출 위험도 분석 완료',
        riskLevel: data.risk_level,
        riskScore: data.risk_score,
        tags: [
          `위험 ${data.risk_level}`,
          `${data.findings.length}건 탐지`,
          data.gemma_used ? 'Gemma 적용' : '규칙 기반',
        ],
        recommendations: data.recommendations,
      })

      if (data.findings.length > 0) {
        addMessage({
          role: 'assistant',
          type: 'findings',
          title: '탐지 항목',
          findings: data.findings.slice(0, 12),
          total: data.findings.length,
        })
      }

      addMessage({
        role: 'assistant',
        type: 'masked',
        title: '마스킹된 내용',
        body: data.masked_text,
        onCopy: () => copyText(data.masked_text, '마스킹 내용'),
      })

      addMessage({
        role: 'assistant',
        type: 'prompt',
        title:
          importContext === 'ai'
            ? '안전 프롬프트 (외부 AI용)'
            : '외부 반입용 안전 텍스트',
        body: data.safe_prompt,
        note: !data.gemma_used
          ? 'Gemma 미연결 — 규칙 기반 템플릿으로 생성됨'
          : null,
        onCopy: () => copyText(data.safe_prompt, '안전 텍스트'),
      })
    } catch (e) {
      setError(e.message)
      setMessages((prev) =>
        prev.map((m) =>
          m.id === agentId
            ? { ...m, type: 'error', title: '검사 실패', body: e.message }
            : m,
        ),
      )
    } finally {
      clearInterval(timer)
      setLoading(false)
      setLoadingStep('')
    }
  }

  const runScanFile = async (file) => {
    const fd = new FormData()
    fd.append('file', file)
    setLoading(true)
    setError(null)
    addMessage({
      role: 'user',
      title: '파일 업로드',
      preview: file.name,
      tags: [activeContext.label, file.name],
    })
    try {
      const res = await fetch(`/api/scan/file?use_gemma=${useGemma}`, {
        method: 'POST',
        body: fd,
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || '파일 검사 실패')
      setLastResult(data)
      const rc = riskClass(data.risk_level)
      addMessage({
        role: 'assistant',
        type: 'risk',
        riskClass: rc,
        title: '파일 검사 완료',
        riskLevel: data.risk_level,
        riskScore: data.risk_score,
        tags: [file.name, `위험 ${data.risk_level}`],
        recommendations: data.recommendations,
      })
      addMessage({
        role: 'assistant',
        type: 'masked',
        title: '마스킹된 내용',
        body: data.masked_text,
        onCopy: () => copyText(data.masked_text, '마스킹'),
      })
      addMessage({
        role: 'assistant',
        type: 'prompt',
        title: '외부 반입용 안전 텍스트',
        body: data.safe_prompt,
        onCopy: () => copyText(data.safe_prompt, '안전 텍스트'),
      })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleScan = () => {
    if (!text.trim()) {
      setError('내용을 입력하거나 파일을 올려 주세요.')
      return
    }
    setError(null)
    runScanWithContent(text, activeContext.label)
  }

  const handleFile = (e) => {
    const file = e.target.files?.[0]
    if (file) runScanFile(file)
    e.target.value = ''
  }

  const handleFolder = async (e) => {
    const files = Array.from(e.target.files || [])
    e.target.value = ''
    if (!files.length) return
    const merged = await mergeFiles(files)
    if (!merged.trim()) {
      setError('폴더에서 읽을 수 있는 텍스트가 없습니다.')
      return
    }
    runScanWithContent(merged, '폴더 검사', `${files.length}개 파일`)
  }

  const handleDrop = async (e) => {
    e.preventDefault()
    setDragActive(false)
    const items = e.dataTransfer?.items
    const files = []
    if (items) {
      for (const item of items) {
        if (item.kind === 'file') {
          const entry = item.webkitGetAsEntry?.()
          if (entry?.isDirectory) {
            await walkEntry(entry, '', files)
          } else {
            const f = item.getAsFile()
            if (f) files.push(f)
          }
        }
      }
    } else {
      files.push(...Array.from(e.dataTransfer.files || []))
    }
    if (files.length === 0) return
    if (files.length === 1 && !files[0].webkitRelativePath) {
      return runScanFile(files[0])
    }
    const merged = await mergeFiles(files)
    runScanWithContent(merged, '드래그 입력', `${files.length}개 파일`)
  }

  const walkEntry = (entry, path, out) =>
    new Promise((resolve) => {
      if (entry.isFile) {
        entry.file((file) => {
          Object.defineProperty(file, 'webkitRelativePath', {
            value: path + file.name,
            configurable: true,
          })
          out.push(file)
          resolve()
        })
      } else if (entry.isDirectory) {
        const reader = entry.createReader()
        reader.readEntries(async (entries) => {
          for (const ent of entries) {
            await walkEntry(ent, path + entry.name + '/', out)
          }
          resolve()
        })
      } else resolve()
    })

  const loadSample = (id) => {
    const sample = SAMPLES.find((s) => s.id === id)
    if (!sample) return
    setSampleId(id)
    setError(null)
    runScanWithContent(sample.text, sample.label)
  }

  const resetChat = () => {
    setMessages([])
    setLastResult(null)
    setError(null)
    setText('')
  }

  const healthLabel = health
    ? health.gemma_available
      ? 'Gemma 연결됨 · API 정상'
      : 'API 정상 · Gemma 오프라인'
    : '연결 확인 중…'

  return (
    <div className="app-shell">
      <div className="bg-grid" />
      <div className="bg-glow bg-glow--1" />
      <div className="bg-glow bg-glow--2" />

      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Shield size={18} />
          </div>
          <div>
            <h1>SafePrompt Guard</h1>
            <p>외부 반입 전 보안 검사 에이전트</p>
          </div>
        </div>
        <div className="topbar-actions">
          <span className={`status-pill ${health?.gemma_available ? '' : 'status-pill--warn'}`}>
            {healthLabel}
          </span>
          <button type="button" className="icon-btn" onClick={toggle} title="테마 전환">
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          {messages.length > 0 && (
            <button type="button" className="icon-btn" onClick={resetChat} title="대화 초기화">
              <RotateCcw size={16} />
            </button>
          )}
        </div>
      </header>

      <div className="context-bar">
        {IMPORT_CONTEXTS.map((ctx) => (
          <button
            key={ctx.id}
            type="button"
            className={`context-chip ${importContext === ctx.id ? 'context-chip--active' : ''}`}
            onClick={() => setImportContext(ctx.id)}
          >
            <span>{ctx.icon}</span>
            {ctx.label}
          </button>
        ))}
      </div>
      <p className="context-hint">{activeContext.hint}</p>

      <main
        className={`chat-app ${dragActive ? 'drag-active' : ''}`}
        onDragEnter={(e) => {
          e.preventDefault()
          setDragActive(true)
        }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget)) setDragActive(false)
        }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <div className="chat-stream" ref={streamRef}>
          {messages.length === 0 && (
            <div className="welcome-card">
              <h2>외부로 나가기 전, 여기서 먼저 검사하세요</h2>
              <p>
                AI 질문, Git push, 파일 공유, 협업 도구 전송 등{' '}
                <strong>외부 반입·유출</strong>이 일어나기 전에 민감정보를 탐지하고
                마스킹합니다.
              </p>
              <ul className="welcome-list">
                <li>3단계 탐지: 정규식 → 규칙 → Gemma 문맥 분석</li>
                <li>파일·폴더 드래그 또는 붙여넣기 지원</li>
                <li>마스킹 결과 + 외부 공유용 안전 텍스트 생성</li>
              </ul>
            </div>
          )}

          {messages.map((m) => (
            <ChatBubble key={m.id} message={m} onCopy={copyText} />
          ))}

          {error && (
            <div className="chat-message">
              <div className="avatar">!</div>
              <div className="bubble" style={{ borderColor: 'var(--danger)' }}>
                <strong>오류</strong>
                <p>{error}</p>
              </div>
            </div>
          )}
        </div>

        <section className="composer">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={loading}
            placeholder="코드, 로그, 설정, 문서를 붙여넣거나 파일·폴더를 드래그하세요. 외부 AI / Git / 공유 전에 검사합니다."
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleScan()
            }}
          />
          <div className="composer-actions">
            <div className="left-actions">
              <label className="tool-btn">
                <Upload size={14} />
                파일
                <input
                  ref={fileRef}
                  type="file"
                  accept=".txt,.log,.env,.py,.java,.js,.ts,.json,.yml,.yaml,.properties,.md"
                  onChange={handleFile}
                />
              </label>
              <label className="tool-btn">
                <FolderOpen size={14} />
                폴더
                <input
                  ref={folderRef}
                  type="file"
                  webkitdirectory=""
                  directory=""
                  multiple
                  onChange={handleFolder}
                />
              </label>
              <select
                className="sample-select"
                value={sampleId}
                onChange={(e) => {
                  setSampleId(e.target.value)
                  loadSample(e.target.value)
                }}
                disabled={loading}
              >
                {SAMPLES.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
              <label className="toggle-pill">
                <input
                  type="checkbox"
                  checked={useGemma}
                  onChange={(e) => setUseGemma(e.target.checked)}
                />
                Gemma
              </label>
            </div>
            <button type="button" className="scan-btn" onClick={handleScan} disabled={loading}>
              <ScanSearch size={16} />
              {loading ? '검사 중…' : '검사 실행'}
            </button>
          </div>
        </section>
      </main>

      {toast && <div className="copy-toast">{toast}</div>}
    </div>
  )
}

function ChatBubble({ message: m }) {
  const isUser = m.role === 'user'

  if (m.type === 'loading') {
    return (
      <div className="chat-message">
        <div className="avatar">AI</div>
        <div className="bubble">
          <strong>{m.title}</strong>
          <p>{m.step || '분석 중…'}</p>
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
            {m.riskLevel} · {m.riskScore}/100
          </p>
          {m.recommendations?.map((r, i) => (
            <p key={i} style={{ marginTop: 6 }}>
              → {r}
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
        <div className="bubble">
          <strong>
            {m.title} ({m.total}건)
          </strong>
          <ul className="mini-findings">
            {m.findings.map((f, i) => (
              <li key={i}>
                [{f.source}] {f.type}
                {f.line ? ` · ${f.line}줄` : ''}
                {typeof f.confidence === 'number'
                  ? ` · ${Math.round(f.confidence * 100)}%`
                  : ''}
              </li>
            ))}
          </ul>
          {m.total > m.findings.length && (
            <p style={{ marginTop: 8, fontSize: 12 }}>… 외 {m.total - m.findings.length}건</p>
          )}
        </div>
      </div>
    )
  }

  if (m.type === 'masked' || m.type === 'prompt') {
    return (
      <div className="chat-message">
        <div className="avatar">AI</div>
        <div className="bubble">
          <strong>{m.title}</strong>
          {m.note && <p>{m.note}</p>}
          <pre className="code-output">{m.body}</pre>
          <div className="message-actions">
            <button type="button" className="msg-btn msg-btn--primary" onClick={m.onCopy}>
              <Copy size={12} /> 복사
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
      <div className="avatar">{isUser ? '나' : 'AI'}</div>
      <div className="bubble">
        <strong>{m.title}</strong>
        {m.preview && <pre className="user-preview">{m.preview}</pre>}
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
