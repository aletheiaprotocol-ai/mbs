#!/usr/bin/env bash
set -euo pipefail

echo "HOST=$(hostname)"
echo "DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if command -v module >/dev/null 2>&1; then
  module load bsc mkl intel python/3.12.1 cuda/12.3 >/dev/null 2>&1 || true
fi

if [ -f /gpfs/scratch/ehpc714/lk_env/bin/activate ]; then
  # shellcheck disable=SC1091
  source /gpfs/scratch/ehpc714/lk_env/bin/activate
  echo "VENV=/gpfs/scratch/ehpc714/lk_env"
else
  echo "VENV_MISSING=/gpfs/scratch/ehpc714/lk_env"
fi

python - <<'PY'
import importlib.util
import os
import shutil
import sys
print(f"PYTHON={sys.executable}")
for mod in ["torch", "transformers", "vllm", "fastapi", "uvicorn"]:
    spec = importlib.util.find_spec(mod)
    print(f"PYMOD_{mod.upper()}={bool(spec)}")
print(f"VLLM_BIN={shutil.which('vllm') or ''}")
for path in ["/gpfs/scratch/ehpc714/models", "/gpfs/scratch/ehpc714"]:
    print(f"LIST={path}")
    try:
        for name in sorted(os.listdir(path))[:50]:
            print(name)
    except Exception as exc:
        print(f"ERR={type(exc).__name__}:{exc}")
PY
