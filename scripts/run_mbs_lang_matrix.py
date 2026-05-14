"""Build a fixture-classified MBS-Lang token-fairness matrix.

This script is deterministic and fixture-only. It proves the MBS-Lang contract
surface: local-language input/output wrappers, English schema keys/enums, and
Token Fairness Ratio reporting. It must not be presented as model-behavior or
translation-quality evidence.
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

from mbs.compiler import load_schema
from mbs.lang import compile_language_contract

CLASSIFICATION = "fixture_mbs_lang_matrix_not_provider_benchmark"
LANGUAGE_NAMES = {
    "ar": "Arabic",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "hu": "Hungarian",
    "tr": "Turkish",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic MBS-Lang fixture matrix")
    parser.add_argument("--root", default=".", help="MBS repo root")
    parser.add_argument("--out-dir", default="results/mbs_lang_matrix_fixture", help="Artifact output directory")
    parser.add_argument("--json", action="store_true", help="Print manifest JSON only")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    example_dir = root / "examples" / "multilingual_risk_review"
    schema_path = example_dir / "schema.json"
    schema = load_schema(schema_path)
    case_files = sorted(example_dir.glob("cases_*.jsonl"))

    rows = []
    for case_file in case_files:
        rows.extend(_rows_for_case_file(schema, case_file))

    ratios = [row["token_fairness_ratio"] for row in rows if row["token_fairness_ratio"] is not None]
    failures = [failure for row in rows for failure in row["contract_boundary_failures"]]
    summary = {
        "languages": sorted({row["input_language"] for row in rows}),
        "rows": len(rows),
        "case_files": len(case_files),
        "min_token_fairness_ratio": min(ratios) if ratios else None,
        "max_token_fairness_ratio": max(ratios) if ratios else None,
        "avg_token_fairness_ratio": round(sum(ratios) / len(ratios), 3) if ratios else None,
        "contract_boundary_failures": len(failures),
    }
    matrix = {
        "classification": CLASSIFICATION,
        "evidence_boundary": (
            "Deterministic MBS-Lang fixture matrix; proves contract wrapper, token-fairness "
            "accounting, and key/enum boundary checks, not provider/model or translation behavior."
        ),
        "schema": str(schema_path),
        "example_dir": str(example_dir),
        "summary": summary,
        "rows": rows,
    }

    matrix_path = out_dir / "mbs_lang_matrix.json"
    _write_json(matrix_path, matrix)
    report_path = out_dir / "mbs_lang_matrix.md"
    report_path.write_text(_format_markdown(matrix), encoding="utf-8")

    checks = {
        "languages": summary["languages"],
        "rows": summary["rows"],
        "case_files": summary["case_files"],
        "contract_boundary_failures": summary["contract_boundary_failures"],
        "max_token_fairness_ratio": summary["max_token_fairness_ratio"],
        "english_baselines_present": all(row["english_baseline_tokens"] > 0 for row in rows),
        "schema_keys_preserved": all(row["schema_keys_preserved"] for row in rows),
        "enum_values_preserved": all(row["enum_values_preserved"] for row in rows),
    }
    passed = (
        checks["languages"] == ["ar", "de", "en", "es", "fr", "hu", "tr"]
        and checks["rows"] == 8
        and checks["case_files"] == 7
        and checks["contract_boundary_failures"] == 0
        and checks["english_baselines_present"] is True
        and checks["schema_keys_preserved"] is True
        and checks["enum_values_preserved"] is True
    )
    manifest = {
        "classification": CLASSIFICATION,
        "status": "PASS" if passed else "FAIL",
        "artifacts": {"matrix": str(matrix_path), "report": str(report_path)},
        "checks": checks,
        "next_evidence_gate": "Run equivalent multilingual contracts against provider/OSS/HPC rows and classify them separately.",
    }
    _write_json(out_dir / "manifest.json", manifest)

    if args.json:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
    else:
        print(f"MBS-Lang matrix: {manifest['status']}")
        print(f"Classification: {manifest['classification']}")
        print(f"Matrix: {matrix_path}")
        print(f"Report: {report_path}")
    return 0 if passed else 2


def _rows_for_case_file(schema: dict[str, Any], case_file: Path) -> list[dict[str, Any]]:
    rows = []
    for line in case_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        input_language = case.get("input_language") or case_file.stem.removeprefix("cases_")
        output_language = case.get("output_language") or input_language
        compiled = compile_language_contract(
            schema,
            input_language=input_language,
            output_language=output_language,
            contract_language="en",
        )
        prompt = compiled["prompt"]
        key_checks = {key: f'"{key}"' in prompt for key in schema.get("properties", {})}
        enum_values = _enum_values(schema)
        enum_checks = {value: value in prompt for value in enum_values}
        wrapper_checks = {
            "input_language_instruction": f"Analyze {input_language} input." in prompt,
            "contract_language_instruction": "Keep schema keys and enum values in en." in prompt,
            "output_language_instruction": f"Use {output_language} for free-text explanation fields." in prompt,
        }
        failures = [f"missing_key:{key}" for key, ok in key_checks.items() if not ok]
        failures.extend(f"missing_enum:{value}" for value, ok in enum_checks.items() if not ok)
        failures.extend(f"missing_wrapper:{name}" for name, ok in wrapper_checks.items() if not ok)
        rows.append(
            {
                "case_id": case.get("id"),
                "case_file": str(case_file),
                "language_name": LANGUAGE_NAMES.get(input_language, input_language),
                "input_language": input_language,
                "output_language": output_language,
                "contract_language": "en",
                "token_estimate": compiled["token_estimate"],
                "english_baseline_tokens": compiled["english_baseline_tokens"],
                "token_fairness_ratio": compiled["token_fairness_ratio"],
                "schema_hash": compiled["schema_hash"],
                "contract_hash": compiled["contract_hash"],
                "schema_keys_preserved": all(key_checks.values()),
                "enum_values_preserved": all(enum_checks.values()),
                "wrapper_instructions_present": all(wrapper_checks.values()),
                "contract_boundary_failures": failures,
            }
        )
    return rows


def _enum_values(schema: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for spec in schema.get("properties", {}).values():
        enum = spec.get("enum") if isinstance(spec, dict) else None
        if enum:
            values.extend(str(value) for value in enum)
    return values


def _format_markdown(matrix: dict[str, Any]) -> str:
    lines = [
        "# MBS-Lang Fixture Matrix",
        "",
        f"Classification: `{matrix['classification']}`",
        "",
        matrix["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Languages: {', '.join(matrix['summary']['languages'])}",
        f"- Rows: {matrix['summary']['rows']}",
        f"- Case files: {matrix['summary']['case_files']}",
        f"- Token Fairness Ratio range: {matrix['summary']['min_token_fairness_ratio']} - {matrix['summary']['max_token_fairness_ratio']}",
        f"- Average Token Fairness Ratio: {matrix['summary']['avg_token_fairness_ratio']}",
        f"- Contract boundary failures: {matrix['summary']['contract_boundary_failures']}",
        "",
        "## Rows",
        "",
        "| case | input | output | contract | tokens | English baseline | TFR | boundary |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in matrix["rows"]:
        boundary = "PASS" if not row["contract_boundary_failures"] else "; ".join(row["contract_boundary_failures"])
        lines.append(
            "| {case_id} | {input_language} | {output_language} | {contract_language} | {token_estimate} | "
            "{english_baseline_tokens} | {token_fairness_ratio} | {boundary} |".format(
                **row,
                boundary=boundary,
            )
        )
    lines.extend(
        [
            "",
            "## Proof Limit",
            "",
            "This is deterministic fixture evidence for the MBS-Lang contract surface. It does not measure provider reliability, OSS/HPC model behavior, or translation quality.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())