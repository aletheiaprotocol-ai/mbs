"""Collect or reuse multilingual provider responses and build MBS-Lang evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run MBS-Lang provider evidence collection/build")
    parser.add_argument("--root", default=".", help="MBS repo root")
    parser.add_argument("--responses", default=None, help="Existing response JSONL. If omitted, collect responses first.")
    parser.add_argument("--out-dir", default="results/mbs_lang_provider_evidence", help="Evidence output directory")
    parser.add_argument("--model", required=True, help="Provider/model/deployment id")
    parser.add_argument("--classification", choices=["fixture", "provider", "oss", "hpc"], default="provider")
    parser.add_argument("--mode", choices=["text", "json_mode", "tool_call"], default="json_mode")
    parser.add_argument("--provider", choices=["azure", "openai-compatible"], default="azure")
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--deployment", default=None)
    parser.add_argument("--api-key-env", default="AZURE_OPENAI_API_KEY")
    parser.add_argument("--api-version", default=None)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--seed", type=int, default=444)
    parser.add_argument("--gate-config", default=None)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    schema = root / "examples" / "multilingual_risk_review" / "schema.json"
    cases = root / "examples" / "multilingual_risk_review" / "cases.jsonl"
    responses = Path(args.responses) if args.responses else out_dir / "mbs_lang_provider.responses.jsonl"
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
        str(root / "scripts" / "build_lang_provider_evidence.py"),
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
            print("MBS-Lang provider evidence dry run")
            for command in commands:
                print("RUN", " ".join(command))
        return 0

    command_failures: list[dict[str, Any]] = []
    for command in commands:
        completed = subprocess.run(command, check=False, capture_output=args.json, text=True)
        if completed.returncode == 0:
            continue
        is_build_step = str(command[1]).endswith("build_lang_provider_evidence.py")
        failure = {"command": command, "returncode": completed.returncode}
        if not is_build_step:
            failure["stdout_tail"] = _tail(completed.stdout)
            failure["stderr_tail"] = _tail(completed.stderr)
        command_failures.append(failure)
        if not is_build_step or not (out_dir / "manifest.json").exists():
            if args.json:
                _write_json(out_dir / "run_error.json", failure)
            raise subprocess.CalledProcessError(completed.returncode, command, output=completed.stdout, stderr=completed.stderr)

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
        "languages": manifest.get("checks", {}).get("languages"),
        "trace_errors": manifest.get("checks", {}).get("trace_errors"),
        "command_failures": command_failures,
        "evidence_boundary": plan["evidence_boundary"],
    }
    _write_json(out_dir / "run_manifest.json", run_manifest)

    if args.json:
        print(json.dumps(run_manifest, indent=2))
    else:
        print(f"MBS-Lang provider evidence run: {run_manifest['status']}")
        print(f"Responses: {responses}")
        print(f"Evidence manifest: {manifest_path}")
    return 0 if run_manifest["status"] == "PASS" else 2


def _default_gate(root: Path, classification: str) -> Path:
    if classification == "fixture":
        return root / "benchmarks" / "fixture_smoke_gate.yaml"
    return root / "benchmarks" / "provider_lang_gate.example.yaml"


def _boundary(classification: str) -> str:
    if classification == "fixture":
        return "Fixture classification is a software/example MBS-Lang check, not provider benchmark evidence."
    return "MBS-Lang behavior evidence only for the listed schema, cases, languages, model, mode, gate, and run settings."


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _tail(text: str | None, limit: int = 2000) -> str:
    if not text:
        return ""
    return text[-limit:]


if __name__ == "__main__":
    raise SystemExit(main())