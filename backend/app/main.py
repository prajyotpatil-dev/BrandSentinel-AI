"""
BrandSentinel AI — FastAPI Application Entry Point

Hackathon: CodeNexus India 2026 — Round 2
"""
import time
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import init_db, get_db
from app.schemas import (
    HealthResponse, GuidelineItem, GuidelineCreate,
    AuditRequest, AuditResponse,
    DecisionRequest, DecisionResponse,
    SubmissionHistory,
    OverallStatus,
    DocumentStatus, DocumentCategory,
    DocumentUpdate,
)
from app.seed_data import get_seed_guidelines, SAMPLE_DRAFTS
from app import models
from app.services.upload_service import upload_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and seed data on startup."""
    init_db()
    _seed_guidelines_if_empty()
    yield


def _seed_guidelines_if_empty():
    """Seed brand guidelines if table is empty."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        count = db.query(models.GuidelineModel).count()
        if count == 0:
            for g in get_seed_guidelines():
                db.add(models.GuidelineModel(**g))
            db.commit()
            print(f"[BrandSentinel] Seeded {len(get_seed_guidelines())} ApexCloud guidelines.")
    finally:
        db.close()


app = FastAPI(
    title="BrandSentinel AI",
    description="Explainable Pre-Publication Brand Governance Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
#  HEALTH
# ─────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse, tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """Return system health, active model, and loaded guideline count."""
    count = db.query(models.GuidelineModel).count()
    ai_available = bool(settings.gemini_api_key)
    return HealthResponse(
        status="ok",
        model="gemini-2.0-flash-exp" if ai_available else "fallback-deterministic",
        guideline_count=count,
        fallback_mode=not ai_available,
    )


# ─────────────────────────────────────────────
#  GUIDELINES
# ─────────────────────────────────────────────

@app.get("/api/guidelines", response_model=list[GuidelineItem], tags=["Guidelines"])
def list_guidelines(db: Session = Depends(get_db)):
    """List all active brand guidelines."""
    return db.query(models.GuidelineModel).all()


@app.post("/api/guidelines", response_model=GuidelineItem, status_code=201, tags=["Guidelines"])
def add_guideline(guideline: GuidelineCreate, db: Session = Depends(get_db)):
    """Add a custom brand rule dynamically."""
    import uuid
    db_guideline = models.GuidelineModel(
        id=str(uuid.uuid4()),
        title=guideline.title,
        category=guideline.category,
        rule_text=guideline.rule_text,
        source_document=guideline.source_document,
        version=guideline.version,
        tags=guideline.tags,
    )
    db.add(db_guideline)
    db.commit()
    db.refresh(db_guideline)
    return db_guideline


# ─────────────────────────────────────────────
#  SAMPLES
# ─────────────────────────────────────────────

@app.get("/api/samples", tags=["Demo"])
def get_samples():
    """Return pre-seeded sample drafts for judge testing."""
    return SAMPLE_DRAFTS


# ─────────────────────────────────────────────
#  AUDIT
# ─────────────────────────────────────────────

@app.post("/api/audit", response_model=AuditResponse, tags=["Audit"])
def run_audit(request: AuditRequest, db: Session = Depends(get_db)):
    """
    Run a brand governance audit on submitted content.

    Uses hybrid audit engine:
    1. Deterministic rules check (regex/glossary)
    2. Relevant guideline retrieval (keyword/vector)
    3. Gemini AI contextual analysis (with deterministic fallback)
    """
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="Content text cannot be empty.")

    from app.services.audit_orchestrator import AuditOrchestrator
    orchestrator = AuditOrchestrator(db)
    result = orchestrator.run(request.text, request.workspace_id or "default")
    return result


# ─────────────────────────────────────────────
#  DECISION
# ─────────────────────────────────────────────

