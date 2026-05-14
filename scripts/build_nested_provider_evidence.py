"""Build classified MBS evidence packs for hard nested provider/OSS outputs.

This script adapts JSONL responses collected from a real provider, local OSS
model, or HPC run against `examples/nested_tool_arguments/`. Use
`--classification provider`, `--classification oss`, or `--classification hpc`
only for real model outputs. Local examples can use `--classification fixture`.
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
from mbs.gate import evaluate_gate, load_gate_config, write_gate_json
from mbs.report import aggregate_results, markdown_report, trace_errors
from mbs.triage import triage_results, write_triage_json


CLASSIFICATION_NOTE = {
    "fixture": "fixture_smoke_not_provider_benchmark",
    "provider": "real_provider_behavior_evidence",
    "oss": "open_source_model_behavior_evidence",
    "hpc": "hpc_model_behavior_evidence",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build hard nested provider/OSS/HPC evidence packs")
    parser.add_argument("--root", default=".", help="MBS repo root")
    parser.add_argument("--responses", required=True, help="Provider/OSS/HPC response JSONL")
    parser.add_argument("--out-dir", default="results/nested_provider_evidence", help="Artifact output directory")
    parser.add_argument("--model", required=True, help="Model/deployment identifier to record in adapted rows")
    parser.add_argument("--decoding-mode", default="tool_call", help="Recorded decoding mode, e.g. tool_call or json_mode")
    parser.add_argument("--classification", choices=sorted(CLASSIFICATION_NOTE), default="provider")
    parser.add_argument("--gate-config", default=None, help="Gate YAML. Defaults to provider gate for real evidence, fixture gate for fixture evidence.")
    parser.add_argument("--prompt-style", default="full")
    parser.add_argument("--copy-results", action="store_true", default=True)
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
    responses = Path(args.responses)
    if not responses.is_absolute():
        responses = root / responses
    gate_config = Path(args.gate_config) if args.gate_config else _default_gate(root, args.classification)
    if not gate_config.is_absolute():
        gate_config = root / gate_config

    adapted_result = out_dir / "nested_provider.mbs.json"
    report_path = out_dir / "report.md"
    gate_path = out_dir / "gate.json"
    triage_path = out_dir / "triage.json"
    pack_dir = out_dir / "evidence_pack"

    payload = adapt_response_jsonl(
        schema,
        responses,
        cases_path=cases,
        model=args.model,
        prompt_style=args.prompt_style,
        decoding_mode=args.decoding_mode,
    )
    _write_json(adapted_result, payload)

    report = aggregate_results([adapted_result])
    report_path.write_text(markdown_report(report, summary_only=True), encoding="utf-8")
    gate = evaluate_gate([adapted_result], config=load_gate_config(gate_config))
    write_gate_json(gate_path, gate)
    triage = triage_results([adapted_result], max_failure_examples=20)
    write_triage_json(triage_path, triage)

    pack = build_evidence_pack(
        [adapted_result],
        pack_dir,
        classification=args.classification,
        gate_config=gate_config,
        copy_results=args.copy_results,
        title=f"MBS Hard Nested {args.classification.upper()} Evidence Pack",
    )

    checks = {
        "classification_label": CLASSIFICATION_NOTE[args.classification],
        "rows": payload["summary"].get("runs", 0),
        "schema_valid_rate": payload["summary"].get("schema_valid_rate"),
        "semantic_correct_rate": payload["summary"].get("semantic_correct_rate"),
        "clean_json_rate": payload["summary"].get("clean_json_rate"),
        "trace_errors": trace_errors(report),
        "gate_status": gate.get("status"),
        "triage_status": triage.get("status"),
        "evidence_pack_classification": pack.get("classification"),
        "raw_results_copied": bool(pack.get("copied_results")),
        "failure_examples": len(triage.get("failure_examples", [])),
    }
    manifest: dict[str, Any] = {
        "classification": args.classification,
        "classification_label": CLASSIFICATION_NOTE[args.classification],
        "evidence_boundary": _boundary(args.classification),
        "schema": str(schema),
        "cases": str(cases),
        "responses": str(responses),
        "model": args.model,
        "decoding_mode": args.decoding_mode,
        "gate_config": str(gate_config),
        "artifacts": {
            "adapted_result": str(adapted_result),
            "report": str(report_path),
            "gate": str(gate_path),
            "triage": str(triage_path),
            "evidence_pack": str(pack_dir),
        },
        "checks": checks,
        "next_evidence_gate": "repeat across more schemas, cases, models, and seeds before making broad reliability claims",
    }
    required_ok = checks["rows"] > 0 and not checks["trace_errors"] and checks["evidence_pack_classification"] == CLASSIFICATION_NOTE[args.classification]
    if args.classification == "fixture":
        required_ok = required_ok and checks["gate_status"] in {"PASS", "FAIL"}
    else:
        required_ok = required_ok and checks["gate_status"] == "PASS"
    manifest["status"] = "PASS" if required_ok else "FAIL"
    _write_json(out_dir / "manifest.json", manifest)

    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print(f"Nested {args.classification} evidence: {manifest['status']}")
        print(f"Classification: {manifest['classification_label']}")
        print(f"Gate: {checks['gate_status']} -> {gate_path}")
        print(f"Triage: {checks['triage_status']} -> {triage_path}")
        print(f"Evidence pack: {pack_dir}")
        print(f"Manifest: {out_dir / 'manifest.json'}")
    return 0 if required_ok else 2


def _default_gate(root: Path, classification: str) -> Path:
    if classification == "fixture":
        return root / "benchmarks" / "fixture_smoke_gate.yaml"
    return root / "benchmarks" / "provider_gate.example.yaml"


def _boundary(classification: str) -> str:
    if classification == "fixture":
        return "Fixture classification is a software/example check, not provider benchmark evidence."
    return "Model-behavior evidence only for the listed nested schema, cases, model, mode, gate, and run settings."


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
