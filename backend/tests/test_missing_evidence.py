"""
Regression tests for Missing Evidence Detection.

Tests that unverified claims are identified even when Gemini AI is unavailable.
Validates claim extraction, evidence verification, and approval protection.
"""
import pytest
from app.services.claim_extractor import ClaimExtractor
from app.services.audit_orchestrator import AuditOrchestrator
from app.schemas import Severity, EvidenceStatus, OverallStatus
from app.database import SessionLocal


@pytest.fixture
def db():
    """Database session for each test."""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def claim_extractor():
    """Claim extractor instance."""
    return ClaimExtractor()


@pytest.fixture
def orchestrator(db):
    """Audit orchestrator with database."""
    return AuditOrchestrator(db)


class TestExtremeSecurityPercentages:
    """Test detection of extreme security percentage claims."""

    def test_99_9999_percent_protection_detected(self, claim_extractor):
        text = "99.9999% protection against all cyberattacks."
        findings = claim_extractor.extract_and_verify(text)
        extreme_findings = [
            f for f in findings
            if "99.9999%" in f.flagged_text and f.severity == Severity.CRITICAL
        ]
        assert len(extreme_findings) >= 1, "Must detect extreme security percentage"
        assert extreme_findings[0].evidence_status == EvidenceStatus.NOT_FOUND


class TestAllCyberattacksProtection:
    """Test detection of 'all cyberattacks' protection claims."""

    def test_protection_against_all_cyberattacks(self, claim_extractor):
        text = "Complete protection against all cyberattacks."
        findings = claim_extractor.extract_and_verify(text)
        all_attacks = [
            f for f in findings
            if "all cyberattacks" in f.flagged_text.lower()
        ]
        assert len(all_attacks) >= 1, "Must detect 'all cyberattacks' claim"
        assert all_attacks[0].severity == Severity.CRITICAL


class TestCustomerCountClaims:
    """Test detection of specific customer count claims."""

    def test_50000_customers_detected(self, claim_extractor):
        text = "50,000 enterprise customers trust our platform."
        findings = claim_extractor.extract_and_verify(text)
        customer_claims = [
            f for f in findings
            if "50,000" in f.flagged_text
        ]
        assert len(customer_claims) >= 1, "Must detect specific customer count"
        assert customer_claims[0].severity == Severity.HIGH
        assert customer_claims[0].evidence_status == EvidenceStatus.NOT_FOUND


class TestGeographicCoverageClaims:
    """Test detection of geographic coverage claims."""

    def test_75_countries_detected(self, claim_extractor):
        text = "Presence in 75 countries worldwide."
        findings = claim_extractor.extract_and_verify(text)
        geo_claims = [f for f in findings if "75 countries" in f.flagged_text]
        assert len(geo_claims) >= 1, "Must detect country count claim"
        assert geo_claims[0].severity == Severity.HIGH


class TestCertificationClaims:
    """Test detection of certification claims with certifying bodies."""

    def test_independent_certification_vague(self, claim_extractor):
        text = "Independent cybersecurity certification."
        findings = claim_extractor.extract_and_verify(text)
        cert_findings = [
            f for f in findings
            if "certification" in f.flagged_text.lower()
        ]
        assert len(cert_findings) >= 1, "Must detect vague certification claim"

    def test_certification_with_named_body(self, claim_extractor):
        text = "Independent cybersecurity certification by the International Cybersecurity Authority."
        findings = claim_extractor.extract_and_verify(text)
        cert_with_body = [
            f for f in findings
            if "International Cybersecurity Authority" in f.flagged_text
        ]
        assert len(cert_with_body) >= 1, "Must detect certification with certifying body"
        assert cert_with_body[0].severity == Severity.HIGH


class TestFinancialClaims:
    """Test detection of cost reduction and financial claims."""

    def test_95_percent_cost_reduction_with_timebound(self, claim_extractor):
        text = "95% cybersecurity operational cost reduction within 30 days."
        findings = claim_extractor.extract_and_verify(text)
        financial = [
            f for f in findings
            if "95%" in f.flagged_text and "30 days" in f.flagged_text
        ]
        assert len(financial) >= 1, "Must detect time-bound financial claim"
        assert financial[0].severity == Severity.CRITICAL
        assert financial[0].evidence_status == EvidenceStatus.NOT_FOUND


class TestProprietaryTechnology:
    """Test detection of proprietary technology names."""

    def test_quantumshield_technology(self, claim_extractor):
        text = "Proprietary QuantumShield technology protects your data."
        findings = claim_extractor.extract_and_verify(text)
        tech_claims = [
            f for f in findings
            if "QuantumShield" in f.flagged_text
        ]
        assert len(tech_claims) >= 1, "Must detect proprietary technology name"
        assert tech_claims[0].severity == Severity.HIGH


class TestVagueQuantityClaims:
    """Test detection of vague quantity claims."""

    def test_thousands_of_organizations(self, claim_extractor):
        text = "Thousands of organisations using the technology."
        findings = claim_extractor.extract_and_verify(text)
        vague = [
            f for f in findings
            if "thousands" in f.flagged_text.lower()
        ]
        assert len(vague) >= 1, "Must detect vague quantity claim"


class TestCompleteScenario:
    """Integration test with all 8 claims from failing test."""

    def test_all_eight_claims_detected(self, claim_extractor):
        text = (
            "Proprietary QuantumShield technology. "
            "99.9999% protection against all cyberattacks. "
            "Independent cybersecurity certification by the International Cybersecurity Authority. "
            "50,000 enterprise customers. "
            "Presence in 75 countries. "
            "95% cybersecurity operational cost reduction within 30 days. "
            "Thousands of organisations using the technology."
        )
        findings = claim_extractor.extract_and_verify(text)

        # Should detect at least 8 distinct claims
        assert len(findings) >= 8, f"Expected at least 8 findings, got {len(findings)}"

        # All findings must have NOT_FOUND evidence status
        for f in findings:
            assert f.evidence_status == EvidenceStatus.NOT_FOUND, (
                f"Finding '{f.flagged_text}' must have NOT_FOUND evidence status"
            )
