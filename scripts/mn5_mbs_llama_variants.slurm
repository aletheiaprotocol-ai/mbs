#!/usr/bin/env bash
#SBATCH -J mbs_llama_variants
#SBATCH -A ehpc714
#SBATCH -q acc_ehpc
#SBATCH -p acc_ehpc
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=20
#SBATCH --gres=gpu:1
#SBATCH --time=04:00:00
#SBATCH --output=/gpfs/scratch/ehpc714/mbs_logs/mbs_llama_variants_%j.out
#SBATCH --error=/gpfs/scratch/ehpc714/mbs_logs/mbs_llama_variants_%j.err

set -euo pipefail
export PYTHONUNBUFFERED=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false

MODEL_PATH=/gpfs/scratch/ehpc714/models/Llama-3.1-8B-Instruct
MODEL_ID=Llama-3.1-8B-Instruct
MODEL_KEY=llama31_8b_variants

module load bsc mkl intel python/3.12.1 cuda/12.3 >/dev/null 2>&1 || true
source /gpfs/scratch/ehpc714/lk_env/bin/activate

WORK=/gpfs/scratch/ehpc714/mbs_public_release
OUT=/gpfs/scratch/ehpc714/mbs_results/hard_agent_routing/${MODEL_KEY}
mkdir -p "$OUT" /gpfs/scratch/ehpc714/mbs_logs
cd "$WORK"

run_variant() {
  local mode="$1"
  local prompt_style="$2"
  local max_tokens="$3"
  local variant="${mode}_${prompt_style}_${max_tokens}tok"

  python scripts/collect_hf_local_responses.py \
    --model-path "$MODEL_PATH" \
    --model-id "$MODEL_ID" \
    --schema examples/hard_agent_routing/schema.json \
    --cases examples/hard_agent_routing/cases.jsonl \
    --mode "$mode" \
    --prompt-style "$prompt_style" \
    --max-new-tokens "$max_tokens" \
    --temperature 0 \
    --limit 40 \
    --out "$OUT/${MODEL_KEY}_${variant}.responses.jsonl"

  python -m mbs.cli adapt-responses \
    --schema examples/hard_agent_routing/schema.json \
    --cases examples/hard_agent_routing/cases.jsonl \
    --responses "$OUT/${MODEL_KEY}_${variant}.responses.jsonl" \
    --model "$MODEL_ID" \
    --decoding-mode "hf_local_${variant}" \
    --out "$OUT/${MODEL_KEY}_${variant}.mbs.json"
}

run_variant json_mode default 256
run_variant json_mode compact 256
run_variant json_mode explicit_keys 256
run_variant text compact 256
run_variant json_mode compact 512

python -m mbs.cli report \
  --results "$OUT/*.mbs.json" \
  --require-traces \
  --summary-only \
  --out "$OUT/${MODEL_KEY}.report.md"

python scripts/analyze_mbs_failures.py \
  --results "$OUT/*.mbs.json" \
  --cases examples/hard_agent_routing/cases.jsonl \
  --out-md "$OUT/${MODEL_KEY}.failure_analysis.md" \
  --out-json "$OUT/${MODEL_KEY}.failure_analysis.json" \
  --out-csv "$OUT/${MODEL_KEY}.failure_analysis.csv"

cat "$OUT/${MODEL_KEY}.report.md"