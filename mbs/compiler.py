"""Schema-to-contract compiler for MBS."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


FREE_ENUMS = {
    frozenset({"POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED"}),
    frozenset({"POSITIVE", "NEGATIVE", "NEUTRAL"}),
    frozenset({"TRUE", "FALSE"}),
    frozenset({"YES", "NO"}),
    frozenset({"PASS", "FAIL"}),
    frozenset({"HIGH", "MEDIUM", "LOW"}),
    frozenset({"MALE", "FEMALE", "OTHER"}),
    frozenset({"SPAM", "HAM"}),
}

PARTIAL_PATTERNS = [
    re.compile(r"(buy|sell|hold|trade|invest)", re.IGNORECASE),
    re.compile(r"(priority|severity|urgency|level)", re.IGNORECASE),
]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def schema_hash(schema: dict[str, Any]) -> str:
    return sha256_text(canonical_json(schema))


def load_schema(source: str | Path | dict[str, Any] | type[Any]) -> dict[str, Any]:
    """Load a JSON Schema from a dict, path, stdin marker, or Pydantic model."""
    if isinstance(source, dict):
        return source

    if isinstance(source, type):
        if hasattr(source, "model_json_schema"):
            return source.model_json_schema()
        if hasattr(source, "schema"):
            return source.schema()

    if str(source) == "-":
        return json.load(sys.stdin)

    with open(source, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def classify_enum(field_name: str, enum_values: list[str]) -> str:
    """Classify an enum as FREE, PARTIAL, or PAID."""
    normalized = frozenset(str(v).upper() for v in enum_values)
    for free_set in FREE_ENUMS:
        if normalized == frozenset(v.upper() for v in free_set):
            return "FREE"
    for pattern in PARTIAL_PATTERNS:
        if pattern.search(field_name):
            return "PARTIAL"
    return "PAID"


def _json_type_to_text(spec: dict[str, Any]) -> str:
    t = spec.get("type")
    if isinstance(t, list):
        return "|".join(str(x) for x in t)
    if t:
        return str(t)
    if "properties" in spec:
        return "object"
    if "items" in spec:
        return "array"
    return "string"


def extract_fields(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract top-level JSON Schema fields and enum classifications."""
    fields: list[dict[str, Any]] = []
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    for name, spec in properties.items():
        if not isinstance(spec, dict):
            spec = {}
        enum = spec.get("enum")
        field = {
            "name": name,
            "type": _json_type_to_text(spec),
            "required": name in required,
            "enum": enum,
            "description": spec.get("description", ""),
            "schema": spec,
        }
        field["enum_class"] = classify_enum(name, enum) if enum else None
        fields.append(field)
    return fields


def compile_schema(
    schema: dict[str, Any] | type[Any],
    format: str = "natural",
    task_context: str = "",
    include_free_enums: bool = False,
    verbose: bool = False,
    input_language: str | None = None,
    output_language: str | None = None,
    contract_language: str | None = None,
) -> dict[str, Any]:
    """Compile a schema into a minimal behavioral contract."""
    schema_dict = load_schema(schema) if not isinstance(schema, dict) else schema
    fields = extract_fields(schema_dict)

    analysis = []
    for f in fields:
        if f["enum_class"] == "FREE" and not include_free_enums:
            action = "omit"
        elif f["enum"]:
            action = "specify"
        else:
            action = "name_only"
        analysis.append(
            {
                "name": f["name"],
                "type": f["type"],
                "required": f["required"],
                "has_enum": f["enum"] is not None,
                "enum_class": f["enum_class"],
                "enum_values": f["enum"],
                "action": action,
            }
        )

    if format == "natural":
        prompt = _build_natural(fields, task_context, include_free_enums)
    elif format == "progressive":
        prompt = _build_progressive(fields, task_context, include_free_enums)
    elif format == "full":
        prompt = _build_full(fields, task_context)
    elif format == "strict":
        prompt = _build_strict(fields, task_context)
    else:
        raise ValueError(f"Unknown format: {format}")

    if input_language or output_language or contract_language:
        prompt = _apply_language_wrapper(
            prompt,
            input_language=input_language,
            output_language=output_language,
            contract_language=contract_language,
        )

    full_prompt = _build_full(fields, task_context)
    token_est = estimate_tokens(prompt)
    full_token_est = estimate_tokens(full_prompt)

    return {
        "prompt": prompt,
        "contract": prompt,
        "token_estimate": token_est,
        "full_prompt": full_prompt,
        "full_token_estimate": full_token_est,
        "savings_pct": round((1 - token_est / max(full_token_est, 1)) * 100, 1),
        "schema_hash": schema_hash(schema_dict),
        "contract_hash": sha256_text(prompt),
        "field_analysis": analysis,
        "paid_enums": [a for a in analysis if a["enum_class"] == "PAID"],
        "free_enums": [a for a in analysis if a["enum_class"] == "FREE"],
        "partial_enums": [a for a in analysis if a["enum_class"] == "PARTIAL"],
    }


def estimate_tokens(text: str) -> int:
    """Small deterministic token estimate for local reporting."""
    if not text:
        return 0
    words = re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)
    return max(1, int(len(words) * 1.15))


