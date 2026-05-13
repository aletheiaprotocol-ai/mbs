"""Run an MBS OSS model matrix against an OpenAI-compatible endpoint.

This script assumes a server such as vLLM is already running for the target
model. It iterates matrix rows and writes provider JSONL files. Use
`mbs adapt-responses` and `mbs report` after collection.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MBS OSS structured-output matrix collection")
    parser.add_argument("--matrix", default="benchmarks/oss_structured_output_matrix.json")
    parser.add_argument("--endpoint", required=True, help="OpenAI-compatible base URL, e.g. http://127.0.0.1:8000")
    parser.add_argument("--out-dir", default="results/oss")
    parser.add_argument("--models", nargs="*", help="Optional exact model ids from the matrix")
    parser.add_argument("--modes", nargs="*", help="Optional modes, default from matrix")
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()

    matrix = json.loads(Path(args.matrix).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    selected_models = set(args.models or [])
    modes = args.modes or matrix.get("modes", ["text", "json_mode", "tool_call"])
    schema = matrix["schemas"][0]
    cases = matrix["cases"][0]

    commands: list[list[str]] = []
    for family in matrix.get("families", []):
        for model in family.get("models", []):
            model_id = model["id"]
            if selected_models and model_id not in selected_models:
                continue
            slug = slugify(model_id)
            for mode in modes:
                out = out_dir / f"{slug}_{mode}.responses.jsonl"
                commands.append(
                    [
                        args.python,
                        "scripts/collect_azure_openai_responses.py",
                        "--provider",
                        "openai-compatible",
                        "--endpoint",
                        args.endpoint,
                        "--api-key-env",
                        "OPENAI_API_KEY",
                        "--model",
                        model_id,
                        "--mode",
                        mode,
                        "--schema",
                        schema,
                        "--cases",
                        cases,
                        "--out",
                        str(out),
                    ]
                )

    for command in commands:
        print("RUN", " ".join(command))
        subprocess.run(command, check=True)
    print(json.dumps({"commands": len(commands), "out_dir": str(out_dir)}, indent=2))
    return 0


def slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


if __name__ == "__main__":
    raise SystemExit(main())
