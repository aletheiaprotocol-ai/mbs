"""Analyze per-case MBS failures across result files.

This script is evidence-oriented: it separates infrastructure failures from
model behavior rows, summarizes model-level rates, identifies repeatedly failing
cases, and extracts expected-vs-observed action/priority decisions when provider
responses are available next to the MBS result files.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze MBS benchmark failures by model and case")
    parser.add_argument("--results", nargs="+", required=True, help="MBS result JSON files, dirs, or glob patterns")
    parser.add_argument("--cases", default=None, help="Optional cases JSONL for case text/expected outputs")
    parser.add_argument("--out-md", default=None)
    parser.add_argument("--out-json", default=None)
    parser.add_argument("--out-csv", default=None, help="Optional CSV summary of case-level failures")
    parser.add_argument("--exclude-infra", action="store_true", default=True)
    args = parser.parse_args()

    cases = load_cases(args.cases) if args.cases else {}
    files = expand_paths(args.results)
    analysis = analyze(files, cases=cases, exclude_infra=args.exclude_infra)

    if args.out_json:
        out_json = Path(args.out_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.out_csv:
        write_cases_csv(analysis, Path(args.out_csv))
    md = markdown_report(analysis)
    if args.out_md:
        out_md = Path(args.out_md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(md, encoding="utf-8")
    else:
        print(md)
    return 0


def expand_paths(values: list[str]) -> list[Path]:
    paths: list[Path] = []
    for value in values:
        matches = [Path(p) for p in glob.glob(value)]
        if not matches and Path(value).exists():
            matches = [Path(value)]
        for path in matches:
            if path.is_dir():
                paths.extend(sorted(path.rglob("*.mbs.json")))
            elif path.name.endswith(".mbs.json") or path.suffix == ".json":
                paths.append(path)
    return sorted({path.resolve() for path in paths})


def load_cases(path: str) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        case_id = str(row.get("id") or row.get("case_id"))
        cases[case_id] = row
    return cases


def analyze(files: list[Path], *, cases: dict[str, dict[str, Any]], exclude_infra: bool) -> dict[str, Any]:
    all_rows: list[dict[str, Any]] = []
    response_index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for file_path in files:
        payload = json.loads(file_path.read_text(encoding="utf-8-sig"))
        model = str(payload.get("model") or "unknown")
        mode = str(payload.get("decoding_mode") or "default")
        responses = load_responses_for(file_path, payload)
        for row in payload.get("rows", []):
            enriched = dict(row)
            enriched["source_file"] = str(file_path)
            all_rows.append(enriched)
            key = (model, mode, str(row.get("case_id")))
            if key in responses:
                response_index[key] = responses[key]

    behavior_rows = [row for row in all_rows if not row.get("infra_failure")] if exclude_infra else all_rows
    models = summarize_models(behavior_rows)
    cases_summary = summarize_cases(behavior_rows, cases, response_index)
    field_mismatches = summarize_field_mismatches(cases_summary)
    failure_types = Counter(str(row.get("failure_type") or "PASS") for row in behavior_rows)
    return {
        "files": [str(path) for path in files],
        "input_rows": len(all_rows),
        "behavior_rows": len(behavior_rows),
        "infra_failed_rows": len([row for row in all_rows if row.get("infra_failure")]),
        "models": models,
        "failure_types": dict(sorted(failure_types.items(), key=lambda item: (-item[1], item[0]))),
        "field_mismatches": field_mismatches,
        "cases": cases_summary,
    }


def load_responses_for(file_path: Path, payload: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    candidates: list[Path] = []
    raw = payload.get("responses")
    if raw:
        candidates.append(Path(str(raw)))
    candidates.append(file_path.with_name(file_path.name.replace(".mbs.json", ".responses.jsonl")))
    candidates.append(file_path.with_suffix(".responses.jsonl"))
    existing = next((path for path in candidates if path.exists()), None)
    if not existing:
        return {}
    model = str(payload.get("model") or "unknown")
    mode = str(payload.get("decoding_mode") or "default")
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for line in existing.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[(model, mode, str(row.get("case_id")))] = row
    return rows


def summarize_models(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("model") or "unknown"), str(row.get("decoding_mode") or "default"))].append(row)
    summaries = []
    for (model, mode), items in grouped.items():
        total = len(items)
        summaries.append(
            {
                "model": model,
                "decoding_mode": mode,
                "rows": total,
                "json_valid_rate": rate(items, "json_valid"),
                "schema_valid_rate": rate(items, "schema_valid"),
                "semantic_correct_rate": rate(items, "semantic_correct"),
                "top_failures": top_counts(row.get("failure_type") or "PASS" for row in items),
            }
        )
    return sorted(summaries, key=lambda row: (-(row["semantic_correct_rate"] or 0), -(row["schema_valid_rate"] or 0), row["model"]))


def summarize_cases(
    rows: list[dict[str, Any]],
    cases: dict[str, dict[str, Any]],
    response_index: dict[tuple[str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("case_id"))].append(row)
    summaries = []
    for case_id, items in grouped.items():
        failures = [row for row in items if row.get("status") != "PASS" or not row.get("semantic_correct")]
        case = cases.get(case_id, {})
        expected = case.get("expected_valid_outputs") or expected_from_errors(items)
        observed_actions = Counter()
        observed_priorities = Counter()
        field_mismatches = Counter()
        for row in items:
            key = (str(row.get("model") or "unknown"), str(row.get("decoding_mode") or "default"), case_id)
            output = extract_structured_output(response_index.get(key, {}))
            if isinstance(output, dict):
                if output.get("action") is not None:
                    observed_actions[str(output.get("action"))] += 1
                if output.get("priority") is not None:
                    observed_priorities[str(output.get("priority"))] += 1
                if isinstance(expected, dict):
                    for field, expected_value in expected.items():
                        if not semantically_equal(output.get(field), expected_value):
                            field_mismatches[field] += 1
        summaries.append(
            {
                "case_id": case_id,
                "runs": len(items),
                "failures": len(failures),
                "failure_rate": round(len(failures) / len(items), 4) if items else None,
                "expected_action": expected.get("action") if isinstance(expected, dict) else None,
                "expected_priority": expected.get("priority") if isinstance(expected, dict) else None,
                "observed_actions": dict(observed_actions.most_common()),
                "observed_priorities": dict(observed_priorities.most_common()),
                "field_mismatches": dict(field_mismatches.most_common()),
                "top_failures": top_counts(row.get("failure_type") or "PASS" for row in items),
                "input": case.get("input", ""),
            }
        )
    return sorted(summaries, key=lambda row: (-row["failures"], row["case_id"]))


def summarize_field_mismatches(cases_summary: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in cases_summary:
        counts.update(row.get("field_mismatches") or {})
    return dict(counts.most_common())


def semantically_equal(observed: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return sorted(map(str, observed or [])) == sorted(map(str, expected)) if isinstance(observed, list) else False
    return observed == expected


def write_cases_csv(analysis: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "runs",
        "failures",
        "failure_rate",
        "expected_action",
        "expected_priority",
        "observed_actions",
        "observed_priorities",
        "field_mismatches",
        "top_failures",
        "input",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in analysis.get("cases", []):
            writer.writerow({key: serialize_csv_value(row.get(key)) for key in fieldnames})


def serialize_csv_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return "" if value is None else str(value)


def expected_from_errors(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in rows:
        for error in row.get("errors") or []:
            expected = error.get("expected")
            if isinstance(expected, dict):
                return expected
    return {}


def extract_structured_output(response_row: dict[str, Any]) -> Any:
    if not response_row:
        return None
    tool_calls = response_row.get("tool_calls") or []
    if tool_calls:
        args = tool_calls[0].get("function", {}).get("arguments")
        return parse_json(args)
    return parse_json(response_row.get("response"))


def parse_json(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    parsed = try_json(text)
    if parsed is not None:
        return parsed
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return try_json(text[start : end + 1])
    return None


def try_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None


def rate(rows: list[dict[str, Any]], key: str) -> float | None:
    if not rows:
        return None
    return round(sum(1 for row in rows if row.get(key) is True) / len(rows), 4)


def top_counts(values: Any, limit: int = 5) -> dict[str, int]:
    counts = Counter(str(value) for value in values)
    return dict(counts.most_common(limit))


def markdown_report(analysis: dict[str, Any]) -> str:
    lines = ["# MBS Failure Analysis", ""]
    lines.extend(
        [
            f"- Files: {len(analysis.get('files', []))}",
            f"- Input rows: {analysis.get('input_rows', 0)}",
            f"- Behavior rows: {analysis.get('behavior_rows', 0)}",
            f"- Infra-failed rows: {analysis.get('infra_failed_rows', 0)}",
            "",
        ]
    )
    lines.extend(["## Model Summary", ""])
    lines.append("| model | mode | rows | json valid | schema valid | semantic correct | top failures |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | --- |")
    for row in analysis.get("models", []):
        lines.append(
            "| {model} | {decoding_mode} | {rows} | {json_valid_rate:.4f} | {schema_valid_rate:.4f} | {semantic_correct_rate:.4f} | {top_failures} |".format(
                **row
            )
        )
    lines.append("")
    lines.extend(["## Hardest Cases", ""])
    lines.append("| case | failures/runs | expected action | observed actions | field mismatches | top failures | input |")
    lines.append("| --- | ---: | --- | --- | --- | --- | --- |")
    for row in analysis.get("cases", [])[:20]:
        input_text = str(row.get("input") or "").replace("|", "\\|")
        if len(input_text) > 120:
            input_text = input_text[:117] + "..."
        lines.append(
            f"| {row.get('case_id')} | {row.get('failures')}/{row.get('runs')} | {row.get('expected_action') or ''} | {row.get('observed_actions')} | {row.get('field_mismatches')} | {row.get('top_failures')} | {input_text} |"
        )
    lines.append("")
    lines.extend(["## Field Mismatches", ""])
    lines.append("| field | mismatches |")
    lines.append("| --- | ---: |")
    for key, value in (analysis.get("field_mismatches") or {}).items():
        lines.append(f"| {key} | {value} |")
    lines.append("")
    lines.extend(["## Failure Types", ""])
    lines.append("| failure type | count |")
    lines.append("| --- | ---: |")
    for key, value in (analysis.get("failure_types") or {}).items():
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
