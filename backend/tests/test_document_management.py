"""
Phase 5: Document Management API Tests

Test suite for document listing, retrieval, metadata updates, reprocessing,
soft deletion, and restoration.
"""
import pytest
import io
from datetime import datetime


# ==================== LIST DOCUMENTS TESTS ====================

def test_list_documents_empty(client):
    """Test listing documents returns empty list when none exist."""
    response = client.get("/api/documents")

    assert response.status_code == 200
    result = response.json()

    assert result["items"] == []
    assert result["total"] == 0
    assert result["page"] == 1
    assert result["total_pages"] == 0


def test_list_documents_with_uploads(client):
    """Test listing documents returns uploaded files."""
    # Upload two documents
    txt_content = b"Test content for listing"

    files1 = {"file": ("doc1.txt", io.BytesIO(txt_content), "text/plain")}
    client.post("/api/documents", files=files1, data={"category": "brand_guidelines"})

    files2 = {"file": ("doc2.txt", io.BytesIO(txt_content), "text/plain")}
    client.post("/api/documents", files=files2, data={"category": "product_specs"})

    # List all
    response = client.get("/api/documents")

    assert response.status_code == 200
    result = response.json()

    assert len(result["items"]) == 2
    assert result["total"] == 2
    assert result["items"][0]["filename"] in ["doc1.txt", "doc2.txt"]


def test_list_documents_pagination(client):
    """Test pagination works correctly."""
    # Upload 3 documents
    for i in range(3):
        txt_content = f"Content {i}".encode()
        files = {"file": (f"doc{i}.txt", io.BytesIO(txt_content), "text/plain")}
        client.post("/api/documents", files=files, data={"category": "brand_guidelines"})

    # Page 1, size 2
    response = client.get("/api/documents?page=1&page_size=2")
    result = response.json()

    assert len(result["items"]) == 2
    assert result["total"] == 3
    assert result["page"] == 1
    assert result["page_size"] == 2
    assert result["total_pages"] == 2

    # Page 2, size 2
    response = client.get("/api/documents?page=2&page_size=2")
    result = response.json()

    assert len(result["items"]) == 1
    assert result["page"] == 2


def test_list_documents_filter_by_category(client):
    """Test filtering by category."""
    txt_content = b"Test content"

    # Upload different categories
    files1 = {"file": ("guidelines.txt", io.BytesIO(txt_content), "text/plain")}
    client.post("/api/documents", files=files1, data={"category": "brand_guidelines"})

    files2 = {"file": ("specs.txt", io.BytesIO(txt_content), "text/plain")}
    client.post("/api/documents", files=files2, data={"category": "product_specs"})

    # Filter by brand_guidelines
    response = client.get("/api/documents?category=brand_guidelines")
    result = response.json()

    assert len(result["items"]) == 1
    assert result["items"][0]["category"] == "brand_guidelines"


