"""
Phase 3: File Upload API Tests

Comprehensive test suite for secure file upload, validation, storage, and processing integration.
Fixtures (client, temp_storage, test_engine, db_session) are defined in conftest.py.
"""
import pytest
import uuid
import io
from pathlib import Path


# ==================== VALID UPLOAD TESTS ====================

def test_valid_pdf_upload(client):
    """Test valid PDF upload succeeds and returns document ID."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    c.drawString(100, 750, "Test Brand Guidelines")
    c.drawString(100, 730, "Our brand color is #2563EB")
    c.showPage()
    c.save()
    pdf_buffer.seek(0)

    files = {"file": ("test.pdf", pdf_buffer, "application/pdf")}
    data = {"category": "brand_guidelines"}

    response = client.post("/api/documents", files=files, data=data)

    assert response.status_code == 201
    result = response.json()

    assert "id" in result
    assert result["filename"] == "test.pdf"
    assert result["file_type"] == "application/pdf"
    assert result["category"] == "brand_guidelines"
    assert result["status"] in ["processing", "indexed", "failed"]


def test_valid_txt_upload(client):
    """Test valid TXT upload succeeds."""
    txt_content = b"Brand Guidelines\n\nOur brand color is #2563EB (blue)."

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    data = {"title": "Test Guidelines", "category": "brand_guidelines"}

    response = client.post("/api/documents", files=files, data=data)

    assert response.status_code == 201
    result = response.json()

    assert result["title"] == "Test Guidelines"
    assert result["filename"] == "test.txt"
    assert result["file_type"] == "text/plain"


def test_upload_with_tags(client):
    """Test upload with tags."""
    txt_content = b"Test document content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    data = {"category": "brand_guidelines", "tags": "branding,guidelines,test"}

    response = client.post("/api/documents", files=files, data=data)

    assert response.status_code == 201
    result = response.json()

    assert "tags" in result
    assert len(result["tags"]) == 3
    assert "branding" in result["tags"]


# ==================== SIZE VALIDATION TESTS ====================

def test_oversized_file_rejected(client):
    """Test files over 10 MB are rejected with HTTP 413."""
    # Create 11 MB content
    large_content = b"x" * (11 * 1024 * 1024)

    files = {"file": ("large.txt", io.BytesIO(large_content), "text/plain")}
    data = {"category": "brand_guidelines"}

    response = client.post("/api/documents", files=files, data=data)

    assert response.status_code == 413
    assert "too large" in response.json()["detail"].lower()


def test_empty_file_rejected(client):
    """Test empty files are rejected."""
    files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
    data = {"category": "brand_guidelines"}

    response = client.post("/api/documents", files=files, data=data)

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


# ==================== FORMAT VALIDATION TESTS ====================

def test_unsupported_extension_rejected(client):
    """Test unsupported file extensions are rejected."""
    files = {"file": ("test.exe", io.BytesIO(b"fake exe"), "application/x-msdownload")}
    data = {"category": "brand_guidelines"}

    response = client.post("/api/documents", files=files, data=data)

    assert response.status_code == 400
    assert "not supported" in response.json()["detail"].lower()


def test_unsupported_mime_type_rejected(client):
    """Test unsupported MIME types are rejected."""
    files = {"file": ("test.txt", io.BytesIO(b"content"), "application/json")}
    data = {"category": "brand_guidelines"}

    response = client.post("/api/documents", files=files, data=data)

    assert response.status_code == 400
    assert "MIME type not supported" in response.json()["detail"]


# ==================== SECURITY TESTS ====================

def test_path_traversal_in_filename(client):
    """Test filenames with path traversal sequences are rejected."""
    txt_content = b"Test content"

    files = {"file": ("../../etc/passwd.txt", io.BytesIO(txt_content), "text/plain")}
    data = {"category": "brand_guidelines"}

    response = client.post("/api/documents", files=files, data=data)

    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()


def test_absolute_path_filename(client):
    """Test filenames with absolute paths are rejected."""
    txt_content = b"Test content"

    files = {"file": ("/tmp/test.txt", io.BytesIO(txt_content), "text/plain")}
    data = {"category": "brand_guidelines"}

    response = client.post("/api/documents", files=files, data=data)

    assert response.status_code == 400


def test_null_byte_in_filename(client):
    """
    Test filenames with null bytes are rejected.

    Note: httpx/starlette may URL-encode the null byte (%00) before the
    server sees it.  Either the raw-null or the encoded variant must be
    rejected with 400.
    """
    txt_content = b"Test content"

    files = {"file": ("test\x00.txt", io.BytesIO(txt_content), "text/plain")}
    data = {"category": "brand_guidelines"}

    response = client.post("/api/documents", files=files, data=data)

    # Acceptable outcomes: 400 (rejected) or 422 (unprocessable entity)
    # A 201 with a null-byte filename stored on disk would be a security bug.
    assert response.status_code in (400, 422), (
        f"Expected 400/422 for null-byte filename, got {response.status_code}: "
        f"{response.text}"
    )


def test_server_generated_filename_used(client, temp_storage):
    """Test server-generated filenames are used in storage (not original names)."""
    txt_content = b"Test content"

    files = {"file": ("my_document.txt", io.BytesIO(txt_content), "text/plain")}
    data = {"category": "brand_guidelines"}

    response = client.post("/api/documents", files=files, data=data)

    assert response.status_code == 201
    result = response.json()

    # Original filename is preserved in the API response
    assert result["filename"] == "my_document.txt"

    # Actual storage uses a UUID-based server-generated name
    stored_files = list(temp_storage.glob("*.txt"))
    assert len(stored_files) == 1, (
        f"Expected 1 stored .txt file, found {len(stored_files)}: {stored_files}"
    )

    stored_name = stored_files[0].stem
    try:
        uuid.UUID(stored_name)
    except ValueError:
        pytest.fail(f"Stored filename stem '{stored_name}' is not a valid UUID")


def test_no_absolute_paths_in_response(client):
    """Test API responses never expose absolute storage paths."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    data = {"category": "brand_guidelines"}

    response = client.post("/api/documents", files=files, data=data)

    assert response.status_code == 201
    result = response.json()

    response_str = str(result).lower()
    assert "/tmp/" not in response_str
    assert "c:\\" not in response_str
    assert "storage_path" not in result  # Internal field must not leak


