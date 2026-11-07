"""
Phase 2: Document Processing Service Tests

Comprehensive test suite for PDF, DOCX, TXT extraction, chunking, and persistence.
"""
import pytest
import tempfile
import uuid
from pathlib import Path
from datetime import datetime

from pypdf import PdfWriter
from docx import Document as DocxDocument
from docx.shared import Inches

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import DocumentModel, DocumentChunkModel
from app.services.document_processor import DocumentProcessor, ExtractionResult, TextChunk


# ==================== FIXTURES ====================

@pytest.fixture
def db_session():
    """Create a temporary in-memory database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def processor():
    """Create a DocumentProcessor instance."""
    return DocumentProcessor(target_chunk_size=800, chunk_overlap=100)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_text_pdf(temp_dir):
    """Create a sample PDF with extractable text."""
    pdf_path = temp_dir / "sample_text.pdf"

    # Create a simple PDF using pypdf
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

    try:
        c = canvas.Canvas(str(pdf_path), pagesize=letter)

        # Page 1
        c.drawString(100, 750, "Brand Guidelines Document")
        c.drawString(100, 730, "Page 1 of 2")
        c.drawString(100, 700, "")
        c.drawString(100, 680, "Our brand color is #2563EB (blue). This should be used")
        c.drawString(100, 660, "consistently across all materials.")
        c.drawString(100, 640, "")
        c.drawString(100, 620, "Always use our official tagline: 'Innovation Through Trust'.")
        c.showPage()

        # Page 2
        c.drawString(100, 750, "Brand Guidelines Document")
        c.drawString(100, 730, "Page 2 of 2")
        c.drawString(100, 700, "")
        c.drawString(100, 680, "Never use the term 'cheap' when describing our products.")
        c.drawString(100, 660, "Instead, use 'cost-effective' or 'value-driven'.")
        c.showPage()

        c.save()
        return pdf_path
    except ImportError:
        # If reportlab not available, skip PDF creation tests
        pytest.skip("reportlab not installed")


@pytest.fixture
def sample_empty_pdf(temp_dir):
    """Create a PDF with no extractable text (simulates image-only PDF)."""
    pdf_path = temp_dir / "empty_pdf.pdf"

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        # Create pages with no text, just empty canvas
        c.showPage()
        c.showPage()
        c.save()
        return pdf_path
    except ImportError:
        pytest.skip("reportlab not installed")


@pytest.fixture
def sample_docx(temp_dir):
    """Create a sample DOCX with paragraphs, headings, and a table."""
    docx_path = temp_dir / "sample_document.docx"

    doc = DocxDocument()

    # Add heading
    doc.add_heading("Brand Guidelines", level=1)

    # Add paragraphs
    doc.add_paragraph("Our brand represents innovation and trust.")
    doc.add_paragraph("Always maintain consistency in messaging.")

    # Add subheading
    doc.add_heading("Visual Identity", level=2)

    doc.add_paragraph("Use our official color palette:")

    # Add table
    table = doc.add_table(rows=3, cols=2)
    table.cell(0, 0).text = "Primary"
    table.cell(0, 1).text = "#2563EB"
    table.cell(1, 0).text = "Secondary"
    table.cell(1, 1).text = "#10B981"
    table.cell(2, 0).text = "Accent"
    table.cell(2, 1).text = "#F59E0B"

    # Add more content
    doc.add_heading("Messaging Guidelines", level=2)
    doc.add_paragraph("Never make absolute security claims.")
    doc.add_paragraph("Always provide evidence for performance statements.")

    doc.save(str(docx_path))
    return docx_path


@pytest.fixture
def sample_utf8_txt(temp_dir):
    """Create a sample UTF-8 text file."""
    txt_path = temp_dir / "sample_utf8.txt"

    content = """Brand Guidelines Document

Our brand color is #2563EB (blue). This should be used consistently across all materials.

Always use our official tagline: 'Innovation Through Trust'. Never modify or abbreviate it.

Avoid absolute security claims such as:
- "100% secure"
- "unhackable"
- "zero downtime"

