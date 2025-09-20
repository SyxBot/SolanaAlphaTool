import json
import os
import urllib.request

def send_to_eliza(payload: dict, rules: dict) -> None:
    url = os.getenv("ELIZA_INGEST_URL") or rules.get("ELIZA_INGEST_URL")
    if not url:
        print("[BRIDGE] ELIZA_INGEST_URL not set; skipping send")
        return
    # Forward v1.3 fields if present; remain backward-compatible
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[BRIDGE] → Eliza v1.3 {{mint:{payload.get('mint')}, pre_score_A:{payload.get('pre_score_A')}}} status={resp.status}")
    except Exception as e:
        print(f"[BRIDGE] error sending to Eliza: {e}")