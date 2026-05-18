# Leonardo HPC MBS Evidence — 2026-05-17

This note records live Leonardo GPU evidence collected for MBS nested structured-output behavior. Raw model responses are review-required and are not public-release artifacts.

## Cluster execution

- SSH target: `asaket00@login.leonardo.cineca.it`
- Account: `AIFAC_F02_151`
- Partition/QOS used: `boost_usr_prod` / `boost_qos_dbg`
- Python environment: `/leonardo_work/AIFAC_F02_151/mbs_env/bin/python`
- Remote runner root: `~/mbs_hpc_matrix`
- Scratch HF cache: `/leonardo_scratch/large/userexternal/asaket00/hf_cache`
- Local artifact mirror: `benchmarks/results/leonardo_mbs_hpc_20260517/`
- Local summary: `benchmarks/results/leonardo_mbs_hpc_20260517/summary.json`
- Standard MBS replay cross-check: `benchmarks/results/leonardo_mbs_hpc_20260517/standard_mbs_crosscheck_summary.json`

## Scripts added

- `scripts/leonardo_mbs_hf_matrix.py` — self-contained HF-local nested structured-output matrix runner.
- `scripts/submit_leonardo_mbs_matrix.sh` — Leonardo SLURM submitter with offline/local-files mode and scratch cache/output support.
- `scripts/submit_leonardo_mbs_matrix.sh` supports `JOB_LABEL` so repeated valid runner suites can write distinct logs/results.
- `scripts/leonardo_check_mbs_env.sh` — Leonardo Python environment discovery helper.
- `scripts/crosscheck_leonardo_hpc_artifacts.py` — local replay/cross-check for mirrored HPC `responses.jsonl` files through standard MBS adapter/report/gate APIs.
- `scripts/summarize_leonardo_hpc_artifacts.py` — local summary generator for mirrored Leonardo `manifest.json` files; skips derived `standard_mbs` artifacts.
- `scripts/submit_leonardo_70b_compact_single.sh` — single-model/fresh-process compact 70B retry wrapper.

## Operational blockers found and handled

| Blocker | Resolution/status |
| --- | --- |
| Initial `boost_qos_dbg` 2-hour submission exceeded QOS wall-time policy | Resubmitted with `00:30:00` debug wall time. |
| Compute nodes could not install packages from PyPI (`Network is unreachable`) | Disabled compute-node installs by default and used existing `/leonardo_work/AIFAC_F02_151/mbs_env/bin/python`. |
| Home/work filesystems were full after login-node downloads | Moved future HF cache and result output to `/leonardo_scratch/large/userexternal/asaket00/`. |
| Compute nodes may not have outbound Hugging Face access | Submitter now sets `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_DATASETS_OFFLINE=1`, and runs `--local-files-only`. |
| Medium-suite login-node download was killed after most medium models cached | Continued with targeted cached-model medium job and recorded remaining large/broad downloads as pending. |
| 70B 4-bit probe was initially unsafe because `bitsandbytes` was absent in the working Leonardo env | Installed `bitsandbytes==0.49.2` into `/leonardo_work/AIFAC_F02_151/mbs_env`; GPU verification on A100 passed in job `41800732`; submitted 70B 4-bit retry job `41800766` with `JOB_LABEL=large_70b_4bit_bnb`. |

## Smoke/medium results mirrored locally

