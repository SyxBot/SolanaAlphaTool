import time
from typing import Tuple, Dict
from os import getenv

# In-memory cooldown tracker
_last_seen_by_mint = {}

def filter_event(ev: dict, cfg: dict) -> Tuple[bool, str]:
    """
    Filter an event based on configuration thresholds.

    :param ev: The event to filter.
    :param cfg: Configuration dictionary.
    :return: Tuple (accepted: bool, reason: str).
    """
    now = int(time.time())

    # Pump.fun only
    if cfg.get("PF_PUMPFUN_ONLY", "false").lower() == "true":
        if not (ev.get("mint", "").endswith("pump") or ev.get("source", "") == "pump.fun"):
            return False, "not_pumpfun"

    # Age threshold
    max_age_min = int(cfg.get("PF_MAX_AGE_MIN", 3))
    create_ts = ev.get("create_ts", 0)
    if now - create_ts > max_age_min * 60:
        return False, "age_exceeded"

    # Liquidity threshold
    min_liq_usd = float(cfg.get("PF_MIN_LIQ_USD", 2000))
    if ev.get("liq_usd", 0) < min_liq_usd:
        return False, "low_liquidity"

    # Holders threshold
    min_holders = int(cfg.get("PF_MIN_HOLDERS", 50))
    if ev.get("holders", 0) < min_holders:
        return False, "low_holders"

    # Volume threshold
    min_volume_usd_h1 = float(cfg.get("PF_MIN_VOLUME_USD_H1", 5000))
    if ev.get("vol_usd_h1", 0) < min_volume_usd_h1:
        return False, "low_volume"

    # Cooldown
    cooldown_sec = int(cfg.get("PF_COOLDOWN_SEC", 900))
    mint = ev.get("mint")
    if mint in _last_seen_by_mint and now - _last_seen_by_mint[mint] < cooldown_sec:
        return False, "cooldown"
    _last_seen_by_mint[mint] = now

    # Blocklists
    blocklist_creators = set(cfg.get("PF_BLOCKLIST_CREATORS", "").split(","))
    blocklist_mints = set(cfg.get("PF_BLOCKLIST_MINTS", "").split(","))
    if ev.get("creator") in blocklist_creators:
        return False, "creator_blocked"
    if ev.get("mint") in blocklist_mints:
        return False, "mint_blocked"

    return True, ""
