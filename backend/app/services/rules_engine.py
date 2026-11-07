"""
Deterministic Rules Engine — fast regex/glossary checks.

Runs zero-latency checks for known prohibited phrases, required
disclaimers, and terminology violations without any API calls.
"""
import re
from typing import List
from app.schemas import AuditFinding, Severity, IssueCategory, EvidenceStatus
import uuid


# ───────────────────────────────────────────────
#  Rule Definitions
# ───────────────────────────────────────────────

TERMINOLOGY_RULES: List[dict] = [
    {
        "pattern": r"\bcheap\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.TERMINOLOGY,
        "explanation": (
            "The word 'cheap' is prohibited in ApexCloud marketing copy. "
            "It connotes low quality and contradicts the brand's enterprise positioning."
        ),
        "replacement_hint": "cost-effective",
        "evidence_quote": (
            "Never use the word 'cheap' to describe ApexCloud pricing. "
            "Approved alternative: 'cost-effective'."
        ),
        "evidence_source": "ApexCloud Brand Voice Guide v1.5",
    },
    {
        "pattern": r"\bfree tier forever\b",
        "severity": Severity.MEDIUM,
        "category": IssueCategory.TERMINOLOGY,
        "explanation": (
            "The phrase 'free tier forever' is not an approved product offering description. "
            "Use the approved phrasing instead."
        ),
        "replacement_hint": "free plan with no credit card required",
        "evidence_quote": "Never use 'free tier forever' — use 'free plan with no credit card required'.",
        "evidence_source": "ApexCloud Brand Voice Guide v1.5",
    },
]

SECURITY_CLAIM_RULES: List[dict] = [
    {
        "pattern": r"\b100%\s+(secure|security|safe|protection)\b",
        "severity": Severity.CRITICAL,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Absolute security guarantees are prohibited. No system can be '100% secure'. "
            "This claim is factually unsupportable and creates legal risk."
        ),
        "replacement_hint": "multi-layered enterprise security with 99.99% uptime SLA",
        "evidence_quote": (
            "Never claim absolute, unqualified security guarantees. "
            "Prohibited phrases include: '100% secure'. "
            "Instead use: 'multi-layered enterprise security with 99.99% uptime SLA'."
        ),
        "evidence_source": "ApexCloud Brand Guidelines v3.2",
    },
    {
        "pattern": r"\bunhackable\b",
        "severity": Severity.CRITICAL,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "'Unhackable' is an absolute security claim with no basis in fact. "
            "No platform can guarantee complete immunity from all attacks."
        ),
        "replacement_hint": "multi-layered enterprise security with 99.99% uptime SLA",
        "evidence_quote": (
            "Prohibited phrases include: 'unhackable'. "
            "Instead use: 'multi-layered enterprise security with 99.99% uptime SLA'."
        ),
        "evidence_source": "ApexCloud Brand Guidelines v3.2",
    },
    {
        "pattern": r"\b(complete|complete protection|100%)\s+protection\s+against\s+all",
        "severity": Severity.CRITICAL,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Claiming 'complete protection against all' attacks is an absolute guarantee "
            "prohibited by brand guidelines and legally indefensible."
        ),
        "replacement_hint": "multi-layered enterprise security",
        "evidence_quote": (
            "Prohibited phrases include: '100% protection against all cyberattacks'. "
            "Approved: 'multi-layered enterprise security with 99.99% uptime SLA'."
        ),
        "evidence_source": "ApexCloud Brand Guidelines v3.2",
    },
    {
        "pattern": r"\bzero downtime,?\s+ever\b",
        "severity": Severity.CRITICAL,
        "category": IssueCategory.PROHIBITED_PHRASE,
        "explanation": (
            "'Zero downtime, ever' is an absolute availability guarantee that is prohibited. "
            "ApexCloud's SLA is 99.99% uptime — not 100%."
        ),
        "replacement_hint": "99.99% uptime SLA across multi-region deployments",
        "evidence_quote": (
            "Prohibited phrases include: 'no downtime ever'. "
            "Approved: 'multi-layered enterprise security with 99.99% uptime SLA'."
        ),
        "evidence_source": "ApexCloud Legal & Compliance Policy v4.0",
    },
    {
        "pattern": r"\bimpenetrable\b",
        "severity": Severity.CRITICAL,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": "'Impenetrable' is an absolute security superlative, prohibited by brand guidelines.",
        "replacement_hint": "enterprise-grade security",
        "evidence_quote": "Prohibited phrases include: 'impenetrable'.",
        "evidence_source": "ApexCloud Brand Guidelines v3.2",
    },
    # Semantic variants — absolute security expressed with different phrasing
    {
        "pattern": r"\b(never\s+be\s+hacked|immune\s+to\s+(all\s+)?(cyber)?attacks?|breach[- ]proof|attack[- ]proof|hack[- ]proof|fully\s+secure)\b",
        "severity": Severity.CRITICAL,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "This phrase implies an absolute security guarantee. No system is immune to all attacks. "
            "Absolute security claims are prohibited by brand guidelines regardless of phrasing."
        ),
        "replacement_hint": "multi-layered enterprise security",
        "evidence_quote": (
            "Never claim absolute, unqualified security guarantees. "
            "All security claims must be qualified and verifiable."
        ),
        "evidence_source": "ApexCloud Brand Guidelines v3.2",
    },
    {
        "pattern": r"\bzero\s+(security\s+)?(vulnerabilities|exploits|breaches|risks?|threats?)\b",
        "severity": Severity.CRITICAL,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Claiming zero vulnerabilities or zero security risk is an absolute security guarantee "
            "prohibited by brand guidelines."
        ),
        "replacement_hint": "continuously monitored for vulnerabilities",
        "evidence_quote": (
            "Prohibited phrases include: 'zero vulnerabilities'. "
            "All security claims must be qualified and verifiable."
        ),
        "evidence_source": "ApexCloud Brand Guidelines v3.2",
    },
]

