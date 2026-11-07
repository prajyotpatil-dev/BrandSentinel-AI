/**
 * Document management types matching backend Phase 5 schemas.
 */

export type DocumentStatus = 'uploading' | 'processing' | 'indexed' | 'failed'
export type DocumentCategory = 'brand_guidelines' | 'product_specs' | 'legal_compliance' | 'marketing_templates'

export interface Document {
  id: string
  title: string
  filename: string
  file_type: string
  file_size: number
  category: string
  status: DocumentStatus
  error_message?: string
  page_count?: number
  version: string
  tags: string[]
  uploaded_by: string
  created_at: string
  updated_at: string
  chunk_count: number
}

export interface DocumentListResponse {
  items: Document[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface DocumentUpdate {
  title?: string
  category?: DocumentCategory
  tags?: string[]
}

export interface DocumentReprocessResponse {
  id: string
  status: string
  chunk_count: number
  message: string
}

export interface DocumentDeleteResponse {
  id: string
  status: string
  message: string
}

export interface DocumentRestoreResponse {
  id: string
  status: string
  message: string
}
