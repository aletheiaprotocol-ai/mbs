#!/usr/bin/env bash
#SBATCH -J mbs_hf
#SBATCH -A ehpc714
#SBATCH -q acc_ehpc
#SBATCH -p acc_ehpc
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=20
#SBATCH --gres=gpu:1
#SBATCH --time=03:00:00
#SBATCH --output=/gpfs/scratch/ehpc714/mbs_logs/mbs_hf_%x_%j.out
#SBATCH --error=/gpfs/scratch/ehpc714/mbs_logs/mbs_hf_%x_%j.err

set -euo pipefail
export PYTHONUNBUFFERED=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false

: "${MBS_MODEL_PATH:?Set MBS_MODEL_PATH}"
: "${MBS_MODEL_ID:?Set MBS_MODEL_ID}"
: "${MBS_MODEL_KEY:?Set MBS_MODEL_KEY}"

module load bsc mkl intel python/3.12.1 cuda/12.3 >/dev/null 2>&1 || true
source /gpfs/scratch/ehpc714/lk_env/bin/activate

WORK=/gpfs/scratch/ehpc714/mbs_public_release
OUT=/gpfs/scratch/ehpc714/mbs_results/hard_agent_routing/${MBS_MODEL_KEY}
mkdir -p "$OUT" /gpfs/scratch/ehpc714/mbs_logs
cd "$WORK"

python scripts/collect_hf_local_responses.py \
  --model-path "$MBS_MODEL_PATH" \
  --model-id "$MBS_MODEL_ID" \
  --schema examples/hard_agent_routing/schema.json \
  --cases examples/hard_agent_routing/cases.jsonl \
  --mode json_mode \
  --max-new-tokens 256 \
  --temperature 0 \
  --limit 40 \
  --out "$OUT/${MBS_MODEL_KEY}_json_mode.responses.jsonl"

python -m mbs.cli adapt-responses \
  --schema examples/hard_agent_routing/schema.json \
  --cases examples/hard_agent_routing/cases.jsonl \
  --responses "$OUT/${MBS_MODEL_KEY}_json_mode.responses.jsonl" \
  --model "$MBS_MODEL_ID" \
  --decoding-mode hf_local_json_mode \
  --out "$OUT/${MBS_MODEL_KEY}_json_mode.mbs.json"

python -m mbs.cli report \
  --results "$OUT/${MBS_MODEL_KEY}_json_mode.mbs.json" \
  --require-traces \
  --summary-only \
  --out "$OUT/${MBS_MODEL_KEY}_json_mode.report.md"

cat "$OUT/${MBS_MODEL_KEY}_json_mode.report.md"
