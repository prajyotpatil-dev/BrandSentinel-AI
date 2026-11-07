import { useState } from 'react'
import {
  Send,
  Loader2,
  FileText,
  RotateCcw,
} from 'lucide-react'
import { runAudit } from '../api/client'
import type { AuditResponse } from '../types'

interface Props {
  text: string
  setText: (t: string) => void
  status: string
  isAuditing: boolean
  setIsAuditing: (v: boolean) => void
  onAuditComplete: (result: AuditResponse) => void
  backendOnline: boolean
}

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  draft: { label: 'Draft', color: 'bg-zinc-700 text-zinc-300' },
  auditing: { label: 'Auditing...', color: 'bg-blue-500/20 text-blue-400' },
  flagged: { label: 'Issues Detected', color: 'bg-orange-500/20 text-orange-400' },
  needs_escalation: { label: 'Needs Escalation', color: 'bg-red-500/20 text-red-400' },
  clean: { label: 'Clean', color: 'bg-emerald-500/20 text-emerald-400' },
  approved: { label: 'Approved', color: 'bg-emerald-500/20 text-emerald-400' },
  rejected: { label: 'Rejected', color: 'bg-red-500/20 text-red-400' },
}

export function SubmissionEditor({
  text,
  setText,
  status,
  isAuditing,
  setIsAuditing,
  onAuditComplete,
  backendOnline,
}: Props) {
  const [error, setError] = useState<string | null>(null)

  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0
  const charCount = text.length
  const statusCfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.draft

  const handleAudit = async () => {
    if (!text.trim()) {
      setError('Please enter content to audit.')
      return
    }
    setError(null)
    setIsAuditing(true)
    try {
      const result = await runAudit(text)
      onAuditComplete(result)
    } catch (err: any) {
      const status = err?.response?.status
      const detail = err?.response?.data?.detail

      if (!err?.response && (err?.code === 'ERR_NETWORK' || err?.message?.includes('Network Error'))) {
        setError('Backend connection failed. Please ensure the backend server is running on port 8000.')
      } else if (status === 503 || status === 429) {
        setError('AI service is temporarily experiencing high demand or rate limits. Completed audit using deterministic rules and claim verification fallback.')
      } else if (status === 401 || status === 403) {
        setError('Invalid or missing API key configuration on backend.')
      } else if (status === 422) {
        setError(detail || 'Invalid request content.')
      } else {
        setError(detail || 'Audit failed — please check backend connection or try again.')
      }
      setIsAuditing(false)
    }
  }

  const handleClear = () => {
    setText('')
    setError(null)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Panel header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-zinc-400" />
          <h2 className="text-sm font-semibold text-zinc-300">Content Submission</h2>
        </div>
        <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${statusCfg.color}`}>
          {statusCfg.label}
        </span>
      </div>

      {/* Textarea */}
      <div className="relative flex-1 min-h-0">
        <textarea
          value={text}
          onChange={(e) => { setText(e.target.value); setError(null) }}
          placeholder="Paste or type marketing content to audit against brand guidelines..."
          className="w-full h-full min-h-[320px] lg:min-h-[480px] bg-zinc-900 border border-zinc-800 rounded-xl p-4 text-sm text-zinc-200 placeholder:text-zinc-600 resize-none focus:outline-none focus:ring-1 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-colors"
          disabled={isAuditing}
        />
      </div>

      {/* Footer: counts + actions */}
      <div className="flex items-center justify-between mt-3">
        <div className="text-xs text-zinc-500 flex gap-3">
          <span>{wordCount} words</span>
          <span>{charCount} chars</span>
        </div>
        <div className="flex items-center gap-2">
          {text && (
            <button onClick={handleClear} className="btn-ghost flex items-center gap-1" disabled={isAuditing}>
              <RotateCcw className="w-3 h-3" />
              Clear
            </button>
          )}
          <button
            onClick={handleAudit}
            disabled={isAuditing || !text.trim() || !backendOnline}
            className="btn-primary flex items-center gap-2 text-sm"
          >
            {isAuditing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analysing...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Run Brand Audit
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mt-2 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
          {error}
        </div>
      )}
    </div>
  )
}
