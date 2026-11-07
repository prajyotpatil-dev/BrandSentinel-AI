"""
Gemini LLM Auditor with OpenRouter Fallback — contextual brand governance analysis.

Uses google-genai SDK (google-genai>=2.0) as primary, OpenRouter API as secondary fallback.
Falls back silently on timeout/error; deterministic results always apply.

Evidence fabrication prevention:
- Prompt instructs: ground strictly on provided guidelines only.
- Unverifiable claims → evidence_status = "not_found".
- evidence_quote must be a verbatim excerpt from the supplied guidelines.
"""
import json
import uuid
import logging
import time
import random
import urllib.request
import urllib.error
from typing import List, Tuple

from app.schemas import AuditFinding, GuidelineItem, Severity, IssueCategory, EvidenceStatus
from app.config import settings

logger = logging.getLogger(__name__)


def _should_retry_gemini(err: Exception) -> Tuple[bool, bool]:
    """
    Determine if an exception represents a transient error worth retrying,
    and whether to skip retries immediately (e.g. 429 quota / 404 not found / 401 auth).
    Returns (should_retry, skip_to_secondary).
    """
    err_str = str(err).lower()

    # Permanent or quota errors -> try secondary immediately without retrying Gemini
    if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
        logger.warning("[LLMauditor] Gemini quota exhausted or rate limited (429). Failing over to OpenRouter immediately.")
        return False, True
    if "404" in err_str or "not_found" in err_str:
        logger.warning(f"[LLMauditor] Gemini model {settings.gemini_model} not found (404). Failing over to OpenRouter immediately.")
        return False, True
    if "401" in err_str or "403" in err_str or "unauthenticated" in err_str or "api_key" in err_str:
        logger.warning("[LLMauditor] Gemini authentication or authorization failure. Failing over to OpenRouter immediately.")
        return False, True

    # Transient errors -> retry briefly
    if any(code in err_str for code in ["503", "502", "504", "unavailable", "overloaded", "timeout", "deadline exceeded"]):
        return True, False

    status_code = getattr(err, "status_code", None) or getattr(err, "code", None)
    if status_code in [502, 503, 504]:
        return True, False
    if status_code in [429, 401, 403, 404]:
        return False, True

    return True, False


def _get_retry_after(err: Exception) -> float:
    """Extract Retry-After header value if present."""
    headers = getattr(err, "headers", {})
    retry_after = headers.get("Retry-After") or headers.get("retry-after")
    if retry_after:
        try:
            return float(retry_after)
        except ValueError:
            pass
    return 0.0


def _build_prompt(content: str, guidelines: List[GuidelineItem]) -> str:
    guidelines_text = "\n\n".join(
        f"[{i+1}] Rule: {g.title}\n"
        f"Source: {g.source_document}\n"
        f"Policy: {g.rule_text}"
        for i, g in enumerate(guidelines)
    )
    return f"""You are a rigorous brand governance auditor for ApexCloud.

CRITICAL RULES:
1. Only flag violations explicitly supported by the provided brand guidelines below.
2. Quote verbatim from the guidelines in evidence_quote — do NOT paraphrase or invent.
3. If no supporting guideline exists, set evidence_status to "not_found" and confidence_score below 0.4.
4. Keep suggested_replacement targeted: preserve the author's sentence structure, swap only the problematic phrasing.
5. Do NOT flag the same issue twice.
6. Return ONLY a valid JSON array. Return [] if fully compliant.

BRAND GUIDELINES:
{guidelines_text}

CONTENT TO AUDIT:
\"\"\"{content}\"\"\"

Return a JSON array where each element has exactly these fields:
- category: one of [terminology, unsupported_claim, tone_voice, prohibited_phrase, compliance]
- severity: one of [critical, high, medium, low]
- flagged_text: exact excerpt copied from the content
- explanation: why this violates the specific policy
- evidence_quote: verbatim quote from the guidelines (null if not_found)
- evidence_source: source document name from the guidelines (null if not_found)
- evidence_status: "supported" | "contradicted" | "not_found"
- suggested_replacement: minimal targeted correction
- confidence_score: float 0.0–1.0

Return only the JSON array, no markdown fences, no extra text."""