ABSOLUTE_PERFORMANCE_RULES: List[dict] = [
    {
        "pattern": r"\b(always\s+available|always\s+on|always\s+up|never\s+(goes?\s+)?down|no\s+downtime\s+ever|downtime\s+is\s+impossible)\b",
        "severity": Severity.CRITICAL,
        "category": IssueCategory.PROHIBITED_PHRASE,
        "explanation": (
            "Absolute availability claims ('always available', 'never goes down') are prohibited. "
            "ApexCloud's SLA is 99.99% uptime — not 100%. Use the approved SLA language."
        ),
        "replacement_hint": "99.99% uptime SLA across multi-region deployments",
        "evidence_quote": (
            "Do not claim 'always available' without the SLA qualifier. "
            "Prohibited: 'no downtime ever'. Approved: 'ApexCloud guarantees 99.99% SLA across multi-region deployments.'"
        ),
        "evidence_source": "ApexCloud Product Specifications v2.1",
    },
    {
        "pattern": r"\b(100%\s+uptime|zero\s+downtime(?!\s*,?\s*ever))\b",
        "severity": Severity.CRITICAL,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "'100% uptime' or 'zero downtime' is an unachievable absolute availability claim. "
            "The approved figure is 99.99% uptime SLA."
        ),
        "replacement_hint": "99.99% uptime SLA",
        "evidence_quote": (
            "ApexCloud guarantees 99.99% SLA across multi-region deployments. "
            "Do not round up to 100%. Do not claim 'always available' without the SLA qualifier."
        ),
        "evidence_source": "ApexCloud Product Specifications v2.1",
    },
    {
        "pattern": r"\b(guaranteed?\s+to\s+(work|perform|deliver|succeed)|failure[- ]proof|error[- ]free|bug[- ]free|flawless(ly)?|perfect\s+reliability)\b",
        "severity": Severity.CRITICAL,
        "category": IssueCategory.PROHIBITED_PHRASE,
        "explanation": (
            "Absolute performance guarantees ('guaranteed to work', 'failure-proof', 'error-free') "
            "are prohibited. No software system can make such promises."
        ),
        "replacement_hint": "enterprise-grade reliability with SLA-backed uptime",
        "evidence_quote": (
            "The following phrases are prohibited: 'guaranteed to work' (without conditions). "
            "All reliability claims must reference the 99.99% uptime SLA."
        ),
        "evidence_source": "ApexCloud Legal & Compliance Policy v4.0",
    },
]

