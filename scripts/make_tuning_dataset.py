"""Create reviewable structured-output tuning rows from MBS benchmark results.

This is intentionally conservative: it only emits rows for cases with stable
expected outputs from the original cases file and benchmark rows that are not
semantically correct. The output is JSONL suitable for human review before any
SFT/DPO conversion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Build reviewable tuning rows from MBS failures")
    parser.add_argument("--mbs-result", required=True, nargs="+", help="One or more MBS result JSON files containing rows")
    parser.add_argument("--cases", required=True, help="Original benchmark cases JSONL with expected_valid_outputs")
    parser.add_argument("--schema", required=True, help="Schema used for the benchmark")
    parser.add_argument("--out", required=True, help="Output JSONL path")
    parser.add_argument(
        "--include-status",
        nargs="*",
        default=["REVIEW", "FAIL"],
        help="MBS row statuses eligible for tuning rows",
    )
    parser.add_argument("--min-failures", type=int, default=1, help="Minimum failures per case/model/mode key")
    args = parser.parse_args()

    schema_text = Path(args.schema).read_text(encoding="utf-8")
    schema = json.loads(schema_text)
    schema_hash = hashlib.sha256(canonical_json(schema).encode("utf-8")).hexdigest()[:16]
    cases = index_cases(load_jsonl(args.cases))

    rows: list[dict[str, Any]] = []
    for result_path in args.mbs_result:
        result = json.loads(Path(result_path).read_text(encoding="utf-8"))
        for row in result.get("rows", []):
            row["_source_result"] = result_path
            rows.append(row)
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        case_id = str(row.get("case_id"))
        key = (case_id, str(row.get("model", "unknown")), str(row.get("decoding_mode", "unknown")))
        if is_eligible(row, set(args.include_status)) and case_id in cases:
            grouped.setdefault(key, []).append(row)

    output_rows: list[dict[str, Any]] = []
    for (case_id, model, mode), failures in grouped.items():
        if len(failures) < args.min_failures:
            continue
        case = cases[case_id]
        expected = case.get("expected_valid_outputs")
        if not isinstance(expected, dict):
            continue
        output_rows.append(
            {
                "case_id": case_id,
                "input": case.get("input", ""),
                "expected_output": expected,
                "schema_hash": schema_hash,
                "schema_path": args.schema,
                "source_result": sorted({str(f.get("_source_result")) for f in failures}),
                "source_model": model,
                "source_decoding_mode": mode,
                "failure_count": len(failures),
                "failure_types": sorted({str(f.get("failure_type")) for f in failures}),
                "review_status": "needs_human_review",
            }
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in output_rows) + ("\n" if output_rows else ""), encoding="utf-8")
    print(json.dumps({"out": str(out), "rows": len(output_rows), "schema_hash": schema_hash}, indent=2))
    return 0


def load_jsonl(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def index_cases(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for case in cases:
        case_id = case.get("case_id", case.get("id"))
        if case_id is not None:
            indexed[str(case_id)] = case
    return indexed


def is_eligible(row: dict[str, Any], statuses: set[str]) -> bool:
    if row.get("infra_failure"):
        return False
    if row.get("semantic_correct") is True:
        return False
    return str(row.get("status")) in statuses


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


if __name__ == "__main__":
    raise SystemExit(main())
