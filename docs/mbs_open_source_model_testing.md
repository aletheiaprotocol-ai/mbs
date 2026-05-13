# MBS Open-Source Model Testing

This workflow tests structured-output behavior across open-source model families
and weights. It is designed for OpenAI-compatible servers such as vLLM.

## Matrix

The starter matrix is in `benchmarks/oss_structured_output_matrix.json` and covers:

- Qwen: 3B, 14B, 72B-AWQ
- Llama: 8B, 70B-AWQ
- Mixtral: 8x7B, 8x7B-AWQ
- modes: text, JSON mode, tool calling

The matrix is a plan, not evidence. Evidence starts only after response JSONL
files and MBS reports exist.

## Run With A Local Or vLLM Server

Start an OpenAI-compatible server for one model, then collect responses:

```bash
python scripts/collect_azure_openai_responses.py \
  --provider openai-compatible \
  --endpoint http://127.0.0.1:8000 \
  --api-key-env OPENAI_API_KEY \
  --model Qwen/Qwen2.5-14B-Instruct \
  --mode tool_call \
  --schema examples/tool_argument_generation/schema.json \
  --cases examples/tool_argument_generation/cases.jsonl \
  --out results/oss/qwen14b_tool_call.responses.jsonl
```

Then adapt and report:

```bash
mbs adapt-responses \
  --schema examples/tool_argument_generation/schema.json \
  --cases examples/tool_argument_generation/cases.jsonl \
  --responses results/oss/qwen14b_tool_call.responses.jsonl \
  --model Qwen/Qwen2.5-14B-Instruct \
  --decoding-mode tool_call \
  --out results/oss/qwen14b_tool_call.mbs.json

mbs report --results results/oss/*.mbs.json --require-traces --summary-only
mbs triage --results results/oss/*.mbs.json --max-failure-examples 40
```

## When Fine-Tuning Is Justified

Fine-tuning is not the first response to failure. First classify failures:

1. API/server failures: fix infrastructure.
2. `invalid_json` in text mode only: use JSON/tool mode or stronger prompt.
3. `missing_required_key`, `wrong_type`, `invalid_enum`: evaluate constrained decoding or tool calling.
4. repeated `semantic_mismatch` on valid JSON: consider task-specific fine-tuning.

Fine-tuning becomes justified only when failures persist across prompt fixes,
JSON/tool modes, and repeated hard cases, and when the target behavior is stable
enough to train against.