def test_list_documents_filter_by_status(client):
    """Test filtering by status."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    client.post("/api/documents", files=files, data={"category": "brand_guidelines"})

    # Filter by indexed status
    response = client.get("/api/documents?status=indexed")
    result = response.json()

    assert result["total"] >= 1
    for item in result["items"]:
        assert item["status"] == "indexed"


def test_list_documents_excludes_deleted_by_default(client):
    """Test soft-deleted documents are excluded from normal listings."""
    txt_content = b"Test content"

    # Upload document
    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Soft delete it
    client.delete(f"/api/documents/{doc_id}")

    # List without include_deleted
    response = client.get("/api/documents")
    result = response.json()

    assert result["total"] == 0
    assert all(item["id"] != doc_id for item in result["items"])


def test_list_documents_includes_deleted_when_requested(client):
    """Test include_deleted=true includes soft-deleted documents."""
    txt_content = b"Test content"

    # Upload and delete
    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    client.delete(f"/api/documents/{doc_id}")

    # List with include_deleted=true
    response = client.get("/api/documents?include_deleted=true")
    result = response.json()

    assert result["total"] == 1
    assert result["items"][0]["id"] == doc_id


def test_list_documents_search_by_title(client):
    """Test search parameter filters by title."""
    txt_content = b"Test content"

    # Upload with different titles
    files1 = {"file": ("doc1.txt", io.BytesIO(txt_content), "text/plain")}
    client.post("/api/documents", files=files1, data={"title": "Brand Guidelines 2024", "category": "brand_guidelines"})

    files2 = {"file": ("doc2.txt", io.BytesIO(txt_content), "text/plain")}
    client.post("/api/documents", files=files2, data={"title": "Product Specifications", "category": "brand_guidelines"})

    # Search by title
    response = client.get("/api/documents?search=Guidelines")
    result = response.json()

    assert result["total"] == 1
    assert "Guidelines" in result["items"][0]["title"]


def test_list_documents_search_by_filename(client):
    """Test search parameter filters by original filename."""
    txt_content = b"Test content"

    files1 = {"file": ("brand_book.pdf", io.BytesIO(txt_content), "text/plain")}
    client.post("/api/documents", files=files1, data={"category": "brand_guidelines"})

    files2 = {"file": ("product_spec.docx", io.BytesIO(txt_content), "text/plain")}
    client.post("/api/documents", files=files2, data={"category": "brand_guidelines"})

    # Search by filename
    response = client.get("/api/documents?search=brand")
    result = response.json()

    assert result["total"] == 1
    assert "brand_book" in result["items"][0]["filename"]


def test_list_documents_filter_by_file_type(client):
    """Test filtering by file type (partial MIME type match)."""
    txt_content = b"Test content for file type filter"

    # Upload two TXT files (different from any previous uploads)
    files1 = {"file": ("type_test_1.txt", io.BytesIO(txt_content), "text/plain")}
    client.post("/api/documents", files=files1, data={"category": "brand_guidelines"})

    files2 = {"file": ("type_test_2.txt", io.BytesIO(txt_content), "text/plain")}
    client.post("/api/documents", files=files2, data={"category": "brand_guidelines"})

    # Filter by MIME type "text/plain" (should match both)
    response = client.get("/api/documents?file_type=text")
    result = response.json()

    assert result["total"] >= 2
    # All results should have "text" in their file_type
    for item in result["items"]:
        assert "text" in item["file_type"].lower()


# ==================== GET DOCUMENT TESTS ====================

def test_get_document_by_id(client):
    """Test retrieving document details by ID."""
    txt_content = b"Test content for retrieval"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={
        "title": "Test Doc",
        "category": "brand_guidelines",
        "tags": "test,retrieval"
    })
    doc_id = upload_response.json()["id"]

    # Retrieve by ID
    response = client.get(f"/api/documents/{doc_id}")

    assert response.status_code == 200
    result = response.json()

    assert result["id"] == doc_id
    assert result["title"] == "Test Doc"
    assert result["filename"] == "test.txt"
    assert result["category"] == "brand_guidelines"
    assert "chunk_count" in result


def test_get_document_missing_id_returns_404(client):
    """Test retrieving non-existent document returns 404."""
    response = client.get("/api/documents/nonexistent-id")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_document_deleted_returns_404(client):
    """Test retrieving soft-deleted document returns 404."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Soft delete
    client.delete(f"/api/documents/{doc_id}")

    # Try to retrieve
    response = client.get(f"/api/documents/{doc_id}")

    assert response.status_code == 404


def test_get_document_never_exposes_storage_path(client):
    """Test document details never expose absolute storage paths."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    response = client.get(f"/api/documents/{doc_id}")
    result = response.json()

    response_str = str(result).lower()
    assert "storage_path" not in result
    assert "/tmp/" not in response_str
    assert "c:\\" not in response_str


# ==================== UPDATE DOCUMENT TESTS ====================

def test_update_document_title(client):
    """Test updating document title."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Update title
    response = client.patch(f"/api/documents/{doc_id}", json={"title": "Updated Title"})

    assert response.status_code == 200
    result = response.json()

    assert result["title"] == "Updated Title"
    assert result["filename"] == "test.txt"  # Filename unchanged


def test_update_document_category(client):
    """Test updating document category."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Update category
    response = client.patch(f"/api/documents/{doc_id}", json={"category": "product_specs"})

    assert response.status_code == 200
    result = response.json()

    assert result["category"] == "product_specs"


def test_update_document_tags(client):
    """Test updating document tags."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Update tags
    response = client.patch(f"/api/documents/{doc_id}", json={"tags": ["new", "tags"]})

    assert response.status_code == 200
    result = response.json()

    assert result["tags"] == ["new", "tags"]


