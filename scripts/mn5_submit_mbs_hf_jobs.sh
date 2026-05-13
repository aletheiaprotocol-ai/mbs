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
submit_model mbs_qwen3b /gpfs/scratch/ehpc714/models/Qwen2.5-3B-Instruct Qwen2.5-3B-Instruct qwen25_3b
submit_model mbs_qwen32b /gpfs/scratch/ehpc714/models/Qwen2.5-32B-Instruct Qwen2.5-32B-Instruct qwen25_32b
submit_model mbs_phi35mini /gpfs/scratch/ehpc714/models/Phi-3.5-mini-instruct Phi-3.5-mini-instruct phi35_mini
submit_model mbs_gemma2b /gpfs/scratch/ehpc714/models/Gemma-2-2B-it Gemma-2-2B-it gemma2_2b_it
submit_model mbs_gemma9b /gpfs/scratch/ehpc714/models/Gemma-2-9b-it Gemma-2-9b-it gemma2_9b_it
submit_model mbs_stablelm12b /gpfs/scratch/ehpc714/models/StableLM-2-12b-chat StableLM-2-12b-chat stablelm2_12b
submit_model mbs_tinyllama /gpfs/scratch/ehpc714/models/TinyLlama-1.1B-Chat-v1.0 TinyLlama-1.1B-Chat-v1.0 tinyllama11b

squeue -u bme344410
