"""ApexCloud brand guidelines seed data and sample test drafts."""
from app.schemas import GuidelineItem
from typing import List, Dict, Any
import uuid


def get_seed_guidelines() -> List[Dict[str, Any]]:
    """Return pre-built ApexCloud brand guidelines."""
    return [
        {
            "id": "guideline-001",
            "title": "Prohibited Security Absolutism",
            "category": "unsupported_claim",
            "rule_text": (
                "Never claim absolute, unqualified security guarantees. "
                "Prohibited phrases include: '100% secure', 'unhackable', 'impenetrable', "
                "'zero vulnerabilities', '100% protection against all cyberattacks'. "
                "Instead use: 'multi-layered enterprise security with 99.99% uptime SLA'. "
                "All security claims must be qualified and verifiable."
            ),
            "source_document": "ApexCloud Brand Guidelines v3.2",
            "version": "3.2",
            "tags": ["security", "claims", "prohibited"],
        },
        {
            "id": "guideline-002",
            "title": "SLA Uptime Guarantee",
            "category": "unsupported_claim",
            "rule_text": (
                "ApexCloud guarantees 99.99% SLA across multi-region deployments. "
                "Do not round up to 100%. Do not claim 'always available' without "
                "the SLA qualifier. All uptime claims must reference: "
                "'ApexCloud guarantees 99.99% SLA across multi-region deployments.'"
            ),
            "source_document": "ApexCloud Product Specifications v2.1",
            "version": "2.1",
            "tags": ["SLA", "uptime", "claims"],
        },
        {
            "id": "guideline-003",
            "title": "Pricing Terminology",
            "category": "terminology",
            "rule_text": (
                "Never use the word 'cheap' to describe ApexCloud pricing. "
                "Approved alternative: 'cost-effective'. "
                "Never use 'free tier forever' — use 'free plan with no credit card required'. "
                "Never describe competitors as 'expensive' in marketing copy."
            ),
            "source_document": "ApexCloud Brand Voice Guide v1.5",
            "version": "1.5",
            "tags": ["pricing", "terminology"],
        },
        {
            "id": "guideline-004",
            "title": "Voice and Tone Standards",
            "category": "tone_voice",
            "rule_text": (
                "ApexCloud voice is: Confident, transparent, and customer-first. "
                "Do NOT use high-pressure sales language such as: 'hurry before it's gone', "
                "'limited time only — sign up NOW', 'don't miss out', "
                "'act immediately or lose your discount'. "
                "Avoid superlatives without data: 'the best', 'the only', 'number one'. "
                "Do not use aggressive urgency tactics."
            ),
            "source_document": "ApexCloud Brand Voice Guide v1.5",
            "version": "1.5",
            "tags": ["tone", "voice", "sales"],
        },
        {
            "id": "guideline-005",
            "title": "Benchmark Disclaimer Requirement",
            "category": "compliance",
            "rule_text": (
                "All benchmark claims, performance statistics, or comparative data "
                "MUST include the mandatory disclaimer: "
                "'Results based on internal testing conducted Q3 2025.' "
                "Omitting this disclaimer from any performance claim is a compliance violation."
            ),
            "source_document": "ApexCloud Legal & Compliance Policy v4.0",
            "version": "4.0",
            "tags": ["benchmark", "disclaimer", "compliance", "legal"],
        },
        {
            "id": "guideline-006",
            "title": "Prohibited Absolute Guarantees",
            "category": "prohibited_phrase",
            "rule_text": (
                "The following phrases are prohibited in all external communications: "
                "- 'guaranteed to work' (without conditions) "
                "- 'risk-free' (financial risk must always be qualified) "
                "- 'no downtime ever' "
                "- 'we will never lose your data' (only 'industry-leading data redundancy with 3-site replication') "
                "- 'instant setup' without qualifying 'typically under 15 minutes'."
            ),
            "source_document": "ApexCloud Legal & Compliance Policy v4.0",
            "version": "4.0",
            "tags": ["prohibited", "guarantees"],
        },
        {
            "id": "guideline-007",
            "title": "Product Names and Capitalization",
            "category": "terminology",
            "rule_text": (
                "Always write 'ApexCloud' as one word, capital A and C. "
                "Never write: 'Apex Cloud' (two words), 'apexcloud' (lowercase), 'APEXCLOUD' (all caps). "
                "Product names: ApexCloud Core, ApexCloud Enterprise, ApexCloud Shield. "
                "Do not invent product names not in this list."
            ),
            "source_document": "ApexCloud Brand Guidelines v3.2",
            "version": "3.2",
            "tags": ["naming", "spelling", "product"],
        },
        {
            "id": "guideline-008",
            "title": "Data Residency Claims",
            "category": "compliance",
            "rule_text": (
                "Data residency claims must specify regions. Approved statement: "
                "'ApexCloud offers data residency in US, EU, APAC, and India regions.' "
                "Do not claim 'your data never leaves your country' without specifying "
                "the available regions and applicable plans. "
                "Data residency is available on Enterprise plan only."
            ),
            "source_document": "ApexCloud Legal & Compliance Policy v4.0",
            "version": "4.0",
            "tags": ["data", "residency", "compliance"],
        },
    ]


SAMPLE_DRAFTS = [
    {
        "id": "sample-1",
        "title": "Security Claim Violation",
        "description": "Contains critical security absolutism and unsupported guarantee",
        "text": (
            "Introducing ApexCloud Shield — the only 100% unhackable cloud platform on the market. "
            "Our advanced AI provides complete protection against all cyberattacks, ensuring your "
            "data is 100% secure at all times. With ApexCloud, downtime is a thing of the past — "
            "we guarantee zero downtime, ever. Our platform delivers 3x faster performance than "
            "any competitor. Sign up NOW before this limited-time offer expires!"
        ),
    },
    {
        "id": "sample-2",
        "title": "Terminology Deviation",
        "description": "Uses prohibited pricing terminology and wrong product naming",
        "text": (
            "Looking for a cheap cloud solution that doesn't sacrifice reliability? "
            "Apex Cloud offers the most affordable pricing in the industry. "
            "Start with our free tier forever plan — no credit card needed! "
            "Our platform has been tested as the best and fastest solution available. "
            "Don't miss out — act immediately or lose your early-bird discount."
        ),
    },
    {
        "id": "sample-3",
        "title": "Compliant Launch Post",
        "description": "Follows all brand guidelines — should pass with zero critical findings",
        "text": (
            "ApexCloud Enterprise delivers multi-layered enterprise security with 99.99% uptime SLA "
            "across multi-region deployments. Our cost-effective pricing plans make enterprise-grade "
            "cloud infrastructure accessible to growing businesses. "
            "ApexCloud offers data residency in US, EU, APAC, and India regions, available on our "
            "Enterprise plan. Performance benchmarks show a 40% reduction in infrastructure costs. "
            "Results based on internal testing conducted Q3 2025."
        ),
    },
]