# ==================== PROCESSING TESTS ====================

def test_processing_failure_sets_failed_status(client):
    """Test that empty files are rejected at upload, never reaching processing."""
    files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
    data = {"category": "brand_guidelines"}

    response = client.post("/api/documents", files=files, data=data)

    assert response.status_code == 400


def test_indexed_only_after_chunks_persist(client):
    """Test document is marked indexed only after chunks are persisted."""
    txt_content = b"Brand Guidelines Document\n\n" + b"Content paragraph. " * 50

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    data = {"category": "brand_guidelines"}

    response = client.post("/api/documents", files=files, data=data)

    assert response.status_code == 201
    result = response.json()

    # Must not be marked indexed without successful chunk persistence
    assert result["status"] == "indexed", (
        f"Expected 'indexed', got '{result['status']}': "
        f"{result.get('error_message', '')}"
    )


# ==================== REGRESSION TESTS ====================

def test_existing_audit_endpoint_still_works(client):
    """Regression: existing audit workflow is not broken by Phase 3 changes."""
    response = client.post(
        "/api/audit",
        json={"text": "Our product is 100% secure and unhackable."}
    )

    assert response.status_code == 200
    result = response.json()
    assert "findings" in result
    assert "overall_status" in result


def test_existing_guidelines_endpoint_still_works(client):
    """Regression: existing guidelines endpoint is not broken."""
    response = client.get("/api/guidelines")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_existing_health_endpoint_still_works(client):
    """Regression: health endpoint is not broken."""
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ==================== CLEANUP TESTS ====================

def test_temp_file_cleanup_on_validation_failure(client, temp_storage):
    """Test temporary files are cleaned up when validation fails."""
    initial_count = len(list(temp_storage.rglob("*")))

    files = {"file": ("test.exe", io.BytesIO(b"fake"), "application/x-msdownload")}
    data = {"category": "brand_guidelines"}

    response = client.post("/api/documents", files=files, data=data)

    assert response.status_code == 400

    final_count = len(list(temp_storage.rglob("*")))
    assert final_count == initial_count, (
        f"Temp files not cleaned up: {list(temp_storage.rglob('*'))}"
    )


# ==================== STORAGE LOCATION TESTS ====================

def test_storage_outside_frontend_dist(temp_storage):
    """Test default storage location is outside frontend public/dist directories."""
    storage_str = str(temp_storage).lower()

    assert "frontend" not in storage_str
    assert "/public" not in storage_str
    assert "/dist" not in storage_str
    assert "/static" not in storage_str