@app.post("/api/decision", response_model=DecisionResponse, tags=["Decision"])
def record_decision(request: DecisionRequest, db: Session = Depends(get_db)):
    """
    Record a human reviewer decision on audited content.

    Updates submission status and creates an auditable decision record.

    Approval protection:
    - Blocks approval when unresolved critical findings exist (without explicit justification)
    - Blocks approval when audit status is REVIEW_REQUIRED (incomplete analysis)
    - Blocks approval when required contextual checks did not complete
    """
    from datetime import datetime

    submission = db.query(models.SubmissionModel).filter(
        models.SubmissionModel.id == request.submission_id
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail=f"Submission '{request.submission_id}' not found.")

    # Check for unresolved critical findings when approving
    if request.decision.value == "approved":
        # Block approval if audit was incomplete (REVIEW_REQUIRED status)
        if submission.overall_status == "review_required":
            raise HTTPException(
                status_code=422,
                detail=(
                    "Cannot approve: Audit status is REVIEW_REQUIRED. "
                    "Mandatory contextual analysis could not complete. "
                    "Retry the audit or provide manual verification before approving."
                ),
            )

        # Block approval if unresolved critical findings exist
        unresolved_critical = [
            f for f in submission.findings
            if f.severity == "critical" and not f.dismissed
            and f.id not in request.resolved_findings
        ]
        if unresolved_critical and not request.reviewer_notes:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Cannot approve: {len(unresolved_critical)} unresolved critical finding(s). "
                    "Provide reviewer_notes explaining the override."
                ),
            )

        # Warn about unresolved high-severity findings
        unresolved_high = [
            f for f in submission.findings
            if f.severity == "high" and not f.dismissed
            and f.id not in request.resolved_findings
        ]
        if unresolved_high and not request.reviewer_notes:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Cannot approve: {len(unresolved_high)} unresolved high-severity finding(s). "
                    "Review and resolve these findings, or provide reviewer_notes justifying approval."
                ),
            )

    # Update submission final text and status
    submission.final_text = request.final_text
    submission.overall_status = request.decision.value

    # Record decision
    decision_record = models.DecisionModel(
        id=str(__import__("uuid").uuid4()),
        submission_id=request.submission_id,
        decision=request.decision.value,
        reviewer_name=request.reviewer_name,
        reviewer_notes=request.reviewer_notes,
        resolved_findings=request.resolved_findings,
    )
    db.add(decision_record)
    db.commit()
    db.refresh(decision_record)

    return DecisionResponse(
        submission_id=decision_record.submission_id,
        decision=decision_record.decision,
        timestamp=decision_record.timestamp,
        reviewer_name=decision_record.reviewer_name,
        reviewer_notes=decision_record.reviewer_notes,
    )


# ─────────────────────────────────────────────
#  HISTORY
# ─────────────────────────────────────────────

