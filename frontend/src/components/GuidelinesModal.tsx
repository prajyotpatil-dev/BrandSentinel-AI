import { useState } from 'react'
import { X, Plus, BookOpen, Tag, FileText } from 'lucide-react'
import { addGuideline } from '../api/client'
import type { GuidelineItem } from '../types'

interface Props {
  guidelines: GuidelineItem[]
  onClose: () => void
  onRefresh: () => void
}

const CATEGORY_COLORS: Record<string, string> = {
  terminology: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  unsupported_claim: 'bg-red-500/10 text-red-400 border-red-500/20',
  tone_voice: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  prohibited_phrase: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  compliance: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
}

export function GuidelinesModal({ guidelines, onClose, onRefresh }: Props) {
  const [showAdd, setShowAdd] = useState(false)
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('terminology')
  const [ruleText, setRuleText] = useState('')
  const [isAdding, setIsAdding] = useState(false)

  const handleAdd = async () => {
    if (!title.trim() || !ruleText.trim()) return
    setIsAdding(true)
    try {
      await addGuideline({
        title,
        category,
        rule_text: ruleText,
        source_document: 'User Added',
      })
      setTitle('')
      setRuleText('')
      setShowAdd(false)
      onRefresh()
    } catch { /* silent */ }
    setIsAdding(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-emerald-500" />
            <h2 className="text-base font-semibold">Brand Guidelines Hub</h2>
            <span className="text-xs text-zinc-500 bg-zinc-800 rounded px-2 py-0.5">
              {guidelines.length} rules
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowAdd(!showAdd)}
              className="btn-ghost flex items-center gap-1 text-emerald-400"
            >
              <Plus className="w-3.5 h-3.5" /> Add Rule
            </button>
            <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 p-1">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Add Form */}
        {showAdd && (
          <div className="px-5 py-4 border-b border-zinc-800 bg-zinc-800/30">
            <div className="grid gap-3">
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Rule title"
                className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-1 focus:ring-emerald-500/50"
              />
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-1 focus:ring-emerald-500/50"
              >
                <option value="terminology">Terminology</option>
                <option value="unsupported_claim">Unsupported Claim</option>
                <option value="tone_voice">Tone & Voice</option>
                <option value="prohibited_phrase">Prohibited Phrase</option>
                <option value="compliance">Compliance</option>
              </select>
              <textarea
                value={ruleText}
                onChange={(e) => setRuleText(e.target.value)}
                placeholder="Rule text — describe the policy in detail"
                rows={3}
                className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 resize-none focus:outline-none focus:ring-1 focus:ring-emerald-500/50"
              />
              <button onClick={handleAdd} disabled={isAdding} className="btn-primary text-sm w-fit">
                {isAdding ? 'Adding...' : 'Add Guideline'}
              </button>
            </div>
          </div>
        )}

        {/* Guidelines List */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {guidelines.map((g) => (
            <div key={g.id} className="card">
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-sm font-medium text-zinc-200">{g.title}</h3>
                <span className={`text-[10px] font-medium border rounded-full px-2 py-0.5 shrink-0 ${CATEGORY_COLORS[g.category] ?? 'bg-zinc-800 text-zinc-400 border-zinc-700'}`}>
                  {g.category.replace('_', ' ')}
                </span>
              </div>
              <p className="text-xs text-zinc-400 mt-2 leading-relaxed">{g.rule_text}</p>
              <div className="flex items-center gap-3 mt-2 text-[10px] text-zinc-600">
                <span className="flex items-center gap-1">
                  <FileText className="w-3 h-3" /> {g.source_document}
                </span>
                {g.tags.length > 0 && (
                  <span className="flex items-center gap-1">
                    <Tag className="w-3 h-3" /> {g.tags.join(', ')}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
