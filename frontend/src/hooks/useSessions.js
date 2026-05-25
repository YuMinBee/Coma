import { useState, useEffect, useCallback } from 'react'
import { IMPORT_CONTEXTS } from '../constants'

const STORAGE_KEY = 'safeprompt-sessions-v2'

function newSessionId() {
  return `s-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function createSession(contextId, title = '새 검사') {
  return {
    id: newSessionId(),
    contextId: normalizeContextId(contextId),
    title,
    createdAt: Date.now(),
    messages: [],
    lastResult: null,
    panel: { open: false, tab: 'masked', expandedFindingIndices: [] },
  }
}

function normalizeContextId(contextId) {
  return IMPORT_CONTEXTS.some((c) => c.id === contextId) ? contextId : 'share'
}

function normalizeSession(session) {
  const p = session.panel || {}
  const legacy = p.expandedFindingIndex
  const indices =
    p.expandedFindingIndices ??
    (legacy !== null && legacy !== undefined ? [legacy] : [])
  return {
    ...session,
    contextId: normalizeContextId(session.contextId),
    panel: {
      open: !!p.open,
      tab: p.tab || 'masked',
      expandedFindingIndices: indices,
    },
  }
}

function loadStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw)
    if (data.sessions) {
      data.sessions = data.sessions.map(normalizeSession)
    }
    return data
  } catch {
    return null
  }
}

function contextLabel(id) {
  const normalized = normalizeContextId(id)
  return IMPORT_CONTEXTS.find((c) => c.id === normalized)?.label || normalized
}

export function useSessions(initialContextId = 'ai') {
  const [sessions, setSessions] = useState(() => {
    const stored = loadStored()
    if (stored?.sessions?.length) return stored.sessions
    return [createSession(initialContextId)]
  })
  const [activeId, setActiveId] = useState(() => {
    const stored = loadStored()
    if (stored?.activeId && stored.sessions?.some((s) => s.id === stored.activeId)) {
      return stored.activeId
    }
    const first = stored?.sessions?.[0]?.id
    if (first) return first
    return null
  })

  useEffect(() => {
    if (!activeId && sessions[0]) setActiveId(sessions[0].id)
  }, [activeId, sessions])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ sessions, activeId }))
  }, [sessions, activeId])

  const activeSession =
    sessions.find((s) => s.id === activeId) || sessions[0] || null

  const updateSession = useCallback((id, patch) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, ...patch } : s)),
    )
  }, [])

  const createNewSession = useCallback(
    (contextId, title) => {
      const session = createSession(contextId, title || contextLabel(contextId))
      setSessions((prev) => [session, ...prev])
      setActiveId(session.id)
      return session.id
    },
    [],
  )

  const switchContext = useCallback(
    (contextId) => {
      createNewSession(contextId)
    },
    [createNewSession],
  )

  const selectSession = useCallback((id) => setActiveId(id), [])

  const patchActive = useCallback(
    (patch) => {
      setSessions((prev) => {
        const id = activeId || prev[0]?.id
        if (!id) return prev
        return prev.map((s) => {
          if (s.id !== id) return s
          const next = typeof patch === 'function' ? patch(s) : patch
          return { ...s, ...next }
        })
      })
    },
    [activeId],
  )

  return {
    sessions,
    activeSession,
    activeId,
    createNewSession,
    switchContext,
    selectSession,
    patchActive,
    updateSession,
    contextLabel,
  }
}