UPTIME_CLAIM_RULES: List[dict] = [
    {
        # Catches any uptime percentage claim NOT equal to the approved 99.99%
        "pattern": r"\b(100%|99\.9{3,}%|99\.99{1}[0-9]+%)\s*(uptime|availability|available)\b",
        "severity": Severity.CRITICAL,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Uptime claim exceeds the approved 99.99% SLA. "
            "Claiming 100% uptime or higher than 99.99% is prohibited."
        ),
        "replacement_hint": "99.99% uptime SLA",
        "evidence_quote": (
            "ApexCloud guarantees 99.99% SLA across multi-region deployments. "
            "Do not round up to 100%."
        ),
        "evidence_source": "ApexCloud Product Specifications v2.1",
    },
]

PRICING_CLAIM_RULES: List[dict] = [
    {
        "pattern": r"\b(lowest\s+price|cheapest\s+(in\s+the\s+(industry|market))?|most\s+affordable\s+in|unbeatable\s+price|best\s+price\s+(in|on)\s+the\s+market)\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Unsupported pricing superiority claims are prohibited. "
            "These claims require documented market analysis to be verifiable."
        ),
        "replacement_hint": "cost-effective enterprise pricing",
        "evidence_quote": (
            "Never describe competitors as 'expensive' in marketing copy. "
            "Never use superlatives without data: 'the best', 'the only', 'number one'."
        ),
        "evidence_source": "ApexCloud Brand Voice Guide v1.5",
    },
    {
        "pattern": r"\bfree\s+(forever|for\s+(life|ever|always))\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Perpetual free claims ('free forever', 'free for life') are not an approved product offering. "
            "Use the approved phrasing: 'free plan with no credit card required'."
        ),
        "replacement_hint": "free plan with no credit card required",
        "evidence_quote": "Never use 'free tier forever' — use 'free plan with no credit card required'.",
        "evidence_source": "ApexCloud Brand Voice Guide v1.5",
    },
    {
        "pattern": r"\b(save\s+(up\s+to\s+)?\d+%\s*(on\s+)?your\s+bill|cut\s+your\s+(cloud\s+)?costs?\s+by\s+\d+%)\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Specific savings percentages require the benchmark disclaimer "
            "'Results based on internal testing conducted Q3 2025.' to be verifiable."
        ),
        "replacement_hint": "reduce infrastructure costs",
        "evidence_quote": (
            "All benchmark claims, performance statistics, or comparative data "
            "MUST include: 'Results based on internal testing conducted Q3 2025.'"
        ),
        "evidence_source": "ApexCloud Legal & Compliance Policy v4.0",
        "requires_absent": "Results based on internal testing conducted Q3 2025",
    },
]

COMPETITIVE_CLAIM_RULES: List[dict] = [
    {
        "pattern": r"\b(better\s+than\s+(all\s+)?competitors?|#1\s+(cloud|platform)|number\s+one\s+(cloud|provider|platform)|the\s+only\s+(platform|solution|provider)\s+that|no\s+one\s+else\s+(can|does)|beat(s)?\s+every\s+(competitor|alternative))\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Unsupported competitive superiority claims are prohibited. "
            "Superlatives ('the only', '#1', 'better than all') require verifiable third-party data."
        ),
        "replacement_hint": "industry-leading enterprise cloud platform",
        "evidence_quote": (
            "Avoid superlatives without data: 'the best', 'the only', 'number one'. "
            "Do not use aggressive urgency tactics."
        ),
        "evidence_source": "ApexCloud Brand Voice Guide v1.5",
    },
    {
        "pattern": r"\b(competitors?\s+are\s+(expensive|overpriced|slow|outdated|inferior)|unlike\s+competitors?[\s,]+we\s+(never|always|guarantee))\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Disparaging competitor claims are prohibited in ApexCloud marketing copy. "
            "Comparative claims must be supported by verifiable evidence."
        ),
        "replacement_hint": "ApexCloud's enterprise approach",
        "evidence_quote": "Never describe competitors as 'expensive' in marketing copy.",
        "evidence_source": "ApexCloud Brand Voice Guide v1.5",
    },
]

