import math
import string
from typing import List, Tuple, Union, Dict

ASCII = set(string.printable)

def _is_ascii_2_16(s: str) -> bool:
    if not isinstance(s, str): return False
    if not (2 <= len(s) <= 16): return False
    return all(ch in ASCII and ch != "\x0b" and ch != "\x0c" for ch in s)

# returns: (survivors, dropped_reasons)
def security_gate(events: List[dict], rules: dict) -> Tuple[List[dict], Union[list,dict]]:
    blacklist = set(rules.get("name_blacklist", []))
    cooldown_min = int(rules.get("cooldown_minutes", 0))
    # simple in-proc cooldown map; callers typically run long-lived process
    # NOTE: replace with external store if you need cross-process sharing
    if not hasattr(security_gate, "_cooldown"):
        security_gate._cooldown = {}  # mint -> expiry_ts

    survivors, dropped = [], []

    for ev in events:
        mint = ev.get("mint")
        meta = ev.get("v1_1", {}).get("meta", {})
        mint_auth = ev.get("mintAuthority") or meta.get("mintAuthority")
        freeze_auth = ev.get("freezeAuthority") or meta.get("freezeAuthority")

        name = ev.get("name") or ev.get("symbol") or meta.get("name") or meta.get("symbol")

        reasons = []

        # Authority sanity: must be burned/null (represented here as None/falsey)
        if mint_auth or freeze_auth:
            reasons.append("authority_present")

        # Hygiene
        if name and (not _is_ascii_2_16(name) or any(term.lower() in name.lower() for term in blacklist)):
            reasons.append("name_invalid")

        # Simple numeric sanity for a couple of known numeric fields
        for k in ("price", "liq_usd", "vol_5m_usd"):
            v = ev.get(k)
            if v is not None and (not isinstance(v, (int,float)) or not math.isfinite(float(v))):
                reasons.append(f"bad_{k}")

        # Cooldown
        if cooldown_min > 0 and mint:
            from time import time as _now
            now = int(_now())
            exp = security_gate._cooldown.get(mint, 0)
            if exp and exp > now:
                reasons.append("cooldown")
            else:
                security_gate._cooldown[mint] = now + cooldown_min * 60

        if reasons:
            dropped.append({"mint": mint, "reasons": reasons})
        else:
            survivors.append(ev)

    return survivors, dropped