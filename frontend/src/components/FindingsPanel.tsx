import { useState } from 'react'
import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Quote,
  ArrowRight,
  Loader2,
  ShieldCheck,
  ShieldAlert,
  X,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react'
import { submitDecision, runAudit } from '../api/client'
import type { AuditResponse, AuditFinding, DecisionType } from '../types'

interface Props {
  auditResult: AuditResponse | null
  isAuditing: boolean
  text: string
  setText: (t: string) => void
  onDecisionComplete: (decision: {
    decision: string
    timestamp: string
    reviewer_name: string
    reviewer_notes?: string
    final_text: string
  }) => void
  onAuditComplete: (result: AuditResponse) => void
  onAuditStart: () => void
}

const SEVERITY_STYLES: Record<string, string> = {
  critical: 'badge-critical',
  high: 'badge-high',
  medium: 'badge-medium',
  low: 'badge-low',
}

const CATEGORY_LABELS: Record<string, string> = {
  terminology: 'Terminology',
  unsupported_claim: 'Unsupported Claim',
  tone_voice: 'Tone & Voice',
  prohibited_phrase: 'Prohibited Phrase',
  compliance: 'Compliance',
}

const EVIDENCE_STYLES: Record<string, { label: string; color: string; desc: string }> = {
  supported: { label: 'Verified (Supported)', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20', desc: 'Supported by approved brand guidelines.' },
  contradicted: { label: 'Contradicted', color: 'text-red-400 bg-red-500/10 border-red-500/20', desc: 'Directly contradicts approved brand guidelines.' },
  not_found: { label: 'Unsupported Claim', color: 'text-amber-400 bg-amber-500/10 border-amber-500/20', desc: 'No supporting evidence found in approved documentation.' },
}

export function FindingsPanel({ auditResult, isAuditing, text, setText, onDecisionComplete, onAuditComplete, onAuditStart }: Props) {
  const [expandedFindings, setExpandedFindings] = useState<Set<string>>(new Set())
  const [dismissedFindings, setDismissedFindings] = useState<Set<string>>(new Set())
  const [appliedFindings, setAppliedFindings] = useState<Set<string>>(new Set())
  const [reviewerName, setReviewerName] = useState('Guest Reviewer')
  const [reviewerNotes, setReviewerNotes] = useState('')
  const [acknowledgeIncomplete, setAcknowledgeIncomplete] = useState(false)
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false)
  const [decisionError, setDecisionError] = useState<string | null>(null)
  const [isReauditing, setIsReauditing] = useState(false)

  // Empty state
  if (!auditResult && !isAuditing) {
    return (
      <div className="flex items-center justify-center h-full min-h-[480px]">
        <div className="text-center max-w-sm">
          <ShieldCheck className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
          <h3 className="text-sm font-medium text-zinc-400 mb-1">No Audit Results Yet</h3>
          <p className="text-xs text-zinc-600">
            Submit content and run a brand governance audit to see findings here.
          </p>
        </div>
      </div>
    )
  }

  // Loading state
  if (isAuditing) {
    return (
      <div className="flex items-center justify-center h-full min-h-[480px]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-emerald-500 animate-spin mx-auto mb-3" />
          <h3 className="text-sm font-medium text-zinc-300">Analysing Content</h3>
          <p className="text-xs text-zinc-500 mt-1">Running hybrid audit engine...</p>
        </div>
      </div>
    )
  }

  const findings = auditResult!.findings
  const criticalCount = findings.filter((f) => f.severity === 'critical').length
  const highCount = findings.filter((f) => f.severity === 'high').length
  const mediumCount = findings.filter((f) => f.severity === 'medium').length
  const lowCount = findings.filter((f) => f.severity === 'low').length

  const toggleExpand = (id: string) => {
    setExpandedFindings((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const handleApplyRevision = async (finding: AuditFinding) => {
    if (!finding.suggested_replacement) return
    // Replace all occurrences, not just the first one
    const newText = text.split(finding.flagged_text).join(finding.suggested_replacement)
    if (newText !== text) {
      setText(newText)
      setAppliedFindings((prev) => new Set(prev).add(finding.id))

      // Re-run audit with updated text
      setIsReauditing(true)
      onAuditStart()
      try {
        const result = await runAudit(newText)
        onAuditComplete(result)
      } catch (error) {
        console.error('Re-audit failed:', error)
      } finally {
        setIsReauditing(false)
      }
    }
  }

  const handleDismiss = (id: string) => {
    setDismissedFindings((prev) => new Set(prev).add(id))
  }

  const handleRetryAI = async () => {
    setIsReauditing(true)
    onAuditStart()
    try {
      const result = await runAudit(text)
      onAuditComplete(result)
    } catch (error) {
      console.error('Retry AI analysis failed:', error)
    } finally {
      setIsReauditing(false)
    }
  }

  const handleDecision = async (decision: DecisionType) => {
    setDecisionError(null)
    if (decision === 'approved' && auditResult?.overall_status === 'review_required') {
      if (!acknowledgeIncomplete) {
        setDecisionError('Mandatory check incomplete: You must acknowledge the skipped AI analysis before approving.')
        return
      }
      if (!reviewerNotes.trim()) {
        setDecisionError('Reviewer notes are required when approving an audit with incomplete AI analysis.')
        return
      }
    }
    setIsSubmittingDecision(true)
    try {
      const resolved = [...appliedFindings, ...dismissedFindings]
      const resp = await submitDecision({
        submission_id: auditResult!.submission_id,
        decision,
        reviewer_name: reviewerName || 'Guest Reviewer',
        reviewer_notes: reviewerNotes || undefined,
        resolved_findings: resolved,
        final_text: text,
      })
      onDecisionComplete({
        decision: resp.decision,
        timestamp: resp.timestamp,
        reviewer_name: resp.reviewer_name,
        reviewer_notes: resp.reviewer_notes,
        final_text: text,
      })
    } catch (err: any) {
      setDecisionError(err?.response?.data?.detail || 'Decision submission failed.')
    } finally {
      setIsSubmittingDecision(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Summary Banner */}
      <div className="card mb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {auditResult!.overall_status === 'review_required' ? (
              <AlertTriangle className="w-5 h-5 text-amber-400" />
            ) : findings.length === 0 ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
            ) : (
              <ShieldAlert className="w-5 h-5 text-amber-400" />
            )}
            <span className="text-sm font-medium">
              {auditResult!.overall_status === 'review_required'
                ? 'Review Required'
                : findings.length === 0
                ? 'Content is compliant'
                : `${findings.length} issue${findings.length !== 1 ? 's' : ''} detected`}
            </span>
            <span className="text-xs text-zinc-500">
              in {auditResult!.execution_time_ms.toFixed(0)}ms
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            {criticalCount > 0 && <span className="badge-critical">{criticalCount} Critical</span>}
            {highCount > 0 && <span className="badge-high">{highCount} High</span>}
            {mediumCount > 0 && <span className="badge-medium">{mediumCount} Medium</span>}
            {lowCount > 0 && <span className="badge-low">{lowCount} Low</span>}
          </div>
        </div>
        {auditResult!.summary && (
          <p className="text-xs text-zinc-400 mt-2">{auditResult!.summary}</p>
        )}

        {/* Pipeline Status Breakdown */}
        <div className="mt-3 pt-3 border-t border-zinc-800 grid grid-cols-2 sm:grid-cols-5 gap-2 text-[11px]">
          <div className="bg-zinc-800/50 rounded-lg p-2 border border-zinc-700/50">
            <div className="text-zinc-400 font-medium">Deterministic Rules</div>
            <div className="text-emerald-400 flex items-center gap-1 mt-0.5">✓ Completed</div>
          </div>
          <div className="bg-zinc-800/50 rounded-lg p-2 border border-zinc-700/50">
            <div className="text-zinc-400 font-medium">Claim Extraction</div>
            <div className="text-emerald-400 flex items-center gap-1 mt-0.5">✓ Completed</div>
          </div>
          <div className="bg-zinc-800/50 rounded-lg p-2 border border-zinc-700/50">
            <div className="text-zinc-400 font-medium">Guideline Retrieval</div>
            <div className="text-emerald-400 flex items-center gap-1 mt-0.5">✓ Completed</div>
          </div>
          <div className="bg-zinc-800/50 rounded-lg p-2 border border-zinc-700/50">
            <div className="text-zinc-400 font-medium">Gemini AI Analysis</div>
            {auditResult!.gemini_status === 'success' ? (
              <div className="text-emerald-400 flex items-center gap-1 mt-0.5">✓ Completed</div>
            ) : auditResult!.gemini_status === 'failed' ? (
              <div className="text-red-400 flex items-center gap-1 mt-0.5">✗ Failed</div>
            ) : (
              <div className="text-zinc-500 flex items-center gap-1 mt-0.5">- Skipped</div>
            )}
          </div>
          <div className="bg-zinc-800/50 rounded-lg p-2 border border-zinc-700/50">
            <div className="text-zinc-400 font-medium">OpenRouter AI</div>
            {auditResult!.openrouter_status === 'success' ? (
              <div className="text-emerald-400 flex items-center gap-1 mt-0.5">✓ Completed (Fallback)</div>
            ) : auditResult!.openrouter_status === 'failed' ? (
              <div className="text-red-400 flex items-center gap-1 mt-0.5">✗ Failed</div>
            ) : (
              <div className="text-zinc-500 flex items-center gap-1 mt-0.5">- Skipped</div>
            )}
          </div>
        </div>

        {/* Skipped checks warning / Provider badge */}
        {auditResult!.llm_provider === 'openrouter' && (
          <div className="mt-3 flex items-start gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-lg px-3 py-2">
            <ShieldCheck className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-indigo-300">OpenRouter Fallback Active</p>
              <p className="text-xs text-zinc-400 mt-0.5">
                Gemini was unavailable, so OpenRouter successfully provided contextual analysis.
              </p>
            </div>
          </div>
        )}

        {auditResult!.checks_skipped && auditResult!.checks_skipped.length > 0 && !auditResult!.llm_checked && (
          <div className="mt-3 flex items-start gap-2 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-amber-400">Incomplete Analysis — AI Contextual Check Unavailable</p>
              <p className="text-xs text-zinc-400 mt-0.5">
                Deterministic and claim verification checks passed successfully. However, both Gemini and OpenRouter AI analysis failed.
                Click <strong>Retry</strong> below or review manually before approving.
              </p>
              <button
                onClick={handleRetryAI}
                disabled={isReauditing}
                className="mt-2 text-xs bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 rounded px-2 py-1 flex items-center gap-1 transition-colors"
              >
                {isReauditing ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                Retry AI Analysis
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Findings List */}
      <div className="flex-1 overflow-y-auto space-y-3 min-h-0 pr-1">
        {findings.map((finding) => {
          const isDismissed = dismissedFindings.has(finding.id)
          const isApplied = appliedFindings.has(finding.id)
          const isExpanded = expandedFindings.has(finding.id)
          const evidence = EVIDENCE_STYLES[finding.evidence_status]

          if (isDismissed) return null

          return (
            <div
              key={finding.id}
              className={`card transition-all ${isApplied ? 'opacity-60 border-emerald-500/30' : ''}`}
            >
              {/* Header row */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={SEVERITY_STYLES[finding.severity]}>
                    {finding.severity}
                  </span>
                  <span className="text-xs text-zinc-500 bg-zinc-800 rounded px-1.5 py-0.5">
                    {CATEGORY_LABELS[finding.category] ?? finding.category}
                  </span>
                  {isApplied && (
                    <span className="text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-2 py-0.5">
                      ✓ Applied
                    </span>
                  )}
                </div>
                <button
                  onClick={() => toggleExpand(finding.id)}
                  className="text-zinc-500 hover:text-zinc-300 transition-colors p-1"
                >
                  {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
              </div>

              {/* Flagged text */}
              <div className="mt-2 text-sm">
                <span className="bg-red-500/15 text-red-300 px-1 rounded">
                  {finding.flagged_text}
                </span>
              </div>

              {/* Explanation */}
              <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
                {finding.explanation}
              </p>

              {/* Expanded details */}
              {isExpanded && (
                <div className="mt-3 space-y-3">
                  {/* Evidence box */}
                  {finding.evidence_quote && (
                    <div className="bg-zinc-800/60 border border-zinc-700/50 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1.5">
                        <Quote className="w-3 h-3 text-zinc-500" />
                        <span className="text-[11px] font-medium text-zinc-400">Guideline Evidence</span>
                        <span className={`text-[10px] border rounded-full px-1.5 py-0.5 ${evidence.color}`}>
                          {evidence.label}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-300 italic leading-relaxed">
                        "{finding.evidence_quote}"
                      </p>
                      {finding.evidence_source && (
                        <p className="text-[10px] text-zinc-500 mt-1.5">
                          Source: {finding.evidence_source}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Suggested replacement */}
                  {finding.suggested_replacement && !isApplied && (
                    <div className="flex items-start gap-2 bg-emerald-500/5 border border-emerald-500/15 rounded-lg p-3">
                      <ArrowRight className="w-3.5 h-3.5 text-emerald-500 mt-0.5 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <span className="text-[11px] text-emerald-400 font-medium">Suggested Replacement</span>
                        <p className="text-xs text-zinc-300 mt-1">{finding.suggested_replacement}</p>
                      </div>
                      <button
                        onClick={() => handleApplyRevision(finding)}
                        className="shrink-0 text-[11px] bg-emerald-600 hover:bg-emerald-500 text-white px-2.5 py-1 rounded-md transition-colors"
                      >
                        Apply
                      </button>
                    </div>
                  )}

                  {/* Dismiss */}
                  {!isApplied && (
                    <button
                      onClick={() => handleDismiss(finding.id)}
                      className="text-[11px] text-zinc-500 hover:text-zinc-300 transition-colors flex items-center gap-1"
                    >
                      <X className="w-3 h-3" /> Dismiss this finding
                    </button>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Decision Bar */}
      {findings.length > 0 && (
        <div className="mt-4 card border-zinc-700/70">
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <input
                type="text"
                value={reviewerName}
                onChange={(e) => setReviewerName(e.target.value)}
                placeholder="Reviewer name"
                className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-emerald-500/50"
              />
              <input
                type="text"
                value={reviewerNotes}
                onChange={(e) => setReviewerNotes(e.target.value)}
                placeholder="Notes (required to override critical findings)"
                className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-emerald-500/50"
              />
            </div>

            {auditResult?.overall_status === 'review_required' && (
              <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 rounded-lg p-2.5">
                <input
                  type="checkbox"
                  id="acknowledge"
                  checked={acknowledgeIncomplete}
                  onChange={(e) => setAcknowledgeIncomplete(e.target.checked)}
                  className="rounded border-zinc-700 bg-zinc-800 text-amber-500 focus:ring-amber-500/50"
                />
                <label htmlFor="acknowledge" className="text-xs text-amber-300 cursor-pointer">
                  I acknowledge that AI contextual analysis was unavailable and confirm I have manually reviewed this content and its claims.
                </label>
              </div>
            )}

            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => handleDecision('changes_requested')}
                disabled={isSubmittingDecision}
                className="btn-ghost text-sm"
              >
                Request Changes
              </button>
              <button
                onClick={() => handleDecision('rejected')}
                disabled={isSubmittingDecision}
                className="btn-danger text-sm"
              >
                Reject
              </button>
              <button
                onClick={() => handleDecision('approved')}
                disabled={isSubmittingDecision}
                className="btn-primary text-sm flex items-center gap-1.5"
              >
                {isSubmittingDecision ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-4 h-4" />
                )}
                Approve for Publication
              </button>
            </div>
            {decisionError && (
              <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                {decisionError}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Clean content — direct approve */}
      {findings.length === 0 && auditResult && auditResult.overall_status === 'clean' && (
        <div className="mt-4 card border-emerald-500/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              <span className="text-sm font-medium text-emerald-400">Content is compliant — ready for approval</span>
            </div>
            <button
              onClick={() => handleDecision('approved')}
              disabled={isSubmittingDecision}
              className="btn-primary text-sm"
            >
              Approve
            </button>
          </div>
        </div>
      )}

      {/* Review Required — incomplete audit */}
      {auditResult && auditResult.overall_status === 'review_required' && (
        <div className="mt-4 card border-amber-500/20 bg-amber-500/5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5" />
              <div>
                <span className="text-sm font-medium text-amber-400">Audit Incomplete — Manual Review Required</span>
                <p className="text-xs text-zinc-400 mt-1">
                  AI contextual analysis could not complete. Deterministic checks passed, but the content has not been fully verified.
                  Manual review is required before approving for publication.
                </p>
              </div>
            </div>
            <button
              onClick={async () => {
                setIsReauditing(true)
                onAuditStart()
                try {
                  const result = await runAudit(text)
                  onAuditComplete(result)
                } catch (error) {
                  console.error('Retry audit failed:', error)
                } finally {
                  setIsReauditing(false)
                }
              }}
              disabled={isReauditing}
              className="shrink-0 text-sm bg-amber-600 hover:bg-amber-500 text-white px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
            >
              {isReauditing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              Retry Audit
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
