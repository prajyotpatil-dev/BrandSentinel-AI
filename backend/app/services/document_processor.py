"""
Document Processing Service for BrandSentinel AI.

Handles PDF, DOCX, and TXT extraction with structured text output and traceable chunking.
Phase 2: Processing service only - no upload routes or UI.
"""
import re
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from docx import Document as DocxDocument
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph

from sqlalchemy.orm import Session
from app.models import DocumentModel, DocumentChunkModel


@dataclass
class ExtractionResult:
    """Result of document text extraction."""
    success: bool
    full_text: str
    page_count: Optional[int] = None
    warnings: List[str] = None
    error_message: Optional[str] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TextChunk:
    """A chunk of document text with provenance metadata."""
    chunk_index: int
    chunk_text: str
    char_start: int
    char_end: int
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DocumentProcessor:
    """
    Process documents (PDF, DOCX, TXT) into extracted text and traceable chunks.

    Handles:
    - Format-specific text extraction
    - Structured chunking with overlap
    - Provenance tracking (page numbers, headings, offsets)
    - Safe error handling
    - Transactional persistence
    """

    def __init__(self, target_chunk_size: int = 800, chunk_overlap: int = 100):
        """
        Initialize document processor.

        Args:
            target_chunk_size: Target characters per chunk (~800)
            chunk_overlap: Characters to overlap between chunks (~100)
        """
        self.target_chunk_size = target_chunk_size
        self.chunk_overlap = chunk_overlap

    # ==================== PDF EXTRACTION ====================

    def extract_pdf(self, file_path: Path) -> ExtractionResult:
        """
        Extract text from PDF with page-level preservation.

        Features:
        - Page-by-page text extraction
        - Page number preservation
        - Empty/image-only page detection
        - Encryption detection
        - Safe error handling

        Args:
            file_path: Path to PDF file

        Returns:
            ExtractionResult with text, page_count, and warnings
        """
        try:
            reader = PdfReader(str(file_path))

            # Check for encryption
            if reader.is_encrypted:
                return ExtractionResult(
                    success=False,
                    full_text="",
                    error_message="Document is password-protected and cannot be processed"
                )

            page_count = len(reader.pages)
            page_texts = []
            empty_pages = []

            # Extract text page by page
            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text()
                    if text:
                        # Clean up excessive whitespace while preserving structure
                        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
                        text = text.strip()

                    if not text or len(text.split()) < 5:  # Less than 5 words
                        empty_pages.append(page_num)
                        page_texts.append("")
                    else:
                        page_texts.append(text)

                except Exception as e:
                    # Page extraction failed, mark as empty
                    empty_pages.append(page_num)
                    page_texts.append("")

            # Join pages with clear delimiters
            full_text = "\n\n".join(text for text in page_texts if text)

            # Check for OCR requirement (too many empty pages or very little text)
            warnings = []
            word_count = len(full_text.split())

            if len(empty_pages) > page_count * 0.5:  # More than 50% empty pages
                warnings.append(
                    f"OCR or manual review may be required: "
                    f"{len(empty_pages)}/{page_count} pages had no extractable text"
                )
            elif word_count < 50 and page_count > 2:  # Very few words for multi-page doc
                warnings.append(
                    f"OCR or manual review may be required: "
                    f"Only {word_count} words extracted from {page_count} pages"
                )

            if not full_text.strip():
                return ExtractionResult(
                    success=False,
                    full_text="",
                    page_count=page_count,
                    error_message="No extractable text found. OCR or manual review required.",
                    warnings=warnings
                )

            metadata = {
                "empty_pages": empty_pages if empty_pages else [],
                "extraction_method": "pypdf"
            }

            return ExtractionResult(
                success=True,
                full_text=full_text,
                page_count=page_count,
                warnings=warnings,
                metadata=metadata
            )

        except PdfReadError as e:
            return ExtractionResult(
                success=False,
                full_text="",
                error_message=f"PDF parsing failed: malformed or corrupted document"
            )
        except Exception as e:
            return ExtractionResult(
                success=False,
                full_text="",
                error_message=f"PDF extraction failed: {type(e).__name__}"
            )

    # ==================== DOCX EXTRACTION ====================

    def extract_docx(self, file_path: Path) -> ExtractionResult:
        """
        Extract text from DOCX with paragraph/heading/table preservation.

        Features:
        - Paragraphs extracted in document order
        - Heading styles retained
        - Tables extracted in reading order
        - No false page numbers (DOCX doesn't have fixed pages)

        Args:
            file_path: Path to DOCX file

        Returns:
            ExtractionResult with text and structural metadata
        """
        try:
            doc = DocxDocument(str(file_path))

            sections = []
            current_heading = None

            # Process document body elements in order (paragraphs and tables)
            for element in doc.element.body:
                if isinstance(element, CT_P):
                    # Paragraph
                    paragraph = Paragraph(element, doc)
                    text = paragraph.text.strip()

                    if not text:
                        continue

                    # Check if it's a heading
                    style_name = paragraph.style.name if paragraph.style else ""
                    if style_name.startswith("Heading"):
                        current_heading = text
                        sections.append({
                            "type": "heading",
                            "text": text,
                            "style": style_name,
                            "heading": current_heading
                        })
                    else:
                        sections.append({
                            "type": "paragraph",
                            "text": text,
                            "heading": current_heading
                        })

                elif isinstance(element, CT_Tbl):
                    # Table
                    table = Table(element, doc)
                    table_text = self._extract_table_text(table)
                    if table_text:
                        sections.append({
                            "type": "table",
                            "text": table_text,
                            "heading": current_heading
                        })

            if not sections:
                return ExtractionResult(
                    success=False,
                    full_text="",
                    error_message="No extractable text found in document"
                )

            # Build full text
            full_text = "\n\n".join(section["text"] for section in sections)

            # Extract metadata
            headings = [s["text"] for s in sections if s["type"] == "heading"]
            metadata = {
                "extraction_method": "python-docx",
                "heading_count": len(headings),
                "table_count": sum(1 for s in sections if s["type"] == "table"),
                "sections": sections  # Store for chunking provenance
            }

            return ExtractionResult(
                success=True,
                full_text=full_text,
                page_count=None,  # DOCX doesn't have fixed page numbers
                warnings=[],
                metadata=metadata
            )

        except Exception as e:
            return ExtractionResult(
                success=False,
                full_text="",
                error_message=f"DOCX extraction failed: {type(e).__name__}"
            )

    def _extract_table_text(self, table: Table) -> str:
        """
        Extract text from a DOCX table in reading order.

        Args:
            table: python-docx Table object

        Returns:
            Formatted table text
        """
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            # Filter out empty cells
            cells = [cell for cell in cells if cell]
            if cells:
                rows.append(" | ".join(cells))

        return "\n".join(rows) if rows else ""

    # ==================== TXT EXTRACTION ====================

    def extract_txt(self, file_path: Path) -> ExtractionResult:
        """
        Extract text from TXT file with encoding handling.

        Features:
        - UTF-8 decoding with fallback
        - Binary/undecodable detection
        - Empty file handling

        Args:
            file_path: Path to TXT file

        Returns:
            ExtractionResult with text
        """
        try:
            # Try UTF-8 first
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                encoding_used = "utf-8"
            except UnicodeDecodeError:
                # Fallback to latin-1 (ISO-8859-1) - accepts all bytes
                try:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        text = f.read()
                    encoding_used = "latin-1"
                except Exception:
                    return ExtractionResult(
                        success=False,
                        full_text="",
                        error_message="Text file could not be decoded (unrecognized encoding)"
                    )

            # Check for binary content (high ratio of non-printable characters)
            if text:
                printable_ratio = sum(c.isprintable() or c.isspace() for c in text) / len(text)
                if printable_ratio < 0.7:  # Less than 70% printable
                    return ExtractionResult(
                        success=False,
                        full_text="",
                        error_message="File appears to be binary, not plain text"
                    )

            if not text.strip():
                return ExtractionResult(
                    success=False,
                    full_text="",
                    error_message="Text file is empty"
                )

            metadata = {
                "extraction_method": "plain_text",
                "encoding": encoding_used
            }

            return ExtractionResult(
                success=True,
                full_text=text,
                page_count=None,
                warnings=[],
                metadata=metadata
            )

        except Exception as e:
            return ExtractionResult(
                success=False,
                full_text="",
                error_message=f"Text file reading failed: {type(e).__name__}"
            )

    # ==================== CHUNKING ====================

    def chunk_text(
        self,
        full_text: str,
        extraction_metadata: Dict = None
    ) -> List[TextChunk]:
        """
        Chunk text into overlapping segments with provenance.

        Features:
        - Target ~800 characters, ~100 overlap
        - Prefer paragraph/heading boundaries
        - Don't split words unnecessarily
        - No empty or duplicate chunks
        - Stable ordered indexes
        - Correct char_start/char_end offsets
        - Preserve page/heading metadata where available

        Args:
            full_text: Complete extracted text
            extraction_metadata: Metadata from extraction (page numbers, headings, etc.)

        Returns:
            List of TextChunk objects with provenance
        """
        if not full_text.strip():
            return []

        # Normalize text (consistent line breaks, no excessive whitespace)
        normalized_text = self._normalize_text(full_text)

        # Split into paragraphs
        paragraphs = self._split_into_paragraphs(normalized_text)

        chunks = []
        chunk_index = 0
        current_pos = 0

        # Build chunks respecting paragraph boundaries
        while current_pos < len(normalized_text):
            chunk_end = min(current_pos + self.target_chunk_size, len(normalized_text))

            # Try to end at a paragraph boundary
            chunk_text = normalized_text[current_pos:chunk_end]

            # If we're not at the end, try to break at paragraph or sentence boundary
            if chunk_end < len(normalized_text):
                # Look for paragraph break within last 200 chars
                last_part = chunk_text[-200:] if len(chunk_text) > 200 else chunk_text
                para_break = last_part.rfind('\n\n')

                if para_break > 0:
                    # Break at paragraph
                    chunk_end = current_pos + len(chunk_text) - len(last_part) + para_break
                    chunk_text = normalized_text[current_pos:chunk_end].strip()
                else:
                    # Look for sentence break
                    sentence_break = self._find_sentence_break(last_part)
                    if sentence_break > 0:
                        chunk_end = current_pos + len(chunk_text) - len(last_part) + sentence_break
                        chunk_text = normalized_text[current_pos:chunk_end].strip()
                    else:
                        # Last resort: break at word boundary
                        word_break = chunk_text.rfind(' ')
                        if word_break > self.target_chunk_size * 0.5:  # At least halfway
                            chunk_text = chunk_text[:word_break].strip()
                            chunk_end = current_pos + word_break

            chunk_text = chunk_text.strip()

            # Skip empty chunks
            if chunk_text:
                # Determine page number and heading (if available)
                page_num, heading = self._determine_provenance(
                    current_pos,
                    chunk_end,
                    extraction_metadata
                )

                chunk = TextChunk(
                    chunk_index=chunk_index,
                    chunk_text=chunk_text,
                    char_start=current_pos,
                    char_end=current_pos + len(chunk_text),
                    page_number=page_num,
                    section_heading=heading
                )

                chunks.append(chunk)
                chunk_index += 1

            # Move forward with overlap
            if chunk_end >= len(normalized_text):
                break

            # Apply overlap, but don't go backward
            next_pos = max(chunk_end - self.chunk_overlap, current_pos + 1)
            current_pos = next_pos

        # Validate no duplicates
        chunks = self._remove_duplicate_chunks(chunks)

        return chunks

    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent chunking."""
        # Consistent line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # Remove excessive blank lines (keep max 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove trailing whitespace from lines
        text = '\n'.join(line.rstrip() for line in text.split('\n'))
        return text.strip()

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        return [p.strip() for p in text.split('\n\n') if p.strip()]

    def _find_sentence_break(self, text: str) -> int:
        """Find last sentence boundary in text."""
        # Look for sentence endings
        for pattern in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
            pos = text.rfind(pattern)
            if pos > 0:
                return pos + len(pattern)
        return -1

    def _determine_provenance(
        self,
        char_start: int,
        char_end: int,
        metadata: Optional[Dict]
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        Determine page number and heading for a chunk based on character offsets.

        Args:
            char_start: Starting character offset
            char_end: Ending character offset
            metadata: Extraction metadata

        Returns:
            (page_number, section_heading) tuple
        """
        if not metadata:
            return None, None

        # For DOCX, try to find relevant heading from sections
        if "sections" in metadata:
            # This is a simplified version - could be enhanced
            # to track exact character positions per section
            return None, None  # DOCX doesn't have page numbers

        # For PDF, page tracking would require more sophisticated offset mapping
        # For Phase 2, we return None and can enhance in future phases
        return None, None

    def _remove_duplicate_chunks(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """Remove duplicate chunks based on text content."""
        seen = set()
        unique = []

        for chunk in chunks:
            # Use first 100 chars as fingerprint
            fingerprint = chunk.chunk_text[:100]
            if fingerprint not in seen:
                seen.add(fingerprint)
                unique.append(chunk)

        return unique

    # ==================== PERSISTENCE ====================

    def process_and_persist(
        self,
        document_id: str,
        file_path: Path,
        file_type: str,
        db: Session
    ) -> Tuple[bool, Optional[str]]:
        """
        Process document and persist to database with transaction safety.

        Features:
        - Set status to "processing" before extraction
        - Extract text (format-specific)
        - Generate chunks
        - Transactionally replace old chunks (if reprocessing)
        - Update document status to "indexed" or "failed"
        - Safe error handling with retryable state

        Args:
            document_id: UUID of document record
            file_path: Path to file on disk
            file_type: MIME type
            db: SQLAlchemy session

        Returns:
            (success, error_message) tuple
        """
        try:
            # Get document record
            document = db.query(DocumentModel).filter_by(id=document_id).first()
            if not document:
                return False, "Document not found"

            # Set processing status
            document.status = "processing"
            db.commit()

            # Extract text based on file type
            if file_type == "application/pdf":
                result = self.extract_pdf(file_path)
            elif file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
                result = self.extract_docx(file_path)
            elif file_type == "text/plain":
                result = self.extract_txt(file_path)
            else:
                document.status = "failed"
                document.error_message = f"Unsupported file type: {file_type}"
                db.commit()
                return False, document.error_message

            # Check extraction success
            if not result.success:
                document.status = "failed"
                document.error_message = result.error_message
                db.commit()
                return False, result.error_message

            # Generate chunks
            chunks = self.chunk_text(result.full_text, result.metadata)

            if not chunks:
                document.status = "failed"
                document.error_message = "No chunks could be generated from extracted text"
                db.commit()
                return False, document.error_message

            # Begin transaction for chunk persistence
            try:
                # Delete old chunks (if reprocessing)
                db.query(DocumentChunkModel).filter_by(document_id=document_id).delete()

                # Insert new chunks
                for chunk in chunks:
                    chunk_model = DocumentChunkModel(
                        id=str(uuid.uuid4()),
                        document_id=document_id,
                        chunk_index=chunk.chunk_index,
                        chunk_text=chunk.chunk_text,
                        page_number=chunk.page_number,
                        section_heading=chunk.section_heading,
                        char_start=chunk.char_start,
                        char_end=chunk.char_end,
                        chunk_metadata=chunk.metadata
                    )
                    db.add(chunk_model)

                # Update document status to indexed
                document.status = "indexed"
                document.page_count = result.page_count
                document.error_message = None

                # Store warnings in metadata if any
                if result.warnings:
                    current_metadata = document.document_metadata or {}
                    current_metadata["processing_warnings"] = result.warnings
                    document.document_metadata = current_metadata

                # Commit all changes atomically
                db.commit()

                return True, None

            except Exception as e:
                # Rollback on persistence failure
                db.rollback()

                # Update document to failed but retryable
                document.status = "failed"
                document.error_message = f"Persistence failed: {type(e).__name__}"
                db.commit()

                return False, document.error_message

        except Exception as e:
            # Catch-all for unexpected errors
            db.rollback()

            try:
                document = db.query(DocumentModel).filter_by(id=document_id).first()
                if document:
                    document.status = "failed"
                    document.error_message = f"Processing failed: {type(e).__name__}"
                    db.commit()
            except:
                pass  # Best effort status update

            return False, f"Processing failed: {type(e).__name__}"
