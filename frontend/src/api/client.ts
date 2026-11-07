/**
 * Axios API client for BrandSentinel AI backend.
 */
import axios from 'axios'
import type {
  AuditResponse,
  DecisionRequest,
  DecisionResponse,
  GuidelineItem,
  HealthResponse,
  SampleDraft,
  SubmissionHistory,
} from '../types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Health
export const getHealth = () =>
  api.get<HealthResponse>('/api/health').then((r) => r.data)

// Guidelines
export const getGuidelines = () =>
  api.get<GuidelineItem[]>('/api/guidelines').then((r) => r.data)

export const addGuideline = (guideline: Partial<GuidelineItem>) =>
  api.post<GuidelineItem>('/api/guidelines', guideline).then((r) => r.data)

// Samples
export const getSamples = () =>
  api.get<SampleDraft[]>('/api/samples').then((r) => r.data)

// Audit
export const runAudit = (text: string, workspace_id = 'default') =>
  api.post<AuditResponse>('/api/audit', { text, workspace_id }).then((r) => r.data)

// Decision
export const submitDecision = (request: DecisionRequest) =>
  api.post<DecisionResponse>('/api/decision', request).then((r) => r.data)

// History
export const getHistory = () =>
  api.get<SubmissionHistory[]>('/api/history').then((r) => r.data)

// Documents (Phase 6)
export const getDocuments = (params?: {
  page?: number
  page_size?: number
  category?: string
  status?: string
  file_type?: string
  search?: string
  include_deleted?: boolean
}) => {
  const query = new URLSearchParams()
  if (params?.page) query.set('page', params.page.toString())
  if (params?.page_size) query.set('page_size', params.page_size.toString())
  if (params?.category) query.set('category', params.category)
  if (params?.status) query.set('status', params.status)
  if (params?.file_type) query.set('file_type', params.file_type)
  if (params?.search) query.set('search', params.search)
  if (params?.include_deleted) query.set('include_deleted', 'true')

  const url = `/api/documents${query.toString() ? `?${query.toString()}` : ''}`
  return api.get<import('../types').DocumentListResponse>(url).then((r) => r.data)
}

export const getDocument = (id: string) =>
  api.get<import('../types').Document>(`/api/documents/${id}`).then((r) => r.data)

export const uploadDocument = (file: File, metadata?: {
  title?: string
  category?: string
  tags?: string
}) => {
  const formData = new FormData()
  formData.append('file', file)
  if (metadata?.title) formData.append('title', metadata.title)
  if (metadata?.category) formData.append('category', metadata.category)
  if (metadata?.tags) formData.append('tags', metadata.tags)

  return api.post<import('../types').Document>('/api/documents', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export const updateDocument = (id: string, update: import('../types').DocumentUpdate) =>
  api.patch<import('../types').Document>(`/api/documents/${id}`, update).then((r) => r.data)

export const reprocessDocument = (id: string) =>
  api.post(`/api/documents/${id}/reprocess`).then((r) => r.data)

export const deleteDocument = (id: string) =>
  api.delete(`/api/documents/${id}`).then((r) => r.data)

export const restoreDocument = (id: string) =>
  api.post(`/api/documents/${id}/restore`).then((r) => r.data)