class LLMauditor:
    """Gemini-powered contextual audit with OpenRouter fallback."""

    MODEL_NAME = settings.gemini_model if hasattr(settings, "gemini_model") else "gemini-3.8-flash"
    OPENROUTER_MODEL = settings.openrouter_model if hasattr(settings, "openrouter_model") else "anthropic/claude-3.5-sonnet"

    def __init__(self):
        self._client = None
        self._available = False
        self._types = None
        self._init_client()

    def _init_client(self):
        if not settings.gemini_api_key and not settings.openrouter_api_key:
            logger.warning("[LLMauditor] No GEMINI_API_KEY or OPENROUTER_API_KEY — deterministic-only mode.")
            return

        if settings.gemini_api_key:
            try:
                from google import genai
                from google.genai import types
                self._client = genai.Client(api_key=settings.gemini_api_key)
                self._types = types
                self._available = True
                logger.info(f"[LLMauditor] Gemini client initialized successfully ({self.MODEL_NAME}).")
            except Exception as e:
                logger.error(f"[LLMauditor] Gemini init failed: {type(e).__name__} - {e}")

        if settings.openrouter_api_key:
            self._available = True
            logger.info(f"[LLMauditor] OpenRouter fallback configured ({self.OPENROUTER_MODEL}).")

    @property
    def is_available(self) -> bool:
        return self._available

    def _call_openrouter(self, prompt: str) -> str:
        """Call OpenRouter API as secondary fallback."""
        if not settings.openrouter_api_key:
            raise ValueError("OpenRouter API key not configured.")

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://brandsentinel.ai",
            "X-Title": "BrandSentinel AI",
        }
        payload = {
            "model": self.OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": "You are a rigorous brand governance auditor. Return ONLY a valid JSON array of findings."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]

    def analyze(
        self,
        content: str,
        guidelines: List[GuidelineItem],
    ) -> Tuple[List[AuditFinding], dict]:
        """
        Analyze content against guidelines with Gemini 3.8 Flash (Primary)
        or OpenRouter (Secondary fallback).

        Returns (findings, metadata).
        """
        metadata = {
            "provider": None,
            "gemini_status": "skipped",
            "openrouter_status": "skipped",
            "error": None
        }

        if not self._available:
            return [], metadata

        prompt = _build_prompt(content, guidelines)
        response_text = None

        # 1. Try Gemini Primary
        if self._client and settings.gemini_api_key:
            metadata["gemini_status"] = "failed"
            max_retries = 3
            base_delay = 1.0
            config_kwargs = {
                "response_mime_type": "application/json",
                "thinking_config": self._types.ThinkingConfig(thinking_level="MEDIUM"),
            }

            for attempt in range(1, max_retries + 1):
                try:
                    res = self._client.models.generate_content(
                        model=self.MODEL_NAME,
                        contents=prompt,
                        config=self._types.GenerateContentConfig(**config_kwargs),
                    )
                    if res and res.text:
                        response_text = res.text
                        metadata["gemini_status"] = "success"
                        metadata["provider"] = "gemini"
                        logger.info("[LLMauditor] Gemini analysis successful.")
                        break
                    else:
                        raise ValueError("Gemini returned empty response text.")
                except Exception as e:
                    metadata["error"] = str(e)
                    should_retry, skip_to_secondary = _should_retry_gemini(e)
                    logger.warning(f"[LLMauditor] Gemini attempt {attempt}/{max_retries} error: {type(e).__name__} - {e}")

                    if skip_to_secondary:
                        logger.info("[LLMauditor] Skipping Gemini retries and failing over to OpenRouter.")
                        break

                    if attempt == max_retries or not should_retry:
                        break

                    delay = (base_delay * (2 ** (attempt - 1))) + random.uniform(0.1, 0.3)
                    time.sleep(delay)

        # 2. Try OpenRouter Secondary Fallback if Gemini failed or unconfigured
        if not response_text and settings.openrouter_api_key:
            metadata["openrouter_status"] = "failed"
            logger.info("[LLMauditor] Attempting OpenRouter fallback...")
            try:
                response_text = self._call_openrouter(prompt)
                metadata["openrouter_status"] = "success"
                metadata["provider"] = "openrouter"
                metadata["error"] = None
                logger.info("[LLMauditor] OpenRouter analysis successful.")
            except Exception as e:
                metadata["error"] = str(e)
                logger.error(f"[LLMauditor] OpenRouter fallback error: {type(e).__name__} - {e}")

        if not response_text:
            return [], metadata

        try:
            raw = response_text.strip()
            # ... (parsing logic remains same)
            # Strip markdown fences if present
            if raw.startswith("```"):
                lines = raw.splitlines()
                start_idx = 1
                end_idx = len(lines)
                if lines[-1].strip() == "```":
                    end_idx = -1
                raw = "\n".join(lines[start_idx:end_idx])

            data = json.loads(raw)
            if not isinstance(data, list):
                data = data.get("findings", []) if isinstance(data, dict) else []

            findings: List[AuditFinding] = []
            for item in data:
                try:
                    f = AuditFinding(
                        id=str(uuid.uuid4()),
                        category=IssueCategory(item.get("category", "compliance")),
                        severity=Severity(item.get("severity", "medium")),
                        flagged_text=item.get("flagged_text", ""),
                        explanation=item.get("explanation", ""),
                        evidence_quote=item.get("evidence_quote"),
                        evidence_source=item.get("evidence_source"),
                        evidence_status=EvidenceStatus(item.get("evidence_status", "not_found")),
                        suggested_replacement=item.get("suggested_replacement"),
                        confidence_score=float(item.get("confidence_score", 0.5)),
                    )
                    if f.flagged_text.strip():
                        findings.append(f)
                except Exception as e:
                    logger.warning(f"[LLMauditor] Skipping malformed finding: {e}")
            return findings, metadata

        except json.JSONDecodeError as e:
            metadata["error"] = f"JSON parse error: {e}"
            logger.error(f"[LLMauditor] {metadata['error']}")
            return [], metadata
        except Exception as e:
            metadata["error"] = f"Processing error: {type(e).__name__} - {e}"
            logger.error(f"[LLMauditor] {metadata['error']}")
            return [], metadata
