#!/usr/bin/env bash
set -euo pipefail

cd /gpfs/scratch/ehpc714/mbs_public_release
mkdir -p /gpfs/scratch/ehpc714/mbs_logs /gpfs/scratch/ehpc714/mbs_results/hard_agent_routing

submit_model() {
  local job_name="$1"
  local model_path="$2"
  local model_id="$3"
  local model_key="$4"
  if [ ! -d "$model_path" ]; then
    echo "SKIP missing model path: $model_path"
    return 0
  fi
  sbatch \
    --job-name="$job_name" \
    --export=ALL,MBS_MODEL_PATH="$model_path",MBS_MODEL_ID="$model_id",MBS_MODEL_KEY="$model_key" \
    scripts/mn5_mbs_hf_model.slurm
}

submit_model mbs_qwen7b /gpfs/scratch/ehpc714/models/Qwen2.5-7B-Instruct Qwen2.5-7B-Instruct qwen25_7b
submit_model mbs_qwen14b /gpfs/scratch/ehpc714/models/Qwen2.5-14B-Instruct Qwen2.5-14B-Instruct qwen25_14b
submit_model mbs_llama8b /gpfs/scratch/ehpc714/models/Llama-3.1-8B-Instruct Llama-3.1-8B-Instruct llama31_8b
submit_model mbs_mistral7b /gpfs/scratch/ehpc714/models/Mistral-7B-Instruct-v0.3 Mistral-7B-Instruct-v0.3 mistral7b_v03

squeue -u bme344410
