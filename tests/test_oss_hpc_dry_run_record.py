from __future__ import annotations

import json
from pathlib import Path

from scripts.assert_oss_hpc_dry_run_record import validate_record


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "docs" / "oss_hpc_endpoint_dry_run_20260514" / "endpoint_dry_run.json"


def test_oss_hpc_dry_run_record_preserves_no_evidence_boundary():
    payload = json.loads(RECORD.read_text(encoding="utf-8"))

    assert payload["status"] == "NO_EVIDENCE_DRY_RUN"
    assert payload["classification"] == "oss"
    assert payload["endpoint_probe"]["reachable_endpoints"] == []
    assert payload["evidence_boundary"]["raw_responses_collected"] is False
    assert payload["evidence_boundary"]["evidence_pack_created"] is False
    assert payload["evidence_boundary"]["aggregate_matrix_row_created"] is False
    assert "No OSS/HPC model-behavior evidence is claimed" in payload["evidence_boundary"]["claim"]


def test_oss_hpc_dry_run_record_matches_active_suite_size():
    result = validate_record(RECORD)

    assert result["status"] == "PASS"
    assert result["checked_urls"] >= 3


def test_oss_hpc_dry_run_record_keeps_real_run_requirements():
    payload = json.loads(RECORD.read_text(encoding="utf-8"))
    required_steps = "\n".join(payload["required_for_real_evidence"])
    non_claims = "\n".join(payload["non_claims"])

    assert payload["runner"] == "scripts/run_nested_provider_evidence.py"
    assert payload["schema"] == "examples/nested_tool_arguments/schema.json"
    assert payload["cases"] == "examples/nested_tool_arguments/cases.jsonl"
    assert payload["gate_config"] == "benchmarks/provider_gate.example.yaml"
    assert "without --dry-run" in required_steps
    assert "raw responses under ignored results/" in required_steps
    assert "not an OSS benchmark" in non_claims
    assert "not an HPC benchmark" in non_claims