@app.get("/api/history", response_model=list[SubmissionHistory], tags=["History"])
def get_history(limit: int = 20, db: Session = Depends(get_db)):
    """Return recent audit history and decision trails."""
    submissions = (
        db.query(models.SubmissionModel)
        .order_by(models.SubmissionModel.created_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for sub in submissions:
        decision_data = None
        if sub.decision:
            decision_data = DecisionResponse(
                submission_id=sub.decision.submission_id,
                decision=sub.decision.decision,
                timestamp=sub.decision.timestamp,
                reviewer_name=sub.decision.reviewer_name,
                reviewer_notes=sub.decision.reviewer_notes,
            )

        results.append(
            SubmissionHistory(
                submission_id=sub.id,
                original_text=sub.original_text[:200] + "..." if len(sub.original_text) > 200 else sub.original_text,
                overall_status=sub.overall_status,
                created_at=sub.created_at,
                decision=decision_data,
            )
        )

    return results


# ─────────────────────────────────────────────
#  DOCUMENTS (Phase 3)
# ─────────────────────────────────────────────

@app.post("/api/documents", status_code=201, tags=["Documents"])
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: str = Form("brand_guidelines"),
    tags: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload and process a document (PDF, DOCX, TXT).

    Security features:
    - Size limit enforcement (10 MB streaming)
    - Extension validation
    - MIME type validation
    - File signature verification
    - Path traversal prevention
    - Server-generated storage filenames

    Processing:
    - Extracts text from uploaded document
    - Generates traceable chunks
    - Indexes for evidence retrieval

    Returns:
    - Document ID
    - Original filename (safely stored as metadata)
    - Processing status
    - File size, type, and timestamps
    - Warning messages if applicable
    - Never returns absolute storage paths
    """
    # Parse tags if provided
    tags_list = None
    if tags:
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]

    # Process upload
    document = await upload_service.process_upload(
        file=file,
        title=title,
        category=category,
        tags=tags_list,
        db=db
    )

    # Build response (never expose absolute storage paths)
    response = {
        "id": document.id,
        "title": document.title,
        "filename": document.filename,  # Original filename
        "file_type": document.file_type,
        "file_size": document.file_size,
        "category": document.category,
        "status": document.status,
        "page_count": document.page_count,
        "version": document.version,
        "tags": document.tags,
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
    }

    # Include error message if failed
    if document.status == "failed" and document.error_message:
        response["error_message"] = document.error_message

    # Include warnings from processing if any
    if document.document_metadata and "processing_warnings" in document.document_metadata:
        response["warnings"] = document.document_metadata["processing_warnings"]

    return response


# ─────────────────────────────────────────────
#  DOCUMENT MANAGEMENT (Phase 5)
# ─────────────────────────────────────────────

@app.get("/api/documents", tags=["Documents"])
def list_documents(
    page: int = 1,
    page_size: int = 20,
    category: Optional[str] = None,
    status: Optional[str] = None,
    file_type: Optional[str] = None,
    search: Optional[str] = None,
    include_deleted: bool = False,
    db: Session = Depends(get_db)
):
    """
    List documents with pagination and filtering.

    By default, excludes soft-deleted documents (deleted_at IS NOT NULL).
    Pass include_deleted=true to include them.
    """
    from app.schemas import DocumentResponse, DocumentListResponse

    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    query = db.query(models.DocumentModel)

    # Exclude soft-deleted by default
    if not include_deleted:
        query = query.filter(models.DocumentModel.deleted_at.is_(None))

    # Filter by category
    if category:
        query = query.filter(models.DocumentModel.category == category)

    # Filter by status
    if status:
        query = query.filter(models.DocumentModel.status == status)

    # Filter by file type
    if file_type:
        query = query.filter(models.DocumentModel.file_type.ilike(f"%{file_type}%"))

    # Search by title or original filename
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (models.DocumentModel.title.ilike(search_term)) |
            (models.DocumentModel.filename.ilike(search_term))
        )

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    documents = query.order_by(models.DocumentModel.created_at.desc()).offset(offset).limit(page_size).all()

    # Build response with chunk counts
    items = []
    for doc in documents:
        chunk_count = db.query(models.DocumentChunkModel).filter_by(document_id=doc.id).count()
        items.append(DocumentResponse(
            id=doc.id,
            title=doc.title,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            category=doc.category,
            status=doc.status,
            error_message=doc.error_message,
            page_count=doc.page_count,
            version=doc.version,
            tags=doc.tags or [],
            uploaded_by=doc.uploaded_by,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            chunk_count=chunk_count
        ))

    total_pages = (total + page_size - 1) // page_size

    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@app.get("/api/documents/{document_id}", tags=["Documents"])
def get_document(document_id: str, db: Session = Depends(get_db)):
    """
    Retrieve document details by ID.

    Returns 404 if document not found or soft-deleted.
    Never exposes absolute storage paths.
    """
    from app.schemas import DocumentResponse

    document = db.query(models.DocumentModel).filter_by(id=document_id).first()

    if not document or document.deleted_at is not None:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

    chunk_count = db.query(models.DocumentChunkModel).filter_by(document_id=document_id).count()

    return DocumentResponse(
        id=document.id,
        title=document.title,
        filename=document.filename,
        file_type=document.file_type,
        file_size=document.file_size,
        category=document.category,
        status=document.status,
        error_message=document.error_message,
        page_count=document.page_count,
        version=document.version,
        tags=document.tags or [],
        uploaded_by=document.uploaded_by,
        created_at=document.created_at,
        updated_at=document.updated_at,
        chunk_count=chunk_count
    )


@app.patch("/api/documents/{document_id}", tags=["Documents"])
def update_document(document_id: str, update: DocumentUpdate, db: Session = Depends(get_db)):
    """
    Update document metadata (title, category, tags).

    Does not modify the file itself or trigger reprocessing.
    Returns 404 if document not found or soft-deleted.
    """
    from app.schemas import DocumentResponse

    document = db.query(models.DocumentModel).filter_by(id=document_id).first()

    if not document or document.deleted_at is not None:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

    # Update fields if provided
    if update.title is not None:
        document.title = update.title
    if update.category is not None:
        document.category = update.category.value
    if update.tags is not None:
        # Validate tag count and individual tag length
        if len(update.tags) > 20:
            raise HTTPException(
                status_code=422,
                detail="Cannot have more than 20 tags per document."
            )
        for tag in update.tags:
            if len(tag) > 50:
                raise HTTPException(
                    status_code=422,
                    detail=f"Tag '{tag[:20]}...' exceeds 50 characters."
                )
        document.tags = update.tags

    db.commit()
    db.refresh(document)

    chunk_count = db.query(models.DocumentChunkModel).filter_by(document_id=document_id).count()

    return DocumentResponse(
        id=document.id,
        title=document.title,
        filename=document.filename,
        file_type=document.file_type,
        file_size=document.file_size,
        category=document.category,
        status=document.status,
        error_message=document.error_message,
        page_count=document.page_count,
        version=document.version,
        tags=document.tags or [],
        uploaded_by=document.uploaded_by,
        created_at=document.created_at,
        updated_at=document.updated_at,
        chunk_count=chunk_count
    )


@app.post("/api/documents/{document_id}/reprocess", tags=["Documents"])
def reprocess_document(document_id: str, db: Session = Depends(get_db)):
    """
    Reprocess an uploaded document.

    - Reads the stored file and re-extracts text
    - Deletes old chunks and creates new ones (no duplicates)
    - Updates document status to "indexed" or "failed"
    - Returns 404 if document not found or soft-deleted
    - Returns 400 if file no longer exists on disk
    """
    from app.schemas import DocumentReprocessResponse
    from app.services.document_processor import DocumentProcessor
    from pathlib import Path

    document = db.query(models.DocumentModel).filter_by(id=document_id).first()

    if not document or document.deleted_at is not None:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

    # Check if file exists
    storage_path = settings.upload_storage_path / document.storage_path
    if not storage_path.exists():
        raise HTTPException(
            status_code=400,
            detail="Source file no longer exists on disk. Cannot reprocess."
        )

    # Reprocess
    processor = DocumentProcessor()
    success, error_message = processor.process_and_persist(
        document_id=document_id,
        file_path=storage_path,
        file_type=document.file_type,
        db=db
    )

    # Refresh to get updated status
    db.refresh(document)

    chunk_count = db.query(models.DocumentChunkModel).filter_by(document_id=document_id).count()

    if success:
        return DocumentReprocessResponse(
            id=document.id,
            status=document.status,
            chunk_count=chunk_count,
            message=f"Document reprocessed successfully. {chunk_count} chunks indexed."
        )
    else:
        return DocumentReprocessResponse(
            id=document.id,
            status=document.status,
            chunk_count=chunk_count,
            message=f"Reprocessing failed: {error_message}"
        )


@app.delete("/api/documents/{document_id}", tags=["Documents"])
def delete_document(document_id: str, db: Session = Depends(get_db)):
    """
    Soft-delete a document.

    - Sets deleted_at timestamp
    - Document no longer appears in normal listings
    - Document no longer retrieved as evidence
    - File remains on disk (can be restored)
    - Returns 404 if document not found or already deleted
    """
    from app.schemas import DocumentDeleteResponse
    from datetime import datetime

    document = db.query(models.DocumentModel).filter_by(id=document_id).first()

    if not document or document.deleted_at is not None:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

    # Soft delete
    document.deleted_at = datetime.utcnow()
    db.commit()

    return DocumentDeleteResponse(
        id=document.id,
        status="deleted",
        message="Document soft-deleted successfully. File preserved on disk."
    )


@app.post("/api/documents/{document_id}/restore", tags=["Documents"])
def restore_document(document_id: str, db: Session = Depends(get_db)):
    """
    Restore a soft-deleted document.

    - Clears deleted_at timestamp
    - Document reappears in normal listings
    - Document becomes retrievable as evidence again
    - Returns 404 if document not found
    - Returns 400 if document is not deleted
    """
    from app.schemas import DocumentRestoreResponse

    document = db.query(models.DocumentModel).filter_by(id=document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

    if document.deleted_at is None:
        raise HTTPException(status_code=400, detail="Document is not deleted")

    # Restore
    document.deleted_at = None
    db.commit()

    return DocumentRestoreResponse(
        id=document.id,
        status=document.status,
        message="Document restored successfully."
    )


# ─────────────────────────────────────────────
#  SAMPLES
# ─────────────────────────────────────────────

@app.get("/api/samples", tags=["Samples"])
def get_samples():
    """Return sample marketing content drafts for testing."""
    return SAMPLE_DRAFTS
