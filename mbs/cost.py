"""Cost reporting for MBS benchmark and check results."""

from __future__ import annotations

from typing import Any


def report_cost(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute cost-per-valid-output from a list of run result records."""
    total_input = 0
    total_output = 0
    valid = 0
    failed = 0

    for row in results:
        tokens = row.get("tokens", {})
        if tokens.get("input_total") is not None:
            input_tokens = int(tokens.get("input_total") or 0)
        else:
            attempts = int(row.get("retry_count") or 0) + 1
            input_tokens = int(tokens.get("input", tokens.get("mbs_contract", 0)) or 0) * max(1, attempts)
        total_input += input_tokens
        total_output += int(tokens.get("output", 0) or 0)
        ok = row.get("schema_valid")
        if ok is None:
            ok = row.get("status") == "PASS"
        if ok:
            valid += 1
        else:
            failed += 1

    total_tokens = total_input + total_output
    return {
        "runs": len(results),
        "valid_outputs": valid,
        "failed_outputs": failed,
        "total_tokens": total_tokens,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "cost_per_valid_output_tokens": None if valid == 0 else round(total_tokens / valid, 3),
    }
