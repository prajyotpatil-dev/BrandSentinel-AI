"""
Claim Extraction and Evidence Verification Engine.

Identifies factual claims that require evidence validation, even when LLM is unavailable.
Categories: security guarantees, statistics, product capabilities, certifications,
financial/pricing claims, competitive superiority, customer/adoption claims.

Phase 7.1: Integrated with search_evidence() for dynamic factual verification.
"""
import re
import uuid
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.schemas import AuditFinding, Severity, IssueCategory, EvidenceStatus


class ClaimPattern:
    """A pattern that identifies a specific type of factual claim."""

    def __init__(
        self,
        name: str,
        pattern: str,
        category: IssueCategory,
        severity: Severity,
        explanation_template: str,
        evidence_required: str,
        replacement_hint: str = "",
    ):
        self.name = name
        self.pattern = pattern
        self.category = category
        self.severity = severity
        self.explanation_template = explanation_template
        self.evidence_required = evidence_required
        self.replacement_hint = replacement_hint
        self.regex = re.compile(pattern, re.IGNORECASE)


# Claim patterns that require evidence verification
CLAIM_PATTERNS = [
    # Extreme security percentage claims
    ClaimPattern(
        name="extreme_security_percentage",
        pattern=r"\b(99\.9{4,}%|99\.999+%)\s*(protection|security|safe)\s*(against|from)?\s*(all\s+)?(cyber)?attacks?\b",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.CRITICAL,
        explanation_template=(
            "Extreme security percentage claim '{claim}' requires verifiable evidence. "
            "Such claims must be supported by documented testing methodology, third-party validation, "
            "and clear scope definition. No evidence found in approved product specifications."
        ),
        evidence_required="Testing methodology and results for security protection percentage",
        replacement_hint="enterprise-grade security with 99.99% uptime SLA",
    ),

    # "All cyberattacks" protection claims
    ClaimPattern(
        name="all_attacks_protection",
        pattern=r"\b(protection|protects?|secure|secures?|safe|defend|defends?|shield|shields?|guard|guards?)\s*(against|from)?\s*all\s+(cyber)?attacks?\b",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.CRITICAL,
        explanation_template=(
            "Claim of protection against 'all attacks' is an absolute guarantee that cannot be verified. "
            "No security solution can protect against every possible attack vector, including zero-day exploits."
        ),
        evidence_required="Comprehensive security testing covering all attack vectors",
        replacement_hint="protection against known attack vectors with continuous monitoring",
    ),

    # Specific customer count claims
    ClaimPattern(
        name="customer_count",
        pattern=r"\b(\d{1,3}(?:,\d{3})*)\s*(enterprise\s+)?customers?\b",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.HIGH,
        explanation_template=(
            "Specific customer count claim '{claim}' requires verification against current customer database. "
            "Customer statistics must be accurate, up-to-date, and documented."
        ),
        evidence_required="Current verified customer count from customer database",
        replacement_hint="thousands of enterprise customers worldwide",
    ),

    # Geographic coverage claims
    ClaimPattern(
        name="geographic_coverage",
        pattern=r"\b(\d{1,3})\s+countries\b",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.HIGH,
        explanation_template=(
            "Geographic coverage claim '{claim}' requires verification against actual operational presence. "
            "Specific country counts must be documented and accurate."
        ),
        evidence_required="Documented list of countries with operational presence",
        replacement_hint="global presence across major regions",
    ),

    # Specific cost reduction percentages
    ClaimPattern(
        name="cost_reduction_percentage",
        pattern=r"\b(\d{1,3})%\s+(cybersecurity\s+)?(cost\s+)?(reduction|savings?|cut)\b",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.HIGH,
        explanation_template=(
            "Specific cost reduction claim '{claim}' requires documented benchmark studies with methodology. "
            "Must include disclaimer: 'Results based on internal testing conducted Q3 2025.'"
        ),
        evidence_required="Benchmark study with methodology and sample data",
        replacement_hint="significant cost savings",
    ),

    # Certification claims (vague)
    ClaimPattern(
        name="vague_certification",
        pattern=r"\b(independent\s+)?cybersecurity\s+certification\b(?!\s*\()",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.HIGH,
        explanation_template=(
            "Vague certification claim '{claim}' lacks required specifics. "
            "Certification claims must name the specific certification (SOC 2, ISO 27001) and certifying body."
        ),
        evidence_required="Specific certification name and certifying body documentation",
        replacement_hint="SOC 2 Type II and ISO 27001 certified",
    ),

    # Proprietary technology names
    ClaimPattern(
        name="proprietary_technology",
        pattern=r"\b(?:proprietary\s+)?(\w+(?:Shield|Guard|Protect|Secure|Defense))\s+technology\b",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.HIGH,
        explanation_template=(
            "Proprietary technology name '{claim}' requires verification against approved product documentation. "
            "Technology claims must be documented in official product specifications."
        ),
        evidence_required="Product specification document listing technology components",
        replacement_hint="enterprise security technology",
    ),

    # "Thousands of organizations" vague quantity claims
    ClaimPattern(
        name="vague_quantity_claim",
        pattern=r"\bthousands?\s+of\s+(organizations|organisations|companies|enterprises|businesses)\b",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.MEDIUM,
        explanation_template=(
            "Vague quantity claim '{claim}' should be specific and verifiable. "
            "Prefer documented specific numbers over vague quantities."
        ),
        evidence_required="Specific customer count documentation",
        replacement_hint="organizations worldwide",
    ),

    # Certification claims with certifying body (e.g., "by the International Cybersecurity Authority")
    ClaimPattern(
        name="certification_with_body",
        pattern=r"\b(?:independent|third.?party|regulatory|industry)\s+(?:cybersecurity\s+)?certification\s+(?:by|from)\s+(?:the\s+)?([A-Z][^.!?,;]{3,50})",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.HIGH,
        explanation_template=(
            "Certification claim '{claim}' requires verification. "
            "The certifying organization must be verifiable and the certification must be current. "
            "Confirm the certification exists and is valid before publication."
        ),
        evidence_required="Certification document with current validity date from the named certifying body",
        replacement_hint="certified by [verify certification details]",
    ),

    # Time-bound financial claims (e.g., "95% cost reduction within 30 days")
    ClaimPattern(
        name="time_bound_financial_outcome",
        pattern=r"\b(\d{1,3})%\s+.*?cost.*?(?:reduction|savings?|cut).*?(?:within|in|over)\s+(\d+)\s+(?:days?|weeks?|months?)\b",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.CRITICAL,
        explanation_template=(
            "Time-bound financial claim '{claim}' requires documented evidence. "
            "Specific percentage reductions with time guarantees must be verified through "
            "controlled testing with disclosed methodology. This claim cannot be made without supporting evidence."
        ),
        evidence_required="Performance study with test methodology, sample size, baseline comparison, and results documentation",
        replacement_hint="potential cost savings (results vary based on implementation)",
    ),

    # Thermal retention claims (e.g., "Cold for 24 hours", "Hot for 18 hours")
    ClaimPattern(
        name="thermal_retention_claim",
        pattern=r"\b(?:cold|hot|warm|keeps?|maintains?)\s+(?:for\s+)?(\d+)\s*hours?\b",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.HIGH,
        explanation_template=(
            "Thermal retention claim '{claim}' requires verification against product performance specifications. "
            "Temperature retention hours must be supported by tested documentation."
        ),
        evidence_required="Product specification sheet detailing thermal testing results",
        replacement_hint="extended temperature retention",
    ),

    # Leakproof claims (e.g., "100% leakproof")
    ClaimPattern(
        name="leakproof_claim",
        pattern=r"\b(?:100%|completely|fully)?\s*leak-?proof\b",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.HIGH,
        explanation_template=(
            "Leakproof claim '{claim}' requires quality assurance test results and specification validation."
        ),
        evidence_required="QA testing documentation for seal integrity",
        replacement_hint="engineered seal design",
    ),

    # Plastic-free claims (e.g., "100% plastic-free")
    ClaimPattern(
        name="plastic_free_claim",
        pattern=r"\b(?:100%|completely)?\s*plastic-?free\b",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.HIGH,
        explanation_template=(
            "Material claim '{claim}' requires verification against bill of materials and material specs."
        ),
        evidence_required="Approved bill of materials confirming material composition",
        replacement_hint="responsibly sourced materials",
    ),

    # Environmental / carbon claims (e.g., "Carbon-neutral", "Zero environmental impact")
    ClaimPattern(
        name="environmental_claim",
        pattern=r"\b(?:carbon-?neutral|zero\s+environmental\s+impact|zero-?carbon|eco-?friendly)\b",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.HIGH,
        explanation_template=(
            "Environmental sustainability claim '{claim}' requires verified lifecycle assessment and certification."
        ),
        evidence_required="Lifecycle assessment report and sustainability certification",
        replacement_hint="sustainable product design",
    ),

    # Antibacterial / hygiene claims (e.g., "Antibacterial surface")
    ClaimPattern(
        name="antibacterial_claim",
        pattern=r"\b(?:antibacterial|antimicrobial)\s+(?:surface|coating|technology)?\b",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.HIGH,
        explanation_template=(
            "Hygiene claim '{claim}' requires laboratory test validation and certification."
        ),
        evidence_required="Laboratory test results for antimicrobial efficacy",
        replacement_hint="hygienic finish",
    ),

    # Warranty claims (e.g., "Lifetime warranty")
    ClaimPattern(
        name="warranty_claim",
        pattern=r"\b(?:lifetime\s+warranty|lifetime\s+guarantee)\b",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.HIGH,
        explanation_template=(
            "Warranty claim '{claim}' requires verification against official company warranty policy."
        ),
        evidence_required="Official warranty policy documentation",
        replacement_hint="standard product warranty",
    ),

    # Care instruction claims (e.g., "Dishwasher-safe")
    ClaimPattern(
        name="care_instruction_claim",
        pattern=r"\b(?:dishwasher-?safe|microwave-?safe)\b",
        category=IssueCategory.UNSUPPORTED_CLAIM,
        severity=Severity.MEDIUM,
        explanation_template=(
            "Care instruction claim '{claim}' requires validation against care guidelines."
        ),
        evidence_required="Product care instruction manual",
        replacement_hint="hand wash recommended",
    ),
]


