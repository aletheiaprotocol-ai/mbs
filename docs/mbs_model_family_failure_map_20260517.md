# MBS Model/Provider Failure Map — 2026-05-17

This note maps the current evidence without promoting dry-run scaffolding into model-behavior claims.

## Evidence included

- `benchmarks/results/nested_azure_gpt55_sweden_pilot/manifest.json`
- `benchmarks/results/provider_matrix_artifact_index_20260517.json`
- `docs/mbs_azure_provider_benchmark_may2026.md`
- `docs/mbs_mn5_vs_azure_comparison_may2026.md`
- `docs/mbs_nested_provider_matrix_may2026.md`
- `benchmarks/results/leonardo_mbs_hpc_20260517/summary.json`
- `docs/mbs_leonardo_hpc_evidence_20260517.md`

## Current nested-tool run

| Family/provider | Model/deployment | Mode | Rows | Infra failures | Schema valid | Semantic correct | Clean JSON | Gate | Main failure cluster |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Azure OpenAI | `gpt-5.5` Sweden deployment | tool call | 25 | 0 | 1.0000 | 0.8800 | 1.0000 | PASS | `semantic_mismatch:3` |
| Azure OpenAI | `gpt-5.5` wrong endpoint/key mapping | tool call | 25 | 25 | 0.0000 | 0.0000 | 0.0000 | FAIL | `DeploymentNotFound` infrastructure failure; excluded from model behavior evidence |

## Prior documented hard-routing evidence

| Family/provider | Model/deployment | Fixture | Rows | Infra failures | Schema valid | Semantic correct | Clean JSON | Main failure cluster |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Azure OpenAI | `gpt-5.5` | hard agent routing, 40 cases x 3 modes | 120 | 0 | 1.0000 | 0.3250 | 1.0000 | `semantic_mismatch:81` |
| Azure OpenAI | `gpt-5-nano` | hard agent routing, 40 cases x 3 modes | 120 | 0 | 0.0333 | 0.0167 | 0.0333 | `invalid_json:116`, `semantic_mismatch:2` |
| MN5/HF local | `Qwen2.5-7B-Instruct` | hard agent routing, JSON mode | 40 | 0 | 0.9250 | 0.2250 | 1.0000 | `semantic_mismatch:28`, `invented_enum:3` |
| MN5/HF local | `Qwen2.5-14B-Instruct` | hard agent routing, JSON mode | 40 | 0 | 0.9500 | 0.2000 | 1.0000 | `semantic_mismatch:30`, `invented_enum:2` |
| MN5/HF local | `Mistral-7B-Instruct-v0.3` | hard agent routing, JSON mode | 40 | 0 | 0.8250 | 0.2000 | 1.0000 | `semantic_mismatch:28`, `invented_enum:7` |
| MN5/HF local | `Llama-3.1-8B-Instruct` | hard agent routing, JSON mode | 40 | 0 | 0.0000 | 0.0000 | 0.0000 | `invalid_json:40` |

## Live Leonardo HF-local nested evidence

