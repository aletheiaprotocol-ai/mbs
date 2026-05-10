#!/usr/bin/env python3
"""
Unit tests for the MBS Schema Compiler.

Tests:
  1. Enum classification (FREE/PARTIAL/PAID)
  2. Prompt compilation (natural, progressive, full, strict)
  3. Token savings validation
  4. Edge cases (empty schema, no enums, all FREE)
  5. Report generation
  6. Held-out schema validation (new 6 schemas not used in design)
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mbs_compiler import classify_enum, compile_schema, extract_fields, format_report


TEST_SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_schemas")


class TestEnumClassification(unittest.TestCase):
    """Test FREE/PARTIAL/PAID enum taxonomy."""

    def test_sentiment_is_free(self):
        result = classify_enum("sentiment", ["POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED"])
        self.assertEqual(result, "FREE")

    def test_sentiment_lowercase_is_free(self):
        result = classify_enum("sentiment", ["positive", "negative", "neutral", "mixed"])
        self.assertEqual(result, "FREE")

    def test_boolean_is_free(self):
        result = classify_enum("approved", ["TRUE", "FALSE"])
        self.assertEqual(result, "FREE")

    def test_yes_no_is_free(self):
        result = classify_enum("confirmed", ["YES", "NO"])
        self.assertEqual(result, "FREE")

    def test_high_medium_low_is_free(self):
        result = classify_enum("severity", ["HIGH", "MEDIUM", "LOW"])
        self.assertEqual(result, "FREE")

    def test_custom_enum_is_paid(self):
        result = classify_enum("action", ["ANSWER", "TOOL_CALL", "CLARIFY", "REFUSE"])
        self.assertEqual(result, "PAID")

    def test_route_enum_is_paid(self):
        result = classify_enum("route", ["HUMAN", "AUTO", "HYBRID", "DEFER"])
        self.assertEqual(result, "PAID")

    def test_verdict_is_paid(self):
        result = classify_enum("verdict", ["NOVEL", "INCREMENTAL", "REPLICATION", "FLAWED"])
        self.assertEqual(result, "PAID")

    def test_priority_is_partial(self):
        # Field name "priority" is domain-suggestive
        result = classify_enum("priority", ["P0", "P1", "P2", "P3"])
        self.assertEqual(result, "PARTIAL")

    def test_severity_with_custom_values_is_partial(self):
        result = classify_enum("severity", ["CRITICAL", "MAJOR", "MINOR", "TRIVIAL"])
        self.assertEqual(result, "PARTIAL")


class TestFieldExtraction(unittest.TestCase):
    """Test JSON schema field extraction."""

    def test_basic_extraction(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name"],
        }
        fields = extract_fields(schema)
        self.assertEqual(len(fields), 2)
        self.assertTrue(fields[0]["required"])
        self.assertFalse(fields[1]["required"])

    def test_enum_extraction(self):
        schema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["ANSWER", "TOOL_CALL"],
                },
            },
        }
        fields = extract_fields(schema)
        self.assertEqual(fields[0]["enum"], ["ANSWER", "TOOL_CALL"])
        self.assertEqual(fields[0]["enum_class"], "PAID")

    def test_empty_schema(self):
        fields = extract_fields({"type": "object"})
        self.assertEqual(len(fields), 0)


class TestCompileSchema(unittest.TestCase):
    """Test prompt compilation for various formats."""

    ALETHEIA_SCHEMA = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["ANSWER", "TOOL_CALL", "CLARIFY", "REFUSE"],
                "description": "The type of response",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score 0-1",
            },
            "reasoning": {
                "type": "string",
                "description": "The reasoning chain",
            },
            "answer": {
                "type": "string",
                "description": "The final answer",
            },
        },
        "required": ["action", "confidence", "reasoning", "answer"],
    }

    def test_natural_format_includes_paid_enum(self):
        result = compile_schema(self.ALETHEIA_SCHEMA, format="natural")
        self.assertIn("ANSWER|TOOL_CALL|CLARIFY|REFUSE", result["prompt"])

    def test_natural_format_excludes_free_enum(self):
        schema = {
            "type": "object",
            "properties": {
                "sentiment": {
                    "type": "string",
                    "enum": ["POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED"],
                },
            },
        }
        result = compile_schema(schema, format="natural")
        # FREE enum should be omitted by default
        self.assertNotIn("POSITIVE", result["prompt"])

    def test_include_free_flag(self):
        schema = {
            "type": "object",
            "properties": {
                "sentiment": {
                    "type": "string",
                    "enum": ["POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED"],
                },
            },
        }
        result = compile_schema(schema, format="natural", include_free_enums=True)
        self.assertIn("POSITIVE", result["prompt"])

    def test_progressive_format(self):
        result = compile_schema(self.ALETHEIA_SCHEMA, format="progressive")
        self.assertIn("ANSWER|TOOL_CALL|CLARIFY|REFUSE", result["prompt"])
        self.assertIn("{", result["prompt"])

    def test_full_format(self):
        result = compile_schema(self.ALETHEIA_SCHEMA, format="full")
        self.assertIn("ANSWER", result["prompt"])
        self.assertIn("valid JSON object", result["prompt"])

    def test_strict_format_forbids_prose_outside_json(self):
        result = compile_schema(self.ALETHEIA_SCHEMA, format="strict")
        self.assertIn("Return one raw JSON object", result["prompt"])
        self.assertIn("chain-of-thought", result["prompt"])
        self.assertIn("ANSWER|TOOL_CALL|CLARIFY|REFUSE", result["prompt"])

    def test_savings_positive(self):
        result = compile_schema(self.ALETHEIA_SCHEMA)
        self.assertGreater(result["savings_pct"], 50)

    def test_full_prompt_is_verbose(self):
        result = compile_schema(self.ALETHEIA_SCHEMA)
        self.assertGreater(result["full_token_estimate"], result["token_estimate"])

    def test_task_context(self):
        result = compile_schema(self.ALETHEIA_SCHEMA, task_context="You are a helpful assistant.")
        self.assertIn("helpful assistant", result["prompt"])

    def test_field_analysis_complete(self):
        result = compile_schema(self.ALETHEIA_SCHEMA)
        self.assertEqual(len(result["field_analysis"]), 4)
        self.assertEqual(len(result["paid_enums"]), 1)

    def test_invalid_format_raises(self):
        with self.assertRaises(ValueError):
            compile_schema(self.ALETHEIA_SCHEMA, format="invalid")


class TestTokenSavings(unittest.TestCase):
    """Validate token savings meet the claimed 86-89% range."""

    def _load_schema(self, name):
        path = os.path.join(TEST_SCHEMAS_DIR, f"{name}.json")
        if not os.path.exists(path):
            self.skipTest(f"Schema file not found: {path}")
        with open(path) as f:
            return json.load(f)

    def test_aletheia_savings(self):
        result = compile_schema(self._load_schema("aletheia"))
        self.assertGreaterEqual(result["savings_pct"], 80)

    def test_sentiment_savings(self):
        result = compile_schema(self._load_schema("sentiment"))
        self.assertGreaterEqual(result["savings_pct"], 80)

    def test_trading_savings(self):
        result = compile_schema(self._load_schema("trading"))
        self.assertGreaterEqual(result["savings_pct"], 80)

    def test_triage_savings(self):
        result = compile_schema(self._load_schema("triage"))
        self.assertGreaterEqual(result["savings_pct"], 80)

    # Held-out schemas (not used in compiler design)
    def test_medical_savings(self):
        result = compile_schema(self._load_schema("medical"))
        self.assertGreaterEqual(result["savings_pct"], 80)

    def test_code_review_savings(self):
        result = compile_schema(self._load_schema("code_review"))
        self.assertGreaterEqual(result["savings_pct"], 80)

    def test_moderation_savings(self):
        result = compile_schema(self._load_schema("moderation"))
        self.assertGreaterEqual(result["savings_pct"], 80)

    def test_research_savings(self):
        result = compile_schema(self._load_schema("research"))
        self.assertGreaterEqual(result["savings_pct"], 80)

    def test_risk_savings(self):
        result = compile_schema(self._load_schema("risk"))
        self.assertGreaterEqual(result["savings_pct"], 80)

    def test_routing_savings(self):
        result = compile_schema(self._load_schema("routing"))
        self.assertGreaterEqual(result["savings_pct"], 80)


class TestReport(unittest.TestCase):
    """Test report generation."""

    def test_report_contains_sections(self):
        schema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["ANSWER", "REFUSE"],
                },
            },
        }
        result = compile_schema(schema)
        report = format_report(result)
        self.assertIn("FIELD ANALYSIS", report)
        self.assertIn("COMPILED PROMPT", report)
        self.assertIn("PAID", report)
        self.assertIn("savings", report.lower())


class TestEdgeCases(unittest.TestCase):
    """Test edge cases."""

    def test_empty_schema(self):
        result = compile_schema({"type": "object"})
        self.assertIsInstance(result["prompt"], str)

    def test_no_enums(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"},
            },
        }
        result = compile_schema(schema)
        self.assertEqual(len(result["paid_enums"]), 0)
        self.assertEqual(len(result["free_enums"]), 0)

    def test_all_free_schema(self):
        schema = {
            "type": "object",
            "properties": {
                "sentiment": {
                    "type": "string",
                    "enum": ["POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED"],
                },
                "confirmed": {
                    "type": "string",
                    "enum": ["YES", "NO"],
                },
            },
        }
        result = compile_schema(schema)
        self.assertEqual(len(result["free_enums"]), 2)
        self.assertEqual(len(result["paid_enums"]), 0)
        # Should NOT include enum values in prompt
        self.assertNotIn("POSITIVE", result["prompt"])

    def test_mixed_taxonomy(self):
        schema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["ANSWER", "TOOL_CALL"],
                },
                "sentiment": {
                    "type": "string",
                    "enum": ["POSITIVE", "NEGATIVE", "NEUTRAL"],
                },
            },
        }
        result = compile_schema(schema)
        self.assertEqual(len(result["paid_enums"]), 1)
        self.assertEqual(len(result["free_enums"]), 1)
        # Only PAID enum should appear in prompt
        self.assertIn("ANSWER", result["prompt"])
        self.assertNotIn("POSITIVE", result["prompt"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
