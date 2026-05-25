import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Shield,
  ScanSearch,
  Upload,
  FolderOpen,
  Sun,
  Moon,
  PanelRightOpen,
} from 'lucide-react'
import './App.css'
import { SAMPLES, DEFAULT_SAMPLE_ID } from './samples'
import { useTheme } from './hooks/useTheme'
import { useSessions } from './hooks/useSessions'
import { defaultArtifactTab } from './hooks/useArtifactPanel'
import {
  ACCEPT_FILE_TYPES,
  IMPORT_CONTEXTS,
  MAX_FOLDER_FILES,
  MAX_FILE_BYTES,
} from './constants'
import Sidebar from './components/Sidebar'
import ArtifactPanel from './components/ArtifactPanel'
import ChatBubble from './components/ChatBubble'

let msgId = 0
const nextId = () => `m-${++msgId}`
const INITIAL_SCAN_STEP = '1차: 정규식 탐지 중…'
const SCAN_PROGRESS_STEPS = [
  '2차: 규칙 탐지 중…',
  '3차: Gemma 문맥 분석 중…',
  '마스킹 및 안전 프롬프트 생성 중…',
]

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

function previewLines(text, maxLines = 8) {
  return text.split('\n').slice(0, maxLines).join('\n')
}

function countFindingsBySource(findings = []) {
  return findings.reduce(
    (acc, finding) => {
      acc[finding.source] = (acc[finding.source] || 0) + 1
      return acc
    },
    { regex: 0, rule: 0, gemma: 0 },
  )
}

function buildAnalysisSteps(data, hasSafePrompt) {
  const counts = countFindingsBySource(data.findings || [])
  return [
    {
      title: '1차 정규식 검사',
      body:
        counts.regex > 0
          ? `토큰, 비밀번호, URL, 개인정보처럼 명확한 패턴 ${counts.regex}건을 확인했습니다.`
          : '명확한 비밀값·개인정보 패턴은 발견되지 않았습니다.',
    },
    {
      title: '2차 규칙 검사',
      body:
        counts.rule > 0
          ? `파일명, 키워드, 테이블명 등 규칙 기반 후보 ${counts.rule}건을 확인했습니다.`
          : '규칙 기반 후보는 발견되지 않았습니다.',
    },
    {
      title: '3차 Gemma 문맥 검사',
      body: data.gemma_used
        ? counts.gemma > 0
          ? `정규식으로 잡기 어려운 문맥 위험 ${counts.gemma}건을 추가로 확인했습니다.`
          : '문맥상 추가 유출 후보는 발견되지 않았습니다.'
        : 'Gemma를 사용하지 못해 정규식·규칙 기반으로만 판단했습니다.',
    },
    {
      title: '마스킹 및 결과 생성',
      body:
        data.findings?.length > 0
          ? hasSafePrompt
            ? '탐지된 항목을 마스킹하고 외부 공유용 안전 프롬프트를 생성했습니다.'
            : '탐지된 항목을 마스킹했습니다.'
          : '탐지 0건이라 안전 프롬프트는 생성하지 않았습니다.',
    },
  ]
}

