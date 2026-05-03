#!/usr/bin/env python3
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "backend/workflows/vyral/manifests/workflow_manifest.json"

manifest = json.loads(MANIFEST.read_text())
required = set(manifest["required_titles"])

for tpl in manifest["templates"]:
    wf = json.loads((REPO_ROOT / tpl["file"]).read_text())
    titles = {n.get("_meta", {}).get("title") for n in wf.values()}
    missing = required - titles
    if missing:
        raise SystemExit(f"FAIL {tpl['file']} missing {sorted(missing)}")
    if tpl["model_mode"] == "sdxl" and "VYRAL_NEGATIVE" not in titles:
        raise SystemExit(f"FAIL {tpl['file']} missing VYRAL_NEGATIVE")

print("OK: workflow titles and trajectories validated")