| Family/provider | Model | Fixture | Rows | Infra failures | Schema valid | Semantic correct | Clean JSON | Gate | Main failure cluster |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Leonardo/HF local | `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | nested tool routing, smoke | 25 | 0 | 0.0400 | 0.0000 | 0.0000 | FAIL | `invalid_json:24`, `semantic_mismatch:1` |
| Leonardo/HF local | `Qwen/Qwen2.5-0.5B-Instruct` | nested tool routing, smoke | 25 | 0 | 0.9600 | 0.1600 | 0.3600 | FAIL | `semantic_mismatch:20`, `invented_enum:1` |
| Leonardo/HF local | `Qwen/Qwen2.5-1.5B-Instruct` | nested tool routing, smoke | 25 | 0 | 0.7600 | 0.2400 | 0.8800 | FAIL | `semantic_mismatch:13`, `invented_enum:3`, `nested_schema_error:3` |
| Leonardo/HF local | `Qwen/Qwen2.5-3B-Instruct` | nested tool routing, smoke | 25 | 0 | 0.8800 | 0.3200 | 1.0000 | FAIL | `semantic_mismatch:14`, `invented_enum:2`, `missing_or_extra_keys:1` |
| Leonardo/HF local | `mistralai/Mistral-7B-Instruct-v0.3` | nested tool routing, smoke | 25 | 0 | 0.3600 | 0.2400 | 1.0000 | FAIL | `nested_schema_error:9`, `invented_enum:6`, `semantic_mismatch:3` |
| Leonardo/HF local | `microsoft/Phi-3.5-mini-instruct` | nested tool routing, smoke | 25 | 25 | 0.0000 | 0.0000 | 0.0000 | FAIL | Infrastructure/local-load failures; excluded from behavior evidence |
| Leonardo/HF local | `ibm-granite/granite-3.1-2b-instruct` | nested tool routing, smoke | 25 | 0 | 0.9600 | 0.3600 | 1.0000 | FAIL | Semantic mismatch dominates |
| Leonardo/HF local | `Qwen/Qwen2.5-7B-Instruct` | nested tool routing, targeted medium | 10 | 0 | 0.8000 | 0.6000 | 1.0000 | FAIL | `semantic_mismatch:2`, `invented_enum:1`, `missing_or_extra_keys:1` |
| Leonardo/HF local | `Qwen/Qwen2.5-14B-Instruct` | nested tool routing, targeted medium | 8 | 0 | 0.8750 | 0.7500 | 1.0000 | FAIL | Near-threshold semantic behavior but still below gate |
| Leonardo/HF local | `mistralai/Mistral-Nemo-Instruct-2407` | nested tool routing, targeted medium | 8 | 0 | 0.8750 | 0.3750 | 1.0000 | FAIL | Semantic mismatch dominates despite clean JSON |
| Leonardo/HF local | `microsoft/phi-4` | nested tool routing, targeted medium | 8 | 0 | 1.0000 | 0.6250 | 0.0000 | FAIL | Schema extractable but not clean JSON; semantic misses remain |
| Leonardo/HF local | `NousResearch/Meta-Llama-3.1-70B-Instruct` | nested tool routing, 4-bit 70B large | 8 | 0 | 1.0000 | 0.5000 | 0.0000 | FAIL | 4-bit load/inference succeeded; semantic mismatch and non-clean JSON remain |
| Leonardo/HF local | `Qwen/Qwen2.5-14B-Instruct` | compact prompt comparison | 12 | 0 | 0.5000 | 0.2500 | 1.0000 | FAIL | Compact prompt improved clean JSON but degraded schema/semantic rates versus nested targeted medium run |
| Leonardo/HF local | `01-ai/Yi-1.5-9B-Chat` | compact prompt comparison | 12 | 0 | 0.3333 | 0.0833 | 0.9167 | FAIL | Compact prompt produced mostly clean JSON but weak schema/semantic correctness |
| Leonardo/HF local | `NousResearch/Meta-Llama-3.1-70B-Instruct` | compact prompt comparison | 12 | 12 | 0.0000 | 0.0000 | 0.0000 | FAIL | Infrastructure-only offload/GPU RAM load failure in multi-model compact job; excluded from behavior evidence |
| Leonardo/HF local | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | nested tool routing, targeted medium | 10 | 0 | 0.0000 | 0.0000 | 0.0000 | FAIL | Reasoning/prose output did not produce clean schema JSON |
| Leonardo/HF local | `01-ai/Yi-1.5-6B-Chat` | nested tool routing, targeted medium | 10 | 0 | 0.9000 | 0.4000 | 0.0000 | FAIL | Extractable schema often valid but not clean JSON; semantic mismatch remains high |
| Leonardo/HF local | `ibm-granite/granite-3.1-8b-instruct` | nested tool routing, targeted medium | 10 | 0 | 1.0000 | 0.5000 | 1.0000 | FAIL | Semantic mismatch dominates |

## Dry-run-only plans not counted as behavior evidence

- `benchmarks/results/nested_lm_studio_dry_run/`
- `benchmarks/results/nested_ollama_tiny_dry_run/`
- `benchmarks/results/nested_ollama_small_dry_run/`
- `benchmarks/results/nested_vllm_openai_compatible_dry_run/`
- `benchmarks/results/nested_hpc_large_dry_run/`

These artifacts prove safe collection planning only. They do not prove model behavior until reviewed response JSONL is collected and classified.

## Current blockers

- Local OSS endpoints: Ollama, LM Studio, and vLLM endpoints were inactive, but Leonardo HF-local `hpc` execution is now available as an alternate OSS path.
- Five-family OSS matrix: partially started via Leonardo; needs additional cached-family runs and standard MBS cross-checks.
- Large/HPC matrix: Leonardo submission path is working and 70B 4-bit behavior evidence exists from job `41800766`; compact 70B should be retried only as a single-model/fresh-process job because multi-model compact job `41807858` hit an infra-only offload/GPU RAM load error.
- Anthropic/Gemini/Cohere matrix: `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`/`GOOGLE_API_KEY`, and `COHERE_API_KEY` were absent in the local environment.
- Enterprise Pilot Ready still requires broader provider/OSS/HPC evidence, remote CI run evidence, and formal compliance/security review.