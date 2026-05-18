"""Build classified nested-tool provider/OSS/HPC evidence from response JSONL.

This script intentionally keeps provider collection separate from evidence
building. It never reads API keys and it never calls provider SDKs. For live
model runs, collect response JSONL with a separate secret-aware workflow, then
pass that file here with the correct classification.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mbs.adapter import adapt_response_jsonl, write_response_template
from mbs.evidence import CLASSIFICATIONS, build_evidence_pack
from mbs.gate import evaluate_gate, load_gate_config
from mbs.report import aggregate_results
from scripts.classify_release_artifacts import classify_paths


DEFAULT_SCHEMA = Path("examples/nested_tool_arguments/schema.json")
DEFAULT_CASES = Path("examples/nested_tool_arguments/cases.jsonl")
DEFAULT_GATE = Path("benchmarks/provider_gate.example.yaml")
DEFAULT_POLICY = Path("examples/nested_tool_arguments/policy.md")
ALLOWED_CLASSIFICATIONS = {"fixture", "provider", "oss", "hpc"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build classified MBS nested-tool provider/OSS/HPC evidence from response JSONL."
    )
    parser.add_argument("--root", default=str(REPO_ROOT), help="Repository root for relative paths.")
    parser.add_argument("--responses", help="Provider/OSS/HPC response JSONL collected outside this script.")
    parser.add_argument("--model", required=True, help="Model or deployment identifier to record in evidence.")
    parser.add_argument("--classification", choices=sorted(ALLOWED_CLASSIFICATIONS), required=True)
    parser.add_argument("--mode", default="tool_call", choices=["text", "json_mode", "tool_call"])
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--gate-config", default=str(DEFAULT_GATE))
    parser.add_argument("--out-dir", default="results/nested_provider_evidence")
    parser.add_argument("--endpoint", help="Optional non-secret endpoint URL recorded as run metadata only.")
    parser.add_argument("--provider", help="Optional provider family label recorded as run metadata only.")
    parser.add_argument(
        "--runner",
        default="openai-compatible",
        choices=["openai-compatible", "ollama", "lm-studio"],
        help="Collection runner family to describe in dry-run plans; no live calls are made by this script.",
    )
    parser.add_argument("--temperature", type=float, help="Optional run temperature recorded as metadata.")
    parser.add_argument("--seed", help="Optional seed recorded as metadata.")
    parser.add_argument("--dry-run", action="store_true", help="Write template/run plan only; do not claim evidence.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    schema = _resolve(root, args.schema)
    cases = _resolve(root, args.cases)
    gate_config = _resolve(root, args.gate_config)

    if args.dry_run:
        manifest = _write_dry_run(args, out_dir, schema, cases, gate_config)
        if args.json:
            legacy = dict(manifest)
            legacy["status"] = "DRY_RUN"
            print(json.dumps(legacy, indent=2, sort_keys=True))
        else:
            _emit(manifest, args.json)
        return 0

    if not args.responses:
        raise SystemExit("--responses is required unless --dry-run is set")
    responses = _resolve(root, args.responses)
    if not responses.exists():
        raise SystemExit(f"response JSONL not found: {responses}")

    classification = classify_paths([responses], repo_root=root)
    if classification["status"] == "FAIL":
        manifest = _failure_manifest(args, out_dir, schema, cases, gate_config, responses, classification)
        _write_json(out_dir / "manifest.json", manifest)
        _emit(manifest, args.json)
        return 2

    results_dir = out_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    result_path = results_dir / f"nested_tool_{args.classification}_{_safe_name(args.model)}.mbs.json"

    payload = adapt_response_jsonl(
        schema,
        responses,
        cases_path=cases,
        model=args.model,
        decoding_mode=args.mode,
    )
    _write_json(result_path, payload)

    report = aggregate_results([result_path])
    gate = evaluate_gate([result_path], config=load_gate_config(gate_config))
    pack_manifest = build_evidence_pack(
        [result_path],
        out_dir / "evidence_pack",
        classification=args.classification,
        gate_config=gate_config,
        copy_results=True,
        title=f"MBS Nested Tool {args.classification.upper()} Evidence",
    )

    checks = {
        "classification_key": args.classification,
        "classification_label": CLASSIFICATIONS[args.classification],
        "artifact_classification_status": classification["status"],
        "artifact_review_required_count": classification["review_required_count"],
        "blocking_findings_count": classification["blocking_findings_count"],
        "runs": payload["summary"].get("runs"),
        "report_rows": report["summary"].get("rows"),
        "total_runs": report["summary"].get("total_runs"),
        "traceable_case_rows": report["summary"].get("traceable_case_rows"),
        "missing_trace_rows": report["summary"].get("missing_trace_rows"),
        "schema_valid_rate": payload["summary"].get("schema_valid_rate"),
        "semantic_correct_rate": payload["summary"].get("semantic_correct_rate"),
        "clean_json_rate": payload["summary"].get("clean_json_rate"),
        "gate_status": gate.get("status"),
        "evidence_pack_gate_status": pack_manifest["checks"].get("gate_status"),
    }
    manifest = {
        "status": "PASS" if gate.get("status") == "PASS" else "FAIL",
        "purpose": "classified nested-tool provider/OSS/HPC behavior evidence",
        "classification": CLASSIFICATIONS[args.classification],
        "classification_key": args.classification,
        "evidence_boundary": (
            "Model-behavior evidence only for the listed schema, cases, model, decoding mode, "
            "run metadata, and response JSONL. Not a broad provider/model claim."
        ),
        "created_at_utc": _now(),
        "schema": _rel(root, schema),
        "cases": _rel(root, cases),
        "responses": _rel(root, responses),
        "model": args.model,
        "decoding_mode": args.mode,
        "run_metadata": _run_metadata(args),
        "artifacts": {
            "result": _rel(root, result_path),
            "evidence_pack": _rel(root, out_dir / "evidence_pack"),
            "manifest": _rel(root, out_dir / "manifest.json"),
        },
        "checks": checks,
        "gate_failures": gate.get("failures", []),
        "artifact_classification": classification,
        "remaining_boundary": "Repeat across more providers, OSS families, seeds, temperatures, and remote CI before broader readiness claims.",
    }
    _write_json(out_dir / "manifest.json", manifest)
    _write_json(out_dir / "run_plan.json", _run_plan(args, out_dir, schema, cases, gate_config))
    _write_compat_run_manifest(out_dir, manifest, gate)
    (out_dir / "README.md").write_text(_readme(manifest), encoding="utf-8")
    _emit(manifest, args.json)
    return 0 if manifest["status"] == "PASS" else 2


def _write_dry_run(args: argparse.Namespace, out_dir: Path, schema: Path, cases: Path, gate_config: Path) -> dict[str, Any]:
    output_field = "tool_call" if args.mode == "tool_call" else "output"
    template = out_dir / "response_template.jsonl"
    write_response_template(cases, template, output_field=output_field, model=args.model, decoding_mode=args.mode)
    run_plan = _run_plan(args, out_dir, schema, cases, gate_config)
    manifest = {
        "status": "NO_EVIDENCE_DRY_RUN",
        "legacy_status": "DRY_RUN",
        "purpose": "nested-tool evidence collection plan only",
        "classification_key": args.classification,
        "classification": CLASSIFICATIONS[args.classification],
        "evidence_boundary": "No model evidence was collected. Do not cite this as provider/OSS/HPC behavior evidence.",
        "created_at_utc": _now(),
        "schema": str(schema),
        "cases": str(cases),
        "gate_config": str(gate_config),
        "model": args.model,
        "decoding_mode": args.mode,
        "run_metadata": _run_metadata(args),
        "artifacts": {
            "response_template": str(template),
            "manifest": str(out_dir / "manifest.json"),
            "run_plan": str(out_dir / "run_plan.json"),
        },
        "commands": run_plan["commands"],
        "next_step": "Collect one real response row per case into the template without secrets, then rerun without --dry-run and with --responses.",
    }
    _write_json(out_dir / "manifest.json", manifest)
    _write_json(out_dir / "run_plan.json", run_plan)
    (out_dir / "README.md").write_text(_readme(manifest), encoding="utf-8")
    return manifest


def _run_plan(args: argparse.Namespace, out_dir: Path, schema: Path, cases: Path, gate_config: Path) -> dict[str, Any]:
    responses = out_dir / "responses.jsonl"
    policy = _resolve(Path(args.root).resolve(), DEFAULT_POLICY)
    collect_command = _collect_command(args, schema, cases, responses, policy)
    build_command = [
        "python",
        "scripts/build_nested_provider_evidence.py",
        "--responses",
        str(responses),
        "--model",
        args.model,
        "--classification",
        args.classification,
        "--mode",
        args.mode,
        "--gate-config",
        str(gate_config),
        "--out-dir",
        str(out_dir),
    ]
    return {
        "status": "DRY_RUN",
        "runner": args.runner,
        "classification": args.classification,
        "collected_responses": True,
        "schema": str(schema),
        "cases": str(cases),
        "gate_config": str(gate_config),
        "commands": [collect_command, build_command],
    }


def _collect_command(args: argparse.Namespace, schema: Path, cases: Path, responses: Path, policy: Path) -> list[str]:
    if args.runner == "ollama":
        command = [
            "python",
            "scripts/collect_ollama_responses.py",
            "--schema",
            str(schema),
            "--cases",
            str(cases),
            "--out",
            str(responses),
            "--model",
            args.model,
            "--mode",
            args.mode,
            "--policy",
            str(policy),
            "--endpoint",
            args.endpoint or "http://localhost:11434",
        ]
    elif args.runner == "lm-studio":
        command = [
            "python",
            "scripts/collect_azure_openai_responses.py",
            "--provider",
            "openai-compatible",
            "--schema",
            str(schema),
            "--cases",
            str(cases),
            "--out",
            str(responses),
            "--model",
            args.model,
            "--mode",
            args.mode,
            "--policy",
            str(policy),
            "--endpoint",
            args.endpoint or "http://localhost:1234",
            "--api-key-env",
            "LM_STUDIO_API_KEY",
        ]
    else:
        command = [
            "python",
            "scripts/collect_azure_openai_responses.py",
            "--provider",
            "openai-compatible",
            "--schema",
            str(schema),
            "--cases",
            str(cases),
            "--out",
            str(responses),
            "--model",
            args.model,
            "--mode",
            args.mode,
            "--policy",
            str(policy),
        ]
        if args.endpoint:
            command.extend(["--endpoint", args.endpoint])
    if args.provider:
        command.extend(["--provider", args.provider])
    if args.temperature is not None:
        command.extend(["--temperature", str(args.temperature)])
    if args.seed:
        command.extend(["--seed", args.seed])
    return command


def _failure_manifest(
    args: argparse.Namespace,
    out_dir: Path,
    schema: Path,
    cases: Path,
    gate_config: Path,
    responses: Path,
    classification: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "FAIL",
        "failure_reason": "blocking_secret_or_artifact_classification_failure",
        "classification_key": args.classification,
        "classification": CLASSIFICATIONS[args.classification],
        "created_at_utc": _now(),
        "schema": str(schema),
        "cases": str(cases),
        "gate_config": str(gate_config),
        "responses": str(responses),
        "model": args.model,
        "decoding_mode": args.mode,
        "run_metadata": _run_metadata(args),
        "artifact_classification": classification,
        "artifacts": {"manifest": str(out_dir / "manifest.json")},
    }


def _run_metadata(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "provider": args.provider,
        "endpoint": args.endpoint,
        "runner": args.runner,
        "temperature": args.temperature,
        "seed": args.seed,
    }


def _write_compat_run_manifest(out_dir: Path, manifest: dict[str, Any], gate: dict[str, Any]) -> None:
    compat = {
        "status": manifest["status"],
        "collected_responses": False,
        "classification": manifest.get("classification_key"),
        "classification_label": manifest.get("classification"),
        "gate_status": gate.get("status"),
        "command_failures": [] if manifest["status"] == "PASS" else [{"command": "mbs gate", "returncode": 2}],
        "artifacts": manifest.get("artifacts", {}),
    }
    _write_json(out_dir / "run_manifest.json", compat)
    pack_dir = out_dir / "evidence_pack"
    for name in ["gate.json", "triage.json"]:
        source = pack_dir / name
        if source.exists():
            target = out_dir / name
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def _readme(manifest: dict[str, Any]) -> str:
    lines = [
        "# MBS Nested Provider Evidence",
        "",
        f"Status: `{manifest['status']}`",
        f"Classification: `{manifest.get('classification')}`",
        "",
        str(manifest.get("evidence_boundary")),
        "",
        f"Model: `{manifest.get('model')}`",
        f"Decoding mode: `{manifest.get('decoding_mode')}`",
        "",
    ]
    checks = manifest.get("checks") or {}
    if checks:
        lines.extend(
            [
                "## Checks",
                "",
                f"- Runs: {checks.get('runs')}",
                f"- Traceable case rows: {checks.get('traceable_case_rows')}",
                f"- Missing trace rows: {checks.get('missing_trace_rows')}",
                f"- Schema-valid rate: {checks.get('schema_valid_rate')}",
                f"- Semantic-correct rate: {checks.get('semantic_correct_rate')}",
                f"- Clean-JSON rate: {checks.get('clean_json_rate')}",
                f"- Gate status: {checks.get('gate_status')}",
                "",
            ]
        )
    if manifest.get("next_step"):
        lines.extend(["## Next step", "", str(manifest["next_step"]), ""])
    if manifest.get("remaining_boundary"):
        lines.extend(["## Remaining boundary", "", str(manifest["remaining_boundary"]), ""])
    return "\n".join(lines)


def _resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_") or "model"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _emit(manifest: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return
    print(f"MBS nested provider evidence: {manifest['status']}")
    print(f"Classification: {manifest.get('classification')}")
    if manifest.get("artifacts", {}).get("manifest"):
        print(f"Manifest: {manifest['artifacts']['manifest']}")


if __name__ == "__main__":
    raise SystemExit(main())
