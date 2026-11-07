import { useState, useEffect } from 'react'
import { X, Save, RefreshCw, Trash2, RotateCcw, AlertCircle, CheckCircle, Loader2, Activity } from 'lucide-react'
import { getDocument, updateDocument, reprocessDocument, deleteDocument, restoreDocument } from '../api/client'
import type { Document, DocumentUpdate } from '../types'

interface DocumentDetailsProps {
  documentId: string
  onClose: () => void
  onUpdate: () => void
}

export function DocumentDetails({ documentId, onClose, onUpdate }: DocumentDetailsProps) {
  const [document, setDocument] = useState<Document | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Edit state
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const [editCategory, setEditCategory] = useState('')
  const [editTags, setEditTags] = useState('')
  const [saving, setSaving] = useState(false)

  // Action state
  const [reprocessing, setReprocessing] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [restoring, setRestoring] = useState(false)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  const loadDocument = async () => {
    try {
      setLoading(true)
      setError(null)
      const doc = await getDocument(documentId)
      setDocument(doc)
      setEditTitle(doc.title)
      setEditCategory(doc.category)
      setEditTags(doc.tags.join(', '))
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load document')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDocument()
  }, [documentId])

  const handleSave = async () => {
    if (!document) return

    try {
      setSaving(true)
      setError(null)

      const update: DocumentUpdate = {}
      if (editTitle !== document.title) update.title = editTitle
      if (editCategory !== document.category) update.category = editCategory as any

      const newTags = editTags.split(',').map(t => t.trim()).filter(Boolean)
      const tagsChanged = JSON.stringify(newTags.sort()) !== JSON.stringify([...document.tags].sort())
      if (tagsChanged) update.tags = newTags

      if (Object.keys(update).length === 0) {
        setIsEditing(false)
        return
      }

      await updateDocument(documentId, update)
      setActionSuccess('Document updated successfully')
      setTimeout(() => setActionSuccess(null), 3000)
      setIsEditing(false)
      loadDocument()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to update document')
    } finally {
      setSaving(false)
    }
  }

  const handleReprocess = async () => {
    try {
      setReprocessing(true)
      setError(null)
      await reprocessDocument(documentId)
      setActionSuccess('Document reprocessing started')
      setTimeout(() => {
        setActionSuccess(null)
        loadDocument()
      }, 2000)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to reprocess document')
    } finally {
      setReprocessing(false)
    }
  }

  const handleDelete = async () => {
    try {
      setDeleting(true)
      setError(null)
      await deleteDocument(documentId)
      setActionSuccess('Document deleted successfully')
      setTimeout(() => {
        onUpdate()
      }, 1500)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to delete document')
      setDeleting(false)
      setShowDeleteConfirm(false)
    }
  }

  const handleRestore = async () => {
    try {
      setRestoring(true)
      setError(null)
      await restoreDocument(documentId)
      setActionSuccess('Document restored successfully')
      setTimeout(() => {
        onUpdate()
      }, 1500)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to restore document')
      setRestoring(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
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
      product_specs: 'Product Specifications',
      legal_compliance: 'Legal Compliance',
      marketing_templates: 'Marketing Templates',
    }
    return labels[category] || category
  }

  if (loading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
        </div>
      </div>
    )
  }

  if (error && !document) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-zinc-100">Document Details</h2>
          <button onClick={onClose} className="btn-ghost">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="card">
          <div className="flex items-center gap-3 text-red-400">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        </div>
      </div>
    )
  }

  if (!document) return null

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-zinc-100">Document Details</h2>
          <p className="text-sm text-zinc-400 mt-1">View and manage document information</p>
        </div>
        <button onClick={onClose} className="btn-ghost">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Success Message */}
      {actionSuccess && (
        <div className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/30 rounded-lg text-green-400 text-sm">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Error Message */}
      {error && document && (
        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Basic Information */}
          <div className="card space-y-4">
            <h3 className="text-lg font-semibold text-zinc-100">Basic Information</h3>

            {isEditing ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">Title</label>
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    maxLength={255}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">Category</label>
                  <select
                    value={editCategory}
                    onChange={(e) => setEditCategory(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="brand_guidelines">Brand Guidelines</option>
                    <option value="product_specs">Product Specifications</option>
                    <option value="legal_compliance">Legal Compliance</option>
                    <option value="marketing_templates">Marketing Templates</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">Tags (comma-separated)</label>
                  <input
                    type="text"
                    value={editTags}
                    onChange={(e) => setEditTags(e.target.value)}
                    placeholder="e.g., branding, 2024, official"
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                  <p className="text-xs text-zinc-500 mt-1">Maximum 20 tags, 50 characters each</p>
                </div>

                <div className="flex items-center gap-3 pt-2">
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="btn-primary flex items-center gap-2"
                  >
                    {saving ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4" />
                        Save Changes
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => {
                      setIsEditing(false)
                      setEditTitle(document.title)
                      setEditCategory(document.category)
                      setEditTags(document.tags.join(', '))
                    }}
                    className="btn-ghost"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <div className="text-xs text-zinc-500 mb-1">Title</div>
                  <div className="text-sm text-zinc-200">{document.title}</div>
                </div>

                <div>
                  <div className="text-xs text-zinc-500 mb-1">Original Filename</div>
                  <div className="text-sm text-zinc-200">{document.filename}</div>
                </div>

                <div>
                  <div className="text-xs text-zinc-500 mb-1">Category</div>
                  <div className="text-sm text-zinc-200">{getCategoryLabel(document.category)}</div>
                </div>

                {document.tags.length > 0 && (
                  <div>
                    <div className="text-xs text-zinc-500 mb-2">Tags</div>
                    <div className="flex flex-wrap gap-2">
                      {document.tags.map((tag, idx) => (
                        <span
                          key={idx}
                          className="bg-zinc-800 text-zinc-300 text-xs px-2 py-1 rounded"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="pt-2">
                  <button
                    onClick={() => setIsEditing(true)}
                    className="btn-primary"
                  >
                    Edit Metadata
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Processing Status */}
          {document.error_message && (
            <div className="card">
              <h3 className="text-lg font-semibold text-zinc-100 mb-4">Processing Error</h3>
              <div className="flex items-start gap-3 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-red-400">{document.error_message}</div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="card">
            <h3 className="text-lg font-semibold text-zinc-100 mb-4">Actions</h3>
            <div className="flex flex-wrap gap-3">
              {!document.deleted_at ? (
                <>
                  <button
                    onClick={handleReprocess}
                    disabled={reprocessing || document.status === 'processing'}
                    className="btn-primary flex items-center gap-2"
                  >
                    {reprocessing ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Reprocessing...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="w-4 h-4" />
                        Reprocess Document
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => setShowDeleteConfirm(true)}
                    disabled={deleting}
                    className="btn-danger flex items-center gap-2"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete Document
                  </button>
                </>
              ) : (
                <button
                  onClick={handleRestore}
                  disabled={restoring}
                  className="btn-primary flex items-center gap-2"
                >
                  {restoring ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Restoring...
                    </>
                  ) : (
                    <>
                      <RotateCcw className="w-4 h-4" />
                      Restore Document
                    </>
                  )}
                </button>
              )}
            </div>

            {!document.deleted_at ? (
              <p className="text-xs text-zinc-500 mt-3">
                Reprocessing will re-extract text and regenerate chunks. This is useful if processing failed or you want to update the index.
              </p>
            ) : (
              <p className="text-xs text-zinc-500 mt-3">
                This document has been deleted. Restoring it will make it visible in the Knowledge Hub and available for evidence retrieval again.
              </p>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Status */}
          <div className="card space-y-3">
            <h3 className="text-sm font-semibold text-zinc-300">Status</h3>
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-zinc-500" />
              {getStatusBadge(document.status)}
            </div>
          </div>

          {/* Document Info */}
          <div className="card space-y-3">
            <h3 className="text-sm font-semibold text-zinc-300">Document Info</h3>

            <div>
              <div className="text-xs text-zinc-500 mb-1">File Type</div>
              <div className="text-sm text-zinc-200">{document.file_type}</div>
            </div>

            <div>
              <div className="text-xs text-zinc-500 mb-1">File Size</div>
              <div className="text-sm text-zinc-200">{formatFileSize(document.file_size)}</div>
            </div>

            {document.page_count && (
              <div>
                <div className="text-xs text-zinc-500 mb-1">Pages</div>
                <div className="text-sm text-zinc-200">{document.page_count}</div>
              </div>
            )}

            <div>
              <div className="text-xs text-zinc-500 mb-1">Chunks</div>
              <div className="text-sm text-zinc-200">{document.chunk_count}</div>
            </div>

            <div>
              <div className="text-xs text-zinc-500 mb-1">Version</div>
              <div className="text-sm text-zinc-200">{document.version}</div>
            </div>
          </div>

          {/* Timestamps */}
          <div className="card space-y-3">
            <h3 className="text-sm font-semibold text-zinc-300">Timestamps</h3>

            <div>
              <div className="text-xs text-zinc-500 mb-1">Uploaded</div>
              <div className="text-sm text-zinc-200">{formatDate(document.created_at)}</div>
            </div>

            <div>
              <div className="text-xs text-zinc-500 mb-1">Last Updated</div>
              <div className="text-sm text-zinc-200">{formatDate(document.updated_at)}</div>
            </div>

            <div>
              <div className="text-xs text-zinc-500 mb-1">Uploaded By</div>
              <div className="text-sm text-zinc-200">{document.uploaded_by}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <>
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50" onClick={() => setShowDeleteConfirm(false)} />
          <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md z-50 p-4">
            <div className="bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl">
              <div className="p-6 space-y-4">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-red-500/10 rounded-lg">
                    <AlertCircle className="w-6 h-6 text-red-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-zinc-100">Delete Document</h3>
                    <p className="text-sm text-zinc-400 mt-1">This action cannot be undone</p>
                  </div>
                </div>

                <p className="text-sm text-zinc-300">
                  This will soft-delete the document. It will be hidden from listings and excluded from future evidence retrieval. The file will be preserved and can be restored later if needed.
                </p>

                <div className="flex items-center gap-3 pt-2">
                  <button
                    onClick={handleDelete}
                    disabled={deleting}
                    className="flex-1 bg-red-600 hover:bg-red-500 text-white font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {deleting ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Deleting...
                      </>
                    ) : (
                      <>
                        <Trash2 className="w-4 h-4" />
                        Delete
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    disabled={deleting}
                    className="flex-1 btn-ghost"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
