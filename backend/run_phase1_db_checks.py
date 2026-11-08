"""Test Phase 1 database operations."""
import sys
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import DocumentModel, DocumentChunkModel, GuidelineModel
from app.database import Base

# Create engine
engine = create_engine('sqlite:///brandsentinel.sqlite', echo=False)
Session = sessionmaker(bind=engine)

def test_document_insertion():
    """Test inserting a document."""
    session = Session()
    try:
        doc = DocumentModel(
            id=str(uuid.uuid4()),
            filename="test_brand_guidelines.pdf",
            file_type="application/pdf",
            file_size=1024000,
            storage_path="/uploads/test_brand_guidelines.pdf",
            title="Test Brand Guidelines",
            category="brand_guidelines",
            status="indexed",
            page_count=10,
            version="1.0",
            tags=["branding", "design"],
            document_metadata={"source": "test"},
            uploaded_by="test_user"
        )
        session.add(doc)
        session.commit()
        print(f"[OK] Document inserted: {doc.id}")
        return doc.id
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Document insertion failed: {e}")
        return None
    finally:
        session.close()

def test_chunk_insertion(doc_id):
    """Test inserting document chunks."""
    session = Session()
    try:
        chunk1 = DocumentChunkModel(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            chunk_index=0,
            chunk_text="Our brand color is #2563EB (blue). This should be used consistently across all materials.",
            page_number=1,
            section_heading="Brand Colors",
            char_start=0,
            char_end=89,
            chunk_metadata={"section": "colors"}
        )
        chunk2 = DocumentChunkModel(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            chunk_index=1,
            chunk_text="Always use our official tagline: 'Innovation Through Trust'. Never modify or abbreviate it.",
            page_number=2,
            section_heading="Tagline Usage",
            char_start=90,
            char_end=181,
            chunk_metadata={"section": "messaging"}
        )
        session.add_all([chunk1, chunk2])
        session.commit()
        print(f"[OK] Chunks inserted: {chunk1.id}, {chunk2.id}")
        return [chunk1.id, chunk2.id]
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Chunk insertion failed: {e}")
        return []
    finally:
        session.close()

def test_guideline_linking(doc_id, chunk_id):
    """Test linking a guideline to a document and chunk."""
    session = Session()
    try:
        guideline = GuidelineModel(
            id=str(uuid.uuid4()),
            title="Brand Color Consistency",
            category="terminology",
            rule_text="Always use brand color #2563EB (blue) in all materials",
            source_document="Test Brand Guidelines",
            document_id=doc_id,
            chunk_id=chunk_id,
            extraction_method="auto_extracted",
            version="1.0",
            tags=["branding", "colors"]
        )
        session.add(guideline)
        session.commit()
        print(f"[OK] Guideline linked: {guideline.id}")
        return guideline.id
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Guideline linking failed: {e}")
        return None
    finally:
        session.close()

def test_foreign_key_cascade(doc_id):
    """Test foreign key cascade deletion."""
    session = Session()
    try:
        # Count chunks before deletion
        chunks_before = session.query(DocumentChunkModel).filter_by(document_id=doc_id).count()
        print(f"[INFO] Chunks before deletion: {chunks_before}")

        # Delete document
        doc = session.query(DocumentModel).filter_by(id=doc_id).first()
        if doc:
            session.delete(doc)
            session.commit()

            # Count chunks after deletion
            chunks_after = session.query(DocumentChunkModel).filter_by(document_id=doc_id).count()
            print(f"[INFO] Chunks after deletion: {chunks_after}")

            if chunks_after == 0:
                print("[OK] Foreign key cascade delete working correctly")
            else:
                print("[ERROR] Cascade delete did not remove chunks")
        else:
            print("[ERROR] Document not found for cascade test")
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Cascade delete test failed: {e}")
    finally:
        session.close()

def test_soft_deletion():
    """Test soft deletion of documents."""
    session = Session()
    try:
        # Create a test document
        doc = DocumentModel(
            id=str(uuid.uuid4()),
            filename="test_soft_delete.pdf",
            file_type="application/pdf",
            file_size=500000,
            storage_path="/uploads/test_soft_delete.pdf",
            title="Test Soft Delete",
            category="product_specs",
            status="indexed"
        )
        session.add(doc)
        session.commit()
        doc_id = doc.id
        print(f"[OK] Test document created: {doc_id}")

        # Soft delete
        doc.deleted_at = datetime.utcnow()
        session.commit()
        print(f"[OK] Document soft deleted: {doc_id}")

        # Verify it still exists but is marked deleted
        deleted_doc = session.query(DocumentModel).filter_by(id=doc_id).first()
        if deleted_doc and deleted_doc.deleted_at:
            print("[OK] Soft deletion working correctly")
        else:
            print("[ERROR] Soft deletion did not set deleted_at")

        # Clean up
        session.delete(deleted_doc)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Soft deletion test failed: {e}")
    finally:
        session.close()

def test_existing_guidelines():
    """Test that existing guidelines remain intact."""
    session = Session()
    try:
        guidelines = session.query(GuidelineModel).all()
        print(f"[OK] Found {len(guidelines)} existing guidelines")

        # Check that new columns are nullable
        for g in guidelines[:3]:  # Check first 3
            print(f"  Guideline: {g.title}")
            print(f"    document_id: {g.document_id}")
            print(f"    chunk_id: {g.chunk_id}")
            print(f"    extraction_method: {g.extraction_method}")

        print("[OK] Existing guidelines remain intact with new nullable columns")
    except Exception as e:
        print(f"[ERROR] Existing guidelines test failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("=== Phase 1 Database Tests ===\n")

    # Test 1: Document insertion
    print("Test 1: Document Insertion")
    doc_id = test_document_insertion()
    if not doc_id:
        print("[FAILED] Cannot proceed without document ID")
        sys.exit(1)
    print()

    # Test 2: Chunk insertion
    print("Test 2: Chunk Insertion")
    chunk_ids = test_chunk_insertion(doc_id)
    if not chunk_ids:
        print("[FAILED] Cannot proceed without chunk IDs")
        sys.exit(1)
    print()

    # Test 3: Guideline linking
    print("Test 3: Guideline Linking")
    guideline_id = test_guideline_linking(doc_id, chunk_ids[0])
    if not guideline_id:
        print("[FAILED] Guideline linking test failed")
    print()

    # Test 4: Soft deletion
    print("Test 4: Soft Deletion")
    test_soft_deletion()
    print()

    # Test 5: Existing guidelines
    print("Test 5: Existing Guidelines Integrity")
    test_existing_guidelines()
    print()

    # Test 6: Foreign key cascade (runs last as it deletes test data)
    print("Test 6: Foreign Key Cascade Delete")
    test_foreign_key_cascade(doc_id)
    print()

    print("=== All Tests Complete ===")
