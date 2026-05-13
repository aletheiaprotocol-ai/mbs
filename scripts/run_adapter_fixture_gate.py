"""Run the reproducible MBS adapter fixture gate.

This is a smoke fixture for the JSON-mode/tool-calling adapter pipeline. It is
not provider benchmark evidence. The fixture intentionally contains one bad text
response and one clean tool-call response so report, compare, and triage all have
real work to do.
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
from mbs.compare import compare_results, write_compare_json
from mbs.report import aggregate_results, markdown_report, trace_errors
from mbs.triage import triage_results, write_triage_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the MBS adapter fixture gate")
    parser.add_argument("--root", default=".", help="MBS repo root")
    parser.add_argument("--out-dir", default="results/adapter_fixture_gate", help="Artifact output directory")
    parser.add_argument("--json", action="store_true", help="Print manifest JSON only")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    schema = root / "examples" / "tool_argument_generation" / "schema.json"
    cases = root / "examples" / "tool_argument_generation" / "cases.jsonl"
    text_responses = root / "examples" / "tool_argument_generation" / "provider_text_responses.jsonl"
    tool_responses = root / "examples" / "tool_argument_generation" / "provider_tool_call_responses.jsonl"

    text_result = out_dir / "text_fixture.mbs.json"
    tool_result = out_dir / "tool_call_fixture.mbs.json"
    report_path = out_dir / "report_summary.md"
    compare_path = out_dir / "compare_text_vs_tool_call.json"
    triage_path = out_dir / "triage.json"
    manifest_path = out_dir / "manifest.json"

    text_payload = adapt_response_jsonl(
        schema,
        text_responses,
        cases_path=cases,
        model="fixture-provider",
        decoding_mode="text",
    )
    tool_payload = adapt_response_jsonl(
        schema,
        tool_responses,
        cases_path=cases,
        model="fixture-provider",
        decoding_mode="tool_call",
    )
    _write_json(text_result, text_payload)
    _write_json(tool_result, tool_payload)

    report = aggregate_results([text_result, tool_result])
    report_errors = trace_errors(report)
    report_path.write_text(markdown_report(report, summary_only=True), encoding="utf-8")

    comparison = compare_results([text_result], [tool_result], key_fields=["schema", "model", "language"])
    write_compare_json(compare_path, comparison)

    triage = triage_results([text_result, tool_result], max_failure_examples=20)
    write_triage_json(triage_path, triage)

    manifest: dict[str, Any] = {
        "classification": "adapter_fixture_smoke_not_provider_benchmark",
        "purpose": "prove provider-response adaptation, traceable report, mode compare, and failure triage pipeline",
        "artifacts": {
            "text_result": str(text_result),
            "tool_call_result": str(tool_result),
            "report": str(report_path),
            "compare": str(compare_path),
            "triage": str(triage_path),
        },
        "checks": {
            "report_trace_errors": report_errors,
            "traceable_case_rows": report["summary"].get("traceable_case_rows"),
            "missing_trace_rows": report["summary"].get("missing_trace_rows"),
            "compare_status": comparison["status"],
            "triage_status": triage["status"],
            "expected_fixture_failures_present": bool(triage.get("failure_examples")),
        },
        "next_evidence_gate": "run real provider or OSS model responses across text, JSON mode, and tool calling; then adapt, report, compare, retry-audit where applicable, and triage",
    }
    _write_json(manifest_path, manifest)

    passed = (
        not report_errors
        and report["summary"].get("traceable_case_rows", 0) > 0
        and report["summary"].get("missing_trace_rows") == 0
        and comparison["status"] == "PASS"
        and bool(triage.get("failure_examples"))
    )
    manifest["status"] = "PASS" if passed else "FAIL"
    _write_json(manifest_path, manifest)

    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print(f"Adapter fixture gate: {manifest['status']}")
        print(f"Classification: {manifest['classification']}")
        print(f"Report: {report_path}")
        print(f"Compare: {comparison['status']} -> {compare_path}")
        print(f"Triage: {triage['status']} with expected fixture failures -> {triage_path}")
        print(f"Manifest: {manifest_path}")
    return 0 if passed else 2


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())