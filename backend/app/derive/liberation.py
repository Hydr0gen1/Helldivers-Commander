from __future__ import annotations


def liberation_pct(health: int, max_health: int) -> float:
    return max(0.0, min(100.0, (1.0 - health / max(max_health, 1)) * 100.0))
