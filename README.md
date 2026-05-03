# VYRAL ComfyUI Workflow Library (v1)

This repository contains the **VYRAL Kitchen Visual Engine** workflow layer for ComfyUI, designed for a FastAPI backend that dynamically injects prompt/runtime settings and executes jobs on hosted GPU instances (e.g., vast.ai).

## Goals
- Provide a stable library of API-ready ComfyUI workflows per content pillar.
- Use a named-node contract (`VYRAL_*`) to prevent backend breakage when node IDs change.
- Support multi-model routing (SDXL vs Flux) and social-media trajectories.
- Include validation and provisioning tools for production setup.
