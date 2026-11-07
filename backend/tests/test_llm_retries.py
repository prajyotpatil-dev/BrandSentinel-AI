"""
Test LLMauditor retry logic and fallback behavior on transient errors (503, 429).
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.llm_auditor import LLMauditor
from app.schemas import GuidelineItem


def test_llm_auditor_fallback_on_unavailable():
    """Test that LLMauditor returns fallback metadata when client is unavailable."""
    auditor = LLMauditor()
    auditor._available = False
    findings, meta = auditor.analyze("test content", [])
    assert findings == []
    assert meta["provider"] is None


@patch("time.sleep", return_value=None)  # Speed up tests by mocking sleep
@patch("urllib.request.urlopen", side_effect=Exception("OpenRouter unreachable"))
def test_llm_auditor_retry_on_503(mock_urlopen, mock_sleep):
    """Test that LLMauditor retries on 503 error and eventually returns fallback metadata if all fail."""
    auditor = LLMauditor()
    auditor._available = True
    auditor._client = MagicMock()

    # Simulate 503 Service Unavailable error on generate_content
    auditor._client.models.generate_content.side_effect = Exception("503 Service Unavailable: High demand")

    guideline = GuidelineItem(
        title="Test Rule",
        category="terminology",
        rule_text="Do not use bad words",
        source_document="Test Doc"
    )

    findings, meta = auditor.analyze("test content", [guideline])

    # Should have retried 3 times then fallen back
    assert findings == []
    assert meta["provider"] is None
    assert meta["gemini_status"] == "failed"
    assert auditor._client.models.generate_content.call_count == 3
