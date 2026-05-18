"""Collect local Hugging Face model responses for MBS.

This is a no-server fallback for HPC systems where vLLM/FastAPI are not
installed. It writes the same provider JSONL shape consumed by
`mbs adapt-responses`.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect local HF model responses for MBS")
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--model-id", default=None)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--mode", choices=["text", "json_mode"], default="text")
    parser.add_argument(
        "--prompt-style",
        choices=["default", "compact", "explicit_keys"],
        default="default",
        help="Prompt template variant for debugging format sensitivity.",
    )
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--device-map",
        default="single",
        help="Use 'single' to load on one CUDA device without Accelerate auto memory balancing.",
    )
    parser.add_argument("--dtype", default="auto")
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_id = args.model_id or args.model_path
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8-sig"))
    cases = load_jsonl(args.cases)
    if args.limit > 0:
        cases = cases[: args.limit]

    tokenizer = AutoTokenizer.from_pretrained(args.model_path, local_files_only=True, trust_remote_code=True)
    load_kwargs: dict[str, Any] = {
        "local_files_only": True,
        "trust_remote_code": True,
        "torch_dtype": dtype_arg(args.dtype, torch),
    }
    if args.device_map != "single":
        load_kwargs["device_map"] = args.device_map
    model = AutoModelForCausalLM.from_pretrained(args.model_path, **load_kwargs)
    if args.device_map == "single" and torch.cuda.is_available():
        model = model.to("cuda")
    model.eval()

    rows: list[dict[str, Any]] = []
    for idx, case in enumerate(cases):
        started = time.time()
        try:
            prompt = build_prompt(schema, case, args.mode, args.prompt_style)
            messages = [
                {"role": "system", "content": "Return only valid JSON matching the requested schema."},
                {"role": "user", "content": prompt},
            ]
            if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
                text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            else:
                text = messages[0]["content"] + "\n" + messages[1]["content"] + "\nAssistant:"
            inputs = tokenizer(text, return_tensors="pt").to(model.device)
            with torch.no_grad():
                output = model.generate(
                    **inputs,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=args.temperature > 0,
                    temperature=args.temperature if args.temperature > 0 else None,
                    pad_token_id=tokenizer.eos_token_id,
                )
            generated = output[0][inputs["input_ids"].shape[1] :]
            response = tokenizer.decode(generated, skip_special_tokens=True).strip()
            row = {
                "case_id": case.get("id", case.get("case_id", idx)),
                "input": case.get("input", ""),
                "model": model_id,
                "decoding_mode": f"hf_local_{args.mode}",
                "prompt_style": args.prompt_style,
                "response": response,
                "latency_s": round(time.time() - started, 4),
                "tokens": {"output": int(generated.numel())},
            }
        except Exception as exc:
            row = {
                "case_id": case.get("id", case.get("case_id", idx)),
                "input": case.get("input", ""),
                "model": model_id,
                "decoding_mode": f"hf_local_{args.mode}",
                "prompt_style": args.prompt_style,
                "response": "",
                "provider_error": type(exc).__name__,
                "provider_error_message": str(exc),
                "latency_s": round(time.time() - started, 4),
            }
        rows.append(row)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"out": str(out), "rows": len(rows), "model": model_id, "mode": args.mode, "prompt_style": args.prompt_style},
            indent=2,
        )
    )
    return 0


def build_prompt(schema: dict[str, Any], case: dict[str, Any], mode: str, prompt_style: str = "default") -> str:
    extra = ""
    if mode == "json_mode":
        extra = "\nYou must output one JSON object and no prose."
    if prompt_style == "compact":
        properties = schema.get("properties", {})
        action_values = properties.get("action", {}).get("enum", [])
        priority_values = properties.get("priority", {}).get("enum", [])
        return (
            "Return exactly one JSON object. No markdown. No explanation.\n"
            "Required keys: action, priority, requires_human, customer_visible, risk_tags, rationale.\n"
            f"Allowed action values: {action_values}.\n"
            f"Allowed priority values: {priority_values}.\n"
            f"Case: {case.get('input', '')}"
        )
    if prompt_style == "explicit_keys":
        return (
            "You are a support-routing classifier. Fill this JSON object only:\n"
            '{"action":"","priority":"","requires_human":false,"customer_visible":true,"risk_tags":[],"rationale":""}\n'
            f"Valid schema: {json.dumps(schema, ensure_ascii=False)}\n"
            f"Customer message: {case.get('input', '')}{extra}"
        )
    return (
        "Choose the correct structured tool-routing output for this case.\n"
        f"Schema: {json.dumps(schema, ensure_ascii=False)}\n"
        f"Case: {case.get('input', '')}"
        f"{extra}"
    )


def dtype_arg(value: str, torch: Any) -> Any:
    if value == "auto":
        return "auto"
    if value in {"float16", "fp16"}:
        return torch.float16
    if value in {"bfloat16", "bf16"}:
        return torch.bfloat16
    if value in {"float32", "fp32"}:
        return torch.float32
    raise ValueError(f"Unsupported dtype: {value}")


def load_jsonl(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
