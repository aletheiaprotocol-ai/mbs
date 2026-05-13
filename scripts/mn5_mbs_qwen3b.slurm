#!/usr/bin/env bash
#SBATCH -J mbs_qwen3b
#SBATCH -A ehpc714
#SBATCH -q acc_ehpc
#SBATCH -p acc_ehpc
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=20
#SBATCH --gres=gpu:1
#SBATCH --time=02:00:00
#SBATCH --output=/gpfs/scratch/ehpc714/mbs_logs/mbs_qwen3b_%j.out
#SBATCH --error=/gpfs/scratch/ehpc714/mbs_logs/mbs_qwen3b_%j.err

set -euo pipefail
export PYTHONUNBUFFERED=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false

module load bsc mkl intel python/3.12.1 cuda/12.3 >/dev/null 2>&1 || true
source /gpfs/scratch/ehpc714/lk_env/bin/activate

WORK=/gpfs/scratch/ehpc714/mbs_public_release
OUT=/gpfs/scratch/ehpc714/mbs_results/hard_agent_routing/qwen25_3b
mkdir -p "$OUT" /gpfs/scratch/ehpc714/mbs_logs
cd "$WORK"

python scripts/collect_hf_local_responses.py \
  --model-path /gpfs/scratch/ehpc714/models/Qwen2.5-3B-Instruct \
  --model-id Qwen2.5-3B-Instruct \
  --schema examples/hard_agent_routing/schema.json \
  --cases examples/hard_agent_routing/cases.jsonl \
  --mode json_mode \
  --max-new-tokens 256 \
  --temperature 0 \
  --limit 40 \
  --out "$OUT/qwen25_3b_json_mode.responses.jsonl"

python -m mbs.cli adapt-responses \
  --schema examples/hard_agent_routing/schema.json \
  --cases examples/hard_agent_routing/cases.jsonl \
  --responses "$OUT/qwen25_3b_json_mode.responses.jsonl" \
  --model Qwen2.5-3B-Instruct \
  --decoding-mode hf_local_json_mode \
  --out "$OUT/qwen25_3b_json_mode.mbs.json"

python -m mbs.cli report \
  --results "$OUT/qwen25_3b_json_mode.mbs.json" \
  --require-traces \
  --summary-only \
  --out "$OUT/qwen25_3b_json_mode.report.md"

cat "$OUT/qwen25_3b_json_mode.report.md"
