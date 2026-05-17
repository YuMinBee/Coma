import { useState, useCallback } from 'react'

export const ARTIFACT_TABS = [
  { id: 'masked', label: '마스킹된 내용' },
  { id: 'prompt', label: '안전 프롬프트' },
  { id: 'findings', label: '탐지 상세' },
]

export function defaultArtifactTab(contextId) {
  if (contextId === 'ai' || contextId === 'collab') return 'prompt'
  return 'masked'
}

export function useArtifactPanel() {
  const [open, setOpen] = useState(false)
  const [tab, setTab] = useState('masked')
  const [expandedFindingIndex, setExpandedFindingIndex] = useState(null)

  const openWithResult = useCallback((contextId) => {
    setTab(defaultArtifactTab(contextId))
    setExpandedFindingIndex(null)
    setOpen(true)
  }, [])

  const close = useCallback(() => setOpen(false), [])

  const openTab = useCallback((tabId, findingIndex = null) => {
    setTab(tabId)
    setExpandedFindingIndex(findingIndex)
    setOpen(true)
  }, [])

  return {
    open,
    tab,
    setTab,
    expandedFindingIndex,
    setExpandedFindingIndex,
    openWithResult,
    openTab,
    close,
  }
}