PRODUCT_CAPABILITY_RULES: List[dict] = [
    {
        "pattern": r"\b(instant\s+setup(?!\s+[\"\']?typically)(?!\s+in\s+under)(?!\s+\(typically))\b",
        "severity": Severity.MEDIUM,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "'Instant setup' must be qualified with 'typically under 15 minutes'. "
            "Unqualified setup time claims are prohibited."
        ),
        "replacement_hint": "instant setup, typically under 15 minutes",
        "evidence_quote": (
            "Prohibited: 'instant setup' without qualifying 'typically under 15 minutes'."
        ),
        "evidence_source": "ApexCloud Legal & Compliance Policy v4.0",
    },
    {
        "pattern": r"\b(we\s+(will\s+)?never\s+lose\s+your\s+data|your\s+data\s+is\s+(100%\s+)?safe\s+forever|data\s+loss\s+is\s+impossible)\b",
        "severity": Severity.CRITICAL,
        "category": IssueCategory.PROHIBITED_PHRASE,
        "explanation": (
            "'We will never lose your data' is a prohibited absolute guarantee. "
            "Use the approved phrasing: 'industry-leading data redundancy with 3-site replication'."
        ),
        "replacement_hint": "industry-leading data redundancy with 3-site replication",
        "evidence_quote": (
            "Prohibited: 'we will never lose your data'. "
            "Approved: 'industry-leading data redundancy with 3-site replication'."
        ),
        "evidence_source": "ApexCloud Legal & Compliance Policy v4.0",
    },
    {
        "pattern": r"\b(risk[- ]free(\s+(trial|guarantee|promise))?)\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.PROHIBITED_PHRASE,
        "explanation": (
            "'Risk-free' is a prohibited term. Financial risk must always be qualified. "
            "Use 'try ApexCloud for 30 days' or reference the specific guarantee terms instead."
        ),
        "replacement_hint": "try ApexCloud Enterprise for 30 days",
        "evidence_quote": (
            "Prohibited phrases include: 'risk-free' (financial risk must always be qualified)."
        ),
        "evidence_source": "ApexCloud Legal & Compliance Policy v4.0",
    },
]

GUARANTEED_OUTCOME_RULES: List[dict] = [
    {
        "pattern": r"\b(guaranteed?\s+(ROI|savings?|results?|outcomes?|success|growth)|we\s+guarantee\s+(you|your|that)|your\s+success\s+is\s+guaranteed?)\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Guaranteed business outcomes are prohibited without specific, verifiable conditions. "
            "Business results depend on many factors outside ApexCloud's control."
        ),
        "replacement_hint": "ApexCloud helps businesses achieve measurable results",
        "evidence_quote": (
            "Never claim absolute, unqualified guarantees. "
            "All benchmark claims must include: 'Results based on internal testing conducted Q3 2025.'"
        ),
        "evidence_source": "ApexCloud Legal & Compliance Policy v4.0",
    },
]

PROMOTIONAL_CLAIM_RULES: List[dict] = [
    {
        "pattern": r"\b(biggest\s+sale|best\s+deal\s+(of|in)\s+the\s+(year|decade|century)|once[- ]in[- ]a[- ]lifetime\s+(offer|deal|opportunity)|exclusive\s+offer\s+(just\s+)?for\s+you)\b",
        "severity": Severity.MEDIUM,
        "category": IssueCategory.TONE_VOICE,
        "explanation": (
            "Hyperbolic promotional claims contradict ApexCloud's transparent, confident brand voice. "
            "'Biggest sale', 'best deal of the year' are not verifiable superlatives."
        ),
        "replacement_hint": "special enterprise pricing — contact sales",
        "evidence_quote": (
            "Avoid superlatives without data: 'the best', 'the only', 'number one'. "
            "Do not use aggressive urgency tactics."
        ),
        "evidence_source": "ApexCloud Brand Voice Guide v1.5",
    },
]

