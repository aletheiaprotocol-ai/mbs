"""Collect or reuse hard nested provider responses and build MBS evidence.

This is the one-command path for the next evidence gate:

1. collect real provider/OSS/HPC responses against `examples/nested_tool_arguments/`,
   or reuse an existing response JSONL;
2. adapt those responses with MBS;
3. build a classified evidence pack;
4. write a manifest that keeps fixture/provider/OSS/HPC boundaries explicit.

No credentials are written to disk. Collection delegates to
`scripts/collect_azure_openai_responses.py`, which reads keys from environment
variables.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Run hard nested provider evidence collection/build")
    parser.add_argument("--root", default=".", help="MBS repo root")
    parser.add_argument("--responses", default=None, help="Existing response JSONL. If omitted, collect responses first.")
    parser.add_argument("--out-dir", default="results/nested_provider_evidence", help="Evidence output directory")
    parser.add_argument("--model", required=True, help="Provider/model/deployment id")
    parser.add_argument("--classification", choices=["fixture", "provider", "oss", "hpc"], default="provider")
    parser.add_argument("--mode", choices=["text", "json_mode", "tool_call"], default="tool_call")
    parser.add_argument("--provider", choices=["azure", "openai-compatible"], default="azure")
    parser.add_argument("--endpoint", default=None, help="Provider endpoint. Required when collecting unless env vars are used.")
    parser.add_argument("--deployment", default=None, help="Azure deployment name. Defaults to --model when collecting on Azure.")
    parser.add_argument("--api-key-env", default="AZURE_OPENAI_API_KEY")
    parser.add_argument("--api-version", default=None)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--seed", type=int, default=333)
    parser.add_argument("--gate-config", default=None, help="Gate YAML. Defaults based on classification.")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--dry-run", action="store_true", help="Write planned commands without calling provider or building evidence.")
    parser.add_argument("--json", action="store_true", help="Print final manifest JSON only")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    schema = root / "examples" / "nested_tool_arguments" / "schema.json"
    cases = root / "examples" / "nested_tool_arguments" / "cases.jsonl"
    responses = Path(args.responses) if args.responses else out_dir / "nested_provider.responses.jsonl"
    if not responses.is_absolute():
        responses = root / responses
    gate_config = Path(args.gate_config) if args.gate_config else _default_gate(root, args.classification)
    if not gate_config.is_absolute():
        gate_config = root / gate_config

    commands: list[list[str]] = []
    collected = False
    if args.responses is None:
        collect_cmd = [
            args.python,
            str(root / "scripts" / "collect_azure_openai_responses.py"),
            "--provider",
            args.provider,
            "--schema",
            str(schema),
            "--cases",
            str(cases),
            "--out",
            str(responses),
            "--mode",
            args.mode,
            "--model",
            args.model,
            "--api-key-env",
            args.api_key_env,
            "--max-tokens",
            str(args.max_tokens),
            "--timeout",
            str(args.timeout),
            "--seed",
            str(args.seed),
        ]
        if args.endpoint:
            collect_cmd.extend(["--endpoint", args.endpoint])
        if args.deployment:
            collect_cmd.extend(["--deployment", args.deployment])
        elif args.provider == "azure":
            collect_cmd.extend(["--deployment", args.model])
        if args.api_version:
            collect_cmd.extend(["--api-version", args.api_version])
        commands.append(collect_cmd)
        collected = True

    build_cmd = [
        args.python,
        str(root / "scripts" / "build_nested_provider_evidence.py"),
        "--root",
        str(root),
        "--responses",
        str(responses),
        "--out-dir",
        str(out_dir),
        "--model",
        args.model,
        "--decoding-mode",
        args.mode,
        "--classification",
        args.classification,
        "--gate-config",
        str(gate_config),
        "--json",
    ]
    commands.append(build_cmd)

    plan = {
        "schema": str(schema),
        "cases": str(cases),
        "responses": str(responses),
        "out_dir": str(out_dir),
        "model": args.model,
        "mode": args.mode,
        "classification": args.classification,
        "gate_config": str(gate_config),
        "collected_responses": collected,
        "commands": commands,
        "evidence_boundary": _boundary(args.classification),
    }
    _write_json(out_dir / "run_plan.json", plan)

    if args.dry_run:
        if args.json:
            print(json.dumps({"status": "DRY_RUN", **plan}, indent=2))
        else:
            print("Nested provider evidence dry run")
            for command in commands:
                print("RUN", " ".join(command))
        return 0

    for command in commands:
        subprocess.run(command, check=True, capture_output=args.json, text=True)

    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    run_manifest = {
        "status": manifest.get("status", "FAIL"),
        "run_plan": "run_plan.json",
        "evidence_manifest": "manifest.json",
        "responses": str(responses),
        "collected_responses": collected,
        "classification": args.classification,
        "classification_label": manifest.get("classification_label"),
        "gate_status": manifest.get("checks", {}).get("gate_status"),
        "trace_errors": manifest.get("checks", {}).get("trace_errors"),
        "evidence_boundary": plan["evidence_boundary"],
    }
    _write_json(out_dir / "run_manifest.json", run_manifest)

    if args.json:
        print(json.dumps(run_manifest, indent=2))
    else:
        print(f"Nested provider evidence run: {run_manifest['status']}")
        print(f"Responses: {responses}")
        print(f"Evidence manifest: {manifest_path}")
        print(f"Run manifest: {out_dir / 'run_manifest.json'}")
    return 0 if run_manifest["status"] == "PASS" else 2


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