export default function App() {
  const { toggle, isDark } = useTheme()
  const {
    sessions,
    activeSession,
    createNewSession,
    switchContext,
    selectSession,
    patchActive,
    contextLabel,
  } = useSessions('ai')

  const [text, setText] = useState('')
  const [useGemma, setUseGemma] = useState(true)
  const [loading, setLoading] = useState(false)
  const [health, setHealth] = useState(null)
  const [toast, setToast] = useState(null)
  const [sampleId, setSampleId] = useState(DEFAULT_SAMPLE_ID)
  const [dragActive, setDragActive] = useState(false)
  const [error, setError] = useState(null)

  const fileRef = useRef(null)
  const folderRef = useRef(null)
  const streamRef = useRef(null)

  const importContext = activeSession?.contextId ?? 'ai'
  const messages = activeSession?.messages ?? []
  const lastResult = activeSession?.lastResult ?? null
  const panel = activeSession?.panel ?? {
    open: false,
    tab: 'masked',
    expandedFindingIndices: [],
  }
  const expandedFindingIndices = panel.expandedFindingIndices ?? []

  const activeContext = IMPORT_CONTEXTS.find((c) => c.id === importContext) || IMPORT_CONTEXTS[0]
  const panelOpen = panel.open && !!lastResult

  const scrollBottom = useCallback(() => {
    requestAnimationFrame(() => {
      if (streamRef.current) streamRef.current.scrollTop = streamRef.current.scrollHeight
    })
  }, [])

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ ollama_available: false, gemma_available: false }))
  }, [])

  useEffect(() => {
    scrollBottom()
  }, [messages, loading, scrollBottom])

  const copyText = async (content, label) => {
    await navigator.clipboard.writeText(content)
    setToast(`${label} 복사됨`)
    setTimeout(() => setToast(null), 2000)
  }

  const openPanel = (tab, findingIndex = null) => {
    const indices = [...expandedFindingIndices]
    if (findingIndex !== null && findingIndex !== undefined && !indices.includes(findingIndex)) {
      indices.push(findingIndex)
    }
    patchActive({
      panel: { open: true, tab, expandedFindingIndices: indices },
    })
  }

  const toggleFindingExpand = (index) => {
    const indices = [...expandedFindingIndices]
    const pos = indices.indexOf(index)
    if (pos >= 0) indices.splice(pos, 1)
    else indices.push(index)
    indices.sort((a, b) => a - b)
    patchActive({
      panel: { ...panel, expandedFindingIndices: indices },
    })
  }

  const closePanel = () => {
    patchActive({ panel: { ...panel, open: false } })
  }

  const applyScanResult = (data, titlePatch = {}) => {
    const rc = riskClass(data.risk_level)
    patchActive((session) => {
      const base = session.messages.filter((m) => m.type !== 'loading')
      const hasSafePrompt = Boolean(data.safe_prompt?.trim())
      const analysisSteps = buildAnalysisSteps(data, hasSafePrompt)
      const newMessages = [
        ...base,
        {
          id: nextId(),
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
        },
        {
          id: nextId(),
          role: 'assistant',
          type: 'analysis',
          title: '검사 과정',
          steps: analysisSteps,
        },
      ]
      if (data.findings.length > 0) {
        newMessages.push({
          id: nextId(),
          role: 'assistant',
          type: 'findings',
          title: '탐지 항목',
          findings: data.findings,
          total: data.findings.length,
        })
      }

      const promptTitle =
        session.contextId === 'ai'
          ? '외부 AI 공유용 안전 프롬프트'
          : '외부 공유용 안전 텍스트'

      newMessages.push({
        id: nextId(),
        role: 'assistant',
        type: 'masked',
        title: '마스킹된 내용',
        body: data.masked_text,
      })

      if (hasSafePrompt) {
        newMessages.push({
          id: nextId(),
          role: 'assistant',
          type: 'prompt',
          title: promptTitle,
          body: data.safe_prompt,
          note: !data.gemma_used ? 'Gemma 미연결 — 규칙 기반 템플릿으로 생성됨' : null,
        })
      }

      return {
        ...titlePatch,
        messages: newMessages,
        lastResult: data,
        panel: {
          open: true,
          tab: hasSafePrompt ? defaultArtifactTab(session.contextId) : 'masked',
          expandedFindingIndices: [],
        },
      }
    })
  }

  const runScanWithContent = async (content, label = '붙여넣기', filename = null) => {
    if (!content.trim()) {
      setError('검사할 내용이 없습니다.')
      return
    }
    setLoading(true)
    setError(null)
    setText('')

    const userMsg = {
      id: nextId(),
      role: 'user',
      title: label,
      preview: content.slice(0, 1200) + (content.length > 1200 ? '\n…' : ''),
      tags: [activeContext.label, filename || '텍스트'].filter(Boolean),
    }
    const agentId = nextId()
    patchActive({
      messages: [
        ...messages,
        userMsg,
        { id: agentId, role: 'assistant', type: 'loading', title: '보안 에이전트', step: INITIAL_SCAN_STEP },
      ],
    })

    let stepIdx = 0
    const timer = setInterval(() => {
      if (stepIdx < SCAN_PROGRESS_STEPS.length) {
        const step = SCAN_PROGRESS_STEPS[stepIdx++]
        patchActive((session) => ({
          messages: session.messages.map((m) => (m.id === agentId ? { ...m, step } : m)),
        }))
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
      const title = filename || label.slice(0, 40) || '검사'
      applyScanResult(data, { title })
    } catch (e) {
      setError(e.message)
      patchActive((session) => ({
        messages: [
          ...session.messages.filter((m) => m.type !== 'loading'),
          { id: nextId(), role: 'assistant', type: 'error', title: '검사 실패', body: e.message },
        ],
      }))
    } finally {
      clearInterval(timer)
      setLoading(false)
    }
  }

  const runScanFile = async (file) => {
    setLoading(true)
    setError(null)
    const userMsg = {
      id: nextId(),
      role: 'user',
      title: '파일 업로드',
      preview: file.name,
      tags: [activeContext.label, file.name],
    }
    const agentId = nextId()
    patchActive({
      messages: [
        ...messages,
        userMsg,
        { id: agentId, role: 'assistant', type: 'loading', title: '보안 에이전트', step: INITIAL_SCAN_STEP },
      ],
    })

    let stepIdx = 0
    const timer = setInterval(() => {
      if (stepIdx < SCAN_PROGRESS_STEPS.length) {
        const step = SCAN_PROGRESS_STEPS[stepIdx++]
        patchActive((session) => ({
          messages: session.messages.map((m) => (m.id === agentId ? { ...m, step } : m)),
        }))
      }
    }, 900)

    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch(`/api/scan/file?use_gemma=${useGemma}`, { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || '파일 검사 실패')
      applyScanResult(data, { title: file.name })
    } catch (e) {
      setError(e.message)
      patchActive((session) => ({
        messages: [
          ...session.messages.filter((m) => m.type !== 'loading'),
          { id: nextId(), role: 'assistant', type: 'error', title: '파일 검사 실패', body: e.message },
        ],
      }))
    } finally {
      clearInterval(timer)
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
          if (entry?.isDirectory) await walkEntry(entry, '', files)
          else {
            const f = item.getAsFile()
            if (f) files.push(f)
          }
        }
      }
    } else {
      files.push(...Array.from(e.dataTransfer.files || []))
    }
    if (!files.length) return
    if (files.length === 1 && !files[0].webkitRelativePath) return runScanFile(files[0])
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
          for (const ent of entries) await walkEntry(ent, path + entry.name + '/', out)
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

  const handleContextSwitch = (ctxId) => {
    if (ctxId !== importContext) switchContext(ctxId)
  }

  const healthLabel = health
    ? health.gemma_available
      ? '로컬 Gemma 연결됨 · API 정상'
      : health.ollama_available
        ? 'Ollama 연결됨 · Gemma 모델 없음'
        : 'API 정상 · 로컬 Gemma 대기'
    : '연결 확인 중…'

  return (
    <div className={`app-shell ${panelOpen ? 'app-shell--panel-open' : ''}`}>
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
            <p>외부 공유 전 보안 검사 에이전트</p>
          </div>
        </div>
        <div className="topbar-actions">
          <span
            className={`status-pill ${health?.gemma_available ? '' : 'status-pill--warn'}`}
            title={health?.gemma_model ? `${health.gemma_model} @ ${health.ollama_base}` : undefined}
          >
            {healthLabel}
          </span>
          {!panelOpen && lastResult && (
            <button
              type="button"
              className="icon-btn"
              onClick={() => openPanel(panel.tab)}
              title="결과 패널 열기"
            >
              <PanelRightOpen size={16} />
            </button>
          )}
          <button type="button" className="icon-btn" onClick={toggle} title="테마 전환">
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </header>

      <div className="context-bar">
        {IMPORT_CONTEXTS.map((ctx) => (
          <button
            key={ctx.id}
            type="button"
            className={`context-chip ${importContext === ctx.id ? 'context-chip--active' : ''}`}
            onClick={() => handleContextSwitch(ctx.id)}
          >
            <span>{ctx.icon}</span>
            {ctx.label}
          </button>
        ))}
      </div>
      <p className="context-hint">{activeContext.hint}</p>

      <div className="workspace">
        <Sidebar
          sessions={sessions}
          activeId={activeSession?.id}
          onSelect={selectSession}
          onNewScan={() => createNewSession(importContext)}
          contextLabel={contextLabel}
        />

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
                <h2>외부로 공유하기 전, 여기서 먼저 검사하세요</h2>
                <p>
                  외부 AI 공유, Git push, 파일 공유 등{' '}
                  <strong>외부 공유·유출</strong> 전에 민감정보를 탐지·마스킹합니다.
                </p>
                <ul className="welcome-list">
                  <li>검사 이력은 왼쪽에서 확인</li>
                  <li>긴 결과는 오른쪽 패널에서 확인 (Gemini형)</li>
                  <li>메뉴 변경 시 새 검사 세션이 시작됩니다</li>
                </ul>
              </div>
            )}

            {messages.map((m) => (
              <ChatBubble
                key={m.id}
                message={m}
                onOpenPanel={openPanel}
                onCopy={copyText}
                expandedFindingIndices={expandedFindingIndices}
                onToggleFinding={toggleFindingExpand}
              />
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
              placeholder="코드, 로그, 설정, 문서를 붙여넣거나 파일·폴더를 드래그하세요."
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleScan()
              }}
            />
            <div className="composer-actions">
              <div className="left-actions">
                <label className="tool-btn">
                  <Upload size={14} /> 파일
                  <input
                    ref={fileRef}
                    type="file"
                    accept={ACCEPT_FILE_TYPES}
                    onChange={handleFile}
                  />
                </label>
                <label className="tool-btn">
                  <FolderOpen size={14} /> 폴더
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

        <ArtifactPanel
          open={panelOpen}
          tab={panel.tab}
          onTabChange={(tab) => openPanel(tab)}
          onClose={closePanel}
          result={lastResult}
          contextId={importContext}
          expandedFindingIndices={expandedFindingIndices}
          onToggleFinding={toggleFindingExpand}
          onCopy={copyText}
        />
      </div>

      {toast && <div className="copy-toast">{toast}</div>}
    </div>
  )
}