# Unverified claims that require evidence — catch even when exact keywords don't match
UNVERIFIED_CLAIM_RULES: List[dict] = [
    # Extreme security percentages
    {
        "pattern": r"\b(99\.9{3,}%|99\.99{2,}%|99\.999+%)\s*(protection|security|safe|secure|availability|uptime)\b",
        "severity": Severity.CRITICAL,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Extreme percentage claims (99.999%+) require verifiable evidence. "
            "Such claims must be supported by documented testing methodology and results."
        ),
        "replacement_hint": "enterprise-grade security with 99.99% uptime SLA",
        "evidence_quote": (
            "All security and performance claims must be verifiable and supported by documented evidence. "
            "Use approved SLA figures: 99.99% uptime."
        ),
        "evidence_source": "ApexCloud Legal & Compliance Policy v4.0",
        "requires_absent": "Results based on internal testing",
    },
    # "All cyberattacks" claims
    {
        "pattern": r"\b(all\s+(cyber)?attacks?|every\s+(cyber)?attack|any\s+(cyber)?attack)\b",
        "severity": Severity.CRITICAL,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Claims about protection against 'all attacks' are absolute guarantees that cannot be verified. "
            "No security solution can protect against every possible attack vector."
        ),
        "replacement_hint": "protection against known attack vectors",
        "evidence_quote": (
            "Never claim protection against 'all attacks' or 'any attack'. "
            "All security claims must be specific and verifiable."
        ),
        "evidence_source": "ApexCloud Brand Guidelines v3.2",
    },
    # Customer count assertions
    {
        "pattern": r"\b(\d{1,3}(,\d{3})*(\.\d+)?\s*(k|thousand|million|m)?)?\s*(enterprise\s+)?customers?\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Customer count claims require verification against current customer database. "
            "Specific numbers must be accurate and up-to-date."
        ),
        "replacement_hint": "thousands of enterprise customers",
        "evidence_quote": (
            "All customer statistics must be verifiable against current records. "
            "Do not fabricate or inflate customer counts."
        ),
        "evidence_source": "ApexCloud Legal & Compliance Policy v4.0",
        "requires_absent": "verified customer count",
    },
    # Geographic coverage claims
    {
        "pattern": r"\b(\d{1,3})\s*(countries|countries\s+worldwide|global\s+regions|international\s+markets)\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Geographic coverage claims must be verified against actual operational presence. "
            "Specific country counts require documented evidence."
        ),
        "replacement_hint": "global presence",
        "evidence_quote": (
            "Geographic coverage claims must match actual operational presence. "
            "Verify specific country counts against current records."
        ),
        "evidence_source": "ApexCloud Legal & Compliance Policy v4.0",
        "requires_absent": "verified geographic presence",
    },
    # Cost reduction percentages
    {
        "pattern": r"\b(\d{1,3})%\s*(cost\s+reduction|cost\s+savings|cost\s+cut|reduction\s+in\s+costs)\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Specific cost reduction percentages require documented benchmark studies with methodology disclosure. "
            "Must include disclaimer: 'Results based on internal testing conducted Q3 2025.'"
        ),
        "replacement_hint": "significant cost savings",
        "evidence_quote": (
            "All benchmark claims, performance statistics, or comparative data "
            "MUST include: 'Results based on internal testing conducted Q3 2025.'"
        ),
        "evidence_source": "ApexCloud Legal & Compliance Policy v4.0",
        "requires_absent": "Results based on internal testing",
    },
    # Certification claims
    {
        "pattern": r"\b(independent\s+)?(cybersecurity\s+)?certification\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Certification claims must name the specific certifying body and be verifiable. "
            "Vague certification claims without specifics are prohibited."
        ),
        "replacement_hint": "SOC 2 Type II and ISO 27001 certified",
        "evidence_quote": (
            "All certification claims must name the specific certification and certifying body. "
            "Reference only actual, current certifications."
        ),
        "evidence_source": "ApexCloud Legal & Compliance Policy v4.0",
        "requires_absent": "SOC 2|ISO 27001|certified",
    },
    # Proprietary technology claims
    {
        "pattern": r"\b(proprietary\s+)?\w+(Shield|Guard|Protect|Secure|Defense)\s+(technology|platform|system)\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Proprietary technology names require verification against approved product documentation. "
            "Claims about technology capabilities must be supported by technical specifications."
        ),
        "replacement_hint": "enterprise security technology",
        "evidence_quote": (
            "All proprietary technology claims must be documented in approved product specifications. "
            "Do not fabricate technology names or capabilities."
        ),
        "evidence_source": "ApexCloud Product Specifications v2.1",
        "requires_absent": "documented in product specifications",
    },
    # "Thousands of organizations" claims
    {
        "pattern": r"\bthousands?\s+of\s+(organizations|organisations|companies|enterprises|businesses)\b",
        "severity": Severity.MEDIUM,
        "category": IssueCategory.UNSUPPORTED_CLAIM,
        "explanation": (
            "Vague quantity claims ('thousands of organizations') should be specific and verifiable. "
            "Prefer specific, documented numbers or approved phrasing."
        ),
        "replacement_hint": "organizations worldwide",
        "evidence_quote": (
            "Prefer specific, verifiable numbers over vague quantities. "
            "Customer statistics must be current and accurate."
        ),
        "evidence_source": "ApexCloud Brand Voice Guide v1.5",
    },
]