| Suite/job | Model | Behavior rows | Infra failures | Schema valid | Semantic correct | Clean JSON | Gate | Main failure clusters |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `smoke_41796661` | `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | 25 | 0 | 0.04 | 0.00 | 0.00 | FAIL | `invalid_json:24`, `semantic_mismatch:1` |
| `smoke_41796661` | `Qwen/Qwen2.5-0.5B-Instruct` | 25 | 0 | 0.96 | 0.16 | 0.36 | FAIL | `semantic_mismatch:20`, `invented_enum:1` |
| `smoke_41796661` | `Qwen/Qwen2.5-1.5B-Instruct` | 25 | 0 | 0.76 | 0.24 | 0.88 | FAIL | `semantic_mismatch:13`, nested/enumeration errors |
| `smoke_41796661` | `Qwen/Qwen2.5-3B-Instruct` | 25 | 0 | 0.88 | 0.32 | 1.00 | FAIL | `semantic_mismatch:14`, `invented_enum:2`, missing/extra keys |
| `smoke_41796661` | `mistralai/Mistral-7B-Instruct-v0.3` | 25 | 0 | 0.36 | 0.24 | 1.00 | FAIL | nested schema errors, invented enums, semantic mismatches |
| `smoke_41796661` | `microsoft/Phi-3.5-mini-instruct` | 0 | 25 | 0.00 | 0.00 | 0.00 | FAIL | infrastructure/local-load failures; not behavior evidence |
| `smoke_41796661` | `ibm-granite/granite-3.1-2b-instruct` | 25 | 0 | 0.96 | 0.36 | 1.00 | FAIL | semantic mismatch dominates |
| `medium_41796816` | `Qwen/Qwen2.5-7B-Instruct` | 10 | 0 | 0.80 | 0.60 | 1.00 | FAIL | `semantic_mismatch:2`, `invented_enum:1`, missing/extra keys |
| `medium_41800201` | `Qwen/Qwen2.5-14B-Instruct` | 8 | 0 | 0.875 | 0.75 | 1.00 | FAIL | near-threshold semantic performance; remaining schema/semantic misses |
| `medium_41800201` | `mistralai/Mistral-Nemo-Instruct-2407` | 8 | 0 | 0.875 | 0.375 | 1.00 | FAIL | semantic mismatch dominates despite clean JSON |
| `medium_41800201` | `microsoft/phi-4` | 8 | 0 | 1.00 | 0.625 | 0.00 | FAIL | schema extractable but not clean JSON; semantic misses remain |
| `medium_41796816` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | 10 | 0 | 0.00 | 0.00 | 0.00 | FAIL | reasoning/prose output did not produce clean schema JSON |
| `medium_41796816` | `01-ai/Yi-1.5-6B-Chat` | 10 | 0 | 0.90 | 0.40 | 0.00 | FAIL | schema often valid after extraction, but not clean JSON and weak semantic accuracy |
| `medium_41796816` | `ibm-granite/granite-3.1-8b-instruct` | 10 | 0 | 1.00 | 0.50 | 1.00 | FAIL | semantic mismatch dominates |
| `large_70b_4bit_bnb_41800766` | `NousResearch/Meta-Llama-3.1-70B-Instruct` | 8 | 0 | 1.00 | 0.50 | 0.00 | FAIL | 4-bit 70B load/inference succeeded; semantic mismatch and non-clean JSON remain |

## Evidence interpretation

- These are live HPC runs, classified as `hpc` evidence.
- They improve Gate 7 evidence breadth because OSS/HF-local models were executed on real GPUs rather than planned only.
- None of the mirrored Leonardo runs passed the nested gate thresholds yet.
- The 70B 4-bit path is now proven operational on Leonardo with `bitsandbytes==0.49.2`; job `41800766` is behavior evidence, not an infrastructure failure.
- Standard MBS replay cross-check processed 21 mirrored model artifacts: 295 total runs, 16 behavior result rows, 5 infra-failure result rows, 0 missing trace rows, 0 uncheckable result rows, aggregate gate `FAIL`.
- Local regression coverage now includes `tests/test_leonardo_hpc_crosscheck.py` for the runner contract, compact prompt, JSON parsing, gate clean-JSON requirement, BOM-tolerant manifest reading, and cross-check record summaries.
- Compact prompt comparison job `41807858` was mirrored and classified for Qwen-14B, Yi-9B, and 70B Llama 4-bit. Qwen/Yi are behavior evidence but still fail gates; the 70B compact row in this multi-model job is infrastructure-only due an offload/GPU RAM load error after prior models.
- Standard MBS replay cross-check after compact artifacts processed 24 result files: 331 traceable runs, 18 behavior result rows, 6 infra-failure result rows, 0 missing trace rows, 0 uncheckable result rows, aggregate gate `FAIL`.
- The Leonardo runner now writes rows incrementally, prints per-row progress, records matrix `prompt_style`, and attempts model/tokenizer deletion plus CUDA cache cleanup between sequential models for future jobs.
- Local regression coverage also includes `tests/test_leonardo_shell_wrappers.py` for the SLURM submitter and 70B compact single-model wrapper settings.
- `microsoft/Phi-3.5-mini-instruct` produced infrastructure/local-load failures in this job and must not be counted as model behavior evidence.
- The current results strengthen the model-family failure map, but they do not support an Enterprise Pilot Ready label.

## Active/pending HPC work

- Compact prompt comparison job `41807858` with `PROMPT_STYLE=compact` for Qwen-14B, Yi-9B, and 70B Llama 4-bit has been retrieved/classified:
	- `Qwen/Qwen2.5-14B-Instruct`: 12 behavior rows, 0 infra failures, schema-valid `0.5`, semantic-correct `0.25`, clean-JSON `1.0`, gate `FAIL`.
	- `01-ai/Yi-1.5-9B-Chat`: 12 behavior rows, 0 infra failures, schema-valid `0.3333`, semantic-correct `0.0833`, clean-JSON `0.9167`, gate `FAIL`.
	- `NousResearch/Meta-Llama-3.1-70B-Instruct`: 0 behavior rows, 12 infra failures, `ValueError` offload/GPU RAM load error; excluded from 70B behavior claims for this compact job.
- Submit additional targeted cached prompt-style comparison jobs only as single-model/fresh-process runs for large 4-bit models.
- Submitted single-model/fresh-process 70B compact retry `41807878` via `scripts/submit_leonardo_70b_compact_single.sh` with `JOB_LABEL=compact_70b_single_01`, `PROMPT_STYLE=compact`, `LIMIT=8`, and `--load-in-4bit`.
- Use scratch cache/output for all future jobs.
- For larger models, continue with cached/local-files-only paths. `bitsandbytes` is installed and GPU-verified; 70B 4-bit job `41800766` completed as behavior evidence but failed gate thresholds.
