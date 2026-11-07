"""
File Upload Service for BrandSentinel AI.

Handles secure file upload, validation, storage, and processing integration.
Phase 3: Upload API and local storage.
"""
import os
import uuid
import shutil
import mimetypes
from pathlib import Path
from typing import Tuple, Optional

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DocumentModel
from app.services.document_processor import DocumentProcessor


# File signature magic bytes for validation
FILE_SIGNATURES = {
    "application/pdf": [
        b"%PDF-",  # PDF files start with %PDF-
    ],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
        b"PK\x03\x04",  # DOCX is a ZIP archive
    ],
    "application/msword": [
        b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1",  # DOC files (OLE2)
    ],
    "text/plain": [
        # Text files don't have a reliable signature, validate by content
    ],
}


class UploadService:
    """
    Secure file upload service with validation and storage.

    Features:
    - Size limit enforcement (streaming)
    - Extension and MIME type validation
    - File signature verification
    - Path traversal prevention
    - Server-generated filenames
    - Atomic file writes
    - Cleanup on failure
    """

    def __init__(self):
        """Initialize upload service with configuration."""
        # Note: Use settings properties dynamically instead of caching
        # to support test overrides
        pass

    @property
    def storage_root(self):
        """Get storage root from current settings."""
        storage_path = settings.upload_storage_path
        # Ensure storage directory exists
        storage_path.mkdir(parents=True, exist_ok=True)
        return storage_path

    @property
    def max_size_bytes(self):
        """Get max size from current settings."""
        return settings.upload_max_size_bytes

    @property
    def allowed_extensions(self):
        """Get allowed extensions from current settings."""
        return settings.upload_allowed_extensions_list

    @property
    def allowed_mimetypes(self):
        """Get allowed MIME types from current settings."""
        return settings.upload_allowed_mimetypes_list

    def validate_filename(self, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate original filename for security issues.

        Args:
            filename: Original filename from upload

        Returns:
            (is_valid, error_message) tuple
        """
        if not filename:
            return False, "Filename is empty"

        # Check for path traversal attempts
        if ".." in filename or "/" in filename or "\\" in filename:
            return False, "Filename contains invalid path characters"

        # Check for absolute paths
        if os.path.isabs(filename):
            return False, "Absolute paths are not allowed"

        # Check for null bytes (raw or URL-encoded by the client layer)
        if "\x00" in filename or "%00" in filename:
            return False, "Filename contains null bytes"

        # Check length
        if len(filename) > 255:
            return False, "Filename is too long (max 255 characters)"

        return True, None

    def validate_extension(self, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate file extension.

        Args:
            filename: Original filename

        Returns:
            (is_valid, error_message) tuple
        """
        file_ext = Path(filename).suffix.lower()

        if not file_ext:
            return False, "File has no extension"

        if file_ext not in self.allowed_extensions:
            return False, f"File type not supported. Allowed: {', '.join(self.allowed_extensions)}"

        return True, None

    def validate_mime_type(self, content_type: str) -> Tuple[bool, Optional[str]]:
        """
        Validate MIME type.

        Args:
            content_type: MIME type from upload

        Returns:
            (is_valid, error_message) tuple
        """
        if not content_type:
            return False, "No content type provided"

        # Normalize MIME type (remove parameters like charset)
        mime_type = content_type.split(";")[0].strip().lower()

        if mime_type not in self.allowed_mimetypes:
            return False, f"MIME type not supported. Allowed: {', '.join(self.allowed_mimetypes)}"

        return True, None

    def validate_file_signature(self, file_path: Path, expected_mime: str) -> Tuple[bool, Optional[str]]:
        """
        Validate file signature (magic bytes).

        Args:
            file_path: Path to uploaded file
            expected_mime: Expected MIME type

        Returns:
            (is_valid, error_message) tuple
        """
        expected_mime = expected_mime.split(";")[0].strip().lower()

        # Text files don't have reliable signatures
        if expected_mime == "text/plain":
            return True, None

        signatures = FILE_SIGNATURES.get(expected_mime, [])
        if not signatures:
            # Unknown MIME type, skip signature check
            return True, None

        try:
            with open(file_path, "rb") as f:
                header = f.read(512)  # Read first 512 bytes

            # Check if file starts with any of the expected signatures
            for signature in signatures:
                if header.startswith(signature):
                    return True, None

            return False, "File signature does not match declared type"

        except Exception as e:
            return False, f"Could not read file for signature validation"

    def generate_storage_filename(self, original_filename: str) -> str:
        """
        Generate secure server-side storage filename.

        Args:
            original_filename: Original filename (for extension)

        Returns:
            Generated filename (UUID + extension)
        """
        file_ext = Path(original_filename).suffix.lower()
        return f"{uuid.uuid4()}{file_ext}"

    def get_storage_path(self, storage_filename: str) -> Path:
        """
        Get full storage path, ensuring it's within storage root.

        Args:
            storage_filename: Server-generated filename

        Returns:
            Resolved Path object
        """
        storage_path = (self.storage_root / storage_filename).resolve()

        # Ensure path is within storage root (prevent path traversal)
        if not str(storage_path).startswith(str(self.storage_root.resolve())):
            raise ValueError("Path traversal detected")

        return storage_path

    async def save_upload(
        self,
        file: UploadFile,
        temp_dir: Optional[Path] = None
    ) -> Tuple[Path, int]:
        """
        Save uploaded file with streaming size enforcement.

        Args:
            file: FastAPI UploadFile
            temp_dir: Optional temporary directory (for testing)

        Returns:
            (temp_file_path, file_size) tuple

        Raises:
            HTTPException: If file is too large or empty
        """
        # Use provided temp directory or create one in storage root
        if temp_dir is None:
            temp_dir = self.storage_root / "temp"
            temp_dir.mkdir(exist_ok=True)

        temp_filename = f"upload_{uuid.uuid4()}.tmp"
        temp_path = temp_dir / temp_filename

        # Track whether we exceeded the size limit while streaming
        size_exceeded = False
        bytes_written = 0

        try:
            with open(temp_path, "wb") as f:
                # Stream file in chunks, enforcing size limit
                while chunk := await file.read(8192):  # 8KB chunks
                    bytes_written += len(chunk)

                    if bytes_written > self.max_size_bytes:
                        # Mark limit exceeded; close file cleanly before unlinking
                        # (Windows locks open files — unlink must happen after close)
                        size_exceeded = True
                        break

                    f.write(chunk)
            # File is now closed — safe to unlink on all platforms

        except Exception as e:
            # Clean up temp file on unexpected I/O error
            temp_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=500,
                detail="File upload failed"
            )

        if size_exceeded:
            temp_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.upload_max_size_mb} MB"
            )

        # Check if file is empty
        if bytes_written == 0:
            temp_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail="File is empty"
            )

        return temp_path, bytes_written

    async def process_upload(
        self,
        file: UploadFile,
        title: Optional[str],
        category: str,
        tags: Optional[list],
        db: Session,
        temp_dir: Optional[Path] = None
    ) -> DocumentModel:
        """
        Process file upload end-to-end.

        Steps:
        1. Validate filename, extension, MIME type
        2. Stream file to temporary location with size enforcement
        3. Validate file signature
        4. Generate server-side filename
        5. Create database record
        6. Move file to final location
        7. Invoke document processor
        8. Cleanup on failure

        Args:
            file: FastAPI UploadFile
            title: Optional document title
            category: Document category
            tags: Optional tags list
            db: Database session
            temp_dir: Optional temp directory (for testing)

        Returns:
            Created DocumentModel

        Raises:
            HTTPException: On validation or processing failures
        """
        original_filename = file.filename or "untitled"
        content_type = file.content_type or ""

        # Validate original filename
        valid, error = self.validate_filename(original_filename)
        if not valid:
            raise HTTPException(status_code=400, detail=error)

        # Validate extension
        valid, error = self.validate_extension(original_filename)
        if not valid:
            raise HTTPException(status_code=400, detail=error)

        # Validate MIME type
        valid, error = self.validate_mime_type(content_type)
        if not valid:
            raise HTTPException(status_code=400, detail=error)

        # Save to temporary location with size enforcement
        temp_path, file_size = await self.save_upload(file, temp_dir)

        try:
            # Validate file signature
            valid, error = self.validate_file_signature(temp_path, content_type)
            if not valid:
                raise HTTPException(status_code=400, detail=error)

            # Generate server-side filename
            storage_filename = self.generate_storage_filename(original_filename)
            storage_path = self.get_storage_path(storage_filename)

            # Ensure storage path doesn't exist (prevent collisions)
            if storage_path.exists():
                # UUID collision is extremely unlikely, but handle it
                storage_filename = self.generate_storage_filename(original_filename)
                storage_path = self.get_storage_path(storage_filename)

            # Create database record
            doc_id = str(uuid.uuid4())
            document = DocumentModel(
                id=doc_id,
                filename=original_filename,
                file_type=content_type.split(";")[0].strip(),
                file_size=file_size,
                storage_path=storage_filename,  # Store relative path only
                title=title or Path(original_filename).stem,
                category=category,
                status="uploading",
                tags=tags or []
            )

            db.add(document)
            db.commit()
            db.refresh(document)

            # Move file to final location atomically
            shutil.move(str(temp_path), str(storage_path))

            # Invoke Phase 2 document processor
            processor = DocumentProcessor()
            success, error_message = processor.process_and_persist(
                document_id=doc_id,
                file_path=storage_path,
                file_type=document.file_type,
                db=db
            )

            # Refresh to get updated status
            db.refresh(document)

            return document

        except HTTPException:
            # Clean up temp file and database record
            temp_path.unlink(missing_ok=True)
            if 'document' in locals():
                db.delete(document)
                db.commit()
            raise

        except Exception as e:
            # Clean up temp file and database record
            temp_path.unlink(missing_ok=True)
            if 'document' in locals():
                db.delete(document)
                db.commit()
            raise HTTPException(
                status_code=500,
                detail="Upload processing failed"
            )


upload_service = UploadService()
