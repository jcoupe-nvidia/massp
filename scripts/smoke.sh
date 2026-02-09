#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-/home/nvidia/cuopt_venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python"
fi

"${PYTHON_BIN}" -m src.solve \
  --config cuopt-config.yaml \
  --instance data/toy \
  --mode both \
  --outdir out

echo "Smoke test completed."