TONE_VOICE_RULES: List[dict] = [
    {
        "pattern": r"\bhurry before (it'?s?|they are|they're) gone\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.TONE_VOICE,
        "explanation": "High-pressure urgency language is prohibited. ApexCloud voice is confident and customer-first, not pressure-driven.",
        "replacement_hint": "Learn more about our enterprise plans",
        "evidence_quote": (
            "Do NOT use high-pressure sales language such as: 'hurry before it's gone'."
        ),
        "evidence_source": "ApexCloud Brand Voice Guide v1.5",
    },
    {
        "pattern": r"\b(sign up|act|purchase)\s+(NOW|IMMEDIATELY|RIGHT NOW|TODAY ONLY)\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.TONE_VOICE,
        "explanation": "Aggressive urgency calls-to-action contradict ApexCloud's confident, transparent brand voice.",
        "replacement_hint": "Get started with ApexCloud",
        "evidence_quote": (
            "Do NOT use high-pressure sales language such as: 'limited time only — sign up NOW', "
            "'act immediately or lose your discount'."
        ),
        "evidence_source": "ApexCloud Brand Voice Guide v1.5",
    },
    {
        "pattern": r"\bdon'?t miss out\b",
        "severity": Severity.MEDIUM,
        "category": IssueCategory.TONE_VOICE,
        "explanation": "FOMO-driven language ('don't miss out') is inconsistent with ApexCloud's measured enterprise voice.",
        "replacement_hint": "Discover ApexCloud's enterprise capabilities",
        "evidence_quote": "Do NOT use high-pressure sales language such as: 'don't miss out'.",
        "evidence_source": "ApexCloud Brand Voice Guide v1.5",
    },
    {
        "pattern": r"\bact immediately or lose\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.TONE_VOICE,
        "explanation": "Pressure tactics like 'act immediately or lose' violate tone standards.",
        "replacement_hint": "Contact sales to discuss your options",
        "evidence_quote": "Do NOT use: 'act immediately or lose your discount'.",
        "evidence_source": "ApexCloud Brand Voice Guide v1.5",
    },
    {
        "pattern": r"\blimited[- ]time (only|offer)\b",
        "severity": Severity.MEDIUM,
        "category": IssueCategory.TONE_VOICE,
        "explanation": "Limited-time pressure framing contradicts ApexCloud's transparent, customer-first voice.",
        "replacement_hint": "current pricing",
        "evidence_quote": "Do NOT use high-pressure sales language such as: 'limited time only'.",
        "evidence_source": "ApexCloud Brand Voice Guide v1.5",
    },
]

