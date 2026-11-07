import { useState, useEffect } from 'react'
import { Upload, Search, FileText, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import { getDocuments } from '../api/client'
import type { Document } from '../types'
import { DocumentUpload } from '../components/DocumentUpload'
import { DocumentList } from '../components/DocumentList'
import { DocumentDetails } from '../components/DocumentDetails'

export function KnowledgeHub() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [showDeleted, setShowDeleted] = useState(false)

  // Selected document for details view
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)

  // Upload state
  const [showUpload, setShowUpload] = useState(false)

  // Global stats (all documents, not just current page)
  const [globalStats, setGlobalStats] = useState({
    total: 0,
    indexed: 0,
    processing: 0,
    failed: 0,
    deleted: 0,
  })

  const loadGlobalStats = async () => {
    try {
      // Fetch all documents to get accurate counts
      const [activeResponse, deletedResponse] = await Promise.all([
        getDocuments({ page: 1, page_size: 1000, include_deleted: false }),
        getDocuments({ page: 1, page_size: 1000, include_deleted: true }),
      ])

      const activeTotal = activeResponse.total
      const deletedTotal = deletedResponse.total - activeTotal

      // Get status counts from active documents
      const indexed = activeResponse.items.filter(d => d.status === 'indexed').length
      const processing = activeResponse.items.filter(d => d.status === 'processing').length
      const failed = activeResponse.items.filter(d => d.status === 'failed').length

      setGlobalStats({
        total: activeTotal,
        indexed,
        processing,
        failed,
        deleted: deletedTotal,
      })
    } catch (err) {
      console.error('Failed to load global stats:', err)
    }
  }

  const loadDocuments = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await getDocuments({
        page,
        page_size: pageSize,
        search: search || undefined,
        category: categoryFilter || undefined,
        status: statusFilter || undefined,
        include_deleted: showDeleted,
      })
      setDocuments(response.items)
      setTotal(response.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadGlobalStats()
  }, [])

  useEffect(() => {
    loadDocuments()
  }, [page, search, categoryFilter, statusFilter, showDeleted])

  const handleUploadComplete = () => {
    setShowUpload(false)
    loadDocuments()
    loadGlobalStats()
  }

  const handleDocumentUpdate = () => {
    loadDocuments()
    loadGlobalStats()
    setSelectedDocId(null)
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <div className="border-b border-zinc-800 bg-zinc-900/50">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-zinc-100">Knowledge Hub</h1>
              <p className="text-sm text-zinc-400 mt-1">
                Manage brand documents, guidelines, and evidence sources
              </p>
            </div>
            <button
              onClick={() => setShowUpload(true)}
              className="btn-primary flex items-center gap-2"
            >
              <Upload className="w-4 h-4" />
              Upload Document
            </button>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="card">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-500/10 rounded-lg">
                  <FileText className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-zinc-100">{globalStats.total}</div>
                  <div className="text-xs text-zinc-400">Total Documents</div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-500/10 rounded-lg">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-zinc-100">{globalStats.indexed}</div>
                  <div className="text-xs text-zinc-400">Indexed</div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <Loader2 className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-zinc-100">{globalStats.processing}</div>
                  <div className="text-xs text-zinc-400">Processing</div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-500/10 rounded-lg">
                  <AlertCircle className="w-5 h-5 text-red-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-zinc-100">{globalStats.failed}</div>
                  <div className="text-xs text-zinc-400">Failed</div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-zinc-500/10 rounded-lg">
                  <FileText className="w-5 h-5 text-zinc-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-zinc-100">{globalStats.deleted}</div>
                  <div className="text-xs text-zinc-400">Deleted</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-6">
        {selectedDocId ? (
          <DocumentDetails
            documentId={selectedDocId}
            onClose={() => setSelectedDocId(null)}
            onUpdate={handleDocumentUpdate}
          />
        ) : (
          <>
            {/* Search and Filters */}
            <div className="card mb-6">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                  <input
                    type="text"
                    placeholder="Search by title or filename..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg pl-10 pr-4 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="">All Categories</option>
                  <option value="brand_guidelines">Brand Guidelines</option>
                  <option value="product_specs">Product Specs</option>
                  <option value="legal_compliance">Legal Compliance</option>
                  <option value="marketing_templates">Marketing Templates</option>
                </select>

                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="">All Status</option>
                  <option value="indexed">Indexed</option>
                  <option value="processing">Processing</option>
                  <option value="failed">Failed</option>
                </select>

                <label className="flex items-center gap-2 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-sm text-zinc-100 cursor-pointer hover:bg-zinc-750 transition-colors">
                  <input
                    type="checkbox"
                    checked={showDeleted}
                    onChange={(e) => setShowDeleted(e.target.checked)}
                    className="w-4 h-4 rounded border-zinc-600 text-emerald-600 focus:ring-2 focus:ring-emerald-500"
                  />
                  <span>Show Deleted</span>
                </label>
              </div>
            </div>

            {/* Document List */}
            {error ? (
              <div className="card">
                <div className="flex items-center gap-3 text-red-400">
                  <AlertCircle className="w-5 h-5" />
                  <span>{error}</span>
                </div>
              </div>
            ) : loading ? (
              <div className="card">
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
                </div>
              </div>
            ) : documents.length === 0 ? (
              <div className="card">
                <div className="text-center py-12">
                  <FileText className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-zinc-300 mb-2">No documents found</h3>
                  <p className="text-sm text-zinc-500 mb-4">
                    {search || categoryFilter || statusFilter
                      ? 'Try adjusting your filters'
                      : 'Upload your first document to get started'}
                  </p>
                  {!search && !categoryFilter && !statusFilter && (
                    <button onClick={() => setShowUpload(true)} className="btn-primary">
                      <Upload className="w-4 h-4 inline mr-2" />
                      Upload Document
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <DocumentList
                documents={documents}
                onSelect={setSelectedDocId}
                page={page}
                totalPages={Math.ceil(total / pageSize)}
                onPageChange={setPage}
              />
            )}
          </>
        )}
      </div>

      {/* Upload Modal */}
      {showUpload && (
        <DocumentUpload
          onClose={() => setShowUpload(false)}
          onComplete={handleUploadComplete}
        />
      )}
    </div>
  )
}
