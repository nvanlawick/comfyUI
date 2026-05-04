#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys


def parse_nodes_lock(path: Path):
	repos = []
	for raw in path.read_text(encoding="utf-8").splitlines():
		line = raw.strip()
		if not line or line.startswith("#"):
			continue
		repo = line.split("@")[0]
		name = repo.rstrip("/").split("/")[-1].replace(".git", "")
		repos.append(name)
	return repos


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--comfy-root", required=True)
	ap.add_argument("--nodes-lock", required=True)
	ap.add_argument("--models-lock", required=True)
	ap.add_argument("--only-baseline", default="1")
	args = ap.parse_args()

	comfy_root = Path(args.comfy_root)
	nodes_lock = Path(args.nodes_lock)
	models_lock = Path(args.models_lock)
	only_baseline = args.only_baseline == "1"

	errors = []

	# verify nodes
	nodes = parse_nodes_lock(nodes_lock)
	for node in nodes:
	  p = comfy_root / "custom_nodes" / node
	  if not p.exists():
		  errors.append(f"missing custom node repo dir: {p}")

	# verify models
	manifest = json.loads(models_lock.read_text(encoding="utf-8"))
	for m in manifest["models"]:
		tier = m.get("tier", "baseline")
		required = bool(m.get("required", True))
		if only_baseline and tier == "candidate":
			continue
		if not required:
			continue
		p = comfy_root / m["dest_dir"] / m["name"]
		if not p.exists():
			errors.append(f"missing required model: {p}")

	if errors:
		print("VERIFY FAILED:")
		for e in errors:
			print(f"- {e}")
		sys.exit(2)

	print("VERIFY OK: all required nodes/models found")


if __name__ == "__main__":
	main()