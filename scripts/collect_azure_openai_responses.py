"""Collect chat provider responses as JSONL for MBS.

This script is intentionally outside the `mbs` package. It supports Azure
OpenAI and OpenAI-compatible local/vLLM servers, reads credentials from
environment variables, does not store secrets, and writes provider responses in
the file format consumed by `mbs adapt-responses`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_API_VERSION = "2025-02-01-preview"


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect chat provider responses for MBS adapter benchmarks")
    parser.add_argument("--provider", choices=["azure", "openai-compatible"], default="azure")
    parser.add_argument("--schema", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--mode", choices=["text", "json_mode", "tool_call"], required=True)
    parser.add_argument("--model", default=os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT_SWEDEN") or "azure-openai")
    parser.add_argument("--endpoint", default=os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT_SWEDEN"))
    parser.add_argument("--api-key-env", default="AZURE_OPENAI_API_KEY")
    parser.add_argument("--deployment", default=os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT_SWEDEN"))
    parser.add_argument("--api-version", default=os.getenv("AZURE_OPENAI_API_VERSION", DEFAULT_API_VERSION))
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--seed", type=int, default=333)
    args = parser.parse_args()

    endpoint = (args.endpoint or "").rstrip("/")
    api_key = os.getenv(args.api_key_env, "")
    deployment = args.deployment or args.model
    if not endpoint:
        raise SystemExit("Azure OpenAI endpoint env var is not set")
    if not api_key:
        raise SystemExit(f"Azure OpenAI key env var is not set: {args.api_key_env}")
    if args.provider == "azure" and not deployment:
        raise SystemExit("Azure OpenAI deployment is not set")

    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    cases = load_jsonl(args.cases)
    rows: list[dict[str, Any]] = []
    for idx, case in enumerate(cases):
        started = time.time()
        request_body = build_request(schema, case, args.mode, args.max_tokens, args.seed)
        try:
            response = post_chat(
                args.provider,
                endpoint,
                deployment,
                args.api_version,
                api_key,
                request_body,
                timeout=args.timeout,
                model=args.model,
            )
            row = row_from_response(case, response, args.mode, args.model, round(time.time() - started, 4))
        except Exception as exc:  # keep infrastructure failures explicit in the JSONL
            row = {
                "case_id": case.get("id", case.get("case_id", idx)),
                "input": case.get("input", ""),
                "model": args.model,
                "decoding_mode": args.mode,
                "response": "",
                "provider_error": provider_error_code(exc),
                "provider_error_message": str(exc),
                "latency_s": round(time.time() - started, 4),
            }
        rows.append(row)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "rows": len(rows), "mode": args.mode, "model": args.model}, indent=2))
    return 0


def load_jsonl(path: str) -> list[dict[str, Any]]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def build_request(schema: dict[str, Any], case: dict[str, Any], mode: str, max_tokens: int, seed: int) -> dict[str, Any]:
    system = "Return only the requested structured output. Do not include explanation outside JSON."
    user = (
        "Choose the correct structured tool-routing output for this case.\n"
        f"Schema: {json.dumps(schema, ensure_ascii=False)}\n"
        f"Case: {case.get('input', '')}"
    )
    body: dict[str, Any] = {
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_completion_tokens": max_tokens,
        "seed": seed,
    }
    if mode == "json_mode":
        body["response_format"] = {"type": "json_object"}
    elif mode == "tool_call":
        body["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": "route_support_tool",
                    "description": "Return the structured support-routing tool decision.",
                    "parameters": schema,
                },
            }
        ]
        body["tool_choice"] = {"type": "function", "function": {"name": "route_support_tool"}}
    return body


def post_chat(
    provider: str,
    endpoint: str,
    deployment: str,
    api_version: str,
    api_key: str,
    body: dict[str, Any],
    *,
    timeout: int,
    model: str,
) -> dict[str, Any]:
    if provider == "azure":
        url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        headers = {"Content-Type": "application/json", "api-key": api_key}
    else:
        url = endpoint.rstrip("/") + "/v1/chat/completions"
        body = {**body, "model": model}
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key or 'EMPTY'}"}
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:500]}") from exc


def provider_error_code(exc: Exception) -> str:
    text = str(exc)
    match = re.search(r'"code"\s*:\s*"([^"]+)"', text)
    if match:
        return match.group(1)
    return type(exc).__name__


def row_from_response(case: dict[str, Any], response: dict[str, Any], mode: str, model: str, latency_s: float) -> dict[str, Any]:
    message = response.get("choices", [{}])[0].get("message", {})
    usage = response.get("usage", {})
    row: dict[str, Any] = {
        "case_id": case.get("id", case.get("case_id")),
        "input": case.get("input", ""),
        "model": model,
        "decoding_mode": mode,
        "latency_s": latency_s,
        "tokens": {"output": usage.get("completion_tokens", 0)},
        "finish_reason": response.get("choices", [{}])[0].get("finish_reason"),
    }
    if mode == "tool_call":
        tool_calls = message.get("tool_calls") or []
        row["tool_calls"] = tool_calls
    else:
        row["response"] = message.get("content", "")
    return row


if __name__ == "__main__":
    sys.exit(main())
