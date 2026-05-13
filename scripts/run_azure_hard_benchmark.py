"""Run the hard agent-routing benchmark against Azure OpenAI deployments.

Credentials and endpoints are read from environment variables. This script does
not print keys. It writes provider JSONL files and adapted MBS JSON files.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_MODELS = ["gpt-5.5", "gpt-5-nano"]
DEFAULT_MODES = ["text", "json_mode", "tool_call"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run expanded MBS Azure hard benchmark")
    parser.add_argument("--schema", default="examples/hard_agent_routing/schema.json")
    parser.add_argument("--cases", default="examples/hard_agent_routing/cases.jsonl")
    parser.add_argument("--out-dir", default="results/hard_agent_routing/expanded")
    parser.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    parser.add_argument("--modes", nargs="*", default=DEFAULT_MODES)
    parser.add_argument("--endpoint", default=None, help="Azure endpoint; defaults to collector env handling")
    parser.add_argument("--api-key-env", default="AZURE_OPENAI_API_KEY")
    parser.add_argument("--api-version", default=None)
    parser.add_argument("--max-tokens", type=int, default=768)
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    adapted: list[str] = []

    for model in args.models:
        for mode in args.modes:
            stem = f"{slugify(model)}_{mode}"
            responses = out_dir / f"{stem}.responses.jsonl"
            mbs_result = out_dir / f"{stem}.mbs.json"
            collect_cmd = [
                args.python,
                "scripts/collect_azure_openai_responses.py",
                "--provider",
                "azure",
                "--model",
                model,
                "--deployment",
                model,
                "--api-key-env",
                args.api_key_env,
                "--mode",
                mode,
                "--schema",
                args.schema,
                "--cases",
                args.cases,
                "--max-tokens",
                str(args.max_tokens),
                "--out",
                str(responses),
            ]
            if args.endpoint:
                collect_cmd.extend(["--endpoint", args.endpoint])
            if args.api_version:
                collect_cmd.extend(["--api-version", args.api_version])
            run(collect_cmd)
            adapt_cmd = [
                args.python,
                "-m",
                "mbs.cli",
                "adapt-responses",
                "--schema",
                args.schema,
                "--responses",
                str(responses),
                "--cases",
                args.cases,
                "--model",
                model,
                "--decoding-mode",
                mode,
                "--out",
                str(mbs_result),
            ]
            run(adapt_cmd)
            adapted.append(str(mbs_result))

    print(json.dumps({"adapted_results": adapted, "count": len(adapted)}, indent=2))
    return 0


def run(command: list[str]) -> None:
    print("RUN", " ".join(command))
    subprocess.run(command, check=True)


def slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


if __name__ == "__main__":
    raise SystemExit(main())
