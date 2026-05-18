# Model Coverage Plan

## Goal

Build durable evidence across model families, weights, quantization levels, providers, and endpoint modes without wasting compute.

## Families to cover

- Qwen
- Llama
- Mistral
- Mixtral
- Gemma
- Phi
- DeepSeek distills
- StableLM
- TinyLlama
- Yi
- OLMo
- Granite
- Falcon if available
- Command-R / Cohere if available
- OpenAI / Azure deployments
- Anthropic if available
- Gemini if available
- local OSS endpoints
- vLLM / Ollama / LM Studio / OpenAI-compatible endpoints

## Weight bands

- Tiny: under 2B.
- Small: 2B-8B.
- Medium: 9B-20B.
- Large: 21B-70B.
- 70B+ where feasible.

## Quantization coverage

- Non-quantized where feasible.
- 8-bit where feasible.
- 4-bit/AWQ/GPTQ/GGUF where feasible.
- Provider-hosted opaque quantization recorded as provider-managed.

## Minimum pilot matrix

For ENTERPRISE PILOT READY, test at least:
- 3 closed/provider deployments;
- 8 OSS families;
- 3 weight bands;
- 2 quantization modes;
- text and JSON-compatible modes;
- at least one tool/function-call provider mode.

## Production matrix target

For ENTERPRISE PRODUCTION READY, test:
- 5+ closed/provider deployments if available;
- 12+ OSS families where available;
- tiny/small/medium/large/70B+ where feasible;
- quantized and non-quantized variants where feasible;
- repeated seeds and regression reruns.

## Required metrics per model

- valid JSON rate;
- schema-valid rate;
- semantic correctness;
- enum accuracy;
- required-key accuracy;
- wrong-type rate;
- extra-key rate;
- source citation correctness when applicable;
- human-review correctness when applicable;
- retry improvement;
- retry regressions;
- cost per valid output;
- cost per semantically correct output;
- latency;
- trace coverage;
- failure taxonomy;
- model/provider/version;
- prompt/contract version;
- schema version;
- benchmark case version.

## Compute discipline

- Start with smoke subsets to catch broken prompts, endpoint errors, schema bugs, and parser bugs.
- Promote only clean configs to full matrix runs.
- Cache models and datasets.
- Deduplicate repeated failures by model/schema/mode.
- Use small models to find prompt/schema defects before spending 70B+ compute.
- Run large models on representative hard packs, not every trivial row.