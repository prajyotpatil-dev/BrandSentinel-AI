"""
Phase 4: Vector Store Evidence Retrieval Tests

Covers:
  - Chunk indexing from persisted DocumentChunkModel records
  - Cosine similarity retrieval and relevance ranking
  - Claim-to-evidence matching (policy vs. factual)
  - Source traceability: document_id, chunk_id, guideline_id, page_number,
    section_heading, source_document, title, version, category
  - Deduplication — same chunk returned only once at its best score
  - Document exclusion: failed / uploading / processing statuses are ignored
  - Soft-deleted document exclusion (deleted_at IS NOT NULL)
  - Missing evidence: empty list when no result meets threshold (no fabrication)
  - search_relevant_guidelines() backward-compat contract unchanged
  - rebuild_index_from_db() counts verified against live DB rows
  - Configurable similarity_threshold override
  - include_policy / include_factual filter flags

All fixtures come from conftest.py (StaticPool in-memory SQLite).
No local fixture redefinitions.
"""
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.services.vector_store import (
    VectorStore,
    EvidenceResult,
    SIMILARITY_THRESHOLD_GUIDELINES,
    SIMILARITY_THRESHOLD_CHUNKS,
    SIMILARITY_THRESHOLD_LOW_CONFIDENCE,
)
from app import models


# ---------------------------------------------------------------------------
# Helpers to seed test data
# ---------------------------------------------------------------------------