COMPLIANCE_RULES: List[dict] = [
    {
        # Detects performance claims without required disclaimer
        "pattern": r"\b(\d+%?x?\s*(faster|better|improved|reduction|increase|decrease|performance|more efficient))\b",
        "severity": Severity.HIGH,
        "category": IssueCategory.COMPLIANCE,
        "explanation": (
            "Benchmark and performance claims require the mandatory disclaimer: "
            "'Results based on internal testing conducted Q3 2025.' "
            "This disclaimer is absent from the current text."
        ),
        "replacement_hint": "{original_text}. Results based on internal testing conducted Q3 2025.",
        "evidence_quote": (
            "All benchmark claims, performance statistics, or comparative data "
            "MUST include: 'Results based on internal testing conducted Q3 2025.'"
        ),
        "evidence_source": "ApexCloud Legal & Compliance Policy v4.0",
        # Special flag: only trigger if disclaimer is NOT found in full text
        "requires_absent": "Results based on internal testing conducted Q3 2025",
    },
]

NAMING_RULES: List[dict] = [
    {
        "pattern": r"\bApex Cloud\b",  # Two words — wrong
        "severity": Severity.MEDIUM,
        "category": IssueCategory.TERMINOLOGY,
        "explanation": "Product name is misspelled. It must be 'ApexCloud' (one word, capital A and C).",
        "replacement_hint": "ApexCloud",
        "evidence_quote": "Always write 'ApexCloud' as one word, capital A and C. Never write: 'Apex Cloud' (two words).",
        "evidence_source": "ApexCloud Brand Guidelines v3.2",
    },
]

ALL_RULES = (
    TERMINOLOGY_RULES
    + SECURITY_CLAIM_RULES
    + ABSOLUTE_PERFORMANCE_RULES
    + UPTIME_CLAIM_RULES
    + PRICING_CLAIM_RULES
    + COMPETITIVE_CLAIM_RULES
    + PRODUCT_CAPABILITY_RULES
    + GUARANTEED_OUTCOME_RULES
    + PROMOTIONAL_CLAIM_RULES
    + UNVERIFIED_CLAIM_RULES
    + TONE_VOICE_RULES
    + COMPLIANCE_RULES
    + NAMING_RULES
)


class RulesEngine:
    """
    Fast deterministic rule checker.

    Runs synchronously against all registered rules using regex matching.
    No external API calls — zero latency.
    """

    def check(self, text: str) -> List[AuditFinding]:
        """
        Check text against all deterministic rules.

        Returns a list of AuditFinding objects for each violation found.
        """
        findings: List[AuditFinding] = []
        seen_patterns: set[str] = set()

        for rule in ALL_RULES:
            pattern = rule["pattern"]
            flags = re.IGNORECASE

            # Skip compliance rules where disclaimer is present
            if "requires_absent" in rule:
                if rule["requires_absent"].lower() in text.lower():
                    continue

            matches = list(re.finditer(pattern, text, flags))
            if not matches:
                continue

            for match in matches:
                flagged = match.group(0)
                dedup_key = f"{pattern}::{flagged.lower()}"
                if dedup_key in seen_patterns:
                    continue
                seen_patterns.add(dedup_key)

                # Build suggested replacement
                replacement = rule.get("replacement_hint", "")
                if "{original_text}" in replacement:
                    # Get surrounding sentence context
                    sentence_match = self._extract_sentence(text, match.start(), match.end())
                    replacement = replacement.replace("{original_text}", sentence_match)

                findings.append(
                    AuditFinding(
                        id=str(uuid.uuid4()),
                        category=rule["category"],
                        severity=rule["severity"],
                        flagged_text=flagged,
                        explanation=rule["explanation"],
                        evidence_quote=rule.get("evidence_quote"),
                        evidence_source=rule.get("evidence_source"),
                        evidence_status=EvidenceStatus.SUPPORTED,  # Deterministic = always supported
                        suggested_replacement=replacement,
                        confidence_score=0.97,  # High confidence for deterministic rules
                    )
                )

        return findings

    def _extract_sentence(self, text: str, start: int, end: int, context_chars: int = 80) -> str:
        """Extract a sentence snippet around the match for context."""
        segment_start = max(0, start - context_chars)
        segment_end = min(len(text), end + context_chars)
        return text[segment_start:segment_end].strip()
