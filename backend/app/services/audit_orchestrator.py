"""
Audit Orchestrator — merges deterministic + LLM findings.

Pipeline:
  1. Deterministic rules engine (always runs, instant)
  2. Claim extraction + evidence verification (always runs, instant)
  3. Vector store retrieval (relevant guidelines for context)
  4. Gemini LLM analysis (if available, with timeout guard)
  5. Deduplicate overlapping findings
  6. Persist submission + findings to SQLite
  7. Return AuditResponse

Status semantics:
  CLEAN            — all checks ran, zero violations found
  VIOLATIONS_FOUND — one or more violations detected (maps to FLAGGED/NEEDS_ESCALATION)
  REVIEW_REQUIRED  — AI checks could not run; deterministic passed but analysis is incomplete.
                     Also raised when unverified claims are present without supporting evidence.
                     Never return CLEAN merely because pattern-matching found zero keyword matches.
"""
import time
import uuid
import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.schemas import AuditFinding, AuditResponse, OverallStatus, Severity
from app.services.rules_engine import RulesEngine
from app.services.claim_extractor import ClaimExtractor
from app.services.vector_store import VectorStore
from app.services.llm_auditor import LLMauditor
from app import models

logger = logging.getLogger(__name__)

# Singleton service instances (module-level, shared across requests)
_rules_engine = RulesEngine()
_claim_extractor = ClaimExtractor()
_vector_store = VectorStore()
_llm_auditor = LLMauditor()

# Human-readable names for audit check stages
CHECK_DETERMINISTIC = "deterministic_rules"
CHECK_CLAIM_EXTRACTION = "claim_extraction_and_verification"
CHECK_VECTOR_RETRIEVAL = "guideline_retrieval"
CHECK_LLM_CONTEXTUAL = "llm_contextual_analysis"


