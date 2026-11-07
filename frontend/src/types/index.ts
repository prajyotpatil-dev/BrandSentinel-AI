/**
 * TypeScript domain types matching backend Pydantic schemas.
 */

export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type IssueCategory =
  | 'terminology'
  | 'unsupported_claim'
  | 'tone_voice'
  | 'prohibited_phrase'
  | 'compliance'
export type EvidenceStatus = 'supported' | 'contradicted' | 'not_found'
export type OverallStatus = 'flagged' | 'clean' | 'needs_escalation' | 'review_required'
export type DecisionType = 'approved' | 'rejected' | 'changes_requested'
export type SubmissionStatus =
  | 'pending'
  | 'auditing'
  | 'flagged'
  | 'clean'
  | 'approved'
  | 'rejected'

export interface GuidelineItem {
  id: string
  title: string
  category: string
  rule_text: string
  source_document: string
  version: string
  tags: string[]
  created_at?: string
  updated_at?: string
}

export interface AuditFinding {
  id: string
  category: IssueCategory
  severity: Severity
  flagged_text: string
  explanation: string
  evidence_quote?: string
  evidence_source?: string
  evidence_status: EvidenceStatus
  suggested_replacement?: string
  confidence_score: number
  dismissed: boolean
  dismissal_reason?: string
}

export interface AuditResponse {
  submission_id: string
  original_text: string
  overall_status: OverallStatus
  summary: string
  findings: AuditFinding[]
  execution_time_ms: number
  llm_checked: boolean
  llm_provider?: string | null
  gemini_status?: string
  openrouter_status?: string
  llm_error?: string | null
  checks_completed: string[]
  checks_skipped: string[]
}

export interface DecisionRequest {
  submission_id: string
  decision: DecisionType
  reviewer_name: string
  reviewer_notes?: string
  resolved_findings: string[]
  final_text: string
}

export interface DecisionResponse {
  submission_id: string
  decision: string
  timestamp: string
  reviewer_name: string
  reviewer_notes?: string
}

export interface SampleDraft {
  id: string
  title: string
  description: string
  text: string
}

export interface HealthResponse {
  status: string
  model: string
  guideline_count: number
  fallback_mode: boolean
}

export interface SubmissionHistory {
  id: string
  original_text: string
  overall_status: string
  summary?: string
  created_at: string
  decision?: DecisionResponse
}

// Document management types (Phase 6)
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
  deleted_at?: string | null
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