def _build_natural(fields: list[dict[str, Any]], task_context: str, include_free: bool) -> str:
    parts: list[str] = []
    if task_context:
        parts.append(task_context.strip())
    parts.append("Respond in JSON with")

    field_specs = []
    for f in fields:
        if f["enum"] and (f["enum_class"] != "FREE" or include_free):
            vals = "|".join(str(v) for v in f["enum"])
            field_specs.append(f'"{f["name"]}": {vals}')
        else:
            field_specs.append(f'"{f["name"]}"')

    parts.append(", ".join(field_specs) + ".")
    return " ".join(parts)


def _build_progressive(fields: list[dict[str, Any]], task_context: str, include_free: bool) -> str:
    parts: list[str] = []
    if task_context:
        parts.append(task_context.strip())
    parts.append("Respond as JSON:")
    parts.append("{")
    lines = []
    for f in fields:
        line = f'  "{f["name"]}": <{f["type"]}>'
        if f["enum"] and (f["enum_class"] != "FREE" or include_free):
            vals = "|".join(str(v) for v in f["enum"])
            line = f'  "{f["name"]}": {vals}'
        lines.append(line)
    parts.append(",\n".join(lines))
    parts.append("}")
    return "\n".join(parts)


def _build_full(fields: list[dict[str, Any]], task_context: str) -> str:
    parts: list[str] = []
    if task_context:
        parts.extend([task_context.strip(), ""])
    parts.extend(["You must respond with a valid JSON object containing the following fields:", ""])
    for f in fields:
        req = " (required)" if f["required"] else " (optional)"
        line = f'- "{f["name"]}"{req}: {f["type"]}'
        if f["description"]:
            line += f' -- {f["description"]}'
        if f["enum"]:
            line += f'. Must be one of: {", ".join(str(v) for v in f["enum"])}'
        parts.append(line)
    parts.extend(["", "Do not include any text outside the JSON object."])
    return "\n".join(parts)


def _build_strict(fields: list[dict[str, Any]], task_context: str) -> str:
    parts: list[str] = []
    if task_context:
        parts.append(task_context.strip())
    parts.append(
        "Return one raw JSON object: first generated character {, final generated character }. "
        "Exclude markdown fences, explanations, analysis, and chain-of-thought."
    )
    required = []
    field_specs = []
    for f in fields:
        if f["required"]:
            required.append(str(f["name"]))
        spec = f'"{f["name"]}":{f["type"]}'
        if f["enum"]:
            spec = f'"{f["name"]}":{("|".join(str(v) for v in f["enum"]))}'
        field_specs.append(spec)
    parts.append("Keys: " + "; ".join(field_specs) + ".")
    if required:
        parts.append("Required: " + ",".join(f'"{key}"' for key in required) + ".")
    parts.append("If unsure, still return the closest schema-valid JSON object.")
    return " ".join(parts)


def _apply_language_wrapper(
    prompt: str,
    input_language: str | None,
    output_language: str | None,
    contract_language: str | None,
) -> str:
    bits = []
    if input_language:
        bits.append(f"Analyze {input_language} input.")
    if contract_language:
        bits.append(f"Keep schema keys and enum values in {contract_language}.")
    if output_language:
        bits.append(f"Use {output_language} for free-text explanation fields.")
    return " ".join(bits + [prompt])


def format_report(result: dict[str, Any]) -> str:
    """Format compilation result as a human-readable report."""
    lines = ["=" * 60, "MBS SCHEMA COMPILER REPORT", "=" * 60, ""]
    lines.extend(["FIELD ANALYSIS:", ""])
    for f in result["field_analysis"]:
        status = f"[{f['enum_class']}]" if f["enum_class"] else "[no enum]"
        enum_str = f" = {' | '.join(str(v) for v in f['enum_values'])}" if f["enum_values"] else ""
        lines.append(f"  {f['name']:20s} {status:10s} -> {f['action']:10s}{enum_str}")
        if f["enum_class"] == "FREE":
            lines.append(f"  {'':20s} Reason: Values match a common pretraining set. Safe to omit.")
        elif f["enum_class"] == "PARTIAL":
            lines.append(f"  {'':20s} Reason: Field name is domain-suggestive. Specify for safety.")
        elif f["enum_class"] == "PAID":
            lines.append(f"  {'':20s} Reason: Application-specific values must be specified.")
        lines.append("")

    lines.extend(
        [
            "SUMMARY:",
            f"  PAID enums (must specify):  {len(result['paid_enums'])}",
            f"  FREE enums (can omit):      {len(result['free_enums'])}",
            f"  PARTIAL enums (recommend):  {len(result['partial_enums'])}",
            "",
            "-" * 60,
            "COMPILED PROMPT:",
            "-" * 60,
            result["prompt"],
            "",
            f"Token estimate: ~{result['token_estimate']}",
            f"Full prompt tokens: ~{result['full_token_estimate']}",
            f"Savings: {result['savings_pct']}%",
            "",
            "-" * 60,
            "FULL (UNOPTIMIZED) PROMPT:",
            "-" * 60,
            result["full_prompt"],
        ]
    )
    return "\n".join(lines)