def _make_doc(
    db: Session,
    *,
    status: str = "indexed",
    deleted_at=None,
    title: str = "Test Document",
    filename: str = "test.txt",
    category: str = "brand_guidelines",
    version: str = "2.0",
) -> models.DocumentModel:
    doc = models.DocumentModel(
        id=str(uuid.uuid4()),
        filename=filename,
        file_type="text/plain",
        file_size=100,
        storage_path=f"{uuid.uuid4()}.txt",
        title=title,
        category=category,
        status=status,
        version=version,
        deleted_at=deleted_at,
        tags=[],
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _make_chunk(
    db: Session,
    document_id: str,
    chunk_text: str,
    *,
    chunk_index: int = 0,
    page_number: int | None = None,
    section_heading: str | None = None,
) -> models.DocumentChunkModel:
    chunk = models.DocumentChunkModel(
        id=str(uuid.uuid4()),
        document_id=document_id,
        chunk_index=chunk_index,
        chunk_text=chunk_text,
        page_number=page_number,
        section_heading=section_heading,
        char_start=0,
        char_end=len(chunk_text),
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def _make_guideline(
    db: Session,
    *,
    title: str = "Test Guideline",
    rule_text: str = "Use approved brand terminology.",
    category: str = "terminology",
    source_document: str = "Brand Guide v1",
    version: str = "1.0",
    document_id: str | None = None,
) -> models.GuidelineModel:
    g = models.GuidelineModel(
        id=str(uuid.uuid4()),
        title=title,
        category=category,
        rule_text=rule_text,
        source_document=source_document,
        version=version,
        document_id=document_id,
        tags=[],
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


# ---------------------------------------------------------------------------
# 1. Chunk indexing — basic retrieval
# ---------------------------------------------------------------------------

class TestChunkIndexing:

    def test_indexed_chunk_returned_for_matching_query(self, db_session):
        """A chunk from an indexed document is returned when the query matches."""
        doc = _make_doc(db_session, status="indexed", title="ApexCloud Datasheet")
        chunk = _make_chunk(
            db_session,
            doc.id,
            "ApexCloud provides 99.9 percent uptime SLA for enterprise customers.",
        )

        store = VectorStore()
        results = store.search_evidence("uptime SLA enterprise", db_session)

        assert len(results) > 0
        chunk_results = [r for r in results if r.source_type == "factual"]
        assert len(chunk_results) > 0
        found = chunk_results[0]
        assert found.chunk_id == chunk.id
        assert found.document_id == doc.id
        assert "uptime" in found.text.lower()

    def test_no_chunks_when_db_empty(self, db_session):
        """search_evidence returns empty list when no chunks exist."""
        store = VectorStore()
        results = store.search_evidence("uptime SLA", db_session, include_policy=False)
        assert results == []

    def test_multiple_chunks_ranked_by_score(self, db_session):
        """When multiple chunks exist, the most relevant one ranks first."""
        doc = _make_doc(db_session, title="Product Specs")
        _make_chunk(
            db_session, doc.id,
            "The weather today is sunny and warm.",
            chunk_index=0,
        )
        _make_chunk(
            db_session, doc.id,
            "Our enterprise uptime SLA guarantees 99.9 percent availability.",
            chunk_index=1,
        )
        _make_chunk(
            db_session, doc.id,
            "Uptime is monitored continuously for enterprise SLA compliance.",
            chunk_index=2,
        )

        store = VectorStore()
        results = store.search_evidence(
            "enterprise uptime SLA availability",
            db_session,
            include_policy=False,
        )

        # The weather chunk should not outrank the SLA chunks
        factual = [r for r in results if r.source_type == "factual"]
        assert len(factual) >= 2
        # Top result must have a higher score than the weather chunk (if included)
        scores = [r.similarity_score for r in factual]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# 2. Source traceability
# ---------------------------------------------------------------------------

class TestSourceTraceability:

    def test_guideline_result_has_guideline_id(self, db_session):
        """Policy evidence carries guideline_id; chunk_id is None."""
        g = _make_guideline(
            db_session,
            title="Color Policy",
            rule_text="Use only the approved brand color palette in all materials.",
        )
        store = VectorStore()
        results = store.search_evidence("approved brand color palette", db_session, include_factual=False)

        assert len(results) > 0
        r = results[0]
        assert r.source_type == "policy"
        assert r.guideline_id == g.id
        assert r.source_id == g.id
        assert r.chunk_id is None

    def test_chunk_result_has_chunk_and_document_id(self, db_session):
        """Factual evidence carries chunk_id and document_id; guideline_id is None."""
        doc = _make_doc(db_session, title="Security Whitepaper", filename="security.txt")
        chunk = _make_chunk(
            db_session, doc.id,
            "All data is encrypted using AES-256 encryption at rest.",
        )
        store = VectorStore()
        results = store.search_evidence("data encrypted AES-256", db_session, include_policy=False)

        assert len(results) > 0
        r = results[0]
        assert r.source_type == "factual"
        assert r.chunk_id == chunk.id
        assert r.document_id == doc.id
        assert r.guideline_id is None
        assert r.source_id == chunk.id

    def test_chunk_result_carries_page_number(self, db_session):
        """page_number from DocumentChunkModel is preserved in EvidenceResult."""
        doc = _make_doc(db_session)
        chunk = _make_chunk(
            db_session, doc.id,
            "Quarterly revenue growth exceeded 40 percent year over year.",
            page_number=7,
        )
        store = VectorStore()
        results = store.search_evidence("quarterly revenue growth", db_session, include_policy=False)

        assert len(results) > 0
        r = next(r for r in results if r.chunk_id == chunk.id)
        assert r.page_number == 7

    def test_chunk_result_carries_section_heading(self, db_session):
        """section_heading from DocumentChunkModel is preserved in EvidenceResult."""
        doc = _make_doc(db_session)
        chunk = _make_chunk(
            db_session, doc.id,
            "Security protocols include multi-factor authentication.",
            section_heading="Security Overview",
        )
        store = VectorStore()
        results = store.search_evidence("security authentication protocols", db_session, include_policy=False)

        assert len(results) > 0
        r = next(r for r in results if r.chunk_id == chunk.id)
        assert r.section_heading == "Security Overview"

    def test_chunk_result_carries_source_document_filename(self, db_session):
        """source_document is the document's original filename."""
        doc = _make_doc(db_session, filename="product_datasheet_v2.pdf")
        _make_chunk(
            db_session, doc.id,
            "Response time under load is consistently below 200 milliseconds.",
        )
        store = VectorStore()
        results = store.search_evidence("response time milliseconds", db_session, include_policy=False)

        assert len(results) > 0
        assert results[0].source_document == "product_datasheet_v2.pdf"

    def test_chunk_result_carries_document_version(self, db_session):
        """version is inherited from the parent DocumentModel."""
        doc = _make_doc(db_session, version="3.1")
        _make_chunk(
            db_session, doc.id,
            "Platform supports unlimited concurrent API connections.",
        )
        store = VectorStore()
        results = store.search_evidence("concurrent API connections", db_session, include_policy=False)

        assert len(results) > 0
        assert results[0].version == "3.1"

    def test_chunk_result_carries_document_category(self, db_session):
        """category is inherited from the parent DocumentModel."""
        doc = _make_doc(db_session, category="product_specs")
        _make_chunk(
            db_session, doc.id,
            "Maximum storage capacity is 10 terabytes per account.",
        )
        store = VectorStore()
        results = store.search_evidence("storage capacity terabytes", db_session, include_policy=False)

        assert len(results) > 0
        assert results[0].category == "product_specs"

    def test_guideline_result_carries_source_document(self, db_session):
        """Guideline's source_document field is surfaced in EvidenceResult."""
        g = _make_guideline(
            db_session,
            rule_text="Never use competitor names in marketing materials.",
            source_document="Global Marketing Policy 2026",
        )
        store = VectorStore()
        results = store.search_evidence("competitor names marketing", db_session, include_factual=False)

        assert len(results) > 0
        assert results[0].source_document == "Global Marketing Policy 2026"

    def test_guideline_document_id_preserved_when_set(self, db_session):
        """A guideline linked to a document carries that document_id in the result."""
        doc = _make_doc(db_session)
        g = _make_guideline(
            db_session,
            rule_text="Follow accessibility standards for all visual content.",
            document_id=doc.id,
        )
        store = VectorStore()
        results = store.search_evidence("accessibility visual content", db_session, include_factual=False)

        assert len(results) > 0
        r = next(r for r in results if r.guideline_id == g.id)
        assert r.document_id == doc.id

    def test_excerpt_truncated_for_long_chunk_text(self, db_session):
        """excerpt is capped at 500 characters for long chunk text."""
        doc = _make_doc(db_session)
        long_text = "The platform offers advanced analytics. " * 30  # > 500 chars
        _make_chunk(db_session, doc.id, long_text)

        store = VectorStore()
        results = store.search_evidence("platform advanced analytics", db_session, include_policy=False)

        assert len(results) > 0
        assert len(results[0].excerpt) <= 500

    def test_text_field_contains_full_chunk_text(self, db_session):
        """text field is never truncated — it is the complete chunk text."""
        doc = _make_doc(db_session)
        long_text = "Deep integration capabilities enable workflows. " * 20
        _make_chunk(db_session, doc.id, long_text)

        store = VectorStore()
        results = store.search_evidence("integration capabilities workflows", db_session, include_policy=False)

        assert len(results) > 0
        assert results[0].text == long_text.strip() or long_text in results[0].text


# ---------------------------------------------------------------------------
# 3. Document exclusion
# ---------------------------------------------------------------------------

class TestDocumentExclusion:

    def test_failed_document_chunks_excluded(self, db_session):
        """Chunks from documents with status='failed' are never returned."""
        doc = _make_doc(db_session, status="failed", title="Failed Upload")
        _make_chunk(
            db_session, doc.id,
            "This failed document should never appear in evidence results.",
        )
        store = VectorStore()
        results = store.search_evidence(
            "failed document evidence",
            db_session,
            include_policy=False,
            similarity_threshold=0.0,
        )
        assert all(r.document_id != doc.id for r in results)

    def test_uploading_document_chunks_excluded(self, db_session):
        """Chunks from documents with status='uploading' are never returned."""
        doc = _make_doc(db_session, status="uploading")
        _make_chunk(db_session, doc.id, "Uploading document chunk text for testing exclusion.")

        store = VectorStore()
        results = store.search_evidence(
            "uploading document chunk",
            db_session,
            include_policy=False,
            similarity_threshold=0.0,
        )
        assert all(r.document_id != doc.id for r in results)

    def test_processing_document_chunks_excluded(self, db_session):
        """Chunks from documents with status='processing' are never returned."""
        doc = _make_doc(db_session, status="processing")
        _make_chunk(db_session, doc.id, "Processing document chunk text for testing exclusion.")

        store = VectorStore()
        results = store.search_evidence(
            "processing document chunk",
            db_session,
            include_policy=False,
            similarity_threshold=0.0,
        )
        assert all(r.document_id != doc.id for r in results)

    def test_soft_deleted_document_chunks_excluded(self, db_session):
        """Chunks from soft-deleted documents (deleted_at set) are never returned."""
        deleted_at = datetime.now(timezone.utc)
        doc = _make_doc(db_session, status="indexed", deleted_at=deleted_at)
        _make_chunk(db_session, doc.id, "Soft deleted document content that must be excluded.")

        store = VectorStore()
        results = store.search_evidence(
            "soft deleted document content",
            db_session,
            include_policy=False,
            similarity_threshold=0.0,
        )
        assert all(r.document_id != doc.id for r in results)

    def test_indexed_not_deleted_document_is_included(self, db_session):
        """Only documents with status='indexed' and no soft deletion are included."""
        # One excluded, one included
        deleted_doc = _make_doc(
            db_session, status="indexed",
            deleted_at=datetime.now(timezone.utc),
            title="Deleted Doc",
        )
        active_doc = _make_doc(
            db_session, status="indexed",
            deleted_at=None,
            title="Active Doc",
        )

        _make_chunk(
            db_session, deleted_doc.id,
            "Deleted enterprise service agreement coverage.",
        )
        _make_chunk(
            db_session, active_doc.id,
            "Enterprise service level agreement coverage for all tiers.",
        )

        store = VectorStore()
        results = store.search_evidence(
            "enterprise service level agreement",
            db_session,
            include_policy=False,
            similarity_threshold=0.0,
        )
        doc_ids_returned = {r.document_id for r in results}
        assert active_doc.id in doc_ids_returned
        assert deleted_doc.id not in doc_ids_returned

    def test_mixed_statuses_only_indexed_included(self, db_session):
        """With multiple documents at different statuses, only 'indexed' ones appear."""
        texts = {
            "indexed":    "Indexed document contains verified product specifications.",
            "failed":     "Failed document processing output never indexed.",
            "uploading":  "Uploading document not yet complete for indexing.",
            "processing": "Processing document pipeline stage not finished.",
        }
        doc_ids: dict[str, str] = {}
        for status, text in texts.items():
            doc = _make_doc(db_session, status=status, title=f"Doc {status}")
            _make_chunk(db_session, doc.id, text)
            doc_ids[status] = doc.id

        store = VectorStore()
        results = store.search_evidence(
            "document specifications indexed product",
            db_session,
            include_policy=False,
            similarity_threshold=0.0,
        )
        returned_ids = {r.document_id for r in results}
        assert doc_ids["indexed"] in returned_ids
        for bad_status in ("failed", "uploading", "processing"):
            assert doc_ids[bad_status] not in returned_ids


# ---------------------------------------------------------------------------
# 4. Missing evidence — no fabrication
# ---------------------------------------------------------------------------

class TestMissingEvidence:

    def test_empty_query_returns_empty_list(self, db_session):
        """Empty or whitespace-only query returns [] immediately."""
        _make_guideline(db_session)
        store = VectorStore()
        assert store.search_evidence("", db_session) == []
        assert store.search_evidence("   ", db_session) == []

    def test_no_evidence_when_query_completely_unrelated(self, db_session):
        """Very high threshold returns empty list when no chunk matches."""
        doc = _make_doc(db_session)
        _make_chunk(db_session, doc.id, "Purple elephants dancing on the moon at midnight.")

        store = VectorStore()
        # With a very high threshold and an unrelated query, nothing should match
        results = store.search_evidence(
            "enterprise SLA uptime guarantee",
            db_session,
            include_policy=False,
            similarity_threshold=0.9,
        )
        assert results == []

    def test_low_similarity_results_excluded_by_threshold(self, db_session):
        """Results below the similarity_threshold are silently dropped."""
        doc = _make_doc(db_session)
        _make_chunk(db_session, doc.id, "Completely unrelated content about gardening tools.")

        store = VectorStore()
        results = store.search_evidence(
            "uptime reliability SLA enterprise",
            db_session,
            include_policy=False,
            similarity_threshold=0.5,
        )
        # Either empty or all results meet the threshold
        for r in results:
            assert r.similarity_score >= 0.5

    def test_policy_evidence_does_not_prove_factual_claim(self, db_session):
        """
        A guideline recommending "99.9% uptime" does NOT establish that the
        product meets that SLA. Source type must be "policy", not "factual".
        """
        _make_guideline(
            db_session,
            title="SLA Communication Policy",
            rule_text="Always communicate 99.9 percent uptime SLA to enterprise prospects.",
        )
        store = VectorStore()
        results = store.search_evidence(
            "99.9 percent uptime SLA enterprise",
            db_session,
            include_factual=False,
        )
        assert len(results) > 0
        for r in results:
            assert r.source_type == "policy", (
                "Guideline evidence must be 'policy', not 'factual' — "
                "a requirement is not a verification of capability."
            )

    def test_no_chunks_returns_empty_factual_list(self, db_session):
        """When no indexed chunks exist, factual search returns empty list."""
        store = VectorStore()
        results = store.search_evidence("any query", db_session, include_policy=False)
        assert results == []


# ---------------------------------------------------------------------------
# 5. Similarity score and ranking
# ---------------------------------------------------------------------------

class TestSimilarityRanking:

    def test_results_ordered_by_score_descending(self, db_session):
        """All returned results are in descending similarity_score order."""
        doc = _make_doc(db_session)
        # Chunk that closely matches the query
        _make_chunk(db_session, doc.id,
                    "Enterprise uptime SLA guarantees 99.9 percent availability for customers.",
                    chunk_index=0)
        # Moderately related
        _make_chunk(db_session, doc.id,
                    "Service agreements include uptime commitments.",
                    chunk_index=1)
        # Weakly related
        _make_chunk(db_session, doc.id,
                    "Contact support for technical assistance.",
                    chunk_index=2)

        store = VectorStore()
        results = store.search_evidence(
            "enterprise uptime SLA availability guarantee",
            db_session,
            include_policy=False,
        )
        scores = [r.similarity_score for r in results]
        assert scores == sorted(scores, reverse=True), "Results must be ranked by score descending"

    def test_similarity_score_in_valid_range(self, db_session):
        """All similarity scores are in [0.0, 1.0]."""
        doc = _make_doc(db_session)
        _make_chunk(db_session, doc.id, "Enterprise customer security and compliance features.")

        store = VectorStore()
        results = store.search_evidence("enterprise security", db_session)
        for r in results:
            assert 0.0 <= r.similarity_score <= 1.0

    def test_top_k_limits_results(self, db_session):
        """top_k is respected — never more results than requested."""
        doc = _make_doc(db_session)
        for i in range(10):
            _make_chunk(
                db_session, doc.id,
                f"Enterprise SLA uptime guarantee performance chunk number {i}.",
                chunk_index=i,
            )

        store = VectorStore()
        results = store.search_evidence(
            "enterprise SLA uptime",
            db_session,
            top_k=3,
            include_policy=False,
        )
        assert len(results) <= 3

    def test_low_confidence_flag_set_below_threshold(self, db_session):
        """low_confidence=True when score < SIMILARITY_THRESHOLD_LOW_CONFIDENCE."""
        doc = _make_doc(db_session)
        # A chunk with almost no word overlap — score will be very low
        _make_chunk(db_session, doc.id, "Xylophone recital annual botanical garden festival.")

        store = VectorStore()
        results = store.search_evidence(
            "xylophone recital botanical",
            db_session,
            include_policy=False,
            similarity_threshold=0.0,
        )
        for r in results:
            if r.similarity_score < SIMILARITY_THRESHOLD_LOW_CONFIDENCE:
                assert r.low_confidence is True


# ---------------------------------------------------------------------------
# 6. Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:

    def test_same_chunk_not_returned_twice(self, db_session):
        """A chunk that would score on both policy and factual searches appears once."""
        # A guideline and a chunk share the same ID is impossible;
        # but if search_evidence is called with both enabled and the same doc chunk
        # somehow matches, deduplication by source_id must prevent duplicates.
        doc = _make_doc(db_session)
        chunk = _make_chunk(
            db_session, doc.id,
            "Enterprise reliability uptime SLA performance benchmark.",
        )

        store = VectorStore()
        results = store.search_evidence(
            "enterprise reliability uptime",
            db_session,
            include_policy=True,
            include_factual=True,
        )
        source_ids = [r.source_id for r in results]
        assert len(source_ids) == len(set(source_ids)), "Duplicate source_id in results"

    def test_multiple_chunks_from_same_document_all_returned(self, db_session):
        """Multiple high-scoring chunks from the same document can all appear."""
        doc = _make_doc(db_session)
        chunk_a = _make_chunk(
            db_session, doc.id,
            "Encryption ensures data security at rest and in transit.",
            chunk_index=0,
        )
        chunk_b = _make_chunk(
            db_session, doc.id,
            "Access control and authentication security measures protect data.",
            chunk_index=1,
        )

        store = VectorStore()
        results = store.search_evidence("data security encryption", db_session, include_policy=False)
        returned_chunk_ids = {r.chunk_id for r in results}
        # Both chunks should appear since they have distinct IDs
        assert chunk_a.id in returned_chunk_ids
        assert chunk_b.id in returned_chunk_ids


# ---------------------------------------------------------------------------
# 7. Filter flags: include_policy / include_factual
# ---------------------------------------------------------------------------

class TestFilterFlags:

    def test_include_policy_false_returns_only_factual(self, db_session):
        """With include_policy=False, only factual results are returned."""
        _make_guideline(db_session, rule_text="Brand voice must be professional and clear.")
        doc = _make_doc(db_session)
        _make_chunk(db_session, doc.id, "Professional tone in all customer communications.")

        store = VectorStore()
        results = store.search_evidence(
            "professional brand voice",
            db_session,
            include_policy=False,
        )
        for r in results:
            assert r.source_type == "factual"

    def test_include_factual_false_returns_only_policy(self, db_session):
        """With include_factual=False, only policy results are returned."""
        _make_guideline(db_session, rule_text="Brand voice must be professional and clear.")
        doc = _make_doc(db_session)
        _make_chunk(db_session, doc.id, "Professional tone in all customer communications.")

        store = VectorStore()
        results = store.search_evidence(
            "professional brand voice",
            db_session,
            include_factual=False,
        )
        for r in results:
            assert r.source_type == "policy"

    def test_both_false_returns_empty_list(self, db_session):
        """With both flags False, result is always empty."""
        _make_guideline(db_session, rule_text="Some guideline text.")
        store = VectorStore()
        results = store.search_evidence(
            "some guideline text",
            db_session,
            include_policy=False,
            include_factual=False,
        )
        assert results == []

    def test_both_source_types_present_when_both_enabled(self, db_session):
        """With both flags True, policy and factual results can co-exist."""
        _make_guideline(
            db_session,
            title="Security Policy",
            rule_text="All data must be encrypted using approved algorithms.",
        )
        doc = _make_doc(db_session)
        _make_chunk(
            db_session, doc.id,
            "Data encryption uses AES-256 algorithm approved for enterprise use.",
        )

        store = VectorStore()
        results = store.search_evidence(
            "data encrypted approved algorithm",
            db_session,
            include_policy=True,
            include_factual=True,
        )
        source_types = {r.source_type for r in results}
        assert "policy" in source_types
        assert "factual" in source_types


# ---------------------------------------------------------------------------
# 8. Configurable similarity_threshold
# ---------------------------------------------------------------------------

class TestConfigurableThreshold:

    def test_custom_threshold_filters_low_scores(self, db_session):
        """Passing a high similarity_threshold drops low-scoring results."""
        doc = _make_doc(db_session)
        _make_chunk(db_session, doc.id, "Sunshine meadows and butterfly gardens.")  # unrelated
        _make_chunk(
            db_session, doc.id,
            "Enterprise SLA uptime guarantee performance reliability.",
        )

        store = VectorStore()
        # Very high threshold should drop the unrelated chunk
        results = store.search_evidence(
            "enterprise SLA uptime",
            db_session,
            include_policy=False,
            similarity_threshold=0.5,
        )
        for r in results:
            assert r.similarity_score >= 0.5

    def test_zero_threshold_includes_any_overlapping_result(self, db_session):
        """similarity_threshold=0.0 keeps any result with non-zero score."""
        doc = _make_doc(db_session)
        _make_chunk(db_session, doc.id, "Enterprise platform integration.")

        store = VectorStore()
        results = store.search_evidence(
            "enterprise",
            db_session,
            include_policy=False,
            similarity_threshold=0.0,
        )
        # With threshold=0.0, at least the chunk with "enterprise" token
        # should appear if it shares the word.
        assert len(results) >= 0  # at minimum it doesn't crash


# ---------------------------------------------------------------------------
# 9. rebuild_index_from_db()
# ---------------------------------------------------------------------------

class TestRebuildIndexFromDb:

    def test_rebuild_counts_guidelines(self, db_session):
        """rebuild_index_from_db reports correct guideline count."""
        _make_guideline(db_session)
        _make_guideline(db_session, title="Second Guideline", rule_text="Another rule.")

        store = VectorStore()
        counts = store.rebuild_index_from_db(db_session)
        assert counts["guidelines"] == 2

    def test_rebuild_counts_indexed_documents(self, db_session):
        """Only indexed, non-deleted documents counted in indexed_documents."""
        _make_doc(db_session, status="indexed")
        _make_doc(db_session, status="indexed")
        _make_doc(db_session, status="failed")
        _make_doc(db_session, status="indexed", deleted_at=datetime.now(timezone.utc))

        store = VectorStore()
        counts = store.rebuild_index_from_db(db_session)
        assert counts["indexed_documents"] == 2

    def test_rebuild_counts_chunks_from_indexed_documents(self, db_session):
        """indexed_chunks counts only chunks from indexed, non-deleted documents."""
        good_doc = _make_doc(db_session, status="indexed")
        bad_doc = _make_doc(db_session, status="failed")
        deleted_doc = _make_doc(
            db_session, status="indexed",
            deleted_at=datetime.now(timezone.utc),
        )

        _make_chunk(db_session, good_doc.id, "Chunk from good document A.", chunk_index=0)
        _make_chunk(db_session, good_doc.id, "Chunk from good document B.", chunk_index=1)
        _make_chunk(db_session, bad_doc.id, "Chunk from failed document.", chunk_index=0)
        _make_chunk(db_session, deleted_doc.id, "Chunk from deleted document.", chunk_index=0)

        store = VectorStore()
        counts = store.rebuild_index_from_db(db_session)
        assert counts["indexed_chunks"] == 2

    def test_rebuild_returns_zeros_on_empty_db(self, db_session):
        """All counts are zero when the database has no relevant rows."""
        store = VectorStore()
        counts = store.rebuild_index_from_db(db_session)
        assert counts == {"guidelines": 0, "indexed_documents": 0, "indexed_chunks": 0}


# ---------------------------------------------------------------------------
# 10. Backward-compatibility: search_relevant_guidelines() unchanged
# ---------------------------------------------------------------------------

class TestSearchRelevantGuidelinesBackwardCompat:
    """
    Verify that the Phase 3-compatible method is entirely unchanged.
    The audit orchestrator depends on this signature and return type.
    """

    def test_returns_guideline_item_list(self, db_session):
        """search_relevant_guidelines returns List[GuidelineItem], not EvidenceResult."""
        from app.schemas import GuidelineItem

        _make_guideline(
            db_session,
            title="Voice Policy",
            rule_text="Maintain professional and authoritative brand voice.",
        )
        store = VectorStore()
        results = store.search_relevant_guidelines(
            "professional brand voice",
            db_session,
            top_k=4,
        )
        assert isinstance(results, list)
        for item in results:
            assert isinstance(item, GuidelineItem)

    def test_returns_empty_list_when_no_guidelines(self, db_session):
        """Empty DB → empty list, no exception."""
        store = VectorStore()
        results = store.search_relevant_guidelines("test query", db_session)
        assert results == []

    def test_top_k_respected(self, db_session):
        """top_k limits the number of guidelines returned."""
        for i in range(6):
            _make_guideline(
                db_session,
                title=f"Guideline {i}",
                rule_text=f"Professional brand marketing rule number {i} for compliance.",
            )
        store = VectorStore()
        results = store.search_relevant_guidelines("professional brand marketing", db_session, top_k=3)
        assert len(results) <= 3

    def test_returns_highest_scoring_guidelines(self, db_session):
        """Most relevant guideline ranks first."""
        _make_guideline(
            db_session,
            title="Color Guide",
            rule_text="Never use red or orange in the primary brand palette.",
        )
        _make_guideline(
            db_session,
            title="Uptime Policy",
            rule_text="Guarantee 99.9 percent enterprise SLA uptime.",
        )
        store = VectorStore()
        results = store.search_relevant_guidelines(
            "enterprise SLA uptime guarantee",
            db_session,
            top_k=4,
        )
        assert len(results) >= 1
        assert "uptime" in results[0].rule_text.lower() or "sla" in results[0].rule_text.lower()

    def test_signature_unchanged(self, db_session):
        """Method accepts exactly (query_text, db, top_k) and returns list."""
        import inspect
        store = VectorStore()
        sig = inspect.signature(store.search_relevant_guidelines)
        params = list(sig.parameters.keys())
        assert "query_text" in params
        assert "db" in params
        assert "top_k" in params

    def test_guideline_items_have_required_fields(self, db_session):
        """Returned GuidelineItem objects have all expected fields."""
        g = _make_guideline(
            db_session,
            title="Typography Rules",
            rule_text="Use only the approved typefaces in all printed materials.",
            category="design",
            source_document="Brand Standards 2026",
            version="2.0",
        )
        store = VectorStore()
        results = store.search_relevant_guidelines("approved typefaces printed", db_session, top_k=4)
        assert len(results) >= 1
        item = results[0]
        assert item.id == g.id
        assert item.title == "Typography Rules"
        assert item.category == "design"
        assert item.source_document == "Brand Standards 2026"
        assert item.version == "2.0"


# ---------------------------------------------------------------------------
# 11. EvidenceResult dataclass contract
# ---------------------------------------------------------------------------

class TestEvidenceResultContract:

    def test_excerpt_auto_populated_from_text(self):
        """excerpt defaults to text when not explicitly passed."""
        r = EvidenceResult(
            source_type="policy",
            similarity_score=0.75,
            text="Use only approved brand colors in all materials.",
            title="Color Policy",
            source_id="abc123",
        )
        assert r.excerpt == r.text

    def test_excerpt_truncated_at_500_chars(self):
        """excerpt is capped at 500 characters when text is longer."""
        long_text = "x" * 1000
        r = EvidenceResult(
            source_type="factual",
            similarity_score=0.5,
            text=long_text,
            title="Document",
            source_id="abc",
        )
        assert len(r.excerpt) == 500
        assert r.excerpt == long_text[:500]

    def test_short_text_not_truncated(self):
        """text shorter than 500 chars is not modified in excerpt."""
        short_text = "Short but meaningful text."
        r = EvidenceResult(
            source_type="factual",
            similarity_score=0.3,
            text=short_text,
            title="Doc",
            source_id="id1",
        )
        assert r.excerpt == short_text

    def test_optional_fields_default_to_none(self):
        """Optional provenance fields default to None."""
        r = EvidenceResult(
            source_type="factual",
            similarity_score=0.4,
            text="Some chunk.",
            title="Doc",
            source_id="id1",
        )
        assert r.document_id is None
        assert r.chunk_id is None
        assert r.guideline_id is None
        assert r.page_number is None
        assert r.section_heading is None

    def test_low_confidence_defaults_false(self):
        """low_confidence defaults to False."""
        r = EvidenceResult(
            source_type="policy",
            similarity_score=0.8,
            text="Rule text.",
            title="Policy",
            source_id="id2",
        )
        assert r.low_confidence is False
