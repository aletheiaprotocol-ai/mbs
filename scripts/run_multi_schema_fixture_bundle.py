"""Build a local multi-schema MBS fixture benchmark evidence bundle.

This bundle is software/fixture breadth evidence only. It aggregates serious
workflow fixtures across schemas and verifies trace coverage, gate thresholds,
and cost-per-valid-output reporting without making provider benchmark claims.
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
from mbs.gate import evaluate_gate, load_gate_config
from mbs.report import aggregate_results


WORKFLOWS = [
    {
        "key": "incident_response_runbook",
        "model": "incident-fixture-json-mode",
        "schema": "examples/incident_response_runbook/schema.json",
        "cases": "examples/incident_response_runbook/cases.jsonl",
        "responses": "examples/incident_response_runbook/provider_good_responses.jsonl",
    },
    {
        "key": "fintech_transaction_risk",
        "model": "fintech-fixture-json-mode",
        "schema": "examples/fintech_transaction_risk/schema.json",
        "cases": "examples/fintech_transaction_risk/cases.jsonl",
        "responses": "examples/fintech_transaction_risk/provider_good_responses.jsonl",
    },
    {
        "key": "support_ticket_triage",
        "model": "support-fixture-json-mode",
        "schema": "examples/support_ticket_triage/schema.json",
        "cases": "examples/support_ticket_triage/cases.jsonl",
        "responses": "examples/support_ticket_triage/provider_good_responses.jsonl",
    },
    {
        "key": "nested_tool_arguments",
        "model": "nested-tool-fixture-tool-call",
        "schema": "examples/nested_tool_arguments/schema.json",
        "cases": "examples/nested_tool_arguments/cases.jsonl",
        "responses": "examples/nested_tool_arguments/provider_tool_call_good.jsonl",
        "decoding_mode": "tool_call",
    },
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build local multi-schema fixture evidence bundle")
    parser.add_argument("--root", default=".", help="MBS repo root")
    parser.add_argument("--out-dir", default="benchmarks/results/multi_schema_fixture_bundle")
    parser.add_argument("--gate-config", default="benchmarks/multi_schema_fixture_gate.yaml")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    result_dir = out_dir / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    result_files: list[Path] = []
    workflow_summaries: list[dict[str, Any]] = []

    for workflow in WORKFLOWS:
        payload = adapt_response_jsonl(
            root / workflow["schema"],
            root / workflow["responses"],
            cases_path=root / workflow["cases"],
            model=workflow["model"],
            decoding_mode=workflow.get("decoding_mode", "json_mode"),
        )
        result_path = result_dir / f"{workflow['key']}.mbs.json"
        _write_json(result_path, payload)
        result_files.append(result_path)
        workflow_summaries.append(
            {
                "key": workflow["key"],
                "schema": workflow["schema"],
                "model": workflow["model"],
                "runs": payload["summary"].get("runs"),
                "schema_valid_rate": payload["summary"].get("schema_valid_rate"),
                "semantic_correct_rate": payload["summary"].get("semantic_correct_rate"),
                "clean_json_rate": payload["summary"].get("clean_json_rate"),
                "cost_per_valid_output_tokens": payload["summary"].get("cost_per_valid_output_tokens"),
            }
        )

    gate_config = root / args.gate_config
    pack_manifest = build_evidence_pack(
        result_files,
        out_dir / "evidence_pack",
        classification="fixture",
        gate_config=gate_config,
        copy_results=True,
        title="MBS Multi-Schema Fixture Benchmark Bundle",
    )
    report = aggregate_results(result_files)
    gate = evaluate_gate(result_files, config=load_gate_config(gate_config))
    classification_boundary = {
        "classification": "fixture_smoke_not_provider_benchmark",
        "not_provider_benchmark": True,
        "not_broad_model_benchmark": True,
        "public_claim_boundary": "Local fixture/software benchmark breadth evidence across fixed example schemas only.",
    }

    checks = {
        "result_files": len(result_files),
        "report_rows": report["summary"].get("rows"),
        "schemas": sorted(report["summary"].get("schemas") or []),
        "models": sorted(report["summary"].get("models") or []),
        "total_runs": report["summary"].get("total_runs"),
        "traceable_case_rows": report["summary"].get("traceable_case_rows"),
        "missing_trace_rows": report["summary"].get("missing_trace_rows"),
        "mean_schema_valid_rate": report["summary"].get("mean_schema_valid_rate"),
        "mean_semantic_correct_rate": report["summary"].get("mean_semantic_correct_rate"),
        "mean_clean_json_rate": report["summary"].get("mean_clean_json_rate"),
        "gate_status": gate.get("status"),
        "evidence_pack_gate_status": pack_manifest["checks"].get("gate_status"),
        "cost_per_valid_output_present": all(
            item.get("cost_per_valid_output_tokens") is not None for item in workflow_summaries
        ),
    }
    passed = (
        checks["result_files"] == 4
        and checks["report_rows"] == 4
        and len(checks["schemas"]) == 4
        and len(checks["models"]) == 4
        and checks["total_runs"] == 49
        and checks["traceable_case_rows"] == 49
        and checks["missing_trace_rows"] == 0
        and checks["mean_schema_valid_rate"] == 1.0
        and checks["mean_semantic_correct_rate"] == 1.0
        and checks["mean_clean_json_rate"] == 1.0
        and checks["gate_status"] == "PASS"
        and checks["evidence_pack_gate_status"] == "PASS"
        and checks["cost_per_valid_output_present"] is True
    )

    manifest = {
        "status": "PASS" if passed else "FAIL",
        "classification": classification_boundary["classification"],
        "purpose": "local multi-schema fixture benchmark breadth evidence",
        "evidence_boundary": classification_boundary,
        "workflows": workflow_summaries,
        "artifacts": {
            "results_dir": str(result_dir),
            "evidence_pack": str(out_dir / "evidence_pack"),
            "manifest": str(out_dir / "manifest.json"),
        },
        "checks": checks,
        "remaining_boundary": "Real provider/OSS evidence, remote CI evidence, and governance review remain separate blockers.",
    }
    _write_json(out_dir / "manifest.json", manifest)
    (out_dir / "README.md").write_text(_readme(manifest), encoding="utf-8")

    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(f"MBS multi-schema fixture bundle: {manifest['status']}")
        print(f"Classification: {manifest['classification']}")
        print(f"Result files: {checks['result_files']}")
        print(f"Report rows: {checks['report_rows']}")
        print(f"Total runs: {checks['total_runs']}")
        print(f"Traceable case rows: {checks['traceable_case_rows']}")
        print(f"Gate status: {checks['gate_status']}")
        print(f"Manifest: {out_dir / 'manifest.json'}")
    return 0 if passed else 2


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _readme(manifest: dict[str, Any]) -> str:
    checks = manifest["checks"]
    lines = [
        "# MBS Multi-Schema Fixture Benchmark Bundle",
        "",
        f"Status: `{manifest['status']}`",
        f"Classification: `{manifest['classification']}`",
        "",
        "This is local fixture/software benchmark breadth evidence. It is not provider evidence and not broad model benchmark evidence.",
        "",
        "## Checks",
        "",
        f"- Result files: {checks['result_files']}",
        f"- Report rows: {checks['report_rows']}",
        f"- Schemas: {len(checks['schemas'])}",
        f"- Models: {len(checks['models'])}",
        f"- Total runs: {checks['total_runs']}",
        f"- Traceable case rows: {checks['traceable_case_rows']}",
        f"- Missing trace rows: {checks['missing_trace_rows']}",
        f"- Mean schema-valid rate: {checks['mean_schema_valid_rate']}",
        f"- Mean semantic-correct rate: {checks['mean_semantic_correct_rate']}",
        f"- Mean clean-JSON rate: {checks['mean_clean_json_rate']}",
        f"- Gate status: {checks['gate_status']}",
        "",
        "## Workflows",
        "",
    ]
    for workflow in manifest["workflows"]:
        lines.append(
            f"- `{workflow['key']}`: runs={workflow['runs']}, schema={workflow['schema_valid_rate']}, semantic={workflow['semantic_correct_rate']}, clean_json={workflow['clean_json_rate']}, cost_per_valid={workflow['cost_per_valid_output_tokens']}"
        )
    lines.extend(["", f"Remaining boundary: {manifest['remaining_boundary']}", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
