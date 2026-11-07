"""
Unit + integration tests for the BrandSentinel AI audit engine.

Tests:
- Absolute security guarantee → Critical finding with evidence
- Clean text → zero blocking findings
- Terminology violation → correct severity and suggestion
- Compliance benchmark → disclaimer detection
"""
import pytest
from app.services.rules_engine import RulesEngine
from app.schemas import Severity, IssueCategory, EvidenceStatus


@pytest.fixture
def engine():
    """Fresh rules engine for each test."""
    return RulesEngine()


# ─────────────────────────────────────────────
#  Security Claims
# ─────────────────────────────────────────────

class TestAbsoluteSecurityClaims:
    """Critical violations: absolute security guarantees."""

    def test_unhackable_triggers_critical(self, engine: RulesEngine):
        text = "Our platform is completely unhackable and immune to all threats."
        findings = engine.check(text)
        critical = [f for f in findings if f.severity == Severity.CRITICAL]
        assert len(critical) >= 1, "Expected at least 1 Critical finding for 'unhackable'"
        assert any("unhackable" in f.flagged_text.lower() for f in critical)

    def test_100_percent_secure_triggers_critical(self, engine: RulesEngine):
        text = "Your data is 100% secure with ApexCloud Shield."
        findings = engine.check(text)
        critical = [f for f in findings if f.severity == Severity.CRITICAL]
        assert len(critical) >= 1, "Expected Critical finding for '100% secure'"

    def test_100_protection_against_all_triggers_critical(self, engine: RulesEngine):
        text = "ApexCloud provides 100% protection against all cyberattacks."
        findings = engine.check(text)
        critical = [f for f in findings if f.severity == Severity.CRITICAL]
        assert len(critical) >= 1, "Expected Critical finding for '100% protection against all'"

    def test_zero_downtime_ever_triggers_critical(self, engine: RulesEngine):
        text = "We guarantee zero downtime, ever. Your business never stops."
        findings = engine.check(text)
        critical = [f for f in findings if f.severity == Severity.CRITICAL]
        assert len(critical) >= 1, "Expected Critical for 'zero downtime, ever'"

    def test_critical_finding_has_evidence(self, engine: RulesEngine):
        """Critical findings must have evidence sources from approved guidelines."""
        text = "ApexCloud is completely unhackable."
        findings = engine.check(text)
        critical = [f for f in findings if f.severity == Severity.CRITICAL]
        assert len(critical) >= 1
        for c in critical:
            assert c.evidence_source is not None, "Critical finding must have an evidence source"
            assert c.evidence_status == EvidenceStatus.SUPPORTED, "Deterministic findings are always SUPPORTED"

    def test_critical_finding_has_replacement(self, engine: RulesEngine):
        """Critical findings must include a suggested replacement."""
        text = "Our system is 100% secure."
        findings = engine.check(text)
        critical = [f for f in findings if f.severity == Severity.CRITICAL]
        assert len(critical) >= 1
        for c in critical:
            assert c.suggested_replacement is not None and len(c.suggested_replacement) > 0


# ─────────────────────────────────────────────
#  Clean Content
# ─────────────────────────────────────────────

class TestCleanContent:
    """Compliant content should produce zero or only low-severity findings."""

    def test_fully_compliant_text_has_no_critical_high(self, engine: RulesEngine):
        text = (
            "ApexCloud Enterprise delivers multi-layered enterprise security with 99.99% uptime SLA "
            "across multi-region deployments. Our cost-effective pricing plans make enterprise-grade "
            "cloud infrastructure accessible. Performance improved by 40%. "
            "Results based on internal testing conducted Q3 2025."
        )
        findings = engine.check(text)
        blocking = [f for f in findings if f.severity in (Severity.CRITICAL, Severity.HIGH)]
        assert len(blocking) == 0, (
            f"Expected no Critical/High findings for compliant text, got: "
            f"{[(f.severity, f.flagged_text) for f in blocking]}"
        )

    def test_empty_text_returns_no_findings(self, engine: RulesEngine):
        findings = engine.check("   ")
        assert len(findings) == 0


# ─────────────────────────────────────────────
#  Terminology
# ─────────────────────────────────────────────

