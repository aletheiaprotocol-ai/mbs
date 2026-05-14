"""Schema validation for structured model outputs."""

from __future__ import annotations

import json
import re
from typing import Any


def validate_output(schema: dict[str, Any], output: str | dict[str, Any]) -> dict[str, Any]:
    """Validate output against the subset of JSON Schema MBS needs for v1."""
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if isinstance(output, str):
        try:
            data = json.loads(output)
            json_valid = True
        except json.JSONDecodeError as exc:
            return {
                "json_valid": False,
                "schema_valid": False,
                "status": "FAIL",
                "errors": [
                    {
                        "field": "$",
                        "type": "invalid_json",
                        "message": str(exc),
                    }
                ],
                "warnings": [],
                "output": None,
            }
    else:
        data = output
        json_valid = True

    _validate_schema(schema, data, "$", errors, warnings)
    status = "FAIL" if errors else "REVIEW" if warnings else "PASS"
    return {
        "json_valid": json_valid,
        "schema_valid": not errors,
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "output": data,
    }


def _validate_schema(
    schema: dict[str, Any],
    value: Any,
    path: str,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    expected_type = schema.get("type")
    if expected_type == "object" or "properties" in schema:
        if not isinstance(value, dict):
            errors.append({"field": path, "type": "wrong_type", "expected": "object", "received": type(value).__name__})
            return
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append({"field": _join(path, key), "type": "missing_required_key"})
        for key, child_schema in properties.items():
            if key in value:
                _validate_schema(child_schema, value[key], _join(path, key), errors, warnings)
        for key in value.keys():
            if key not in properties:
                extra = {"field": _join(path, key), "type": "extra_key"}
                if schema.get("additionalProperties") is False:
                    errors.append(extra)
                else:
                    warnings.append(extra)
        return

    if expected_type == "array":
        if not isinstance(value, list):
            errors.append({"field": path, "type": "wrong_type", "expected": "array", "received": type(value).__name__})
            return
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for idx, item in enumerate(value):
                _validate_schema(item_schema, item, f"{path}[{idx}]", errors, warnings)
        return

    enum = schema.get("enum")
    if enum is not None and value not in enum:
        errors.append(_enum_error(path, value, enum))

    if expected_type and expected_type not in ("object", "array"):
        if not _matches_type(value, expected_type):
            errors.append(
                {
                    "field": path,
                    "type": "wrong_type",
                    "expected": expected_type,
                    "received": type(value).__name__,
                }
            )


def _matches_type(value: Any, expected_type: str | list[str]) -> bool:
    if isinstance(expected_type, list):
        return any(_matches_type(value, t) for t in expected_type)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return True


def _enum_error(path: str, value: Any, enum: list[Any]) -> dict[str, Any]:
    error: dict[str, Any] = {
        "field": path,
        "type": "invalid_enum",
        "received": value,
        "allowed": enum,
    }
    if not isinstance(value, str) or not all(isinstance(v, str) for v in enum):
        return error

    exact_by_lower = {str(v).lower(): v for v in enum}
    if value.lower() in exact_by_lower:
        error["hint"] = "case_mismatch"
        error["suggested"] = exact_by_lower[value.lower()]
        return error

    parts = [part.strip() for part in re.split(r"\s*(?:\||,|/)\s*", value) if part.strip()]
    if len(parts) > 1 and all(part in enum for part in parts):
        error["hint"] = "joined_enum_values"
        error["message"] = "Choose exactly one enum value, not multiple alternatives."
        return error

    error["type"] = "invented_enum"
    return error


def _join(base: str, key: str) -> str:
    return key if base == "$" else f"{base}.{key}"
