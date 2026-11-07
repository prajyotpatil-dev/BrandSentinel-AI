import { useState, useEffect, useCallback } from 'react'
import {
  FileText,
  BookOpen,
  History,
  ChevronDown,
  AlertTriangle,
  WifiOff,
} from 'lucide-react'
import { getHealth, getSamples, getGuidelines, getHistory } from '../api/client'
import type {
  AuditResponse,
  SampleDraft,
  GuidelineItem,
  HealthResponse,
  SubmissionHistory,
} from '../types'
import { SubmissionEditor } from '../components/SubmissionEditor'
import { FindingsPanel } from '../components/FindingsPanel'
import { GuidelinesModal } from '../components/GuidelinesModal'
import { HistoryModal } from '../components/HistoryModal'
import { DecisionCertificate } from '../components/DecisionCertificate'

export function AuditPage() {
  // Global state
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [backendOnline, setBackendOnline] = useState(true)
  const [samples, setSamples] = useState<SampleDraft[]>([])
  const [guidelines, setGuidelines] = useState<GuidelineItem[]>([])
  const [history, setHistory] = useState<SubmissionHistory[]>([])

  // Workspace state
  const [contentText, setContentText] = useState('')
  const [auditResult, setAuditResult] = useState<AuditResponse | null>(null)
  const [isAuditing, setIsAuditing] = useState(false)
  const [submissionStatus, setSubmissionStatus] = useState<string>('draft')

  // Decision state
  const [decisionMade, setDecisionMade] = useState<{
    decision: string
    timestamp: string
    reviewer_name: string
    reviewer_notes?: string
    final_text: string
  } | null>(null)

  // Modals
  const [showGuidelines, setShowGuidelines] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [showSampleMenu, setShowSampleMenu] = useState(false)

  // Initial data fetch
  useEffect(() => {
    const init = async () => {
      try {
        const [h, s, g] = await Promise.all([
          getHealth(),
          getSamples(),
          getGuidelines(),
        ])
        setHealth(h)
        setSamples(s)
        setGuidelines(g)
        setBackendOnline(true)
      } catch {
        setBackendOnline(false)
      }
    }
    init()
  }, [])

  const loadSample = (sample: SampleDraft) => {
    setContentText(sample.text)
    setAuditResult(null)
    setDecisionMade(null)
    setSubmissionStatus('draft')
    setShowSampleMenu(false)
  }

  const refreshGuidelines = useCallback(async () => {
    try {
      const g = await getGuidelines()
      setGuidelines(g)
    } catch { /* silent */ }
  }, [])

  const refreshHistory = useCallback(async () => {
    try {
      const h = await getHistory()
      setHistory(h)
    } catch { /* silent */ }
  }, [])

  const handleAuditComplete = (result: AuditResponse) => {
    setAuditResult(result)
    setIsAuditing(false)
    setSubmissionStatus(result.overall_status)
  }

  const handleDecisionComplete = (decision: {
    decision: string
    timestamp: string
    reviewer_name: string
    reviewer_notes?: string
    final_text: string
  }) => {
    setDecisionMade(decision)
    setSubmissionStatus(decision.decision)
    refreshHistory()
  }

  const handleReset = () => {
    setContentText('')
    setAuditResult(null)
    setDecisionMade(null)
    setSubmissionStatus('draft')
  }

  return (
    <>
      {/* Page Header */}
      <div className="border-b border-zinc-800 bg-zinc-900/50">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-zinc-100">Content Audit</h1>
              <p className="text-sm text-zinc-400 mt-1">
                Validate marketing content against brand guidelines
              </p>
            </div>

            <div className="flex items-center gap-1.5">
              {/* Sample Drafts Dropdown */}
              <div className="relative">
                <button
                  onClick={() => setShowSampleMenu(!showSampleMenu)}
                  className="btn-ghost flex items-center gap-1.5"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Load Sample</span>
                  <ChevronDown className="w-3 h-3" />
                </button>
                {showSampleMenu && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setShowSampleMenu(false)} />
                    <div className="absolute right-0 mt-1 w-72 bg-zinc-900 border border-zinc-700 rounded-xl shadow-xl z-50 py-1 overflow-hidden">
                      {samples.map((s) => (
                        <button
                          key={s.id}
                          onClick={() => loadSample(s)}
                          className="w-full text-left px-4 py-2.5 hover:bg-zinc-800 transition-colors"
                        >
                          <div className="text-sm font-medium text-zinc-200">{s.title}</div>
                          <div className="text-xs text-zinc-500 mt-0.5">{s.description}</div>
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>

              <button
                onClick={() => { setShowGuidelines(true); refreshGuidelines() }}
                className="btn-ghost flex items-center gap-1.5"
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Guidelines</span>
                {health && (
                  <span className="text-[10px] bg-zinc-800 text-zinc-400 rounded px-1.5 py-0.5">
                    {health.guideline_count}
                  </span>
                )}
              </button>

              <button
                onClick={() => { setShowHistory(true); refreshHistory() }}
                className="btn-ghost flex items-center gap-1.5"
              >
                <History className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">History</span>
              </button>

              {/* Status indicators */}
              {!backendOnline && (
                <div className="flex items-center gap-1 text-red-400 text-xs ml-2">
                  <WifiOff className="w-3.5 h-3.5" />
                  <span>Offline</span>
                </div>
              )}
              {health?.fallback_mode && backendOnline && (
                <div className="flex items-center gap-1 text-amber-400 text-xs ml-2">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Fallback Mode</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 py-6">
        {decisionMade ? (
          <DecisionCertificate
            decision={decisionMade}
            auditResult={auditResult!}
            onReset={handleReset}
          />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            {/* Left Column: Editor (40%) */}
            <div className="lg:col-span-2">
              <SubmissionEditor
                text={contentText}
                setText={setContentText}
                status={submissionStatus}
                isAuditing={isAuditing}
                setIsAuditing={setIsAuditing}
                onAuditComplete={handleAuditComplete}
                backendOnline={backendOnline}
              />
            </div>

            {/* Right Column: Findings (60%) */}
            <div className="lg:col-span-3">
              <FindingsPanel
                auditResult={auditResult}
                isAuditing={isAuditing}
                text={contentText}
                setText={setContentText}
                onDecisionComplete={handleDecisionComplete}
                onAuditComplete={handleAuditComplete}
                onAuditStart={() => setIsAuditing(true)}
              />
            </div>
          </div>
        )}
      </main>

      {/* Modals */}
      {showGuidelines && (
        <GuidelinesModal
          guidelines={guidelines}
          onClose={() => setShowGuidelines(false)}
          onRefresh={refreshGuidelines}
        />
      )}
      {showHistory && (
        <HistoryModal
          history={history}
          onClose={() => setShowHistory(false)}
        />
      )}
    </>
  )
}
