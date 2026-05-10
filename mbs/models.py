"""Model-suite registry helpers for broad MBS benchmark coverage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_model_registry(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def suite_models(registry: dict[str, Any], suite: str) -> list[dict[str, Any]]:
    suites = registry.get("suites", {})
    model_meta = registry.get("models", {})
    if suite not in suites:
        raise KeyError(f"Unknown model suite: {suite}")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for model_id in suites[suite]:
        if model_id in seen:
            continue
        seen.add(model_id)
        meta = dict(model_meta.get(model_id, {}))
        meta["id"] = model_id
        rows.append(meta)
    return rows


def suite_summary(models: list[dict[str, Any]]) -> dict[str, Any]:
    families = sorted({m.get("family", "unknown") for m in models})
    size_bands = sorted({m.get("size_band", "unknown") for m in models})
    access = _counts(m.get("access", "unknown") for m in models)
    return {
        "models": len(models),
        "families": len(families),
        "family_names": families,
        "size_bands": size_bands,
        "access": access,
        "min_params_b": min((m.get("params_b") for m in models if isinstance(m.get("params_b"), (int, float))), default=None),
        "max_params_b": max((m.get("params_b") for m in models if isinstance(m.get("params_b"), (int, float))), default=None),
    }


def validate_suite_coverage(
    models: list[dict[str, Any]],
    min_models: int = 1,
    min_families: int = 1,
    min_size_bands: int = 1,
) -> list[str]:
    summary = suite_summary(models)
    errors: list[str] = []
    if summary["models"] < min_models:
        errors.append(f"models {summary['models']} < {min_models}")
    if summary["families"] < min_families:
        errors.append(f"families {summary['families']} < {min_families}")
    if len(summary["size_bands"]) < min_size_bands:
        errors.append(f"size_bands {len(summary['size_bands'])} < {min_size_bands}")
    return errors


def write_model_ids(path: str | Path, models: list[dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(m["id"] for m in models) + "\n", encoding="utf-8")


def _counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts
