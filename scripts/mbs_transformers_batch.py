#!/usr/bin/env python3
"""Run a full MBS row matrix after loading one Transformers model once.

This is the preferred HPC runner for larger models. The older single-row
runner is still useful for repair jobs, but repeatedly loading a 30B/70B model
for every schema row burns wall time and queue slots.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from mbs.bench import first_failure_type, language_label, load_jsonl, summarize
from mbs.compiler import canonical_json, compile_schema, estimate_tokens, load_schema
from mbs.trace import create_trace

from scripts import mbs_transformers_bench as single


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run batched MBS benchmark rows with one model load")
    parser.add_argument("--model-list", required=True, help="model_id or model_id<TAB>local_path rows")
    parser.add_argument("--model-index", type=int, required=True)
    parser.add_argument("--matrix-list", help="schema/prompt TSV rows")
    parser.add_argument("--lang-list", help="language/prompt TSV rows")
    parser.add_argument("--mode", choices=["matrix", "lang"], required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--run-id", default=os.environ.get("SLURM_ARRAY_JOB_ID") or os.environ.get("SLURM_JOB_ID"))
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--retries", type=int, default=0)
    parser.add_argument(
        "--retry-policy",
        choices=["schema", "semantic"],
        default=os.environ.get("MBS_RETRY_POLICY", "semantic"),
    )
    parser.add_argument(
        "--retry-adoption",
        choices=["best", "latest"],
        default=os.environ.get("MBS_RETRY_ADOPTION", "best"),
    )
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--dtype", choices=["auto", "bf16", "fp16", "fp32"], default="auto")
    parser.add_argument("--chat-template", choices=["auto", "never"], default="auto")
    args = parser.parse_args(argv)
    args.local_files_only = args.local_files_only or single._truthy_env("MBS_LOCAL_FILES_ONLY") or single._truthy_env(
        "HF_HUB_OFFLINE"
    )

    model_label, model_target = _load_model_row(args.model_list, args.model_index)
    rows = _load_work_rows(args)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        import torch
        from transformers import AutoTokenizer
    except ModuleNotFoundError as exc:
        _write_batch_infra_failures(args, rows, model_label, model_target, "missing_dependency", exc)
        return 0

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_target,
            trust_remote_code=True,
            local_files_only=args.local_files_only,
        )
        torch_dtype = single._resolve_dtype(torch, args.dtype)
        model = single._load_generation_model(
            model_target,
            torch_dtype=torch_dtype,
            local_files_only=args.local_files_only,
        )
    except Exception as exc:
        _write_batch_infra_failures(args, rows, model_label, model_target, "model_load_failed", exc)
        return 0

    model.eval()
    written = []
    for row_index, row in enumerate(rows):
        payload = _run_row(args, model, tokenizer, model_label, model_target, row, row_index)
        out_path = _out_path(args, model_label, row["row_id"], row_index)
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(str(out_path))
        print(json.dumps({"row_id": row["row_id"], "summary": payload["summary"]}, ensure_ascii=False))

    print(json.dumps({"model": model_label, "mode": args.mode, "files_written": len(written)}, indent=2))
    return 0


def _load_model_row(path: str | Path, index: int) -> tuple[str, str]:
    rows = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t", 1)
        label = parts[0].strip()
        target = parts[1].strip() if len(parts) > 1 and parts[1].strip() else label
        rows.append((label, target))
    if index < 0 or index >= len(rows):
        raise IndexError(f"model-index {index} outside model list of {len(rows)} rows")
    return rows[index]


def _load_work_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    if args.mode == "matrix":
        if not args.matrix_list:
            raise ValueError("--matrix-list is required for --mode matrix")
        rows = []
        for raw in Path(args.matrix_list).read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            row_id, schema_path, cases_path, prompt_style = line.split("\t")[:4]
            rows.append(
                {
                    "row_id": row_id,
                    "schema_path": schema_path,
                    "cases_path": cases_path,
                    "prompt_style": prompt_style or "full",
                    "input_language": "",
                    "output_language": "",
                    "contract_language": "",
                }
            )
        return rows

    if not args.lang_list:
        raise ValueError("--lang-list is required for --mode lang")
    rows = []
    for raw in Path(args.lang_list).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        row_id, schema_path, cases_path, prompt_style, input_language, output_language, contract_language = parts[:7]
        rows.append(
            {
                "row_id": row_id,
                "schema_path": schema_path,
                "cases_path": cases_path,
                "prompt_style": prompt_style or "full",
                "input_language": input_language,
                "output_language": output_language,
                "contract_language": contract_language,
            }
        )
    return rows


def _run_row(
    args: argparse.Namespace,
    model: Any,
    tokenizer: Any,
    model_label: str,
    model_target: str,
    row: dict[str, str],
    row_index: int,
) -> dict[str, Any]:
    schema = load_schema(row["schema_path"])
    cases = load_jsonl(row["cases_path"])
    contract = compile_schema(
        schema,
        format=row["prompt_style"],
        input_language=row.get("input_language") or None,
        output_language=row.get("output_language") or None,
        contract_language=row.get("contract_language") or None,
    )
    lang_label = language_label(
        row.get("input_language") or None,
        row.get("output_language") or None,
        row.get("contract_language") or None,
    )

    result_rows: list[dict[str, Any]] = []
    for case_index, case in enumerate(cases):
        started = time.time()
        prompt = single._build_prompt(contract["prompt"], case.get("input", ""))
        case_args = _case_args(args, row, row_index, case_index)
        try:
            (
                raw_text,
                output,
                validation,
                semantic_ok,
                generated_tokens,
                used_chat_template,
                retry_count,
                attempts,
            ) = single._run_with_retries(model, tokenizer, schema, prompt, case, case_args)
        except Exception as exc:
            result_rows.append(single._generation_failure_row(case_args, schema, contract, case, case_index, started, exc, model_label))
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
        result_rows.append(
            {
                "case_id": case.get("id", case_index),
                "model": model_label,
                "prompt_style": row["prompt_style"],
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

    return {
        "schema": row["schema_path"],
        "cases": row["cases_path"],
        "model": model_label,
        "load_target": model_target,
        "prompt_style": row["prompt_style"],
        "decoding_mode": single._payload_decoding_mode(result_rows),
        "language": lang_label,
        "chat_template": args.chat_template,
        "retries": args.retries,
        "retry_policy": args.retry_policy,
        "retry_adoption": args.retry_adoption,
        "temperature": args.temperature,
        "seed": None if args.seed is None else args.seed + (row_index * 100000),
        "local_files_only": args.local_files_only,
        "summary": summarize(result_rows),
        "rows": result_rows,
    }


def _case_args(args: argparse.Namespace, row: dict[str, str], row_index: int, case_index: int) -> argparse.Namespace:
    seed = None if args.seed is None else args.seed + (row_index * 100000) + (case_index * 1000)
    return argparse.Namespace(
        schema=row["schema_path"],
        cases=row["cases_path"],
        model="",
        model_label="",
        out="",
        prompt_style=row["prompt_style"],
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        seed=seed,
        retries=args.retries,
        retry_policy=args.retry_policy,
        retry_adoption=args.retry_adoption,
        local_files_only=args.local_files_only,
        input_language=row.get("input_language") or None,
        output_language=row.get("output_language") or None,
        contract_language=row.get("contract_language") or None,
        dtype=args.dtype,
        chat_template=args.chat_template,
    )


def _write_batch_infra_failures(
    args: argparse.Namespace,
    rows: list[dict[str, str]],
    model_label: str,
    model_target: str,
    failure_type: str,
    exc: BaseException,
) -> None:
    for row_index, row in enumerate(rows):
        schema = load_schema(row["schema_path"])
        contract = compile_schema(
            schema,
            format=row["prompt_style"],
            input_language=row.get("input_language") or None,
            output_language=row.get("output_language") or None,
            contract_language=row.get("contract_language") or None,
        )
        row_args = _case_args(args, row, row_index, 0)
        row_args.out = str(_out_path(args, model_label, row["row_id"], row_index))
        row_args.model = model_target
        row_args.model_label = model_label
        single._write_infra_failure(row_args, schema, contract, failure_type, exc, model_label)


def _out_path(args: argparse.Namespace, model_label: str, row_id: str, row_index: int) -> Path:
    model_key = "".join(ch for ch in model_label.replace("/", "_").replace(":", "_") if ch.isalnum() or ch in "._-")
    run_id = args.run_id or str(int(time.time()))
    prefix = "matrix" if args.mode == "matrix" else "lang"
    retry_tag = f"r{args.retries}"
    temp_tag = f"t{str(args.temperature).replace('.', 'p')}"
    seed_tag = "snone" if args.seed is None else f"s{args.seed}"
    return Path(args.out_dir) / f"{prefix}_{row_id}_{model_key}_{run_id}_{args.model_index}_{row_index}_{retry_tag}_{temp_tag}_{seed_tag}.json"


if __name__ == "__main__":
    raise SystemExit(main())