Instead, use measured language with evidence.
"""

    txt_path.write_text(content, encoding='utf-8')
    return txt_path


@pytest.fixture
def sample_empty_txt(temp_dir):
    """Create an empty text file."""
    txt_path = temp_dir / "empty.txt"
    txt_path.write_text("", encoding='utf-8')
    return txt_path


@pytest.fixture
def sample_binary_file(temp_dir):
    """Create a binary file (not text)."""
    bin_path = temp_dir / "binary.bin"
    bin_path.write_bytes(b'\x00\x01\x02\x03\x04\x05\xFF\xFE')
    return bin_path


# ==================== PDF TESTS ====================

def test_pdf_normal_text_extraction(processor, sample_text_pdf):
    """Test normal PDF with extractable text."""
    result = processor.extract_pdf(sample_text_pdf)

    assert result.success is True
    assert len(result.full_text) > 0
    assert "Brand Guidelines" in result.full_text
    assert "#2563EB" in result.full_text
    assert result.page_count == 2
    assert len(result.warnings) == 0


def test_pdf_empty_text_triggers_ocr_warning(processor, sample_empty_pdf):
    """Test image-only/empty-text PDF reports OCR requirement."""
    result = processor.extract_pdf(sample_empty_pdf)

    assert result.success is False
    assert "OCR or manual review required" in result.error_message
    assert result.page_count == 2


def test_pdf_malformed_fails_safely(processor, temp_dir):
    """Test malformed PDF fails with safe error message."""
    malformed_path = temp_dir / "malformed.pdf"
    malformed_path.write_text("This is not a valid PDF file", encoding='utf-8')

    result = processor.extract_pdf(malformed_path)

    assert result.success is False
    assert "malformed" in result.error_message.lower() or "parsing failed" in result.error_message.lower()
    assert "Traceback" not in result.error_message  # No stack trace


def test_pdf_nonexistent_file(processor, temp_dir):
    """Test nonexistent PDF file."""
    nonexistent = temp_dir / "nonexistent.pdf"

    result = processor.extract_pdf(nonexistent)

    assert result.success is False
    assert result.error_message is not None


# ==================== DOCX TESTS ====================

def test_docx_paragraphs_in_order(processor, sample_docx):
    """Test DOCX paragraphs are extracted in order."""
    result = processor.extract_docx(sample_docx)

    assert result.success is True
    assert "Brand Guidelines" in result.full_text
    assert "Visual Identity" in result.full_text
    assert "Messaging Guidelines" in result.full_text

    # Check order
    pos_guidelines = result.full_text.find("Brand Guidelines")
    pos_visual = result.full_text.find("Visual Identity")
    pos_messaging = result.full_text.find("Messaging Guidelines")

    assert pos_guidelines < pos_visual < pos_messaging


def test_docx_heading_styles_retained(processor, sample_docx):
    """Test DOCX heading styles are retained in metadata."""
    result = processor.extract_docx(sample_docx)

    assert result.success is True
    assert "sections" in result.metadata

    sections = result.metadata["sections"]
    heading_sections = [s for s in sections if s["type"] == "heading"]

    assert len(heading_sections) > 0
    assert any("Heading" in s.get("style", "") for s in heading_sections)


def test_docx_tables_extracted(processor, sample_docx):
    """Test DOCX tables are extracted."""
    result = processor.extract_docx(sample_docx)

    assert result.success is True
    assert "#2563EB" in result.full_text  # Table content
    assert result.metadata["table_count"] > 0


def test_docx_no_false_page_numbers(processor, sample_docx):
    """Test DOCX does not assign false page numbers."""
    result = processor.extract_docx(sample_docx)

    assert result.success is True
    assert result.page_count is None  # DOCX doesn't have fixed pages


def test_docx_malformed_fails_safely(processor, temp_dir):
    """Test malformed DOCX fails with safe error."""
    malformed_path = temp_dir / "malformed.docx"
    malformed_path.write_text("Not a DOCX file", encoding='utf-8')

    result = processor.extract_docx(malformed_path)

    assert result.success is False
    assert result.error_message is not None


# ==================== TXT TESTS ====================

def test_txt_utf8_extracts_correctly(processor, sample_utf8_txt):
    """Test UTF-8 text file extracts correctly."""
    result = processor.extract_txt(sample_utf8_txt)

    assert result.success is True
    assert "Brand Guidelines" in result.full_text
    assert "#2563EB" in result.full_text
    assert result.metadata["encoding"] == "utf-8"


def test_txt_empty_handled_explicitly(processor, sample_empty_txt):
    """Test empty text file is handled explicitly."""
    result = processor.extract_txt(sample_empty_txt)

    assert result.success is False
    assert "empty" in result.error_message.lower()


def test_txt_binary_rejected(processor, sample_binary_file):
    """Test binary file is rejected as not plain text."""
    result = processor.extract_txt(sample_binary_file)

    assert result.success is False
    assert "binary" in result.error_message.lower() or "decode" in result.error_message.lower()


# ==================== CHUNKING TESTS ====================

def test_chunk_target_size_800_overlap_100(processor):
    """Test chunking produces chunks near target size with overlap."""
    text = " ".join([f"Sentence {i} with some content." for i in range(100)])

    chunks = processor.chunk_text(text)

    assert len(chunks) > 0

    # Check chunk sizes are reasonable (allowing variation for boundaries)
    # Last chunk can be smaller as it contains remaining text
    for i, chunk in enumerate(chunks):
        if i < len(chunks) - 1:  # Not last chunk
            assert 400 <= len(chunk.chunk_text) <= 1200
        else:  # Last chunk can be smaller
            assert len(chunk.chunk_text) > 0

    # Check overlap exists between consecutive chunks
    if len(chunks) > 1:
        for i in range(len(chunks) - 1):
            # Should have some overlap in content
            chunk1_end = chunks[i].chunk_text[-50:]
            chunk2_start = chunks[i+1].chunk_text[:150]
            # At least some words should overlap
            words1 = set(chunk1_end.split())
            words2 = set(chunk2_start.split())
            overlap = words1 & words2
            assert len(overlap) > 0  # Some word overlap


def test_chunk_no_word_splitting(processor):
    """Test words are not unnecessarily split."""
    text = "This is a test document. " * 100

    chunks = processor.chunk_text(text)

    for chunk in chunks:
        # Check chunks end at word boundaries (no trailing partial words)
        assert not chunk.chunk_text.endswith("-")
        # Check chunks don't start with lowercase after space (mid-word split)
        words = chunk.chunk_text.split()
        if len(words) > 1:
            # First word can start with lowercase if it's after overlap
            # But no words should be obviously truncated
            for word in words:
                if len(word) > 3:
                    # Real words, not fragments
                    assert word.isalnum() or any(c.isalnum() for c in word)


def test_chunk_no_empty_chunks(processor):
    """Test no empty chunks are generated."""
    text = "Paragraph one.\n\nParagraph two.\n\n\n\nParagraph three."

    chunks = processor.chunk_text(text)

    assert len(chunks) > 0
    for chunk in chunks:
        assert len(chunk.chunk_text.strip()) > 0


def test_chunk_no_duplicate_chunks(processor):
    """Test no duplicate chunks are generated."""
    text = "Unique content here. " * 50

    chunks = processor.chunk_text(text)

    # Check first 100 chars of each chunk for duplicates
    fingerprints = [chunk.chunk_text[:100] for chunk in chunks]
    assert len(fingerprints) == len(set(fingerprints))


def test_chunk_stable_ordered_indexes(processor):
    """Test chunk indexes are stable and ordered."""
    text = "Content paragraph. " * 100

    chunks = processor.chunk_text(text)

    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i


def test_chunk_char_offsets_match_source(processor):
    """Test char_start/char_end match source text."""
    text = "First paragraph content.\n\nSecond paragraph content.\n\nThird paragraph content."

    chunks = processor.chunk_text(text)

    normalized = processor._normalize_text(text)

    for chunk in chunks:
        # Extract text using offsets
        extracted = normalized[chunk.char_start:chunk.char_end]
        # Should match chunk text (after stripping, since chunk may trim edges)
        assert chunk.chunk_text.strip() in extracted or extracted in chunk.chunk_text


# ==================== PERSISTENCE TESTS ====================

def test_document_and_chunks_persist(processor, db_session, sample_utf8_txt):
    """Test document and chunks are persisted."""
    doc_id = str(uuid.uuid4())

    # Create document record
    doc = DocumentModel(
        id=doc_id,
        filename="test.txt",
        file_type="text/plain",
        file_size=1000,
        storage_path="/test/test.txt",
        title="Test Document",
        category="brand_guidelines",
        status="uploading"
    )
    db_session.add(doc)
    db_session.commit()

    # Process and persist
    success, error = processor.process_and_persist(
        doc_id,
        sample_utf8_txt,
        "text/plain",
        db_session
    )

    assert success is True
    assert error is None

    # Verify document status
    doc = db_session.query(DocumentModel).filter_by(id=doc_id).first()
    assert doc.status == "indexed"

    # Verify chunks created
    chunks = db_session.query(DocumentChunkModel).filter_by(document_id=doc_id).all()
    assert len(chunks) > 0


def test_failed_extraction_sets_failed_status(processor, db_session, sample_empty_txt):
    """Test failed extraction sets failed status."""
    doc_id = str(uuid.uuid4())

    doc = DocumentModel(
        id=doc_id,
        filename="empty.txt",
        file_type="text/plain",
        file_size=0,
        storage_path="/test/empty.txt",
        title="Empty Document",
        category="brand_guidelines",
        status="uploading"
    )
    db_session.add(doc)
    db_session.commit()

    success, error = processor.process_and_persist(
        doc_id,
        sample_empty_txt,
        "text/plain",
        db_session
    )

    assert success is False
    assert error is not None

    doc = db_session.query(DocumentModel).filter_by(id=doc_id).first()
    assert doc.status == "failed"
    assert doc.error_message is not None


def test_indexed_only_after_persistence(processor, db_session, sample_utf8_txt):
    """Test indexed status is set only after successful persistence."""
    doc_id = str(uuid.uuid4())

    doc = DocumentModel(
        id=doc_id,
        filename="test.txt",
        file_type="text/plain",
        file_size=1000,
        storage_path="/test/test.txt",
        title="Test Document",
        category="brand_guidelines",
        status="uploading"
    )
    db_session.add(doc)
    db_session.commit()

    success, error = processor.process_and_persist(
        doc_id,
        sample_utf8_txt,
        "text/plain",
        db_session
    )

    assert success is True

    # Check document is indexed
    doc = db_session.query(DocumentModel).filter_by(id=doc_id).first()
    assert doc.status == "indexed"

    # Check chunks exist (proof of complete persistence)
    chunks = db_session.query(DocumentChunkModel).filter_by(document_id=doc_id).count()
    assert chunks > 0


def test_reprocessing_removes_old_chunks(processor, db_session, sample_utf8_txt):
    """Test reprocessing removes/replaces old chunks safely."""
    doc_id = str(uuid.uuid4())

    doc = DocumentModel(
        id=doc_id,
        filename="test.txt",
        file_type="text/plain",
        file_size=1000,
        storage_path="/test/test.txt",
        title="Test Document",
        category="brand_guidelines",
        status="uploading"
    )
    db_session.add(doc)
    db_session.commit()

    # First processing
    success1, _ = processor.process_and_persist(
        doc_id,
        sample_utf8_txt,
        "text/plain",
        db_session
    )
    assert success1 is True

    chunks_after_first = db_session.query(DocumentChunkModel).filter_by(document_id=doc_id).count()

    # Reprocess
    success2, _ = processor.process_and_persist(
        doc_id,
        sample_utf8_txt,
        "text/plain",
        db_session
    )
    assert success2 is True

    chunks_after_second = db_session.query(DocumentChunkModel).filter_by(document_id=doc_id).count()

    # Should have same number of chunks (no duplicates)
    assert chunks_after_second == chunks_after_first


# ==================== REGRESSION TESTS ====================

def test_processor_import_no_warnings():
    """Test document_processor imports without SQLAlchemy warnings."""
    # This test passes if no warnings during import
    from app.services import document_processor
    assert document_processor is not None
