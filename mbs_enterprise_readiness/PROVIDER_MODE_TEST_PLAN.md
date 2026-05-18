# Provider Mode Test Plan

## Goal

Measure MBS behavior across provider output modes and MBS contract combinations.

## Required modes

1. Plain text output.
2. JSON mode.
3. Function/tool calling.
4. MBS contract + text.
5. MBS contract + JSON mode.
6. MBS contract + tool calling.
7. No retry.
8. One retry.
9. Failure-specific retry.
10. Semantic retry.
11. Human-review flag routing.

## Required provider classes

- Azure OpenAI.
- OpenAI direct if available.
- Anthropic if available.
- Gemini if available.
- Cohere/Command-R if available.
- vLLM OpenAI-compatible.
- Ollama.
- LM Studio.
- Other OpenAI-compatible local/HPC endpoint.

## Required comparisons

- provider native structured mode vs MBS contract;
- MBS contract without provider JSON support;
- retry vs no retry;
- generic retry vs failure-specific retry;
- semantic retry vs schema-only retry;
- tool-call argument reliability vs JSON object reliability.

## Required artifacts per run

- raw outputs;
- parsed outputs;
- traces;
- command log;
- model list;
- model versions;
- schema versions;
- case versions;
- report summary;
- failure examples;
- retry comparison;
- cost/latency summary;
- infra failure classification;
- software bug classification;
- benchmark design issue classification;
- real model behavior classification.

## Acceptance for pilot

- At least one closed provider and one OSS endpoint per selected workflow.
- Text and JSON-compatible modes tested.
- Retry/no-retry comparison present.
- Infra failures separated from model behavior.

## Acceptance for production

- Multiple closed providers and OSS endpoints.
- Tool/function call mode where supported.
- Cost/latency distributions.
- Row-level failure maps.
- Regression reruns across versions.