"""
Lightweight Keyword + Cosine Similarity Vector Store.

Phase 4: Extended to index both brand guidelines (policy evidence) and
persisted document chunks (factual evidence) from the knowledge base.

Retrieves ranked evidence for a given query using:
1. Numpy cosine similarity on TF-based term vectors (no external embedding API)
2. Keyword overlap fallback if numpy fails

Avoids ChromaDB or sentence-transformers dependency — reliable in restricted
environments. Does not replace the existing interface; extends it.

Evidence type distinction:
  policy  — What the brand *requires*. Sourced from GuidelineModel records.
  factual — What the product *actually does/is*. Sourced from DocumentChunkModel
             records in indexed documents.

A guideline that recommends an SLA phrase does NOT prove the product meets
that SLA. Never return factual evidence from guidelines, nor policy evidence
from document chunks.
"""
import re
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from sqlalchemy.orm import Session

from app import models
from app.schemas import GuidelineItem

# ---------------------------------------------------------------------------
# Configurable thresholds
# ---------------------------------------------------------------------------

# Minimum cosine similarity to include a result at all.
# Results below this threshold are considered irrelevant and silently dropped.
SIMILARITY_THRESHOLD_GUIDELINES = 0.05
SIMILARITY_THRESHOLD_CHUNKS = 0.05

# The threshold for flagging a result as "low confidence" in the provenance.
# Above SIMILARITY_THRESHOLD but below this → included but marked uncertain.
SIMILARITY_THRESHOLD_LOW_CONFIDENCE = 0.10


# ---------------------------------------------------------------------------
# Evidence result dataclass
# ---------------------------------------------------------------------------

@dataclass
class EvidenceResult:
    """
    A single ranked evidence result with full provenance.

    Attributes:
        source_type:       "policy" (guideline) or "factual" (document chunk).
        similarity_score:  Cosine similarity in [0.0, 1.0].
        text:              The exact text from the guideline rule or chunk.
        title:             Guideline title or document filename.
        source_id:         GuidelineModel.id or DocumentChunkModel.id.
        document_id:       DocumentModel.id (None for guidelines without a doc link).
        chunk_id:          DocumentChunkModel.id (None for guideline results).
        guideline_id:      GuidelineModel.id (None for chunk results).
        category:          Guideline category or document category.
        version:           Document or guideline version string.
        page_number:       Source page number (chunks only, None for guidelines).
        section_heading:   Section heading (chunks only, None for guidelines).
        excerpt:           Exact text excerpt used for retrieval (same as text for
                           guidelines; truncated chunk text for long chunks).
        source_document:   Guideline source_document field or document filename.
        low_confidence:    True when similarity is below LOW_CONFIDENCE threshold.
    """
    source_type: str                       # "policy" | "factual"
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

    def __post_init__(self):
        # Excerpt defaults to text when not explicitly supplied
        if not self.excerpt:
            self.excerpt = self.text[:500] if len(self.text) > 500 else self.text


# ---------------------------------------------------------------------------
# VectorStore
# ---------------------------------------------------------------------------

