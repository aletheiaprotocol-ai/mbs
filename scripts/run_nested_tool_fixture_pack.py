"""Build reviewable MBS evidence packs for hard nested tool-call fixtures.

This is a local fixture/software check, not provider benchmark evidence. It proves
MBS can adapt nested tool-call arguments and separate nested schema failures from
semantic mismatches with traceable reports and evidence packs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mbs.adapter import adapt_response_jsonl
from mbs.evidence import build_evidence_pack
from mbs.report import aggregate_results, markdown_report
from mbs.triage import triage_results, write_triage_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Build hard nested tool-call fixture evidence packs")
    parser.add_argument("--root", default=".", help="MBS repo root")
    parser.add_argument("--out-dir", default="results/nested_tool_fixture_pack", help="Artifact output directory")
    parser.add_argument("--json", action="store_true", help="Print manifest JSON only")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    example_dir = root / "examples" / "nested_tool_arguments"
    schema = example_dir / "schema.json"
    cases = example_dir / "cases.jsonl"
    good_responses = example_dir / "provider_tool_call_good.jsonl"
    bad_responses = example_dir / "provider_tool_call_bad.jsonl"
    gate_config = root / "benchmarks" / "fixture_smoke_gate.yaml"

    good_result = out_dir / "nested_tool_good.mbs.json"
    bad_result = out_dir / "nested_tool_bad.mbs.json"
    combined_report = out_dir / "combined_report.md"
    combined_triage = out_dir / "combined_triage.json"

    good_payload = adapt_response_jsonl(
        schema,
        good_responses,
        cases_path=cases,
        model="nested-tool-good-fixture",
        decoding_mode="tool_call",
    )
    bad_payload = adapt_response_jsonl(
        schema,
        bad_responses,
        cases_path=cases,
        model="nested-tool-bad-fixture",
        decoding_mode="tool_call",
    )
    _write_json(good_result, good_payload)
    _write_json(bad_result, bad_payload)

    good_pack = build_evidence_pack(
        [good_result],
        out_dir / "evidence_pack_good",
        classification="fixture",
        gate_config=gate_config,
        copy_results=True,
        title="MBS Nested Tool-Call Good Fixture Evidence Pack",
    )
    bad_pack = build_evidence_pack(
        [bad_result],
        out_dir / "evidence_pack_bad",
        classification="fixture",
        copy_results=True,
        title="MBS Nested Tool-Call Bad Fixture Evidence Pack",
    )

    report = aggregate_results([good_result, bad_result])
    combined_report.write_text(markdown_report(report, summary_only=True), encoding="utf-8")
    triage = triage_results([good_result, bad_result], max_failure_examples=20)
    write_triage_json(combined_triage, triage)

    manifest: dict[str, Any] = {
        "classification": "fixture_smoke_not_provider_benchmark",
        "purpose": "prove nested tool-call schema validation and semantic mismatch separation",
        "artifacts": {
            "good_result": str(good_result),
            "bad_result": str(bad_result),
            "good_evidence_pack": str(out_dir / "evidence_pack_good"),
            "bad_evidence_pack": str(out_dir / "evidence_pack_bad"),
            "combined_report": str(combined_report),
            "combined_triage": str(combined_triage),
        },
        "checks": {
            "good_schema_valid_rate": good_payload["summary"].get("schema_valid_rate"),
            "good_semantic_correct_rate": good_payload["summary"].get("semantic_correct_rate"),
            "bad_schema_valid_rate": bad_payload["summary"].get("schema_valid_rate"),
            "bad_semantic_correct_rate": bad_payload["summary"].get("semantic_correct_rate"),
            "good_gate_status": good_pack["checks"].get("gate_status"),
            "bad_triage_status": bad_pack["checks"].get("triage_status"),
            "combined_triage_status": triage.get("status"),
            "failure_examples": len(triage.get("failure_examples", [])),
            "nested_schema_error_present": _has_error(bad_payload, "customer.verified", "wrong_type")
            and _has_error(bad_payload, "actions[0].currency", "missing_required_key")
            and _has_error(bad_payload, "actions[0].amount", "wrong_type"),
            "strict_extra_key_error_present": _has_error(bad_payload, "customer.tier", "extra_key")
            and _has_error(bad_payload, "actions[0].memo", "extra_key")
            and _has_error(bad_payload, "debug", "extra_key"),
            "joined_enum_error_present": _has_error(bad_payload, "priority", "invalid_enum", hint="joined_enum_values"),
            "case_mismatch_error_present": _has_error(bad_payload, "priority", "invalid_enum", hint="case_mismatch"),
            "invalid_json_error_present": _has_error(bad_payload, "$", "invalid_json"),
            "semantic_mismatch_present": _has_error(bad_payload, "$", "semantic_mismatch"),
        },
        "next_evidence_gate": "run real provider or OSS outputs against examples/nested_tool_arguments and classify those outputs separately",
    }
    passed = (
        manifest["checks"]["good_schema_valid_rate"] == 1.0
        and manifest["checks"]["good_semantic_correct_rate"] == 1.0
        and manifest["checks"]["bad_schema_valid_rate"] < 0.8
        and manifest["checks"]["bad_semantic_correct_rate"] < 0.5
        and manifest["checks"]["good_gate_status"] == "PASS"
        and manifest["checks"]["bad_triage_status"] == "FAIL"
        and manifest["checks"]["nested_schema_error_present"]
        and manifest["checks"]["strict_extra_key_error_present"]
        and manifest["checks"]["joined_enum_error_present"]
        and manifest["checks"]["case_mismatch_error_present"]
        and manifest["checks"]["invalid_json_error_present"]
        and manifest["checks"]["semantic_mismatch_present"]
    )
    manifest["status"] = "PASS" if passed else "FAIL"
    _write_json(out_dir / "manifest.json", manifest)

    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print(f"Nested tool fixture pack: {manifest['status']}")
        print(f"Classification: {manifest['classification']}")
        print(f"Good pack: {manifest['artifacts']['good_evidence_pack']}")
        print(f"Bad pack: {manifest['artifacts']['bad_evidence_pack']}")
        print(f"Combined report: {combined_report}")
        print(f"Combined triage: {triage.get('status')} -> {combined_triage}")
        print(f"Manifest: {out_dir / 'manifest.json'}")
    return 0 if passed else 2


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _has_error(payload: dict[str, Any], field: str, error_type: str, *, hint: str | None = None) -> bool:
    for row in payload.get("rows", []):
        for error in row.get("errors", []):
            if error.get("field") == field and error.get("type") == error_type:
                if hint is not None and error.get("hint") != hint:
                    continue
                return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