class ClaimExtractor:
    """
    Extracts factual claims from content and verifies them against approved evidence.

    Works deterministically without LLM dependency, catching unverified claims
    even when Gemini API is unavailable.
    """

    def extract_and_verify(
        self,
        text: str,
        db: Optional[Session] = None,
    ) -> List[AuditFinding]:
        """
        Extract claims from text and verify against approved evidence.

        Returns findings for claims that lack supporting evidence.
        """
        findings: List[AuditFinding] = []
        seen_claims: set[str] = set()

        for pattern in CLAIM_PATTERNS:
            matches = list(pattern.regex.finditer(text))

            for match in matches:
                flagged_text = match.group(0)
                dedup_key = f"{pattern.name}::{flagged_text.lower()}"

                if dedup_key in seen_claims:
                    continue
                seen_claims.add(dedup_key)

                # Check for supporting evidence
                evidence_status, evidence_quote, evidence_source = self._verify_claim(
                    claim_text=flagged_text,
                    pattern=pattern,
                    full_text=text,
                    db=db,
                )

                # Flag if evidence is NOT_FOUND or CONTRADICTED
                if evidence_status in [EvidenceStatus.NOT_FOUND, EvidenceStatus.CONTRADICTED]:
                    if evidence_status == EvidenceStatus.CONTRADICTED:
                        explanation = (
                            f"Claim '{flagged_text}' contradicts approved product documentation "
                            f"(Found in: {evidence_source}). Quote: '{evidence_quote}'"
                        )
                    else:
                        explanation = pattern.explanation_template.format(claim=flagged_text)

                    findings.append(
                        AuditFinding(
                            id=str(uuid.uuid4()),
                            category=pattern.category,
                            severity=pattern.severity,
                            flagged_text=flagged_text,
                            explanation=explanation,
                            evidence_quote=evidence_quote,
                            evidence_source=evidence_source,
                            evidence_status=evidence_status,
                            suggested_replacement=pattern.replacement_hint,
                            confidence_score=0.85,  # High confidence for pattern-based extraction
                        )
                    )

        return findings

    def _verify_claim(
        self,
        claim_text: str,
        pattern: ClaimPattern,
        full_text: str,
        db: Optional[Session],
    ) -> Tuple[EvidenceStatus, Optional[str], Optional[str]]:
        """
        Verify a claim against approved guidelines and product facts.

        Phase 7.1: Now uses search_evidence() for dynamic factual verification.

        Returns (evidence_status, evidence_quote, evidence_source).
        """
        # For extreme security percentages and "all attacks" — these are inherently unverifiable
        # No amount of evidence can prove protection against ALL attacks or 99.9999% security
        if pattern.name in ["extreme_security_percentage", "all_attacks_protection"]:
            return (
                EvidenceStatus.NOT_FOUND,
                None,
                None,
            )

        # Check if the full text contains required disclaimers for certain claim types
        if pattern.name == "cost_reduction_percentage":
            if "Results based on internal testing" in full_text:
                return (
                    EvidenceStatus.SUPPORTED,
                    "Results based on internal testing conducted Q3 2025.",
                    "ApexCloud Legal & Compliance Policy v4.0",
                )

        # Check if specific certifications are named (SOC 2, ISO 27001)
        if pattern.name == "vague_certification":
            if re.search(r"\b(SOC\s*2|ISO\s*27001)\b", full_text, re.IGNORECASE):
                return (
                    EvidenceStatus.SUPPORTED,
                    "SOC 2 Type II and ISO 27001 certified",
                    "ApexCloud Security Certifications",
                )

        # Phase 7.1: Dynamic evidence retrieval for factual claims
        # Search uploaded product specifications and factual documents
        if db and pattern.name in [
            "customer_count",
            "geographic_coverage",
            "proprietary_technology",
            "time_bound_financial_outcome",
            "vague_quantity_claim",
            "certification_with_body",
            "thermal_retention_claim",
            "leakproof_claim",
            "plastic_free_claim",
            "environmental_claim",
            "antibacterial_claim",
            "warranty_claim",
            "care_instruction_claim",
        ]:
            from app.services.vector_store import VectorStore

            store = VectorStore()

            # Search for factual evidence (NOT policy guidelines)
            evidence_results = store.search_evidence(
                query_text=claim_text,
                db=db,
                top_k=5,
                include_policy=False,  # Factual claims need factual evidence
                include_factual=True,
                similarity_threshold=0.2,  # Slightly lower threshold to ensure recall for claims
            )

            if evidence_results:
                # Check if any evidence supports the claim
                for result in evidence_results:
                    evidence_text = result.text.lower()
                    claim_lower = claim_text.lower()

                    # Extract numbers from claim for comparison
                    claim_numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', claim_text)
                    evidence_numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', evidence_text)

                    # Check for numeric match (customer counts, countries, etc.)
                    if claim_numbers and claim_numbers[0] in evidence_numbers:
                        # Build source attribution with full provenance
                        source_parts = []
                        if result.document_id:
                            source_parts.append(result.title)
                        if result.version and result.version != "1.0":
                            source_parts.append(f"v{result.version}")
                        if result.page_number:
                            source_parts.append(f"page {result.page_number}")

                        source = " - ".join(source_parts) if source_parts else result.source_document

                        return (
                            EvidenceStatus.SUPPORTED,
                            result.text[:200],  # Excerpt for finding
                            source,
                        )

                    # Check for thermal retention match / contradiction
                    if pattern.name == "thermal_retention_claim":
                        if claim_numbers and evidence_numbers:
                            # If claim says 24 hours but evidence says 12 hours -> CONTRADICTED
                            if claim_numbers[0] not in evidence_numbers:
                                source = f"{result.title}"
                                if result.version:
                                    source += f" v{result.version}"
                                if result.page_number:
                                    source += f" - page {result.page_number}"
                                return (
                                    EvidenceStatus.CONTRADICTED,
                                    result.text[:200],
                                    source,
                                )

                    # Check for warranty contradiction (e.g. claim is lifetime, evidence is limited/1-year)
                    if pattern.name == "warranty_claim":
                        if "lifetime" in claim_lower and ("limited" in evidence_text or "year" in evidence_text or "month" in evidence_text):
                            source = f"{result.title}"
                            if result.version:
                                source += f" v{result.version}"
                            if result.page_number:
                                source += f" - page {result.page_number}"
                            return (
                                EvidenceStatus.CONTRADICTED,
                                result.text[:200],
                                source,
                            )

                    # Check for keyword matches in evidence for other factual claims
                    keyword_matches = {
                        "leakproof_claim": ["leakproof", "leak-proof", "leak proof", "seal", "waterproof"],
                        "plastic_free_claim": ["plastic-free", "plastic free", "bpa-free", "stainless steel", "metal"],
                        "environmental_claim": ["carbon-neutral", "carbon neutral", "sustainable", "eco-friendly", "zero carbon"],
                        "antibacterial_claim": ["antibacterial", "antimicrobial", "hygienic"],
                        "care_instruction_claim": ["dishwasher", "wash", "clean", "care"],
                        "warranty_claim": ["warranty", "guarantee"],
                    }

                    if pattern.name in keyword_matches:
                        if any(kw in evidence_text for kw in keyword_matches[pattern.name]):
                            source_parts = []
                            if result.document_id:
                                source_parts.append(result.title)
                            if result.version and result.version != "1.0":
                                source_parts.append(f"v{result.version}")
                            if result.page_number:
                                source_parts.append(f"page {result.page_number}")
                            source = " - ".join(source_parts) if source_parts else result.source_document

                            return (
                                EvidenceStatus.SUPPORTED,
                                result.text[:200],
                                source,
                            )

                    # Check for technology name match
                    if pattern.name == "proprietary_technology":
                        tech_match = re.search(
                            r"(\w+(?:Shield|Guard|Protect|Secure|Defense))",
                            claim_text,
                            re.IGNORECASE,
                        )
                        if tech_match:
                            tech_name = tech_match.group(1)
                            if tech_name.lower() in evidence_text:
                                source = f"{result.title}"
                                if result.version:
                                    source += f" v{result.version}"
                                if result.page_number:
                                    source += f" - page {result.page_number}"

                                return (
                                    EvidenceStatus.SUPPORTED,
                                    result.text[:200],
                                    source,
                                )

                    # Check for certification body match
                    if pattern.name == "certification_with_body":
                        org_match = re.search(
                            r"(?:by|from)\s+(?:the\s+)?([A-Z][^.!?,;]{3,50})",
                            claim_text,
                        )
                        if org_match:
                            org_name = org_match.group(1).strip()
                            if org_name.lower() in evidence_text:
                                source = f"{result.title}"
                                if result.version:
                                    source += f" v{result.version}"

                                return (
                                    EvidenceStatus.SUPPORTED,
                                    result.text[:200],
                                    source,
                                )

                # Evidence found but doesn't support the claim - check for contradiction
                for result in evidence_results:
                    if claim_numbers and evidence_numbers:
                        if claim_numbers[0] not in evidence_numbers and len(evidence_numbers) > 0:
                            source = f"{result.title}"
                            if result.version:
                                source += f" v{result.version}"
                            if result.page_number:
                                source += f" - page {result.page_number}"

                            return (
                                EvidenceStatus.CONTRADICTED,
                                result.text[:200],
                                source,
                            )

            # No evidence found for this claim
            return (EvidenceStatus.NOT_FOUND, None, None)

        # Default: no evidence found
        return (EvidenceStatus.NOT_FOUND, None, None)
