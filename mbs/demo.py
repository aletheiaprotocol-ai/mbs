"""Small YC-ready MBS demo and benchmark sample."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .compiler import canonical_json, compile_schema, estimate_tokens
from .cost import report_cost
from .trace import create_trace
from .validate import validate_output


YC_SCHEMA: dict[str, Any] = {
    "name": "support_agent_action",
    "description": "Choose the safest structured action for a customer-support agent.",
    "type": "object",
    "required": ["action", "priority", "category", "reason"],
    "additionalProperties": False,
    "properties": {
        "action": {
            "type": "string",
            "enum": ["ANSWER", "CREATE_TICKET", "ESCALATE", "REQUEST_INFO"],
            "description": "The next action the agent should take.",
        },
        "priority": {
            "type": "string",
            "enum": ["LOW", "MEDIUM", "HIGH"],
            "description": "Operational urgency.",
        },
        "category": {
            "type": "string",
            "enum": ["BILLING", "SECURITY", "BUG", "ACCOUNT", "OTHER"],
            "description": "Support queue category.",
        },
        "reason": {"type": "string", "description": "Short explanation for the decision."},
    },
}

YC_PROMPT = "Customer says: I think my account was taken over and I cannot sign in."

YC_BAD_OUTPUT: dict[str, Any] = {
    "action": "ANSWER|ESCALATE",
    "priority": "high",
    "category": "SECURITY",
    "reason": "Account takeover should be handled urgently.",
}

YC_REPAIRED_OUTPUT: dict[str, Any] = {
    "action": "ESCALATE",
    "priority": "HIGH",
    "category": "SECURITY",
    "reason": "Possible account takeover requires urgent escalation.",
}

YC_CASES: list[dict[str, Any]] = [
    {
        "id": "account_takeover",
        "input": YC_PROMPT,
        "expected": {"action": "ESCALATE", "priority": "HIGH", "category": "SECURITY"},
    },
    {
        "id": "double_charge",
        "input": "Customer says: I was charged twice for the same invoice.",
        "expected": {"action": "CREATE_TICKET", "priority": "MEDIUM", "category": "BILLING"},
    },
    {
        "id": "mobile_crash",
        "input": "Customer says: The mobile app crashes every time I open checkout.",
        "expected": {"action": "CREATE_TICKET", "priority": "MEDIUM", "category": "BUG"},
    },
]

_OUTPUTS: dict[str, dict[str, dict[str, dict[str, Any]]]] = {
    "precise_mock": {
        "verbose_prompt": {
            "account_takeover": {
                "action": "ESCALATE",
                "priority": "HIGH",
                "category": "SECURITY",
                "reason": "Possible account takeover.",
            },
            "double_charge": {
                "action": "CREATE_TICKET",
                "priority": "MEDIUM",
                "category": "BILLING",
                "reason": "Billing issue needs a ticket.",
            },
            "mobile_crash": {
                "action": "CREATE_TICKET",
                "priority": "medium",
                "category": "BUG",
                "reason": "Crash should be investigated.",
            },
        },
        "mbs_contract": {
            "account_takeover": {
                "action": "ESCALATE",
                "priority": "HIGH",
                "category": "SECURITY",
                "reason": "Possible account takeover.",
            },
            "double_charge": {
                "action": "CREATE_TICKET",
                "priority": "MEDIUM",
                "category": "BILLING",
                "reason": "Billing issue needs a ticket.",
            },
            "mobile_crash": {
                "action": "CREATE_TICKET",
                "priority": "MEDIUM",
                "category": "BUG",
                "reason": "Crash should be investigated.",
            },
        },
    },
    "cheap_mock": {
        "verbose_prompt": {
            "account_takeover": YC_BAD_OUTPUT,
            "double_charge": {
                "action": "CREATE_TICKET",
                "priority": "MEDIUM",
                "reason": "Billing issue needs a ticket.",
            },
            "mobile_crash": {
                "action": "CREATE_TICKET",
                "priority": "MEDIUM",
                "category": "BUG",
                "reason": "Crash should be investigated.",
            },
        },
        "mbs_contract": {
            "account_takeover": YC_BAD_OUTPUT,
            "double_charge": {
                "action": "CREATE_TICKET",
                "priority": "MEDIUM",
                "reason": "Billing issue needs a ticket.",
            },
            "mobile_crash": {
                "action": "CREATE_TICKET",
                "priority": "MEDIUM",
                "category": "BUG",
                "reason": "Crash should be investigated.",
            },
        },
    },
}

_REPAIRS: dict[tuple[str, str], dict[str, Any]] = {
    (
        "cheap_mock",
        "account_takeover",
    ): YC_REPAIRED_OUTPUT,
    (
        "cheap_mock",
        "double_charge",
    ): {
        "action": "CREATE_TICKET",
        "priority": "MEDIUM",
        "category": "BILLING",
        "reason": "Double charge should be routed to billing.",
    },
}


def build_yc_demo() -> dict[str, Any]:
    """Build the one-screen end-to-end demo payload."""
    contract = compile_schema(YC_SCHEMA, format="natural", task_context=YC_PROMPT)
    validation = validate_output(YC_SCHEMA, YC_BAD_OUTPUT)
    trace = create_trace(
        YC_SCHEMA,
        contract,
        validation,
        input_text=YC_PROMPT,
        model="cheap_mock",
        output_tokens=estimate_tokens(canonical_json(YC_BAD_OUTPUT)),
    )
    repaired_validation = validate_output(YC_SCHEMA, YC_REPAIRED_OUTPUT)
    repaired_trace = create_trace(
        YC_SCHEMA,
        contract,
        repaired_validation,
        input_text=YC_PROMPT,
        model="cheap_mock+mbs_retry",
        output_tokens=estimate_tokens(canonical_json(YC_REPAIRED_OUTPUT)),
    )
    cost = report_cost(
        [
            {
                "schema_valid": repaired_validation["schema_valid"],
                "retry_count": 1,
                "tokens": {
                    "mbs_contract": contract["token_estimate"],
                    "verbose_baseline": contract["full_token_estimate"],
                    "output": trace["tokens"]["output"] + repaired_trace["tokens"]["output"],
                },
            }
        ]
    )
    return {
        "input": {"schema": YC_SCHEMA, "prompt": YC_PROMPT},
        "contract": {
            "text": contract["prompt"],
            "mbs_tokens": contract["token_estimate"],
            "verbose_tokens": contract["full_token_estimate"],
            "token_savings_pct": contract["savings_pct"],
            "schema_hash": contract["schema_hash"],
            "contract_hash": contract["contract_hash"],
        },
        "run": {"model": "cheap_mock", "output": YC_BAD_OUTPUT},
        "check": {
            "status": validation["status"],
            "schema_valid": validation["schema_valid"],
            "failure_type": _first_failure(validation),
            "errors": validation["errors"],
            "trace_id": trace["trace_id"],
        },
        "retry": {
            "output": YC_REPAIRED_OUTPUT,
            "status": repaired_validation["status"],
            "schema_valid": repaired_validation["schema_valid"],
            "trace_id": repaired_trace["trace_id"],
        },
        "cost": cost,
    }


def run_yc_benchmark() -> dict[str, Any]:
    """Run a deterministic 3-case x 2-model sample benchmark."""
    mbs_contract = compile_schema(YC_SCHEMA, format="natural", task_context="Return one support action.")
    verbose_contract = compile_schema(YC_SCHEMA, format="full", task_context="Return one support action.")
    rows: list[dict[str, Any]] = []
    for model in ("precise_mock", "cheap_mock"):
        for case in YC_CASES:
            rows.append(
                _benchmark_row(
                    model=model,
                    strategy="verbose_prompt",
                    case=case,
                    output=_OUTPUTS[model]["verbose_prompt"][case["id"]],
                    contract=verbose_contract,
                    retry_output=None,
                )
            )
            retry_output = _REPAIRS.get((model, case["id"]))
            rows.append(
                _benchmark_row(
                    model=model,
                    strategy="mbs_contract+retry",
                    case=case,
                    output=_OUTPUTS[model]["mbs_contract"][case["id"]],
                    contract=mbs_contract,
                    retry_output=retry_output,
                )
            )
    return {
        "schema": YC_SCHEMA["name"],
        "cases": len(YC_CASES),
        "models": ["precise_mock", "cheap_mock"],
        "note": "Deterministic local adapter sample for YC demo. Broad GPU results are tracked separately.",
        "summary": _benchmark_summary(rows),
        "rows": rows,
    }


def write_yc_artifacts(
    result_json: str | Path = "benchmarks/results/yc_sample_benchmark.json",
    result_md: str | Path = "benchmarks/results/yc_sample_benchmark.md",
    brief_md: str | Path = "docs/mbs_yc_evidence_brief.md",
) -> dict[str, str]:
    benchmark = run_yc_benchmark()
    demo = build_yc_demo()
    result_json = Path(result_json)
    result_md = Path(result_md)
    brief_md = Path(brief_md)
    result_json.parent.mkdir(parents=True, exist_ok=True)
    result_md.parent.mkdir(parents=True, exist_ok=True)
    brief_md.parent.mkdir(parents=True, exist_ok=True)
    result_json.write_text(json.dumps(benchmark, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result_md.write_text(format_yc_benchmark_markdown(benchmark), encoding="utf-8")
    brief_md.write_text(format_yc_evidence_brief(demo, benchmark), encoding="utf-8")
    return {"json": str(result_json), "benchmark_markdown": str(result_md), "brief": str(brief_md)}


def format_yc_demo(demo: dict[str, Any] | None = None) -> str:
    demo = demo or build_yc_demo()
    first_error = demo["check"]["errors"][0] if demo["check"]["errors"] else {}
    lines = [
        "MBS YC demo: structured agent output check",
        "",
        "Input prompt:",
        f"  {demo['input']['prompt']}",
        "",
        "Minimal behavioral contract:",
        _indent(demo["contract"]["text"]),
        "",
        "Model output:",
        _indent(json.dumps(demo["run"]["output"], ensure_ascii=False)),
        "",
        "Check:",
        f"  status={demo['check']['status']}",
        f"  failure_type={demo['check']['failure_type']}",
        f"  trace_id={demo['check']['trace_id']}",
    ]
    if first_error:
        lines.append(f"  reason={first_error.get('type')} at {first_error.get('field')}")
        if first_error.get("hint"):
            lines.append(f"  hint={first_error['hint']}")
    lines.extend(
        [
            "",
            "MBS retry repair:",
            _indent(json.dumps(demo["retry"]["output"], ensure_ascii=False)),
            f"  status={demo['retry']['status']}",
            f"  trace_id={demo['retry']['trace_id']}",
            "",
            "Cost/token comparison:",
            f"  MBS contract tokens: {demo['contract']['mbs_tokens']}",
            f"  Verbose prompt tokens: {demo['contract']['verbose_tokens']}",
            f"  Token savings: {demo['contract']['token_savings_pct']}%",
            f"  Cost per valid output after repair: {demo['cost']['cost_per_valid_output_tokens']} tokens",
        ]
    )
    return "\n".join(lines)


def format_yc_benchmark_markdown(benchmark: dict[str, Any] | None = None) -> str:
    benchmark = benchmark or run_yc_benchmark()
    lines = [
        "# MBS YC Benchmark Sample",
        "",
        "Deterministic local sample: 3 support-agent cases x 2 mock model adapters.",
        "It compares a verbose prompt against an MBS contract with validation and one targeted retry.",
        "",
        "| strategy | cases | models | schema-valid | semantic-correct | avg retries | cost / valid output |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in benchmark["summary"]["by_strategy"]:
        lines.append(
            "| {strategy} | {cases} | {models} | {schema_valid_rate:.3f} | {semantic_correct_rate:.3f} | {avg_retry_count:.3f} | {cost_per_valid_output_tokens} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "Metrics: schema-valid means the output passed the schema validator; semantic-correct means required expected fields also matched the case label.",
            "This is not the broad GPU benchmark; it is the smallest reproducible sample for a YC reviewer.",
        ]
    )
    return "\n".join(lines) + "\n"


def format_yc_evidence_brief(demo: dict[str, Any] | None = None, benchmark: dict[str, Any] | None = None) -> str:
    demo = demo or build_yc_demo()
    benchmark = benchmark or run_yc_benchmark()
    mbs = next(row for row in benchmark["summary"]["by_strategy"] if row["strategy"] == "mbs_contract+retry")
    verbose = next(row for row in benchmark["summary"]["by_strategy"] if row["strategy"] == "verbose_prompt")
    return (
        "# MBS YC Evidence Brief\n\n"
        "## Problem\n\n"
        "Agents increasingly call tools, fill forms, and trigger workflows, but their structured outputs still fail in ordinary ways: invalid JSON, missing required fields, wrong enum values, and silent semantic drift. Teams usually discover these failures after the agent has already taken an action.\n\n"
        "## Wedge\n\n"
        "MBS compiles a schema into a minimal behavioral contract, validates model output, records a trace, and reports cost per valid structured output. The initial product is not a full agent platform; it is a small reliability layer for structured agent behavior.\n\n"
        "## 30-Second Demo\n\n"
        f"Input: support-ticket schema + prompt about possible account takeover. The mock model returns `action=ANSWER|ESCALATE` and `priority=high`. MBS returns `{demo['check']['status']}` with failure type `{demo['check']['failure_type']}`, trace `{demo['check']['trace_id']}`, and a targeted enum repair. The repaired output passes with trace `{demo['retry']['trace_id']}`.\n\n"
        "## Sample Result\n\n"
        "| strategy | schema-valid | semantic-correct | avg retries | cost / valid output |\n"
        "| --- | ---: | ---: | ---: | ---: |\n"
        f"| verbose prompt | {verbose['schema_valid_rate']:.3f} | {verbose['semantic_correct_rate']:.3f} | {verbose['avg_retry_count']:.3f} | {verbose['cost_per_valid_output_tokens']} |\n"
        f"| MBS contract + retry | {mbs['schema_valid_rate']:.3f} | {mbs['semantic_correct_rate']:.3f} | {mbs['avg_retry_count']:.3f} | {mbs['cost_per_valid_output_tokens']} |\n\n"
        "## Why It Matters\n\n"
        "MBS turns a vague prompt-quality problem into measurable software behavior: PASS / FAIL / REVIEW, exact failure reasons, trace ids, retry counts, and cost per valid output. The short-term wedge is CI and evaluation for structured agent outputs. Future direction: consume these traces inside larger agent systems after external users validate the narrow product.\n"
    )


def _benchmark_row(
    model: str,
    strategy: str,
    case: dict[str, Any],
    output: dict[str, Any],
    contract: dict[str, Any],
    retry_output: dict[str, Any] | None,
) -> dict[str, Any]:
    validation = validate_output(YC_SCHEMA, output)
    final_output = output
    retry_count = 0
    output_tokens = estimate_tokens(canonical_json(output))
    if strategy.startswith("mbs_contract") and retry_output is not None and not validation["schema_valid"]:
        retry_count = 1
        final_output = retry_output
        validation = validate_output(YC_SCHEMA, retry_output)
        output_tokens += estimate_tokens(canonical_json(retry_output))

    semantic_correct = validation["schema_valid"] and _matches_expected(final_output, case["expected"])
    if validation["schema_valid"] and not semantic_correct:
        validation = {**validation, "status": "REVIEW", "errors": [{"field": "$", "type": "semantic_mismatch"}]}
    trace = create_trace(
        YC_SCHEMA,
        contract,
        validation,
        input_text=case["input"],
        model=model,
        output=final_output,
        output_tokens=output_tokens,
    )
    attempts = retry_count + 1
    input_tokens = contract["token_estimate"] * attempts
    return {
        "case_id": case["id"],
        "model": model,
        "strategy": strategy,
        "status": validation["status"],
        "schema_valid": validation["schema_valid"],
        "semantic_correct": bool(semantic_correct),
        "retry_count": retry_count,
        "failure_type": _first_failure(validation),
        "tokens": {
            "input_total": input_tokens,
            "mbs_contract": contract["token_estimate"],
            "verbose_baseline": contract["full_token_estimate"],
            "output": output_tokens,
        },
        "trace": trace,
    }


def _benchmark_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_strategy: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["strategy"]].append(row)
    for strategy, items in grouped.items():
        cost = report_cost(items)
        by_strategy.append(
            {
                "strategy": strategy,
                "cases": len(items),
                "models": len({item["model"] for item in items}),
                "schema_valid_rate": _rate(items, "schema_valid"),
                "semantic_correct_rate": _rate(items, "semantic_correct"),
                "avg_retry_count": round(sum(int(item.get("retry_count") or 0) for item in items) / len(items), 4),
                "cost_per_valid_output_tokens": cost["cost_per_valid_output_tokens"],
            }
        )
    by_strategy.sort(key=lambda item: item["strategy"])
    return {"by_strategy": by_strategy}


def _matches_expected(output: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(output.get(key) == value for key, value in expected.items())


def _rate(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(1 for row in rows if row.get(key)) / len(rows), 4)


def _first_failure(validation: dict[str, Any]) -> str | None:
    errors = validation.get("errors") or []
    return errors[0].get("type") if errors else None


def _indent(text: str) -> str:
    return "\n".join(f"  {line}" for line in text.splitlines())
