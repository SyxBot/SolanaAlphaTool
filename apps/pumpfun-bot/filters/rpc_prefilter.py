import time
from typing import List, Tuple, Dict

# events: list of dicts with at least {"mint","slot" or "ts","meta":{...}}
# returns: (survivors, drop_stats)
def rpc_prefilter(events: List[dict], rules: dict) -> Tuple[List[dict], Dict[str,int]]:
    allowed_decimals = set(rules.get("allowed_decimals", [6,8,9]))
    max_age_sec = int(rules.get("max_age_minutes", 3)) * 60
    now = int(time.time())

    survivors = []
    drops = {"weird_decimals": 0, "age_out_of_range": 0}

    for ev in events:
        meta = ev.get("meta", {})
        decimals = meta.get("decimals")
        # Prefer explicit ts if present; otherwise fall back to ev.ts or 0
        ts = ev.get("ts") or meta.get("ts") or 0
        age_sec = max(0, now - int(ts)) if ts else 0

        # annotate for downstream
        ev.setdefault("v1_1", {})
        ev["v1_1"]["meta"] = {"decimals": decimals, "age_sec": age_sec, "flags": {}}

        ok = True
        if decimals not in allowed_decimals:
            drops["weird_decimals"] += 1
            ok = False
        if age_sec > max_age_sec:
            drops["age_out_of_range"] += 1
            ok = False

        if ok:
            survivors.append(ev)

    return survivors, drops