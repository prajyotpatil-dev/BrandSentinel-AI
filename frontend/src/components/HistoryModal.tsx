import { X, History, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react'
import type { SubmissionHistory } from '../types'

interface Props {
  history: SubmissionHistory[]
  onClose: () => void
}

const STATUS_ICON: Record<string, JSX.Element> = {
  approved: <CheckCircle2 className="w-4 h-4 text-emerald-500" />,
  rejected: <XCircle className="w-4 h-4 text-red-500" />,
  flagged: <AlertTriangle className="w-4 h-4 text-orange-500" />,
  needs_escalation: <AlertTriangle className="w-4 h-4 text-red-500" />,
  clean: <CheckCircle2 className="w-4 h-4 text-emerald-500" />,
}

export function HistoryModal({ history, onClose }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-emerald-500" />
            <h2 className="text-base font-semibold">Audit History</h2>
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {history.length === 0 ? (
            <div className="text-center py-12">
              <History className="w-10 h-10 text-zinc-700 mx-auto mb-3" />
              <p className="text-sm text-zinc-500">No audit history yet.</p>
            </div>
          ) : (
            history.map((item) => (
              <div key={item.id} className="card">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">
                    {STATUS_ICON[item.overall_status] ?? <AlertTriangle className="w-4 h-4 text-zinc-500" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-zinc-500 capitalize font-medium">
                        {item.overall_status.replace('_', ' ')}
                      </span>
                      <span className="text-[10px] text-zinc-600">
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-400 mt-1 line-clamp-2">{item.original_text}</p>
                    {item.summary && (
                      <p className="text-[11px] text-zinc-500 mt-1">{item.summary}</p>
                    )}
                    {item.decision && (
                      <div className="mt-2 text-[10px] text-zinc-500 bg-zinc-800/50 rounded px-2 py-1">
                        Decision: <strong className="text-zinc-300">{item.decision.decision}</strong>
                        {' by '}{item.decision.reviewer_name}
                        {item.decision.reviewer_notes && ` — "${item.decision.reviewer_notes}"`}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