class AuditOrchestrator:
    """
    Orchestrates the full brand governance audit pipeline.

    Merges deterministic findings with LLM contextual findings,
    deduplicates overlapping issues, and persists to SQLite.
    """

    def __init__(self, db: Session):
        self.db = db

    def run(self, text: str, workspace_id: str = "default") -> AuditResponse:
        """Run the full audit pipeline and return AuditResponse."""
        start_time = time.perf_counter()
        submission_id = str(uuid.uuid4())

        checks_completed: List[str] = []
        checks_skipped: List[str] = []

        # Step 1: Deterministic rules (always)
        deterministic_findings = _rules_engine.check(text)
        checks_completed.append(CHECK_DETERMINISTIC)
        logger.info(f"[Orchestrator] Deterministic: {len(deterministic_findings)} findings")

        # Step 2: Claim extraction + evidence verification (always)
        # This catches unverified factual claims that pattern-matching alone misses.
        # Crucial safety net: zero keyword matches ≠ compliant content.
        claim_findings = _claim_extractor.extract_and_verify(text=text, db=self.db)
        checks_completed.append(CHECK_CLAIM_EXTRACTION)
        logger.info(f"[Orchestrator] Claim extraction: {len(claim_findings)} unverified claims")

        # Step 3: Retrieve relevant guidelines for LLM context
        relevant_guidelines = _vector_store.search_relevant_guidelines(
            query_text=text,
            db=self.db,
            top_k=5,
        )
        checks_completed.append(CHECK_VECTOR_RETRIEVAL)
        logger.info(f"[Orchestrator] Retrieved {len(relevant_guidelines)} relevant guidelines")

        # Step 4: LLM analysis (if available)
        llm_findings: List[AuditFinding] = []
        llm_checked = False
        llm_provider = None
        gemini_status = "skipped"
        openrouter_status = "skipped"
        llm_error = None

        if _llm_auditor.is_available:
            llm_findings, meta = _llm_auditor.analyze(text, relevant_guidelines)
            llm_provider = meta.get("provider")
            gemini_status = meta.get("gemini_status", "skipped")
            openrouter_status = meta.get("openrouter_status", "skipped")
            llm_error = meta.get("error")

            if llm_provider is not None:
                llm_checked = True
                checks_completed.append(CHECK_LLM_CONTEXTUAL)
                logger.info(f"[Orchestrator] LLM ({llm_provider}) analysis successful with {len(llm_findings)} findings.")
            else:
                checks_skipped.append(CHECK_LLM_CONTEXTUAL)
                logger.warning(f"[Orchestrator] LLM analysis failed across all providers. Error: {llm_error}")
        else:
            checks_skipped.append(CHECK_LLM_CONTEXTUAL)
            logger.info("[Orchestrator] LLM unavailable; skipping contextual analysis")

        # Step 5: Merge and deduplicate all findings
        all_findings = self._merge_and_deduplicate(
            deterministic_findings, claim_findings, llm_findings
        )
        logger.info(f"[Orchestrator] Merged: {len(all_findings)} unique findings")

        # Step 6: Calculate overall status.
        # CRITICAL: deterministic-only zero result is NOT automatically CLEAN.
        # Unverified claims or skipped LLM checks → REVIEW_REQUIRED.
        overall_status = self._calculate_status(all_findings, llm_checked)
        summary = self._build_summary(all_findings, llm_checked, len(relevant_guidelines), checks_skipped)

        execution_ms = (time.perf_counter() - start_time) * 1000

        # Step 7: Persist to SQLite
        self._persist_submission(
            submission_id=submission_id,
            text=text,
            findings=all_findings,
            overall_status=overall_status,
            summary=summary,
            execution_ms=execution_ms,
        )

        return AuditResponse(
            submission_id=submission_id,
            original_text=text,
            overall_status=overall_status,
            summary=summary,
            findings=all_findings,
            execution_time_ms=round(execution_ms, 2),
            llm_checked=llm_checked,
            llm_provider=llm_provider,
            gemini_status=gemini_status,
            openrouter_status=openrouter_status,
            llm_error=llm_error,
            checks_completed=checks_completed,
            checks_skipped=checks_skipped,
        )

    def _merge_and_deduplicate(
        self,
        deterministic: List[AuditFinding],
        claim: List[AuditFinding],
        llm: List[AuditFinding],
    ) -> List[AuditFinding]:
        """
        Merge findings, removing LLM and claim findings that duplicate deterministic ones.

        Priority order: deterministic > claim extraction > LLM.
        Deduplication strategy: if flagged_text overlaps with a higher-priority finding,
        keep the higher-priority one.
        """
        merged = list(deterministic)
        existing_texts = {f.flagged_text.lower().strip() for f in deterministic}

        # Add claim extractor findings that don't overlap with deterministic
        for finding in claim:
            finding_text = finding.flagged_text.lower().strip()
            is_duplicate = any(
                finding_text in ex_text or ex_text in finding_text or
                self._token_overlap(finding_text, ex_text) > 0.7
                for ex_text in existing_texts
            )
            if not is_duplicate:
                merged.append(finding)
                existing_texts.add(finding_text)

        # Add LLM findings that don't overlap with either
        for llm_finding in llm:
            llm_text = llm_finding.flagged_text.lower().strip()
            is_duplicate = any(
                llm_text in ex_text or ex_text in llm_text or
                self._token_overlap(llm_text, ex_text) > 0.7
                for ex_text in existing_texts
            )
            if not is_duplicate:
                merged.append(llm_finding)
                existing_texts.add(llm_text)

        # Sort: critical → high → medium → low
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
        }
        merged.sort(key=lambda f: severity_order.get(f.severity, 4))
        return merged

    def _token_overlap(self, a: str, b: str) -> float:
        """Simple token-level Jaccard overlap for dedup heuristic."""
        tokens_a = set(a.split())
        tokens_b = set(b.split())
        if not tokens_a or not tokens_b:
            return 0.0
        return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)

    def _calculate_status(self, findings: List[AuditFinding], llm_checked: bool) -> OverallStatus:
        """
        Determine overall audit status from findings and check completeness.

        Rules:
        - Any findings → NEEDS_ESCALATION (critical) or FLAGGED (high/medium/low)
        - No findings + LLM ran → CLEAN (full confidence)
        - No findings + LLM skipped → REVIEW_REQUIRED (incomplete analysis)

        IMPORTANT: Never return CLEAN when:
        - LLM was unavailable (could miss contextual violations)
        - Unverified claims were found (evidence_status = NOT_FOUND)
        """
        if findings:
            severities = {f.severity for f in findings}
            if Severity.CRITICAL in severities:
                return OverallStatus.NEEDS_ESCALATION
            return OverallStatus.FLAGGED

        # Zero findings — only CLEAN if all mandatory checks ran
        if llm_checked:
            return OverallStatus.CLEAN

        # Deterministic and claim extraction passed but LLM was skipped.
        # Cannot confirm compliance — contextual analysis may catch additional issues.
        return OverallStatus.REVIEW_REQUIRED

    def _build_summary(
        self,
        findings: List[AuditFinding],
        llm_checked: bool,
        guideline_count: int,
        checks_skipped: List[str],
    ) -> str:
        """Build a human-readable audit summary."""
        if findings:
            counts: dict = {}
            for f in findings:
                counts[f.severity] = counts.get(f.severity, 0) + 1
            parts = []
            for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
                if severity in counts:
                    parts.append(f"{counts[severity]} {severity.value}")
            summary = f"⚠️ {len(findings)} issue(s) detected: {', '.join(parts)}."
            if llm_checked:
                summary += f" Analysed against {guideline_count} relevant guidelines."
            else:
                summary += " [Deterministic + claim extraction analysis — AI contextual check was unavailable]"
            return summary

        # No violations detected — distinguish complete vs. incomplete
        if llm_checked:
            return (
                f"✅ Content passed brand governance review. "
                f"No violations detected across deterministic rules, claim verification, "
                f"and AI analysis ({guideline_count} guidelines checked)."
            )

        skipped_labels = [s.replace("_", " ") for s in checks_skipped]
        skipped_str = ", ".join(skipped_labels) if skipped_labels else "AI contextual analysis"
        return (
            f"⚠️ Deterministic and claim verification checks passed — no violations found. "
            f"However, {skipped_str} could not run. "
            f"This audit is INCOMPLETE. Manual review or retry with AI enabled is required "
            f"before approving content for publication."
        )

    def _persist_submission(
        self,
        submission_id: str,
        text: str,
        findings: List[AuditFinding],
        overall_status: OverallStatus,
        summary: str,
        execution_ms: float,
    ):
        """Persist submission and findings to SQLite."""
        submission = models.SubmissionModel(
            id=submission_id,
            original_text=text,
            overall_status=overall_status.value,
            summary=summary,
            execution_time_ms=execution_ms,
        )
        self.db.add(submission)

        for finding in findings:
            db_finding = models.FindingModel(
                id=finding.id,
                submission_id=submission_id,
                category=finding.category.value,
                severity=finding.severity.value,
                flagged_text=finding.flagged_text,
                explanation=finding.explanation,
                evidence_quote=finding.evidence_quote,
                evidence_source=finding.evidence_source,
                evidence_status=finding.evidence_status.value,
                suggested_replacement=finding.suggested_replacement,
                confidence_score=finding.confidence_score,
            )
            self.db.add(db_finding)

        self.db.commit()
        logger.info(f"[Orchestrator] Persisted submission {submission_id} with {len(findings)} findings.")