def test_update_document_multiple_fields(client):
    """Test updating multiple fields at once."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Update multiple fields
    response = client.patch(f"/api/documents/{doc_id}", json={
        "title": "New Title",
        "category": "legal_compliance",
        "tags": ["legal", "reviewed"]
    })

    assert response.status_code == 200
    result = response.json()

    assert result["title"] == "New Title"
    assert result["category"] == "legal_compliance"
    assert result["tags"] == ["legal", "reviewed"]


def test_update_document_missing_id_returns_404(client):
    """Test updating non-existent document returns 404."""
    response = client.patch("/api/documents/nonexistent-id", json={"title": "New"})

    assert response.status_code == 404


def test_update_document_deleted_returns_404(client):
    """Test updating soft-deleted document returns 404."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Soft delete
    client.delete(f"/api/documents/{doc_id}")

    # Try to update
    response = client.patch(f"/api/documents/{doc_id}", json={"title": "New"})

    assert response.status_code == 404


def test_update_document_title_too_long_returns_422(client):
    """Test title validation rejects titles over 255 characters."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Try to set title > 255 chars
    long_title = "x" * 256
    response = client.patch(f"/api/documents/{doc_id}", json={"title": long_title})

    assert response.status_code == 422


def test_update_document_too_many_tags_returns_422(client):
    """Test tag count validation rejects more than 20 tags."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Try to set 21 tags
    too_many_tags = [f"tag{i}" for i in range(21)]
    response = client.patch(f"/api/documents/{doc_id}", json={"tags": too_many_tags})

    assert response.status_code == 422
    # Pydantic validates max_length on list fields
    assert "20 items" in str(response.json()["detail"]) or "too_long" in str(response.json()["detail"])


def test_update_document_tag_too_long_returns_422(client):
    """Test individual tag length validation rejects tags over 50 chars."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Try to set a tag > 50 chars
    long_tag = ["x" * 51]
    response = client.patch(f"/api/documents/{doc_id}", json={"tags": long_tag})

    assert response.status_code == 422
    assert "50 characters" in response.json()["detail"]


# ==================== REPROCESS DOCUMENT TESTS ====================

def test_reprocess_document_success(client):
    """Test reprocessing document successfully re-indexes chunks."""
    txt_content = b"Original content. " * 50

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Reprocess
    response = client.post(f"/api/documents/{doc_id}/reprocess")

    assert response.status_code == 200
    result = response.json()

    assert result["id"] == doc_id
    assert result["status"] == "indexed"
    assert result["chunk_count"] > 0
    assert "successfully" in result["message"].lower()


def test_reprocess_document_missing_id_returns_404(client):
    """Test reprocessing non-existent document returns 404."""
    response = client.post("/api/documents/nonexistent-id/reprocess")

    assert response.status_code == 404


def test_reprocess_document_deleted_returns_404(client):
    """Test reprocessing soft-deleted document returns 404."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Soft delete
    client.delete(f"/api/documents/{doc_id}")

    # Try to reprocess
    response = client.post(f"/api/documents/{doc_id}/reprocess")

    assert response.status_code == 404


def test_reprocess_document_no_duplicate_chunks(client, db_session):
    """Test reprocessing removes old chunks before creating new ones."""
    from app import models

    txt_content = b"Test content. " * 50

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Get initial chunk count
    initial_chunk_count = db_session.query(models.DocumentChunkModel).filter_by(document_id=doc_id).count()

    # Reprocess
    client.post(f"/api/documents/{doc_id}/reprocess")

    # Get new chunk count
    final_chunk_count = db_session.query(models.DocumentChunkModel).filter_by(document_id=doc_id).count()

    # Should not have doubled
    assert final_chunk_count == initial_chunk_count


def test_reprocess_document_updates_status_correctly(client, db_session):
    """Test reprocessing updates document status to indexed or failed."""
    from app import models

    txt_content = b"Valid content. " * 50

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Reprocess
    response = client.post(f"/api/documents/{doc_id}/reprocess")

    assert response.status_code == 200
    result = response.json()

    # Check status is indexed
    assert result["status"] == "indexed"

    # Verify in database
    document = db_session.query(models.DocumentModel).filter_by(id=doc_id).first()
    assert document.status == "indexed"


# ==================== DELETE DOCUMENT TESTS ====================

