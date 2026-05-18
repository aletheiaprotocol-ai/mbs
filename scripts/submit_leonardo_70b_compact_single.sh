#!/usr/bin/env bash
set -euo pipefail

# Submit a fresh-process compact-prompt retry for the cached 70B model.
# This avoids carrying GPU state across prior sequential Qwen/Yi loads.

cd "${HOME}/mbs_hpc_matrix"
export PYTHON_BIN="/leonardo_work/AIFAC_F02_151/mbs_env/bin/python"
export INSTALL_DEPS=0
export ACCOUNT="AIFAC_F02_151"
export PARTITION="boost_usr_prod"
export QOS="boost_qos_dbg"
export TIME_LIMIT="00:30:00"
export GPUS=1
export CPUS=16
export MEM="180G"
export JOB_LABEL="compact_70b_single_01"
export LIMIT=8
export MAX_NEW_TOKENS=220
export PROMPT_STYLE="compact"
export MODELS="NousResearch/Meta-Llama-3.1-70B-Instruct"
export QUANT_ARGS="--load-in-4bit"
exec bash ./submit_leonardo_mbs_matrix.sh large