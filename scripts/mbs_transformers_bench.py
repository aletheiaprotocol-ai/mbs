#!/usr/bin/env python3
"""Run MBS Bench against one local Hugging Face Transformers model.

This script is intended for Leonardo/MN5 jobs after the local MBS harness is
stable. It imports torch/transformers only inside main so the core MBS package
stays lightweight.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from pathlib import Path
from typing import Any

from mbs.bench import first_failure_type, language_label, load_jsonl, summarize
from mbs.compiler import canonical_json, compile_schema, estimate_tokens, load_schema
from mbs.retry import build_retry_prompt
from mbs.trace import create_trace
from mbs.validate import validate_output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run MBS benchmark with a Transformers causal LM")
    parser.add_argument("--schema", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-label")
    parser.add_argument("--out", required=True)
    parser.add_argument("--prompt-style", choices=["natural", "progressive", "full", "strict"], default="full")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, help="Seed for reproducible sampled decoding")
    parser.add_argument("--retries", type=int, default=0, help="Corrective retries after validation failure")
    parser.add_argument(
        "--retry-policy",
        choices=["schema", "semantic"],
        default=os.environ.get("MBS_RETRY_POLICY", "semantic"),
        help="schema retries only JSON/schema failures; semantic also retries semantic mismatches",
    )
    parser.add_argument(
        "--retry-adoption",
        choices=["best", "latest"],
        default=os.environ.get("MBS_RETRY_ADOPTION", "best"),
        help="best keeps the strongest validated attempt; latest reproduces last-retry-wins behavior",
    )
    parser.add_argument("--local-files-only", action="store_true", help="Load model/tokenizer only from local cache")
    parser.add_argument("--input-language")
    parser.add_argument("--output-language")
    parser.add_argument("--contract-language")
    parser.add_argument("--dtype", choices=["auto", "bf16", "fp16", "fp32"], default="auto")
    parser.add_argument(
        "--chat-template",
        choices=["auto", "never"],
        default="auto",
        help="Use tokenizer chat template when available",
    )
    args = parser.parse_args(argv)
    args.local_files_only = args.local_files_only or _truthy_env("MBS_LOCAL_FILES_ONLY") or _truthy_env("HF_HUB_OFFLINE")

    schema = load_schema(args.schema)
    cases = load_jsonl(args.cases)
    contract = compile_schema(
        schema,
        format=args.prompt_style,
        input_language=args.input_language,
        output_language=args.output_language,
        contract_language=args.contract_language,
    )
    model_label = args.model_label or args.model
    lang_label = language_label(args.input_language, args.output_language, args.contract_language)

    try:
        import torch
        from transformers import AutoTokenizer
    except ModuleNotFoundError as exc:
        _write_infra_failure(args, schema, contract, "missing_dependency", exc, model_label)
        return 0

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            args.model,
            trust_remote_code=True,
            local_files_only=args.local_files_only,
        )
        torch_dtype = _resolve_dtype(torch, args.dtype)
        model = _load_generation_model(args.model, torch_dtype=torch_dtype, local_files_only=args.local_files_only)
    except Exception as exc:
        _write_infra_failure(args, schema, contract, "model_load_failed", exc, model_label)
        return 0
    model.eval()

    rows: list[dict[str, Any]] = []
    for idx, case in enumerate(cases):
        started = time.time()
        prompt = _build_prompt(contract["prompt"], case.get("input", ""))
        try:
            case_args = _case_args(args, idx)
            (
                raw_text,
                output,
                validation,
                semantic_ok,
                generated_tokens,
                used_chat_template,
                retry_count,
                attempts,
            ) = _run_with_retries(model, tokenizer, schema, prompt, case, case_args)
        except Exception as exc:
            rows.append(_generation_failure_row(args, schema, contract, case, idx, started, exc, model_label))
            continue
        output_tokens = generated_tokens or estimate_tokens(canonical_json(validation.get("output")))
        trace = create_trace(
            schema,
            contract,
            validation,
            input_text=case.get("input", ""),
            model=model_label,
            output_tokens=output_tokens,
        )
        rows.append(
            {
                "case_id": case.get("id", idx),
                "model": model_label,
                "prompt_style": args.prompt_style,
                "decoding_mode": "transformers_chat" if used_chat_template else "transformers_plain",
                "language": lang_label,
                "status": validation["status"],
                "json_valid": validation["json_valid"],
                "schema_valid": validation["schema_valid"],
                "semantic_correct": semantic_ok,
                "failure_type": first_failure_type(validation),
                "retry_count": retry_count,
                "latency_s": round(time.time() - started, 4),
                "errors": validation["errors"],
                "warnings": validation["warnings"],
                "raw_text": raw_text,
                "attempts": attempts,
                "output": validation.get("output"),
                "tokens": trace["tokens"],
                "trace": trace,
            }
        )

    payload = {
        "schema": args.schema,
        "cases": args.cases,
        "model": model_label,
        "load_target": args.model,
        "prompt_style": args.prompt_style,
        "decoding_mode": _payload_decoding_mode(rows),
        "language": lang_label,
        "chat_template": args.chat_template,
        "retries": args.retries,
        "retry_policy": args.retry_policy,
        "retry_adoption": args.retry_adoption,
        "temperature": args.temperature,
        "seed": args.seed,
        "local_files_only": args.local_files_only,
        "summary": summarize(rows),
        "rows": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    return 0


def _write_infra_failure(
    args: argparse.Namespace,
    schema: dict[str, Any],
    contract: dict[str, Any],
    failure_type: str,
    exc: BaseException,
    model_label: str,
) -> None:
    validation = {
        "status": "FAIL",
        "json_valid": False,
        "schema_valid": False,
        "errors": [{"field": "$", "type": failure_type, "message": str(exc)}],
        "warnings": [],
        "output": None,
    }
    trace = create_trace(schema, contract, validation, input_text="", model=model_label, output_tokens=0)
    row = {
        "case_id": None,
        "model": model_label,
        "prompt_style": args.prompt_style,
        "decoding_mode": "transformers",
        "language": language_label(args.input_language, args.output_language, args.contract_language),
        "status": "INFRA_FAIL",
        "json_valid": False,
        "schema_valid": False,
        "semantic_correct": None,
        "failure_type": failure_type,
        "retry_count": 0,
        "latency_s": 0.0,
        "errors": validation["errors"],
        "warnings": [],
        "raw_text": "",
        "output": None,
        "tokens": trace["tokens"],
        "trace": trace,
    }
    payload = {
        "schema": args.schema,
        "model": model_label,
        "load_target": args.model,
        "prompt_style": args.prompt_style,
        "decoding_mode": "transformers",
        "language": language_label(args.input_language, args.output_language, args.contract_language),
        "chat_template": getattr(args, "chat_template", "auto"),
        "retries": getattr(args, "retries", 0),
        "infra_failure": failure_type,
        "summary": summarize([row]),
        "rows": [row],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))


def _generation_failure_row(
    args: argparse.Namespace,
    schema: dict[str, Any],
    contract: dict[str, Any],
    case: dict[str, Any],
    idx: int,
    started: float,
    exc: BaseException,
    model_label: str,
) -> dict[str, Any]:
    validation = {
        "status": "FAIL",
        "json_valid": False,
        "schema_valid": False,
        "errors": [{"field": "$", "type": "model_generation_failed", "message": str(exc)}],
        "warnings": [],
        "output": None,
    }
    trace = create_trace(
        schema,
        contract,
        validation,
        input_text=case.get("input", ""),
        model=model_label,
        output_tokens=0,
    )
    return {
        "case_id": case.get("id", idx),
        "model": model_label,
        "prompt_style": args.prompt_style,
        "decoding_mode": "transformers",
        "language": language_label(args.input_language, args.output_language, args.contract_language),
        "status": "INFRA_FAIL",
        "json_valid": False,
        "schema_valid": False,
        "semantic_correct": None,
        "failure_type": "model_generation_failed",
        "retry_count": 0,
        "latency_s": round(time.time() - started, 4),
        "errors": validation["errors"],
        "warnings": [],
        "raw_text": "",
        "output": None,
        "tokens": trace["tokens"],
        "trace": trace,
    }


def _resolve_dtype(torch: Any, dtype: str) -> Any:
    if dtype == "bf16":
        return torch.bfloat16
    if dtype == "fp16":
        return torch.float16
    if dtype == "fp32":
        return torch.float32
    return "auto"


def _load_generation_model(model_name_or_path: str, *, torch_dtype: Any, local_files_only: bool) -> Any:
    """Load a text-generation-capable Transformers model.

    Most benchmark targets are ordinary causal LMs. Some newer instruction
    models, notably Mistral3-style releases, expose conditional image/text
    generation classes instead of an AutoModelForCausalLM mapping. For text-only
    prompts their tokenizer and generate path still work, so try those mappings
    as a fallback before declaring an infrastructure failure.
    """

    from transformers import AutoModelForCausalLM

    load_kwargs = {
        "torch_dtype": torch_dtype,
        "device_map": "auto",
        "trust_remote_code": True,
        "local_files_only": local_files_only,
    }
    try:
        return AutoModelForCausalLM.from_pretrained(model_name_or_path, **load_kwargs)
    except Exception as causal_exc:
        fallback_errors: list[str] = []
        for class_name in ("AutoModelForImageTextToText", "AutoModelForVision2Seq"):
            try:
                import transformers

                auto_cls = getattr(transformers, class_name)
            except Exception as exc:
                fallback_errors.append(f"{class_name}: unavailable: {exc}")
                continue
            try:
                return auto_cls.from_pretrained(model_name_or_path, **load_kwargs)
            except Exception as exc:
                fallback_errors.append(f"{class_name}: {exc}")
        details = "; ".join(fallback_errors)
        raise RuntimeError(f"{causal_exc}\nFallback loaders failed: {details}") from causal_exc


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _case_args(args: argparse.Namespace, case_index: int) -> argparse.Namespace:
    values = vars(args).copy()
    if args.seed is not None:
        values["seed"] = args.seed + (case_index * 1000)
    return argparse.Namespace(**values)


def _build_prompt(contract: str, input_text: str) -> str:
    return f"{contract}\n\nInput:\n{input_text}\n\nOutput starts with {{ and ends with }}."


def _run_with_retries(
    model: Any,
    tokenizer: Any,
    schema: dict[str, Any],
    prompt: str,
    case: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[str, Any, dict[str, Any], bool | None, int, bool, int, list[dict[str, Any]]]:
    raw_text = ""
    output: Any = None
    validation: dict[str, Any] | None = None
    semantic_ok: bool | None = None
    best_raw_text = ""
    best_output: Any = None
    best_validation: dict[str, Any] | None = None
    best_semantic_ok: bool | None = None
    best_attempt_index = 0
    total_generated_tokens = 0
    used_chat_template = False
    attempts: list[dict[str, Any]] = []
    max_attempts = max(0, args.retries) + 1

    for attempt_index in range(max_attempts):
        attempt_prompt = prompt if attempt_index == 0 else build_retry_prompt(prompt, raw_text, validation)
        if getattr(args, "seed", None) is not None:
            _set_generation_seed(int(args.seed) + attempt_index)
        raw_text, generated_tokens, attempt_used_chat = _generate_text(
            model,
            tokenizer,
            attempt_prompt,
            args.max_new_tokens,
            args.temperature,
            args.chat_template == "auto",
        )
        used_chat_template = used_chat_template or attempt_used_chat
        total_generated_tokens += generated_tokens
        output, extraction_warnings, extraction_errors = _extract_json_with_diagnostics(raw_text)
        validation = validate_output(schema, output)
        validation["warnings"].extend(extraction_warnings)
        if extraction_errors:
            validation["errors"] = extraction_errors + validation["errors"]
        _refresh_validation_status(validation)
        semantic_ok = _apply_semantic_check(validation, case.get("expected_valid_outputs"))
        if _should_adopt_attempt(args, validation, semantic_ok, best_validation, best_semantic_ok):
            best_raw_text = raw_text
            best_output = output
            best_validation = validation
            best_semantic_ok = semantic_ok
            best_attempt_index = attempt_index
        attempts.append(
            {
                "attempt": attempt_index,
                "json_valid": validation["json_valid"],
                "schema_valid": validation["schema_valid"],
                "semantic_correct": semantic_ok,
                "failure_type": first_failure_type(validation),
                "generated_tokens": generated_tokens,
            }
        )
        if _should_stop_retry(validation, semantic_ok, args):
            break

    assert best_validation is not None
    for attempt in attempts:
        attempt["selected"] = attempt["attempt"] == best_attempt_index
    return (
        best_raw_text,
        best_output,
        best_validation,
        best_semantic_ok,
        total_generated_tokens,
        used_chat_template,
        len(attempts) - 1,
        attempts,
    )


def _should_stop_retry(validation: dict[str, Any], semantic_ok: bool | None, args: argparse.Namespace) -> bool:
    if not validation["schema_valid"]:
        return False
    if getattr(args, "retry_policy", "semantic") == "schema":
        return True
    return semantic_ok is not False


def _refresh_validation_status(validation: dict[str, Any]) -> None:
    if validation.get("errors"):
        validation["status"] = "FAIL"
    elif validation.get("warnings"):
        validation["status"] = "REVIEW"
    else:
        validation["status"] = "PASS"


def _is_better_attempt(
    candidate_validation: dict[str, Any],
    candidate_semantic_ok: bool | None,
    current_validation: dict[str, Any],
    current_semantic_ok: bool | None,
) -> bool:
    """Prefer a retry only when it improves the measured outcome.

    Retries are still counted for cost and latency, but a failed repair should
    not replace a better earlier answer. This is especially important when a
    model changes an actionable enum error into a joined or invented enum.
    """

    return _attempt_score(candidate_validation, candidate_semantic_ok) > _attempt_score(
        current_validation, current_semantic_ok
    )


def _should_adopt_attempt(
    args: argparse.Namespace,
    candidate_validation: dict[str, Any],
    candidate_semantic_ok: bool | None,
    current_validation: dict[str, Any] | None,
    current_semantic_ok: bool | None,
) -> bool:
    if current_validation is None:
        return True
    if getattr(args, "retry_adoption", "best") == "latest":
        return True
    return _is_better_attempt(candidate_validation, candidate_semantic_ok, current_validation, current_semantic_ok)


def _attempt_score(validation: dict[str, Any], semantic_ok: bool | None) -> tuple[int, int, int, int, int, int]:
    status_rank = {"FAIL": 0, "REVIEW": 1, "PASS": 2}.get(str(validation.get("status")), 0)
    semantic_rank = {False: 0, None: 1, True: 2}[semantic_ok]
    return (
        1 if validation.get("schema_valid") else 0,
        status_rank,
        1 if validation.get("json_valid") else 0,
        semantic_rank,
        -_failure_severity(first_failure_type(validation)),
        -len(validation.get("errors") or []),
    )


def _failure_severity(failure_type: str | None) -> int:
    return {
        "invalid_json": 5,
        "reasoning_prose": 5,
        "invented_enum": 4,
        "invalid_enum": 3,
        "wrong_type": 3,
        "missing_required_key": 3,
        "semantic_mismatch": 2,
        "extra_key": 1,
        "prose_wrapped_json": 1,
    }.get(str(failure_type or ""), 0)


def _set_generation_seed(seed: int) -> None:
    random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except Exception:
        pass


def _generate_text(
    model: Any,
    tokenizer: Any,
    prompt: str,
    max_new_tokens: int,
    temperature: float,
    allow_chat_template: bool,
) -> tuple[str, int, bool]:
    inputs, used_chat_template = _tokenize_prompt(tokenizer, prompt, allow_chat_template)
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    generation_kwargs = {
        "max_new_tokens": max_new_tokens,
        "do_sample": temperature > 0,
        "pad_token_id": tokenizer.eos_token_id,
    }
    if temperature > 0:
        generation_kwargs["temperature"] = temperature
    generated = model.generate(**inputs, **generation_kwargs)
    new_tokens = generated[0][inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip(), int(new_tokens.shape[-1]), used_chat_template


def _tokenize_prompt(tokenizer: Any, prompt: str, allow_chat_template: bool) -> tuple[dict[str, Any], bool]:
    if allow_chat_template and getattr(tokenizer, "chat_template", None):
        try:
            chat_text = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=False,
                add_generation_prompt=True,
            )
            return tokenizer(chat_text, return_tensors="pt"), True
        except Exception:
            pass
    return tokenizer(prompt, return_tensors="pt"), False


def _payload_decoding_mode(rows: list[dict[str, Any]]) -> str:
    modes = {row.get("decoding_mode") for row in rows if row.get("decoding_mode")}
    if len(modes) == 1:
        return str(next(iter(modes)))
    if len(modes) > 1:
        return "transformers_mixed"
    return "transformers"


def _extract_json_or_raw(text: str) -> Any:
    output, _, _ = _extract_json_with_diagnostics(text)
    return output


def _extract_json_with_diagnostics(text: str) -> tuple[Any, list[dict[str, Any]], list[dict[str, Any]]]:
    stripped = (text or "").strip()
    for candidate in _json_candidates(stripped):
        try:
            output = json.loads(candidate)
            warnings = []
            if candidate.strip() != stripped:
                warnings.append(
                    {
                        "field": "$",
                        "type": "prose_wrapped_json",
                        "message": "A JSON object was extracted from output that also contained non-JSON text.",
                    }
                )
            return output, warnings, []
        except json.JSONDecodeError:
            continue
    errors = []
    if _looks_like_reasoning_prose(stripped):
        errors.append(
            {
                "field": "$",
                "type": "reasoning_prose",
                "message": "The model produced reasoning or explanation text instead of a JSON object.",
            }
        )
    return text, [], errors


def _json_candidates(text: str) -> list[str]:
    stripped = (text or "").strip()
    candidates: list[str] = []
    if stripped:
        candidates.append(stripped)
    for match in re.finditer(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL | re.IGNORECASE):
        fenced = match.group(1).strip()
        if fenced:
            candidates.append(fenced)
    balanced = _balanced_json_objects(stripped)
    candidates.extend(reversed(balanced))
    greedy = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if greedy:
        candidates.append(greedy.group(0))
    return list(dict.fromkeys(candidates))


def _balanced_json_objects(text: str) -> list[str]:
    objects: list[str] = []
    start: int | None = None
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
            continue
        if char == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                objects.append(text[start : index + 1])
                start = None
    return objects


def _looks_like_reasoning_prose(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    markers = (
        "<think",
        "let me",
        "we need",
        "i need",
        "reasoning",
        "analysis",
        "therefore",
        "step by step",
        "the answer",
    )
    return any(marker in lowered for marker in markers) or ("\n" in text and "{" not in text)


def _semantic_ok(output: Any, expected: Any) -> bool | None:
    if not expected:
        return None
    if not isinstance(output, dict):
        return False
    values = set(_flatten_values(output))
    if isinstance(expected, dict):
        return all(output.get(k) == v for k, v in expected.items())
    if not isinstance(expected, list):
        expected = [expected]
    return any(item in values for item in expected)


def _apply_semantic_check(validation: dict[str, Any], expected: Any) -> bool | None:
    semantic_ok = _semantic_ok(validation.get("output"), expected)
    if semantic_ok is False and validation["schema_valid"]:
        validation["status"] = "REVIEW"
        validation["errors"].append({"field": "$", "type": "semantic_mismatch", "expected": expected})
    return semantic_ok


def _flatten_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        values: list[Any] = []
        for child in value.values():
            values.extend(_flatten_values(child))
        return values
    if isinstance(value, list):
        values = []
        for child in value:
            values.extend(_flatten_values(child))
        return values
    return [value]


if __name__ == "__main__":
    raise SystemExit(main())
