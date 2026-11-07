"""Pydantic V2 domain schemas for API validation and serialization."""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from enum import Enum


class Severity(str, Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueCategory(str, Enum):
    """Types of brand governance issues."""
    TERMINOLOGY = "terminology"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    TONE_VOICE = "tone_voice"
    PROHIBITED_PHRASE = "prohibited_phrase"
    COMPLIANCE = "compliance"


class EvidenceStatus(str, Enum):
    """Verification status of evidence against guidelines."""
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    NOT_FOUND = "not_found"


class OverallStatus(str, Enum):
    """Overall audit status."""
    FLAGGED = "flagged"
    CLEAN = "clean"
    NEEDS_ESCALATION = "needs_escalation"
    REVIEW_REQUIRED = "review_required"  # AI checks could not complete; result is inconclusive


class DecisionType(str, Enum):
    """Human reviewer decision types."""
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class DocumentStatus(str, Enum):
    """Document processing status."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentCategory(str, Enum):
    """Document categories."""
    BRAND_GUIDELINES = "brand_guidelines"
    PRODUCT_SPECS = "product_specs"
    LEGAL_COMPLIANCE = "legal_compliance"
    MARKETING_TEMPLATES = "marketing_templates"


# === Guideline Schemas ===

class GuidelineItem(BaseModel):
    """A brand guideline rule."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex)
    title: str
    category: str
    rule_text: str
    source_document: str
    version: str = "1.0"
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class GuidelineCreate(BaseModel):
    """Request to create a new guideline."""
    title: str
    category: str
    rule_text: str
    source_document: str = "User Added"
    version: str = "1.0"
    tags: List[str] = Field(default_factory=list)


# === Finding Schemas ===

class AuditFinding(BaseModel):
    """A single audit finding with evidence linkage."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex)
    category: IssueCategory
    severity: Severity
    flagged_text: str
    explanation: str
    evidence_quote: Optional[str] = None
    evidence_source: Optional[str] = None
    evidence_status: EvidenceStatus = EvidenceStatus.NOT_FOUND
    suggested_replacement: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    dismissed: bool = False
    dismissal_reason: Optional[str] = None


class FindingDismiss(BaseModel):
    """Request to dismiss a finding."""
    reason: Optional[str] = None


# === Audit Schemas ===

class AuditRequest(BaseModel):
    """Request to audit marketing content."""
    text: str = Field(..., min_length=1, description="Content to audit")
    workspace_id: Optional[str] = "default"


class AuditResponse(BaseModel):
    """Complete audit result."""
    model_config = ConfigDict(from_attributes=True)

    submission_id: str
    original_text: str
    overall_status: OverallStatus
    summary: str
    findings: List[AuditFinding]
    execution_time_ms: float
    # Audit completeness metadata
    llm_checked: bool = False                    # True when Gemini analysis ran successfully
    llm_provider: Optional[str] = None
    gemini_status: str = "skipped"               # success, failed, skipped
    openrouter_status: str = "skipped"           # success, failed, skipped
    llm_error: Optional[str] = None
    checks_completed: List[str] = Field(default_factory=list)  # Checks that ran
    checks_skipped: List[str] = Field(default_factory=list)    # Checks that were skipped


# === Decision Schemas ===

class DecisionRequest(BaseModel):
    """Human reviewer decision on audited content."""
    submission_id: str
    decision: DecisionType
    reviewer_name: str = "Guest Reviewer"
    reviewer_notes: Optional[str] = None
    resolved_findings: List[str] = Field(default_factory=list)
    final_text: str


class DecisionResponse(BaseModel):
    """Recorded decision confirmation."""
    model_config = ConfigDict(from_attributes=True)

    submission_id: str
    decision: str
    timestamp: datetime
    reviewer_name: str
    reviewer_notes: Optional[str] = None


# === History Schemas ===

class SubmissionHistory(BaseModel):
    """Summary for history listing."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_text: str
    overall_status: str
    summary: Optional[str] = None
    created_at: datetime
    decision: Optional[DecisionResponse] = None


# === Evidence Schemas (Phase 4) ===

class EvidenceResult(BaseModel):
    """
    A single ranked evidence result with full provenance.

    source_type distinguishes policy evidence (from brand guidelines, what
    the brand *requires*) from factual evidence (from document chunks, what
    the product *actually does/is*).

    A guideline recommending an SLA phrase does NOT constitute proof that
    the product meets that SLA — never treat policy evidence as factual.
    """
    source_type: str          # "policy" (guideline) | "factual" (document chunk)
    similarity_score: float
    text: str
    title: str
    source_id: str
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    guideline_id: Optional[str] = None
    category: str = ""
    version: str = "1.0"
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    excerpt: str = ""
    source_document: str = ""
    low_confidence: bool = False


# === Document Management Schemas (Phase 5) ===

class DocumentResponse(BaseModel):
    """Document detail response — never exposes absolute storage paths."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    filename: str
    file_type: str
    file_size: int
    category: str
    status: str
    error_message: Optional[str] = None
    page_count: Optional[int] = None
    version: str = "1.0"
    tags: List[str] = Field(default_factory=list)
    uploaded_by: str = "system"
    created_at: datetime
    updated_at: datetime
    chunk_count: int = 0


class DocumentListResponse(BaseModel):
    """Paginated document listing."""
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentUpdate(BaseModel):
    """Request to update document metadata."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[DocumentCategory] = None
    tags: Optional[List[str]] = Field(None, max_length=20, description="Max 20 tags")


class DocumentReprocessResponse(BaseModel):
    """Result of a document reprocessing request."""
    id: str
    status: str
    chunk_count: int
    message: str


class DocumentDeleteResponse(BaseModel):
    """Result of a document soft-delete request."""
    id: str
    status: str
    message: str


class DocumentRestoreResponse(BaseModel):
    """Result of a document restore request."""
    id: str
    status: str
    message: str


# === Health Schemas ===

class HealthResponse(BaseModel):
    """System health check."""
    status: str = "ok"
    model: str
    guideline_count: int
    fallback_mode: bool = False
