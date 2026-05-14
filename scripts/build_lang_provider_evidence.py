"""Build classified MBS-Lang provider/OSS/HPC evidence packs.

Use provider/OSS/HPC classifications only for real multilingual model outputs.
Fixture responses can use `--classification fixture` to test the evidence path.
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
    "fixture": "fixture_mbs_lang_not_provider_benchmark",
    "provider": "real_provider_mbs_lang_behavior_evidence",
    "oss": "open_source_mbs_lang_behavior_evidence",
    "hpc": "hpc_mbs_lang_behavior_evidence",
}
PACK_CLASSIFICATION_NOTE = {
    "fixture": "fixture_smoke_not_provider_benchmark",
    "provider": "real_provider_behavior_evidence",
    "oss": "open_source_model_behavior_evidence",
    "hpc": "hpc_model_behavior_evidence",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build MBS-Lang provider/OSS/HPC evidence packs")
    parser.add_argument("--root", default=".", help="MBS repo root")
    parser.add_argument("--responses", required=True, help="Provider/OSS/HPC response JSONL")
    parser.add_argument("--out-dir", default="results/mbs_lang_provider_evidence", help="Artifact output directory")
    parser.add_argument("--model", required=True, help="Model/deployment identifier to record in adapted rows")
    parser.add_argument("--decoding-mode", default="json_mode", help="Recorded decoding mode")
    parser.add_argument("--classification", choices=sorted(CLASSIFICATION_NOTE), default="provider")
    parser.add_argument("--gate-config", default=None, help="Gate YAML. Defaults by classification.")
    parser.add_argument("--prompt-style", default="full")
    parser.add_argument("--contract-language", default="en")
    parser.add_argument("--copy-results", action="store_true", default=True)
    parser.add_argument("--json", action="store_true", help="Print manifest JSON only")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    example_dir = root / "examples" / "multilingual_risk_review"
    schema = example_dir / "schema.json"
    cases = example_dir / "cases.jsonl"
    responses = Path(args.responses)
    if not responses.is_absolute():
        responses = root / responses
    gate_config = Path(args.gate_config) if args.gate_config else _default_gate(root, args.classification)
    if not gate_config.is_absolute():
        gate_config = root / gate_config

    adapted_result = out_dir / "mbs_lang_provider.mbs.json"
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
        contract_language=args.contract_language,
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
        title=f"MBS-Lang {args.classification.upper()} Evidence Pack",
    )

    languages = sorted({str(row.get("input_language")) for row in payload["rows"] if row.get("input_language")})
    checks = {
        "classification_label": CLASSIFICATION_NOTE[args.classification],
        "rows": payload["summary"].get("runs", 0),
        "languages": languages,
        "schema_valid_rate": payload["summary"].get("schema_valid_rate"),
        "semantic_correct_rate": payload["summary"].get("semantic_correct_rate"),
        "clean_json_rate": payload["summary"].get("clean_json_rate"),
        "trace_errors": trace_errors(report),
        "gate_status": gate.get("status"),
        "triage_status": triage.get("status"),
        "evidence_pack_classification": pack.get("classification"),
        "expected_evidence_pack_classification": PACK_CLASSIFICATION_NOTE[args.classification],
        "raw_results_copied": bool(pack.get("copied_results")),
        "input_language_rows_present": all(row.get("input_language") for row in payload["rows"]),
        "contract_language_en": all(row.get("contract_language") == args.contract_language for row in payload["rows"]),
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
        "next_evidence_gate": "repeat across more languages, schemas, providers, OSS/HPC models, and seeds before broad multilingual reliability claims",
    }
    required_ok = (
        checks["rows"] > 0
        and not checks["trace_errors"]
        and checks["evidence_pack_classification"] == PACK_CLASSIFICATION_NOTE[args.classification]
        and checks["input_language_rows_present"] is True
        and checks["contract_language_en"] is True
    )
    if args.classification == "fixture":
        required_ok = required_ok and checks["gate_status"] in {"PASS", "FAIL"}
    else:
        required_ok = required_ok and checks["gate_status"] == "PASS"
    manifest["status"] = "PASS" if required_ok else "FAIL"
    _write_json(out_dir / "manifest.json", manifest)

    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print(f"MBS-Lang {args.classification} evidence: {manifest['status']}")
        print(f"Classification: {manifest['classification_label']}")
        print(f"Gate: {checks['gate_status']} -> {gate_path}")
        print(f"Evidence pack: {pack_dir}")
    return 0 if required_ok else 2


def _default_gate(root: Path, classification: str) -> Path:
    if classification == "fixture":
        return root / "benchmarks" / "fixture_smoke_gate.yaml"
    return root / "benchmarks" / "provider_lang_gate.example.yaml"


def _boundary(classification: str) -> str:
    if classification == "fixture":
        return "Fixture classification is a software/example MBS-Lang check, not provider benchmark evidence."
    return "MBS-Lang model-behavior evidence only for the listed schema, cases, languages, model, mode, gate, and run settings."


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())