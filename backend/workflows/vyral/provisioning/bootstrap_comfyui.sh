#!/usr/bin/env bash
set -euo pipefail

# =========================
# Config
# =========================
COMFY_ROOT="${COMFY_ROOT:-/workspace/ComfyUI}"
PROV_DIR="${PROV_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
LOCK_NODES="${LOCK_NODES:-$PROV_DIR/custom_nodes_repos.lock}"
LOCK_MODELS="${LOCK_MODELS:-$PROV_DIR/models_manifest.lock.json}"
CACHE_DIR="${CACHE_DIR:-/workspace/model-cache}"
ONLY_BASELINE="${ONLY_BASELINE:-1}"   # 1 = skip candidate models
NO_PULL="${NO_PULL:-0}"               # 1 = do not pull existing repos

CUSTOM_NODES_DIR="$COMFY_ROOT/custom_nodes"
mkdir -p "$CUSTOM_NODES_DIR" "$CACHE_DIR"

echo "[VYRAL] COMFY_ROOT=$COMFY_ROOT"
echo "[VYRAL] PROV_DIR=$PROV_DIR"
echo "[VYRAL] CACHE_DIR=$CACHE_DIR"

# =========================
# Helpers
# =========================
need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1"; exit 1; }
}

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
	sha256sum "$1" | awk '{print $1}'
  else
	shasum -a 256 "$1" | awk '{print $1}'
  fi
}

clone_or_update_repo() {
  local url="$1"
  local ref="$2"
  local name
  name="$(basename "$url" .git)"
  local dst="$CUSTOM_NODES_DIR/$name"

  if [[ -d "$dst/.git" ]]; then
	echo "[nodes] exists: $name"
	if [[ "$NO_PULL" == "0" ]]; then
	  git -C "$dst" fetch --all --tags
	  git -C "$dst" checkout "$ref"
	  git -C "$dst" pull --ff-only || true
	fi
  else
	echo "[nodes] clone: $url -> $dst"
	git clone "$url" "$dst"
	git -C "$dst" checkout "$ref"
  fi
}

download_model() {
  local name="$1"
  local tier="$2"
  local required="$3"
  local dest_dir="$4"
  local url="$5"
  local sha="$6"

  if [[ "$ONLY_BASELINE" == "1" && "$tier" == "candidate" ]]; then
	echo "[models] skip candidate: $name"
	return 0
  fi

  local target_dir="$COMFY_ROOT/$dest_dir"
  local cache_path="$CACHE_DIR/$name"
  local target_path="$target_dir/$name"
  mkdir -p "$target_dir"

  if [[ -f "$target_path" ]]; then
	if [[ "$sha" != "REPLACE_SHA256" && -n "$sha" ]]; then
	  local have
	  have="$(sha256_file "$target_path")"
	  if [[ "$have" == "$sha" ]]; then
		echo "[models] ok existing: $name"
		return 0
	  else
		echo "[models] checksum mismatch existing, re-download: $name"
		rm -f "$target_path"
	  fi
	else
	  echo "[models] exists (no checksum pin): $name"
	  return 0
	fi
  fi

  if [[ -f "$cache_path" ]]; then
	echo "[models] from cache: $name"
  else
	if [[ "$url" == REPLACE_WITH_* || "$url" == "" ]]; then
	  if [[ "$required" == "true" ]]; then
		echo "[models] ERROR missing URL for required model: $name"
		exit 1
	  else
		echo "[models] skip optional without URL: $name"
		return 0
	  fi
	fi
	echo "[models] download: $name"
	if command -v aria2c >/dev/null 2>&1; then
	  aria2c -x 8 -s 8 -k 1M -d "$CACHE_DIR" -o "$name" "$url"
	else
	  curl -L --fail --retry 3 --retry-delay 2 -o "$cache_path" "$url"
	fi
  fi

  if [[ "$sha" != "REPLACE_SHA256" && -n "$sha" ]]; then
	local got
	got="$(sha256_file "$cache_path")"
	if [[ "$got" != "$sha" ]]; then
	  echo "[models] ERROR checksum mismatch for $name"
	  echo " expected=$sha"
	  echo " got=$got"
	  exit 1
	fi
  fi

  cp -f "$cache_path" "$target_path"
  echo "[models] installed: $target_path"
}

# =========================
# Prechecks
# =========================
need_cmd git
need_cmd python3
need_cmd curl

# =========================
# Install/update custom nodes
# =========================
echo "== Install custom nodes =="
while IFS= read -r line; do
  [[ -z "$line" || "$line" =~ ^# ]] && continue
  repo="${line%@*}"
  ref="${line##*@}"
  clone_or_update_repo "$repo" "$ref"
done < "$LOCK_NODES"

# =========================
# Download/install models
# =========================
echo "== Install models =="
python3 - "$LOCK_MODELS" <<'PY' | while IFS=$'\t' read -r name tier required dest_dir url sha; do
import json, sys
p = sys.argv[1]
data = json.load(open(p, "r", encoding="utf-8"))
for m in data["models"]:
	print("\t".join([
		m["name"],
		m.get("tier", "baseline"),
		str(m.get("required", True)).lower(),
		m["dest_dir"],
		m.get("url", ""),
		m.get("sha256", "")
	]))
PY
  download_model "$name" "$tier" "$required" "$dest_dir" "$url" "$sha"
done

# =========================
# Verify + optional restart hook
# =========================
echo "== Verify install =="
python3 "$PROV_DIR/verify_install.py" \
  --comfy-root "$COMFY_ROOT" \
  --nodes-lock "$LOCK_NODES" \
  --models-lock "$LOCK_MODELS" \
  --only-baseline "$ONLY_BASELINE"

echo "[VYRAL] bootstrap completed successfully"