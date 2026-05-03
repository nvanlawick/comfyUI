import copy
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "backend/workflows/vyral/manifests/workflow_manifest.json"

@dataclass
class WorkflowRequest:
    pillar: str
    trajectory: str
    prompt: str
    seed: int = -1
    model_mode: str = "auto"
    negative_prompt: str = ""
    guidance_scale: float = 4.5
    steps: int = 20
    batch_size: int = 1
    overlay_side: str = "left"

class WorkflowService:
    def __init__(self, manifest_path: Path = MANIFEST_PATH):
        self.manifest = json.loads(manifest_path.read_text())
        self.template_map = {(t["pillar"], t["model_mode"]): t["file"] for t in self.manifest["templates"]}
        self._validate_manifest()

    def _validate_manifest(self) -> None:
        required = set(self.manifest["required_titles"])
        for tpl in self.manifest["templates"]:
            data = json.loads((ROOT / tpl["file"]).read_text())
            titles = {n.get("_meta", {}).get("title") for n in data.values()}
            missing = required - titles
            if missing:
                raise RuntimeError(f"Template {tpl['file']} missing titles: {sorted(missing)}")
            if tpl["model_mode"] == "sdxl" and "VYRAL_NEGATIVE" not in titles:
                raise RuntimeError(f"Template {tpl['file']} missing SDXL title: VYRAL_NEGATIVE")

    def _resolve_seed(self, seed: int) -> int:
        return random.randint(0, 2**32 - 1) if seed == -1 else seed

    @staticmethod
    def _find_node_id(workflow: Dict[str, Any], title: str) -> str:
        for node_id, node in workflow.items():
            if node.get("_meta", {}).get("title") == title:
                return node_id
        raise RuntimeError(f"Missing required node title: {title}")

    def build_prompt(self, req: WorkflowRequest) -> Dict[str, Any]:
        req.steps = max(1, min(req.steps, 50))
        req.batch_size = max(1, min(req.batch_size, 4))
        mode = choose_model_mode(req.model_mode, req.pillar, self.manifest)

        workflow = json.loads((ROOT / self.template_map[(req.pillar, mode)]).read_text())
        workflow = copy.deepcopy(workflow)

        width, height = self.manifest["trajectories"][mode][req.trajectory]
        seed_value = self._resolve_seed(req.seed)

        workflow[self._find_node_id(workflow, "VYRAL_POSITIVE")]["inputs"]["text"] = req.prompt
        workflow[self._find_node_id(workflow, "VYRAL_LATENT")]["inputs"].update({"width": width, "height": height, "batch_size": req.batch_size})
        workflow[self._find_node_id(workflow, "VYRAL_SEED")]["inputs"]["value"] = seed_value
        workflow[self._find_node_id(workflow, "VYRAL_SAVE")]["inputs"]["filename_prefix"] = f"/workspace/outputs/vyral/{req.pillar}_{req.trajectory}"

        if mode == "sdxl":
            workflow[self._find_node_id(workflow, "VYRAL_NEGATIVE")]["inputs"]["text"] = req.negative_prompt

        if req.pillar == "campaign_asset":
            for node in workflow.values():
                if node.get("class_type") == "RegionalConditioning":
                    node["inputs"]["overlay_side"] = req.overlay_side

        return {"prompt": workflow, "metadata": {"seed_used": seed_value, "model_used": mode, "workflow_used": self.template_map[(req.pillar, mode)]}}

def choose_model_mode(model_mode: str, pillar: str, manifest: Dict[str, Any]) -> str:
    if model_mode != "auto":
        return model_mode
    return manifest["default_model_by_pillar"][pillar]
