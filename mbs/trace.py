"""Trace generation for MBS runs."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from .compiler import canonical_json, sha256_text


def create_trace(
    schema: dict[str, Any],
    contract: dict[str, Any] | str,
    validation: dict[str, Any],
    input_text: str = "",
    output: Any = None,
    model: str = "unknown",
    mbs_version: str = "0.1.0",
    validator_version: str = "json_schema_v1",
    output_tokens: int = 0,
) -> dict[str, Any]:
    """Create a portable audit trace for an MBS run."""
    contract_text = contract.get("prompt", "") if isinstance(contract, dict) else str(contract)
    output_obj = validation.get("output") if output is None else output
    status = validation.get("status", "PASS" if validation.get("schema_valid") else "FAIL")
    return {
        "trace_id": f"mbs_trace_{uuid.uuid4().hex[:12]}",
        "schema_hash": sha256_text(canonical_json(schema)),
        "contract_hash": sha256_text(contract_text),
        "input_hash": sha256_text(input_text),
        "output_hash": sha256_text(canonical_json(output_obj)),
        "model": model,
        "mbs_version": mbs_version,
        "validator_version": validator_version,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "errors": validation.get("errors", []),
        "tokens": _tokens_from_contract(contract, output_tokens=output_tokens),
    }


def _tokens_from_contract(contract: dict[str, Any] | str, output_tokens: int = 0) -> dict[str, int]:
    if isinstance(contract, dict):
        return {
            "mbs_contract": int(contract.get("token_estimate", 0)),
            "verbose_baseline": int(contract.get("full_token_estimate", 0)),
            "output": int(output_tokens or 0),
        }
    return {"mbs_contract": 0, "verbose_baseline": 0, "output": int(output_tokens or 0)}
