#!/usr/bin/env bash
set -euo pipefail

cat > /tmp/mbs_check_env.py <<'PY'
import importlib.util
import sys

print('PYTHON', sys.executable, sys.version.split()[0])
for module in ['torch', 'transformers', 'accelerate', 'huggingface_hub', 'safetensors']:
    print(module, importlib.util.find_spec(module) is not None)
try:
    import torch
    print('torch_version', torch.__version__)
    print('cuda_available', torch.cuda.is_available())
except Exception as exc:
    print('torch_error', type(exc).__name__, str(exc)[:240])
PY

echo CANDIDATE_PYTHONS
for python_bin in \
    "$HOME/lk_env/bin/python" \
    "$HOME/.venv/bin/python" \
    "$HOME/venv/bin/python" \
    "$HOME/mbs_env/bin/python" \
    "$HOME"/*env*/bin/python \
    /leonardo_work/AIFAC_F02_151/*/bin/python \
    /leonardo_scratch/large/userexternal/asaket00/*/bin/python \
    /usr/bin/python3 \
    python3 \
    python
do
    if command -v "$python_bin" >/dev/null 2>&1 || [ -x "$python_bin" ]; then
        resolved=$(command -v "$python_bin" 2>/dev/null || printf '%s' "$python_bin")
        [ -x "$resolved" ] || continue
        echo "===${resolved}==="
        "$resolved" /tmp/mbs_check_env.py 2>&1 | head -40 || true
    fi
done

echo MODULES_AVAILABLE
module avail 2>&1 | grep -Ei 'python|cuda|pytorch|torch|transformers' | head -80 || true
