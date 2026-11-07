import { useState, useRef, DragEvent } from 'react'
import { Upload, X, FileText, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import { uploadDocument } from '../api/client'

interface DocumentUploadProps {
  onClose: () => void
  onComplete: () => void
}

export function DocumentUpload({ onClose, onComplete }: DocumentUploadProps) {
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('brand_guidelines')
  const [tags, setTags] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFile = (file: File): string | null => {
    const maxSize = 10 * 1024 * 1024 // 10 MB
    const allowedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
    ]
    const allowedExtensions = ['.pdf', '.docx', '.txt']

    if (file.size > maxSize) {
      return 'File size exceeds 10 MB limit'
    }

    const extension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
    if (!allowedExtensions.includes(extension)) {
      return 'Only PDF, DOCX, and TXT files are supported'
    }

    if (!allowedTypes.includes(file.type) && file.type !== '') {
      return 'Invalid file type. Only PDF, DOCX, and TXT files are supported'
    }

    return null
  }

  const handleFileSelect = (selectedFile: File) => {
    const validationError = validateFile(selectedFile)
    if (validationError) {
      setError(validationError)
      setFile(null)
      return
    }

    setFile(selectedFile)
    setError(null)
    if (!title) {
      setTitle(selectedFile.name.replace(/\.[^/.]+$/, ''))
    }
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)

    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      handleFileSelect(droppedFile)
    }
  }

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleSubmit = async () => {
    if (!file) {
      setError('Please select a file')
      return
    }

    try {
      setUploading(true)
      setError(null)

      await uploadDocument(file, {
        title: title || undefined,
        category,
        tags: tags || undefined,
      })

      setSuccess(true)
      setTimeout(() => {
        onComplete()
      }, 1500)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Upload failed')
      setUploading(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl z-50 p-4">
        <div className="bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-zinc-800">
            <div>
              <h2 className="text-xl font-bold text-zinc-100">Upload Document</h2>
              <p className="text-sm text-zinc-400 mt-1">
                Add a new document to your knowledge base
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-4">
            {/* File Drop Zone */}
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                isDragging
                  ? 'border-emerald-500 bg-emerald-500/5'
                  : 'border-zinc-700 hover:border-zinc-600'
              }`}
            >
              {file ? (
                <div className="flex items-center justify-between bg-zinc-800 rounded-lg p-4">
                  <div className="flex items-center gap-3">
                    <FileText className="w-8 h-8 text-emerald-400" />
                    <div className="text-left">
                      <div className="text-sm font-medium text-zinc-200">{file.name}</div>
                      <div className="text-xs text-zinc-500">{formatFileSize(file.size)}</div>
                    </div>
                  </div>
                  <button
                    onClick={() => setFile(null)}
                    className="text-zinc-400 hover:text-zinc-200"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              ) : (
                <>
                  <Upload className="w-12 h-12 text-zinc-500 mx-auto mb-4" />
                  <p className="text-sm font-medium text-zinc-300 mb-2">
                    Drag and drop your file here
                  </p>
                  <p className="text-xs text-zinc-500 mb-4">
                    PDF, DOCX, or TXT • Maximum 10 MB
                  </p>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="btn-primary"
                  >
                    Choose File
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                    className="hidden"
                  />
                </>
              )}
            </div>

            {/* Metadata Fields */}
            {file && (
              <>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">
                    Title (optional)
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Document title"
                    maxLength={255}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">
                    Category
                  </label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="brand_guidelines">Brand Guidelines</option>
                    <option value="product_specs">Product Specifications</option>
                    <option value="legal_compliance">Legal Compliance</option>
                    <option value="marketing_templates">Marketing Templates</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">
                    Tags (optional, comma-separated)
                  </label>
                  <input
                    type="text"
                    value={tags}
                    onChange={(e) => setTags(e.target.value)}
                    placeholder="e.g., branding, 2024, official"
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                  <p className="text-xs text-zinc-500 mt-1">Maximum 20 tags, 50 characters each</p>
                </div>
              </>
            )}

            {/* Error Message */}
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Success Message */}
            {success && (
              <div className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/30 rounded-lg text-green-400 text-sm">
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
                <span>Document uploaded successfully!</span>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 p-6 border-t border-zinc-800">
            <button onClick={onClose} className="btn-ghost">
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!file || uploading || success}
              className="btn-primary flex items-center gap-2"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading...
                </>
              ) : success ? (
                <>
                  <CheckCircle className="w-4 h-4" />
                  Uploaded
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Upload
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
