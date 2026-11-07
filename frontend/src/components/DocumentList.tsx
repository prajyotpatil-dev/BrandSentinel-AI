import { FileText, Calendar, Tag, Activity, ChevronRight } from 'lucide-react'
import type { Document } from '../types'

interface DocumentListProps {
  documents: Document[]
  onSelect: (id: string) => void
  page: number
  totalPages: number
  onPageChange: (page: number) => void
}

export function DocumentList({ documents, onSelect, page, totalPages, onPageChange }: DocumentListProps) {
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  const getStatusBadge = (status: Document['status']) => {
    switch (status) {
      case 'indexed':
        return <span className="inline-flex items-center gap-1 bg-green-500/15 text-green-400 border border-green-500/30 text-xs font-semibold px-2 py-0.5 rounded-full">Indexed</span>
      case 'processing':
        return <span className="inline-flex items-center gap-1 bg-blue-500/15 text-blue-400 border border-blue-500/30 text-xs font-semibold px-2 py-0.5 rounded-full">Processing</span>
      case 'uploading':
        return <span className="inline-flex items-center gap-1 bg-amber-500/15 text-amber-400 border border-amber-500/30 text-xs font-semibold px-2 py-0.5 rounded-full">Uploading</span>
      case 'failed':
        return <span className="inline-flex items-center gap-1 bg-red-500/15 text-red-400 border border-red-500/30 text-xs font-semibold px-2 py-0.5 rounded-full">Failed</span>
    }
  }

  const getCategoryLabel = (category: string) => {
    const labels: Record<string, string> = {
      brand_guidelines: 'Brand Guidelines',
      product_specs: 'Product Specs',
      legal_compliance: 'Legal Compliance',
      marketing_templates: 'Marketing Templates',
    }
    return labels[category] || category
  }

  return (
    <div className="space-y-4">
      {/* Document Cards */}
      <div className="space-y-2">
        {documents.map((doc) => (
          <button
            key={doc.id}
            onClick={() => onSelect(doc.id)}
            className="w-full card hover:border-zinc-700 transition-colors text-left group"
          >
            <div className="flex items-start gap-4">
              {/* Icon */}
              <div className="flex-shrink-0 p-3 bg-emerald-500/10 rounded-lg group-hover:bg-emerald-500/15 transition-colors">
                <FileText className="w-5 h-5 text-emerald-400" />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-zinc-100 mb-1 truncate group-hover:text-emerald-400 transition-colors">
                      {doc.title}
                    </h3>
                    <p className="text-xs text-zinc-500 truncate">{doc.filename}</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400 flex-shrink-0" />
                </div>

                {/* Metadata */}
                <div className="flex flex-wrap items-center gap-3 text-xs text-zinc-500">
                  <span className="flex items-center gap-1">
                    <Activity className="w-3 h-3" />
                    {getStatusBadge(doc.status)}
                  </span>
                  <span>•</span>
                  <span>{getCategoryLabel(doc.category)}</span>
                  <span>•</span>
                  <span>{formatFileSize(doc.file_size)}</span>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {formatDate(doc.created_at)}
                  </span>
                  {doc.chunk_count > 0 && (
                    <>
                      <span>•</span>
                      <span>{doc.chunk_count} chunks</span>
                    </>
                  )}
                </div>

                {/* Tags */}
                {doc.tags.length > 0 && (
                  <div className="flex items-center gap-2 mt-2">
                    <Tag className="w-3 h-3 text-zinc-600" />
                    <div className="flex flex-wrap gap-1">
                      {doc.tags.slice(0, 3).map((tag, idx) => (
                        <span
                          key={idx}
                          className="bg-zinc-800 text-zinc-400 text-xs px-2 py-0.5 rounded"
                        >
                          {tag}
                        </span>
                      ))}
                      {doc.tags.length > 3 && (
                        <span className="text-zinc-500 text-xs">+{doc.tags.length - 3}</span>
                      )}
                    </div>
                  </div>
                )}

                {/* Error Message */}
                {doc.error_message && (
                  <div className="mt-2 text-xs text-red-400">
                    {doc.error_message}
                  </div>
                )}
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between card">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page === 1}
            className="btn-ghost disabled:opacity-30"
          >
            Previous
          </button>
          <span className="text-sm text-zinc-400">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="btn-ghost disabled:opacity-30"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
