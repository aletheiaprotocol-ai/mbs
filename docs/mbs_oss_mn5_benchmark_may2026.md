# MBS OSS Model Benchmark on MN5 — May 2026

This document tracks open-source-model runs for the hard structured agent-routing fixture on MareNostrum 5 (MN5).

## Scope

Schema: `examples/hard_agent_routing/schema.json`

Cases: `examples/hard_agent_routing/cases.jsonl` (40 hard cases)

Collector: `scripts/collect_hf_local_responses.py`

Runner scripts:

- `scripts/mn5_mbs_qwen3b.slurm`
- `scripts/mn5_mbs_hf_model.slurm`
- `scripts/mn5_submit_mbs_hf_jobs.sh`

## Current Status

The initial additional OSS jobs were submitted for:

- `Qwen2.5-7B-Instruct`
- `Qwen2.5-14B-Instruct`
- `Llama-3.1-8B-Instruct`
- `Mistral-7B-Instruct-v0.3`

Those first jobs failed before model behavior was measured because the MN5 environment loaded a `psutil` build that could not import `libhdf5.so.310` through Accelerate's automatic device-map memory-balancing path.

Classification: **infrastructure failure, not model behavior evidence**.

Fix applied: the local HF collector now defaults to `--device-map single`, loading the model directly on one CUDA device and avoiding Accelerate auto memory balancing unless explicitly requested.

After the fix, the 40-case jobs completed and produced MBS result files for all
four submitted OSS models.

## 40-Case MN5 Result Summary

Scope: 40 hard structured support-routing cases, `hf_local_json_mode`, one H100
GPU per job, local cached Hugging Face models.

| model | rows | JSON valid | schema valid | semantic correct | top failures |
| --- | ---: | ---: | ---: | ---: | --- |
| `Qwen2.5-7B-Instruct` | 40 | 1.0000 | 0.9250 | 0.2250 | `semantic_mismatch:28`, `invented_enum:3` |
| `Qwen2.5-14B-Instruct` | 40 | 1.0000 | 0.9500 | 0.2000 | `semantic_mismatch:30`, `invented_enum:2` |
| `Mistral-7B-Instruct-v0.3` | 40 | 1.0000 | 0.8250 | 0.2000 | `semantic_mismatch:28`, `invented_enum:7` |
| `Llama-3.1-8B-Instruct` | 40 | 0.0000 | 0.0000 | 0.0000 | `invalid_json:40` |

Aggregate across the four OSS jobs:

- files: 4
- input rows: 160
- behavior rows: 160
- infrastructure failures: 0
- `semantic_mismatch`: 86
- `invalid_json`: 40
- `invented_enum`: 12
- passing rows: 22

Interpretation: the Qwen and Mistral jobs mostly produced parseable JSON, but
semantic routing correctness remained low. Llama 3.1 8B did not produce valid
JSON under this collector/prompt/mode combination, so its failure is a format
failure under the tested settings, not a semantic-routing measurement.

## Evidence Rule

Do not claim OSS model reliability from queued jobs or infrastructure-failed jobs. OSS evidence requires completed `.mbs.json` result files, trace coverage, and report summaries under `/gpfs/scratch/ehpc714/mbs_results/hard_agent_routing/`.

## Next Step

Next evidence steps:

- run additional decoding/prompt variants for Llama to separate prompt-format
	mismatch from model capability;
- add Qwen 3B and larger cached/AWQ models to the same 40-case fixture;
- compare repeated semantic mismatch clusters with `scripts/analyze_mbs_failures.py`.