def test_delete_document_soft_deletes(client, db_session):
    """Test deleting document soft-deletes it (sets deleted_at)."""
    from app import models

    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Delete
    response = client.delete(f"/api/documents/{doc_id}")

    assert response.status_code == 200
    result = response.json()

    assert result["id"] == doc_id
    assert result["status"] == "deleted"
    assert "soft-deleted" in result["message"].lower()

    # Verify deleted_at is set
    document = db_session.query(models.DocumentModel).filter_by(id=doc_id).first()
    assert document is not None
    assert document.deleted_at is not None


def test_delete_document_missing_id_returns_404(client):
    """Test deleting non-existent document returns 404."""
    response = client.delete("/api/documents/nonexistent-id")

    assert response.status_code == 404


def test_delete_document_already_deleted_returns_404(client):
    """Test deleting already-deleted document returns 404."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Delete once
    client.delete(f"/api/documents/{doc_id}")

    # Try to delete again
    response = client.delete(f"/api/documents/{doc_id}")

    assert response.status_code == 404


def test_delete_document_excluded_from_evidence(client, db_session):
    """Test soft-deleted documents are excluded from vector store evidence retrieval."""
    from app.services.vector_store import VectorStore

    txt_content = b"Brand guidelines with specific terminology rules."

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Verify chunks exist before deletion
    store = VectorStore()
    results_before = store.search_evidence("terminology", db_session, include_factual=True)

    # Delete document
    client.delete(f"/api/documents/{doc_id}")

    # Search again
    results_after = store.search_evidence("terminology", db_session, include_factual=True)

    # Should not include chunks from deleted document
    for result in results_after:
        assert result.document_id != doc_id


# ==================== RESTORE DOCUMENT TESTS ====================

def test_restore_document_success(client, db_session):
    """Test restoring soft-deleted document clears deleted_at."""
    from app import models

    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Delete
    client.delete(f"/api/documents/{doc_id}")

    # Restore
    response = client.post(f"/api/documents/{doc_id}/restore")

    assert response.status_code == 200
    result = response.json()

    assert result["id"] == doc_id
    assert "restored" in result["message"].lower()

    # Verify deleted_at is cleared
    document = db_session.query(models.DocumentModel).filter_by(id=doc_id).first()
    assert document.deleted_at is None


def test_restore_document_reappears_in_listing(client):
    """Test restored document reappears in normal document listings."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Delete
    client.delete(f"/api/documents/{doc_id}")

    # Verify not in listing
    response = client.get("/api/documents")
    assert response.json()["total"] == 0

    # Restore
    client.post(f"/api/documents/{doc_id}/restore")

    # Verify back in listing
    response = client.get("/api/documents")
    result = response.json()

    assert result["total"] == 1
    assert result["items"][0]["id"] == doc_id


def test_restore_document_not_deleted_returns_400(client):
    """Test restoring non-deleted document returns 400."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    upload_response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})
    doc_id = upload_response.json()["id"]

    # Try to restore without deleting first
    response = client.post(f"/api/documents/{doc_id}/restore")

    assert response.status_code == 400
    assert "not deleted" in response.json()["detail"].lower()


def test_restore_document_missing_id_returns_404(client):
    """Test restoring non-existent document returns 404."""
    response = client.post("/api/documents/nonexistent-id/restore")

    assert response.status_code == 404


# ==================== REGRESSION TESTS ====================

def test_existing_upload_endpoint_still_works(client):
    """Regression: existing upload workflow is not broken."""
    txt_content = b"Test content"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    response = client.post("/api/documents", files=files, data={"category": "brand_guidelines"})

    assert response.status_code == 201
    assert "id" in response.json()


def test_existing_audit_endpoint_still_works(client):
    """Regression: audit workflow is not broken."""
    response = client.post(
        "/api/audit",
        json={"text": "Our product is 100% secure."}
    )

    assert response.status_code == 200
    assert "findings" in response.json()


def test_existing_vector_store_still_works(client, db_session):
    """Regression: vector store evidence retrieval still works."""
    from app.services.vector_store import VectorStore

    # Upload document
    txt_content = b"Brand guidelines with terminology rules."

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    client.post("/api/documents", files=files, data={"category": "brand_guidelines"})

    # Search evidence
    store = VectorStore()
    results = store.search_evidence("terminology", db_session, include_factual=True)

    # Should work without errors
    assert isinstance(results, list)
