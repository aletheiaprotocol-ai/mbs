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

## Evidence Rule

Do not claim OSS model reliability results from queued jobs or infrastructure-failed jobs. OSS evidence requires completed `.mbs.json` result files, trace coverage, and report summaries under `/gpfs/scratch/ehpc714/mbs_results/hard_agent_routing/`.

## Next Step

Rerun the 40-case MN5 jobs after the `single` device-map fix, then download completed reports and compare per-case failures by family and weight.
