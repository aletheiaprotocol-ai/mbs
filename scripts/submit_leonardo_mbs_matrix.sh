#!/usr/bin/env bash
set -euo pipefail

REMOTE_ROOT="${REMOTE_ROOT:-$HOME/mbs_hpc_matrix}"
OUT_ROOT="${OUT_ROOT:-/leonardo_scratch/large/userexternal/asaket00/mbs_hpc_matrix/results}"
ACCOUNT="${ACCOUNT:-AIFAC_F02_151}"
PARTITION="${PARTITION:-boost_usr_prod}"
QOS="${QOS:-boost_qos_dbg}"
HF_HOME_DIR="${HF_HOME_DIR:-/leonardo_scratch/large/userexternal/asaket00/hf_cache}"
SUITE="${1:-smoke}"
JOB_LABEL="${JOB_LABEL:-$SUITE}"
TIME_LIMIT="${TIME_LIMIT:-02:00:00}"
GPUS="${GPUS:-1}"
CPUS="${CPUS:-8}"
MEM="${MEM:-120G}"
PYTHON_BIN="${PYTHON_BIN:-python}"
INSTALL_DEPS="${INSTALL_DEPS:-0}"
LIMIT="${LIMIT:-25}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-220}"
MODELS="${MODELS:-}"
QUANT_ARGS="${QUANT_ARGS:-}"
PROMPT_STYLE="${PROMPT_STYLE:-nested}"

mkdir -p "$REMOTE_ROOT/logs" "$OUT_ROOT"
cd "$REMOTE_ROOT"

MODEL_ARGS=""
if [ -n "$MODELS" ]; then
    MODEL_ARGS="--models $MODELS"
fi

cat > "run_${JOB_LABEL}.slurm" <<SLURM
#!/usr/bin/env bash
#SBATCH -A ${ACCOUNT}
#SBATCH -p ${PARTITION}
#SBATCH --qos=${QOS}
#SBATCH --job-name=mbs_${JOB_LABEL}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=${CPUS}
#SBATCH --gres=gpu:${GPUS}
#SBATCH --mem=${MEM}
#SBATCH --time=${TIME_LIMIT}
#SBATCH --output=${REMOTE_ROOT}/logs/mbs_${JOB_LABEL}_%j.out
#SBATCH --error=${REMOTE_ROOT}/logs/mbs_${JOB_LABEL}_%j.err

set -euo pipefail
export PYTHONUNBUFFERED=1
export HF_HOME="${HF_HOME_DIR}"
export TRANSFORMERS_CACHE="\${HF_HOME}/hub"
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export ALETHEIA_LOCAL_FILES_ONLY=1

module load python/3.11 2>/dev/null || true
module load cuda 2>/dev/null || true

if [ "${INSTALL_DEPS}" = "1" ]; then
${PYTHON_BIN} - <<'PY'
import importlib.util, subprocess, sys
missing = [m for m in ['torch','transformers','huggingface_hub','accelerate'] if importlib.util.find_spec(m) is None]
if missing:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', 'torch', 'transformers', 'accelerate', 'huggingface_hub', 'safetensors'])
PY
fi

${PYTHON_BIN} ${REMOTE_ROOT}/leonardo_mbs_hf_matrix.py --suite ${SUITE} ${MODEL_ARGS} --out-dir ${OUT_ROOT}/${JOB_LABEL}_\${SLURM_JOB_ID} --cache-dir ${HF_HOME_DIR} --limit ${LIMIT} --max-new-tokens ${MAX_NEW_TOKENS} --dtype auto --device-map auto --local-files-only --prompt-style ${PROMPT_STYLE} ${QUANT_ARGS}
SLURM

sbatch "run_${JOB_LABEL}.slurm"