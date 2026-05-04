#!/usr/bin/env bash
set -euo pipefail

# Quick updater for running instances
# Keeps same lockfiles and re-runs idempotent bootstrap.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMFY_ROOT="${COMFY_ROOT:-/workspace/ComfyUI}"
ONLY_BASELINE="${ONLY_BASELINE:-1}"

bash "$SCRIPT_DIR/bootstrap_comfyui.sh" \
  COMFY_ROOT="$COMFY_ROOT" \
  ONLY_BASELINE="$ONLY_BASELINE"

echo "[VYRAL] update_all done"