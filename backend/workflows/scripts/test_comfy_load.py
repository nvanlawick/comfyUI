#!/usr/bin/env python3
import json, os, urllib.request
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://localhost:8188")
BATCH = int(os.getenv("STRESS_BATCH", "4"))
payload = {"prompt":{"1":{"class_type":"EmptyLatentImage","inputs":{"width":512,"height":512,"batch_size":1}},"2":{"class_type":"SaveImage","inputs":{"images":["1",0],"filename_prefix":"stress_test"}}}}
for i in range(BATCH):
    req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(i, resp.status)