class VectorStore:
    """
    In-process keyword + cosine similarity retrieval.

    Searches both GuidelineModel records (policy evidence) and
    DocumentChunkModel records (factual evidence).

    The existing search_relevant_guidelines() method is preserved unchanged
    so that the audit orchestrator contract is not broken.

    The new search_evidence() method returns typed EvidenceResult objects
    with full provenance and similarity scores.

    Index rebuild: the store rebuilds its term vectors from the database on
    each call (no persistent in-memory state between restarts). This ensures
    deterministic results after a server restart, as long as the database rows
    are present. This was already the behaviour for guidelines; chunks follow
    the same pattern.
    """

    # ------------------------------------------------------------------
    # Internal helpers (unchanged from Phase 3 baseline)
    # ------------------------------------------------------------------

    def _tokenize(self, text: str) -> List[str]:
        """Simple whitespace + punctuation tokenizer, lowercase."""
        return re.findall(r'\b[a-z]{3,}\b', text.lower())

    def _build_term_vector(self, text: str, vocabulary: List[str]) -> np.ndarray:
        """Build a term-frequency vector for the text over the given vocabulary."""
        tokens = self._tokenize(text)
        freq: dict[str, int] = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        return np.array([freq.get(term, 0) for term in vocabulary], dtype=float)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _build_shared_vocabulary(self, texts: List[str]) -> List[str]:
        """Build a deduplicated vocabulary from a list of texts."""
        return list({
            token
            for text in texts
            for token in self._tokenize(text)
        })

    def _keyword_overlap_score(self, query_tokens: set, text: str) -> int:
        """Return the number of shared tokens between query and text."""
        text_tokens = set(self._tokenize(text))
        return len(query_tokens & text_tokens)

    # ------------------------------------------------------------------
    # Phase 3-compatible method: search guidelines only
    # ------------------------------------------------------------------

    def search_relevant_guidelines(
        self,
        query_text: str,
        db: Session,
        top_k: int = 4,
    ) -> List[GuidelineItem]:
        """
        Retrieve the top_k most relevant guidelines for the query.

        Unchanged from Phase 3: returns GuidelineItem list. The audit
        orchestrator calls this method; do not change its signature or
        return type.

        Uses cosine similarity over TF-based term vectors.
        Falls back to keyword overlap if numpy fails.
        """
        guidelines = db.query(models.GuidelineModel).all()
        if not guidelines:
            return []

        # Build shared vocabulary from all guidelines + query
        all_texts = [query_text] + [f"{g.title} {g.rule_text}" for g in guidelines]
        vocabulary = self._build_shared_vocabulary(all_texts)

        if not vocabulary:
            return []

        try:
            query_vec = self._build_term_vector(query_text, vocabulary)
            scores = []
            for guideline in guidelines:
                guideline_text = f"{guideline.title} {guideline.rule_text}"
                g_vec = self._build_term_vector(guideline_text, vocabulary)
                score = self._cosine_similarity(query_vec, g_vec)
                scores.append((score, guideline))

            # Sort by score descending, return top_k with positive score
            scores.sort(key=lambda x: x[0], reverse=True)
            top_guidelines = [g for _, g in scores[:top_k] if _ > 0.0]

            return [
                GuidelineItem(
                    id=g.id,
                    title=g.title,
                    category=g.category,
                    rule_text=g.rule_text,
                    source_document=g.source_document,
                    version=g.version,
                    tags=g.tags or [],
                )
                for g in top_guidelines
            ]

        except Exception:
            # Keyword fallback: return guidelines with highest token overlap
            query_tokens = set(self._tokenize(query_text))
            scored = []
            for g in guidelines:
                g_tokens = set(self._tokenize(f"{g.title} {g.rule_text}"))
                overlap = len(query_tokens & g_tokens)
                scored.append((overlap, g))
            scored.sort(key=lambda x: x[0], reverse=True)
            top = [g for _, g in scored[:top_k]]
            return [
                GuidelineItem(
                    id=g.id,
                    title=g.title,
                    category=g.category,
                    rule_text=g.rule_text,
                    source_document=g.source_document,
                    version=g.version,
                    tags=g.tags or [],
                )
                for g in top
            ]

    # ------------------------------------------------------------------
    # Phase 4: Unified evidence search across guidelines + chunks
    # ------------------------------------------------------------------

    def search_evidence(
        self,
        query_text: str,
        db: Session,
        top_k: int = 5,
        include_policy: bool = True,
        include_factual: bool = True,
        similarity_threshold: Optional[float] = None,
    ) -> List[EvidenceResult]:
        """
        Retrieve ranked evidence results from both guidelines and document chunks.

        Policy evidence (source_type="policy"):
            Sourced from GuidelineModel records. Represents what the brand
            *requires*. Never use policy evidence to verify factual claims
            about product capabilities.

        Factual evidence (source_type="factual"):
            Sourced from DocumentChunkModel records in documents with
            status="indexed" and no soft deletion. Represents what product
            documents actually say.

        Results are ranked by cosine similarity and filtered by threshold.
        When no relevant evidence is found, returns an empty list — never
        fabricates results or returns low-similarity content as verified.

        Duplicate chunk prevention: if the same chunk_id scores multiple times
        (e.g., through different vocabulary builds), only the highest-scoring
        occurrence is retained.

        Args:
            query_text:          Text to search for.
            db:                  Database session.
            top_k:               Maximum results to return (after merging
                                 policy and factual results).
            include_policy:      Whether to include guideline evidence.
            include_factual:     Whether to include document chunk evidence.
            similarity_threshold: Minimum cosine similarity. Defaults to
                                  SIMILARITY_THRESHOLD_GUIDELINES for policy
                                  and SIMILARITY_THRESHOLD_CHUNKS for factual.

        Returns:
            List[EvidenceResult] ranked by similarity_score descending.
            Empty list when no evidence meets the threshold.
        """
        if not query_text or not query_text.strip():
            return []

        all_results: List[EvidenceResult] = []

        if include_policy:
            all_results.extend(
                self._search_guidelines(query_text, db, similarity_threshold)
            )

        if include_factual:
            all_results.extend(
                self._search_chunks(query_text, db, similarity_threshold)
            )

        # Deduplicate by source_id (highest score wins if the same id appears twice)
        seen_ids: dict[str, float] = {}
        deduped: List[EvidenceResult] = []
        for result in all_results:
            prev_score = seen_ids.get(result.source_id)
            if prev_score is None or result.similarity_score > prev_score:
                seen_ids[result.source_id] = result.similarity_score
                # Remove any previously added result with the same id
                deduped = [r for r in deduped if r.source_id != result.source_id]
                deduped.append(result)

        # Sort all results by score descending
        deduped.sort(key=lambda r: r.similarity_score, reverse=True)

        return deduped[:top_k]

    def _search_guidelines(
        self,
        query_text: str,
        db: Session,
        threshold: Optional[float],
    ) -> List[EvidenceResult]:
        """
        Score all GuidelineModel records against the query.

        Returns EvidenceResult(source_type="policy") for each guideline
        whose similarity meets the threshold.
        """
        min_score = threshold if threshold is not None else SIMILARITY_THRESHOLD_GUIDELINES

        guidelines = db.query(models.GuidelineModel).all()
        if not guidelines:
            return []

        all_texts = [query_text] + [f"{g.title} {g.rule_text}" for g in guidelines]
        vocabulary = self._build_shared_vocabulary(all_texts)
        if not vocabulary:
            return []

        results: List[EvidenceResult] = []

        try:
            query_vec = self._build_term_vector(query_text, vocabulary)
            for g in guidelines:
                guideline_text = f"{g.title} {g.rule_text}"
                g_vec = self._build_term_vector(guideline_text, vocabulary)
                score = self._cosine_similarity(query_vec, g_vec)
                if score >= min_score:
                    results.append(EvidenceResult(
                        source_type="policy",
                        similarity_score=round(score, 6),
                        text=g.rule_text,
                        title=g.title,
                        source_id=g.id,
                        guideline_id=g.id,
                        document_id=g.document_id,   # may be None for manually seeded guidelines
                        category=g.category,
                        version=g.version or "1.0",
                        source_document=g.source_document,
                        low_confidence=(score < SIMILARITY_THRESHOLD_LOW_CONFIDENCE),
                    ))
        except Exception:
            # Keyword fallback for guidelines
            query_tokens = set(self._tokenize(query_text))
            for g in guidelines:
                overlap = self._keyword_overlap_score(query_tokens, f"{g.title} {g.rule_text}")
                if overlap > 0:
                    results.append(EvidenceResult(
                        source_type="policy",
                        similarity_score=float(overlap),
                        text=g.rule_text,
                        title=g.title,
                        source_id=g.id,
                        guideline_id=g.id,
                        document_id=g.document_id,
                        category=g.category,
                        version=g.version or "1.0",
                        source_document=g.source_document,
                        low_confidence=True,
                    ))

        return results

    def _search_chunks(
        self,
        query_text: str,
        db: Session,
        threshold: Optional[float],
    ) -> List[EvidenceResult]:
        """
        Score DocumentChunkModel records against the query.

        Only includes chunks from documents that are:
          - status == "indexed"           (processing complete)
          - deleted_at IS NULL            (not soft-deleted)

        Excludes documents with status in {uploading, processing, failed}.
        This ensures the evidence index only reflects fully processed,
        available knowledge-base entries.

        Returns EvidenceResult(source_type="factual") for each chunk
        whose similarity meets the threshold.
        """
        min_score = threshold if threshold is not None else SIMILARITY_THRESHOLD_CHUNKS

        # Join chunks to their parent document and filter
        chunk_rows = (
            db.query(models.DocumentChunkModel, models.DocumentModel)
            .join(
                models.DocumentModel,
                models.DocumentChunkModel.document_id == models.DocumentModel.id
            )
            .filter(
                models.DocumentModel.status == "indexed",
                models.DocumentModel.deleted_at.is_(None),
            )
            .all()
        )

        if not chunk_rows:
            return []

        chunks = [c for c, _ in chunk_rows]
        docs_by_id = {d.id: d for _, d in chunk_rows}

        all_texts = [query_text] + [c.chunk_text for c in chunks]
        vocabulary = self._build_shared_vocabulary(all_texts)
        if not vocabulary:
            return []

        results: List[EvidenceResult] = []

        try:
            query_vec = self._build_term_vector(query_text, vocabulary)
            for chunk in chunks:
                c_vec = self._build_term_vector(chunk.chunk_text, vocabulary)
                score = self._cosine_similarity(query_vec, c_vec)
                if score >= min_score:
                    doc = docs_by_id[chunk.document_id]
                    results.append(EvidenceResult(
                        source_type="factual",
                        similarity_score=round(score, 6),
                        text=chunk.chunk_text,
                        title=doc.title,
                        source_id=chunk.id,
                        chunk_id=chunk.id,
                        document_id=doc.id,
                        category=doc.category,
                        version=doc.version or "1.0",
                        page_number=chunk.page_number,
                        section_heading=chunk.section_heading,
                        source_document=doc.filename,
                        low_confidence=(score < SIMILARITY_THRESHOLD_LOW_CONFIDENCE),
                    ))
        except Exception:
            # Keyword fallback for chunks
            query_tokens = set(self._tokenize(query_text))
            for chunk in chunks:
                overlap = self._keyword_overlap_score(query_tokens, chunk.chunk_text)
                if overlap > 0:
                    doc = docs_by_id[chunk.document_id]
                    results.append(EvidenceResult(
                        source_type="factual",
                        similarity_score=float(overlap),
                        text=chunk.chunk_text,
                        title=doc.title,
                        source_id=chunk.id,
                        chunk_id=chunk.id,
                        document_id=doc.id,
                        category=doc.category,
                        version=doc.version or "1.0",
                        page_number=chunk.page_number,
                        section_heading=chunk.section_heading,
                        source_document=doc.filename,
                        low_confidence=True,
                    ))

        return results

    def rebuild_index_from_db(self, db: Session) -> dict:
        """
        Verify that the store can access all indexable content from the DB.

        Since the store rebuilds vocabulary on each search call rather than
        maintaining a persistent in-memory index, this method validates DB
        connectivity and returns counts of indexable items.

        This is deterministic and safe to call after a server restart —
        each search call rebuilds from the same persistent DB rows.

        Returns:
            dict with keys:
              "guidelines"        — count of all guideline records
              "indexed_documents" — count of documents with status="indexed"
                                    and no soft deletion
              "indexed_chunks"    — count of chunks from those documents
        """
        guideline_count = db.query(models.GuidelineModel).count()

        indexed_docs = (
            db.query(models.DocumentModel)
            .filter(
                models.DocumentModel.status == "indexed",
                models.DocumentModel.deleted_at.is_(None),
            )
            .all()
        )
        doc_ids = [d.id for d in indexed_docs]

        chunk_count = 0
        if doc_ids:
            chunk_count = (
                db.query(models.DocumentChunkModel)
                .filter(models.DocumentChunkModel.document_id.in_(doc_ids))
                .count()
            )

        return {
            "guidelines": guideline_count,
            "indexed_documents": len(indexed_docs),
            "indexed_chunks": chunk_count,
        }
