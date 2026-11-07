import {
  ShieldCheck,
  XCircle,
  ArrowLeft,
  Copy,
  Check,
  Clock,
  User,
  FileText,
  MessageSquare,
} from 'lucide-react'
import { useState } from 'react'
import type { AuditResponse } from '../types'

interface Props {
  decision: {
    decision: string
    timestamp: string
    reviewer_name: string
    reviewer_notes?: string
    final_text: string
  }
  auditResult: AuditResponse
  onReset: () => void
}

export function DecisionCertificate({ decision, auditResult, onReset }: Props) {
  const [copied, setCopied] = useState(false)

  const isApproved = decision.decision === 'approved'
  const appliedCount = auditResult.findings.length

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(decision.final_text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* silent */ }
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Certificate Card */}
      <div className={`card border-2 ${isApproved ? 'border-emerald-500/30' : 'border-red-500/30'}`}>
        {/* Status Banner */}
        <div className={`flex items-center gap-3 pb-4 border-b ${isApproved ? 'border-emerald-500/20' : 'border-red-500/20'}`}>
          {isApproved ? (
            <ShieldCheck className="w-8 h-8 text-emerald-500" />
          ) : (
            <XCircle className="w-8 h-8 text-red-500" />
          )}
          <div>
            <h2 className="text-lg font-semibold">
              {isApproved ? 'Content Approved for Publication' : decision.decision === 'rejected' ? 'Content Rejected' : 'Changes Requested'}
            </h2>
            <p className="text-xs text-zinc-500">Auditable Decision Certificate</p>
          </div>
        </div>

        {/* Decision Metadata */}
        <div className="grid grid-cols-2 gap-4 py-4">
          <div className="flex items-center gap-2 text-sm">
            <Clock className="w-4 h-4 text-zinc-500" />
            <div>
              <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Timestamp</div>
              <div className="text-zinc-300 text-xs">{new Date(decision.timestamp).toLocaleString()}</div>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <User className="w-4 h-4 text-zinc-500" />
            <div>
              <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Reviewer</div>
              <div className="text-zinc-300 text-xs">{decision.reviewer_name}</div>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <FileText className="w-4 h-4 text-zinc-500" />
            <div>
              <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Findings Reviewed</div>
              <div className="text-zinc-300 text-xs">{appliedCount} issue(s)</div>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <MessageSquare className="w-4 h-4 text-zinc-500" />
            <div>
              <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Submission ID</div>
              <div className="text-zinc-300 text-xs font-mono">{auditResult.submission_id.slice(0, 12)}...</div>
            </div>
          </div>
        </div>

        {/* Reviewer Notes */}
        {decision.reviewer_notes && (
          <div className="py-3 border-t border-zinc-800">
            <div className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Reviewer Notes</div>
            <p className="text-xs text-zinc-400 italic">"{decision.reviewer_notes}"</p>
          </div>
        )}

        {/* Approved Content */}
        <div className="pt-3 border-t border-zinc-800">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-zinc-500 uppercase tracking-wider">
              {isApproved ? 'Approved Content' : 'Final Content'}
            </span>
            <button
              onClick={handleCopy}
              className="btn-ghost flex items-center gap-1 text-xs"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
          <div className="bg-zinc-800/60 border border-zinc-700/50 rounded-lg p-4">
            <p className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">
              {decision.final_text}
            </p>
          </div>
        </div>
      </div>

      {/* New Audit button */}
      <div className="mt-4 text-center">
        <button onClick={onReset} className="btn-ghost flex items-center gap-2 mx-auto">
          <ArrowLeft className="w-4 h-4" />
          Start New Audit
        </button>
      </div>
    </div>
  )
}
