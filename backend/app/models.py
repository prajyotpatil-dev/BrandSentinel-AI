"""SQLAlchemy ORM models for persistent storage."""
from sqlalchemy import Column, String, Text, DateTime, Float, JSON, ForeignKey, Enum as SQLEnum, Integer, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class DocumentModel(Base):
    """Persisted uploaded document for knowledge base."""
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # MIME type: application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, text/plain
    file_size = Column(Integer, nullable=False)  # File size in bytes
    storage_path = Column(String, nullable=False)  # Path to stored file
    title = Column(String, nullable=False)  # Document title (extracted or user-provided)
    category = Column(String, nullable=False)  # brand_guidelines, product_specs, legal_compliance, marketing_templates
    status = Column(String, nullable=False, default="uploading")  # uploading, processing, indexed, failed
    error_message = Column(Text, nullable=True)  # Error details if processing failed
    page_count = Column(Integer, nullable=True)  # Number of pages (PDF) or null
    version = Column(String, default="1.0")
    tags = Column(JSON, default=list)
    document_metadata = Column("metadata", JSON, default=dict)  # Additional metadata as JSON
    uploaded_by = Column(String, default="system")  # User identifier
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete timestamp

    # Relationships
    chunks = relationship("DocumentChunkModel", back_populates="document", cascade="all, delete-orphan")
    guidelines = relationship("GuidelineModel", back_populates="document")

    __table_args__ = (
        Index("idx_documents_status", "status"),
        Index("idx_documents_category", "category"),
        Index("idx_documents_deleted_at", "deleted_at"),
    )


class DocumentChunkModel(Base):
    """Persisted text chunk from processed document."""
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Sequential index within document
    chunk_text = Column(Text, nullable=False)  # Text content (500-1000 characters with overlap)
    page_number = Column(Integer, nullable=True)  # Source page (PDF) or null
    section_heading = Column(String, nullable=True)  # Extracted section heading or null
    char_start = Column(Integer, nullable=False)  # Character offset in original document
    char_end = Column(Integer, nullable=False)  # Character offset end
    chunk_metadata = Column("metadata", JSON, default=dict)  # Chunk-specific metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("DocumentModel", back_populates="chunks")
    guidelines = relationship("GuidelineModel", back_populates="chunk")

    __table_args__ = (
        Index("idx_chunks_document_id", "document_id"),
        Index("idx_chunks_document_chunk", "document_id", "chunk_index"),
    )


class GuidelineModel(Base):
    """Persisted brand guideline rule."""
    __tablename__ = "guidelines"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)  # terminology, unsupported_claim, tone_voice, prohibited_phrase, compliance
    rule_text = Column(Text, nullable=False)
    source_document = Column(String, nullable=False)
    version = Column(String, default="1.0")
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # New fields for document linking (nullable to maintain backward compatibility)
    document_id = Column(String, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    chunk_id = Column(String, ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)
    extraction_method = Column(String, default="manual")  # manual, auto_extracted, llm_generated

    # Relationships
    document = relationship("DocumentModel", back_populates="guidelines")
    chunk = relationship("DocumentChunkModel", back_populates="guidelines")


class SubmissionModel(Base):
    """Persisted content submission for audit."""
    __tablename__ = "submissions"

    id = Column(String, primary_key=True, default=generate_uuid)
    original_text = Column(Text, nullable=False)
    final_text = Column(Text, nullable=True)
    overall_status = Column(String, default="pending")  # pending, flagged, clean, approved, rejected
    summary = Column(Text, nullable=True)
    execution_time_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    findings = relationship("FindingModel", back_populates="submission", cascade="all, delete-orphan")
    decision = relationship("DecisionModel", back_populates="submission", uselist=False, cascade="all, delete-orphan")


class FindingModel(Base):
    """Persisted audit finding."""
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=generate_uuid)
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=False)
    category = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # critical, high, medium, low
    flagged_text = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    evidence_quote = Column(Text, nullable=True)
    evidence_source = Column(String, nullable=True)
    evidence_status = Column(String, default="not_found")  # supported, contradicted, not_found
    suggested_replacement = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0)
    dismissed = Column(String, default="false")  # true, false
    dismissal_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("SubmissionModel", back_populates="findings")


class DecisionModel(Base):
    """Persisted human reviewer decision."""
    __tablename__ = "decisions"

    id = Column(String, primary_key=True, default=generate_uuid)
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=False, unique=True)
    decision = Column(String, nullable=False)  # approved, rejected, changes_requested
    reviewer_name = Column(String, default="Guest Reviewer")
    reviewer_notes = Column(Text, nullable=True)
    resolved_findings = Column(JSON, default=list)  # List of finding IDs
    timestamp = Column(DateTime, default=datetime.utcnow)

    submission = relationship("SubmissionModel", back_populates="decision")
