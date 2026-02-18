"""
Unit tests for language handling in LLMService.

Tests _apply_language_instruction and SUPPORTED_LANGUAGES integration.
Run: pytest tests/unit/test_llm_service_language.py -v
"""

import sys
from pathlib import Path

# Add project root to Python path (for direct invocation)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from utils.llm_service import _apply_language_instruction
from utils.language_config import SUPPORTED_LANGUAGES


# ---------------------------------------------------------------------------
# _apply_language_instruction
# ---------------------------------------------------------------------------

class TestApplyLanguageInstruction:
    """Tests for the _apply_language_instruction helper."""

    def test_langcode_id_appends_indonesian(self):
        result = _apply_language_instruction("You are a bot.", "id")
        assert "Indonesian" in result
        assert "MUST respond entirely in Indonesian" in result

    def test_langcode_es_appends_spanish(self):
        result = _apply_language_instruction("You are a bot.", "es")
        assert "Spanish" in result

    def test_langcode_fr_appends_french(self):
        result = _apply_language_instruction("You are a bot.", "fr")
        assert "French" in result

    def test_langcode_en_returns_original(self):
        original = "You are a bot."
        result = _apply_language_instruction(original, "en")
        assert result == original

    def test_langcode_EN_uppercase_returns_original(self):
        original = "You are a bot."
        result = _apply_language_instruction(original, "EN")
        assert result == original

    def test_langcode_none_returns_original(self):
        original = "You are a bot."
        result = _apply_language_instruction(original, None)
        assert result == original

    def test_langcode_empty_string_returns_original(self):
        original = "You are a bot."
        result = _apply_language_instruction(original, "")
        assert result == original

    def test_system_prompt_none_with_langcode(self):
        result = _apply_language_instruction(None, "id")
        assert result is not None
        assert "Indonesian" in result

    def test_system_prompt_none_without_langcode(self):
        result = _apply_language_instruction(None, None)
        assert result is None

    def test_case_insensitive_langcode(self):
        result = _apply_language_instruction("Prompt.", "ID")
        assert "Indonesian" in result

    def test_unknown_langcode_uses_code_as_name(self):
        result = _apply_language_instruction("Prompt.", "xx")
        assert "xx" in result
        assert "MUST respond entirely in xx" in result

    def test_original_prompt_preserved(self):
        original = "You are a friendly interviewer."
        result = _apply_language_instruction(original, "ja")
        assert result.startswith(original)
        assert "Japanese" in result


# ---------------------------------------------------------------------------
# SUPPORTED_LANGUAGES mapping
# ---------------------------------------------------------------------------

class TestSupportedLanguages:
    """Tests for the centralized SUPPORTED_LANGUAGES dict."""

    def test_en_present(self):
        assert "en" in SUPPORTED_LANGUAGES
        assert SUPPORTED_LANGUAGES["en"] == "English"

    def test_id_maps_to_indonesian(self):
        assert SUPPORTED_LANGUAGES["id"] == "Indonesian"

    def test_all_keys_are_lowercase_two_char(self):
        for code in SUPPORTED_LANGUAGES:
            assert code == code.lower(), f"Key '{code}' is not lowercase"
            assert len(code) == 2, f"Key '{code}' is not 2 characters"

    def test_all_values_are_nonempty_strings(self):
        for code, name in SUPPORTED_LANGUAGES.items():
            assert isinstance(name, str) and len(name) > 0, f"Empty name for '{code}'"

    def test_expected_count(self):
        assert len(SUPPORTED_LANGUAGES) == 19


# ---------------------------------------------------------------------------
# All supported langcodes produce correct language name
# ---------------------------------------------------------------------------

class TestAllLanguagesIntegration:
    """Ensure every supported langcode flows through correctly."""

    @pytest.mark.parametrize("code,expected_name", list(SUPPORTED_LANGUAGES.items()))
    def test_langcode_resolves_to_language_name(self, code, expected_name):
        if code == "en":
            # English should return original prompt unchanged
            result = _apply_language_instruction("Prompt.", code)
            assert result == "Prompt."
        else:
            result = _apply_language_instruction("Prompt.", code)
            assert expected_name in result, (
                f"Expected '{expected_name}' for code '{code}', got: {result}"
            )