class TestTerminologyRules:
    """Prohibited terminology checks."""

    def test_cheap_triggers_high(self, engine: RulesEngine):
        text = "Get our cheap cloud storage starting at $5/month."
        findings = engine.check(text)
        assert any(
            f.severity == Severity.HIGH and "cheap" in f.flagged_text.lower()
            for f in findings
        ), "Expected HIGH finding for 'cheap'"

    def test_cheap_suggestion_is_cost_effective(self, engine: RulesEngine):
        text = "ApexCloud offers cheap pricing."
        findings = engine.check(text)
        cheap_findings = [f for f in findings if "cheap" in f.flagged_text.lower()]
        assert len(cheap_findings) >= 1
        assert "cost-effective" in cheap_findings[0].suggested_replacement.lower()

    def test_apex_cloud_two_words_triggers_medium(self, engine: RulesEngine):
        text = "Apex Cloud delivers enterprise infrastructure."
        findings = engine.check(text)
        naming_findings = [
            f for f in findings
            if f.category == IssueCategory.TERMINOLOGY and "apex cloud" in f.flagged_text.lower()
        ]
        assert len(naming_findings) >= 1
        assert naming_findings[0].severity == Severity.MEDIUM


# ─────────────────────────────────────────────
#  Tone & Voice
# ─────────────────────────────────────────────

class TestToneVoice:
    """High-pressure sales language violations."""

    def test_signup_now_triggers_high(self, engine: RulesEngine):
        text = "Sign up NOW before the offer expires!"
        findings = engine.check(text)
        high_findings = [f for f in findings if f.severity == Severity.HIGH]
        assert len(high_findings) >= 1

    def test_dont_miss_out_triggers_medium(self, engine: RulesEngine):
        text = "Don't miss out on the best deal of the year!"
        findings = engine.check(text)
        assert any(
            f.category == IssueCategory.TONE_VOICE
            for f in findings
        ), "Expected TONE_VOICE finding for 'don't miss out'"


# ─────────────────────────────────────────────
#  Compliance (Benchmark Disclaimer)
# ─────────────────────────────────────────────

class TestComplianceRules:
    """Benchmark disclaimer requirement."""

    def test_performance_claim_without_disclaimer_triggers_high(self, engine: RulesEngine):
        text = "ApexCloud delivers 3x faster processing than legacy solutions."
        findings = engine.check(text)
        compliance = [f for f in findings if f.category == IssueCategory.COMPLIANCE]
        high_compliance = [f for f in compliance if f.severity == Severity.HIGH]
        assert len(high_compliance) >= 1

    def test_benchmark_with_disclaimer_is_clean(self, engine: RulesEngine):
        text = (
            "ApexCloud delivers 40% cost reduction. "
            "Results based on internal testing conducted Q3 2025."
        )
        findings = engine.check(text)
        compliance = [f for f in findings if f.category == IssueCategory.COMPLIANCE]
        assert len(compliance) == 0, "Benchmark with required disclaimer should not trigger compliance finding"


# ─────────────────────────────────────────────
#  Finding Integrity
# ─────────────────────────────────────────────

class TestFindingIntegrity:
    """All findings must meet structural requirements."""

    def test_all_findings_have_required_fields(self, engine: RulesEngine):
        text = (
            "Our unhackable platform offers cheap pricing and guarantees complete "
            "protection against all cyberattacks. Sign up NOW!"
        )
        findings = engine.check(text)
        assert len(findings) > 0, "Expected at least some findings for problematic text"
        for f in findings:
            assert f.id and len(f.id) > 0, "Finding must have an id"
            assert f.category is not None
            assert f.severity is not None
            assert f.flagged_text and len(f.flagged_text) > 0, "Finding must have flagged_text"
            assert f.explanation and len(f.explanation) > 0, "Finding must have explanation"
            assert 0.0 <= f.confidence_score <= 1.0, "Confidence score must be 0-1"

    def test_deterministic_findings_are_always_supported(self, engine: RulesEngine):
        text = "The platform is unhackable and cheap."
        findings = engine.check(text)
        for f in findings:
            assert f.evidence_status == EvidenceStatus.SUPPORTED, (
                f"Deterministic finding '{f.flagged_text}' must be SUPPORTED"
            )
